"""Synthetic weekly inference and same-horizon composition; no live artifacts."""

from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import numpy as np
import pytest
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.forecasting import weekly_inference as module, weekly_portfolio as portfolio_module
from app.forecasting.evaluation import ForecastTargetType
from app.forecasting.features import FEATURE_NAMES
from app.forecasting.finalization import ForecastArtifactModel
from app.forecasting.inference_errors import (
    ForecastArtifactInvalidError, ForecastDataStaleError, ForecastHistoryInsufficientError,
    ForecastMarketDataUnavailableError, ForecastPredictionError,
)
from app.forecasting.portfolio import InvalidForecastPortfolioError, compose_volatility, historical_correlation, aligned_log_returns
from app.forecasting.weekly_registry import LoadedWeeklyArtifact, WEEKLY_VERSION
from app.schemas.weekly_forecasting import WeeklyAssetOutlookResponse, WeeklyPortfolioOutlookResponse
from app.services.portfolio_baseline_resolver import ResolvedPortfolioWeight
from app.services.weekly_forecasting_response_mapper import map_weekly_asset_outlook, map_weekly_portfolio_outlook


CUTOFF = date(2026,9,17)
TODAY = datetime.now(UTC).date()


def asset(symbol="AAPL", horizon=7, origin=TODAY, point=.1, vol=.2):
    return module.WeeklyAssetForecast(symbol, origin, horizon, point, -.2, .4, vol, 0., .5, .8,
        "historical_average", "historical_average", WEEKLY_VERSION, "forecast-features-v1",
        f"forecast-targets-{horizon}d-v1", origin, (TODAY-origin).days,
        ("final_interval_coverage_below_nominal",), ())


def rows(symbol="AAPL", last=CUTOFF, count=280):
    return [SimpleNamespace(symbol=symbol, date=last-timedelta(days=count-1-i),
            adjusted_close=Decimal(str(100+i)), source="synthetic", volume=None) for i in range(count)]


def selected_registry():
    registry = MagicMock()
    registry.artifact_version = WEEKLY_VERSION
    def get(symbol, target, horizon):
        model = ForecastArtifactModel("historical_average", target, "historical_average",
            constant_prediction=horizon / 1000 if target is ForecastTargetType.RETURN else -.01)
        return LoadedWeeklyArtifact(model, CUTOFF, -.1, .2, ("final_interval_coverage_below_nominal",))
    registry.get.side_effect = get
    return registry


def inference(prices=None):
    result = module.WeeklyForecastInferenceService(MagicMock(), registry=selected_registry())
    result._market_data = MagicMock()
    result._market_data.get_range.return_value = rows() if prices is None else prices
    return result


@pytest.mark.parametrize("horizon", [7,14,21])
def test_actual_horizon_routing_features_clipping_and_public_mapping(horizon):
    service = inference()
    result = service.predict("AAPL", horizon_days=horizon, reference_date=CUTOFF)
    assert result.expected_return == horizon / 1000  # Not scaled 30-day output.
    assert result.forecast_realized_volatility == result.volatility_interval_lower == 0
    assert result.volatility_interval_upper == .2
    assert result.return_interval_lower == pytest.approx(horizon / 1000 - .1)
    assert result.target_version == f"forecast-targets-{horizon}d-v1"
    assert [call.args for call in service._registry.get.call_args_list] == [
        ("AAPL", ForecastTargetType.RETURN, horizon), ("AAPL", ForecastTargetType.VOLATILITY, horizon)]
    public = map_weekly_asset_outlook(result).model_dump()
    assert public["experimental"] is True and public["predictive_quality_approved"] is False
    assert public["return_warning_codes"] == ["final_interval_coverage_below_nominal"]
    assert "expected_return_30d" not in public
    for key in ("model_path", "calibration_residual_q10", "directional_accuracy", "feature_version"):
        assert key not in public
    service._market_data.get_range.assert_called_with(("AAPL",), date.min, CUTOFF)


@pytest.mark.parametrize("age", [0,4,5])
def test_freshness_before_artifact_access(age):
    service = inference()
    if age > 4:
        with pytest.raises(ForecastDataStaleError):
            service.predict("AAPL", horizon_days=14, reference_date=CUTOFF+timedelta(days=age))
        service._registry.get.assert_not_called()
    else:
        assert service.predict("AAPL", horizon_days=14,
            reference_date=CUTOFF+timedelta(days=age)).market_data_age_days == age


@pytest.mark.parametrize("prices", [[], rows(count=30)])
def test_insufficient_history(prices):
    with pytest.raises(ForecastHistoryInsufficientError):
        inference(prices).predict("AAPL", horizon_days=7, reference_date=CUTOFF)


def test_bad_horizon_precedes_market_or_artifact_access():
    service = inference()
    with pytest.raises(ForecastArtifactInvalidError):
        service.predict("AAPL", horizon_days=30, reference_date=CUTOFF)
    service._market_data.get_range.assert_not_called()
    service._registry.get.assert_not_called()


def test_database_failure_controlled():
    service = inference()
    service._market_data.get_range.side_effect = SQLAlchemyError("private details")
    with pytest.raises(ForecastMarketDataUnavailableError):
        service.predict("AAPL", horizon_days=7, reference_date=CUTOFF)


def test_new_request_reads_new_observations_not_cached_forecast():
    service = inference()
    first = service.predict("AAPL", horizon_days=7, reference_date=CUTOFF)
    tomorrow = CUTOFF+timedelta(days=1)
    service._market_data.get_range.return_value = rows(last=tomorrow)
    second = service.predict("AAPL", horizon_days=7, reference_date=tomorrow)
    assert first.origin_date == CUTOFF and second.origin_date == tomorrow
    assert service._market_data.get_range.call_count == 2


def test_arima_observed_steps_and_current_features_not_calendar_day_steps():
    service = inference(rows(last=CUTOFF) + [SimpleNamespace(symbol="AAPL", date=CUTOFF+timedelta(days=4),
        adjusted_close=Decimal(500), source="synthetic", volume=None)])
    model = MagicMock()
    model.model_family = "arima"
    model.candidate_id = "arima_1_0_1_v1"
    model.predict.return_value = (.01, .02)
    baseline_get = service._registry.get.side_effect
    service._registry.get.side_effect = lambda symbol, target, horizon: (
        LoadedWeeklyArtifact(model, CUTOFF, -.1, .2, ()) if target is ForecastTargetType.RETURN
        else baseline_get(symbol, target, horizon))
    result = service.predict("AAPL", horizon_days=21, reference_date=CUTOFF+timedelta(days=4))
    assert result.expected_return == .02
    assert model.predict.call_args.kwargs["steps"] == 2
    assert len(model.predict.call_args.kwargs["feature_matrix"][0]) == len(FEATURE_NAMES)


@pytest.mark.parametrize("prediction", [(float("nan"),), (), (float("inf"),)])
def test_bad_prediction_never_falls_back(prediction):
    service = inference()
    model = MagicMock(model_family="linear_regression", candidate_id="linear_regression_v1")
    model.predict.return_value = prediction
    service._registry.get.return_value = LoadedWeeklyArtifact(model, CUTOFF, -.1, .2, ())
    service._registry.get.side_effect = None
    with pytest.raises(ForecastPredictionError):
        service.predict("AAPL", horizon_days=14, reference_date=CUTOFF)


def portfolio_prices():
    return [SimpleNamespace(symbol=symbol, date=TODAY-timedelta(days=319-i),
        adjusted_close=Decimal(str(np.exp(4+.001*i+.02*np.sin(i*(.37+j*.21))))),
        source="synthetic", volume=None)
        for j, symbol in enumerate(("AAPL","MSFT")) for i in range(320)]


def portfolio_service(kind="current"):
    instance = portfolio_module.WeeklyPortfolioForecastService(MagicMock())
    instance._baseline = MagicMock()
    instance._baseline.resolve.return_value = SimpleNamespace(baseline_kind=SimpleNamespace(value=kind),
        resolved_weights=(ResolvedPortfolioWeight("AAPL", Decimal(".6")), ResolvedPortfolioWeight("MSFT", Decimal(".4"))))
    instance._market_data = MagicMock()
    instance._market_data.get_range.return_value = portfolio_prices()
    portfolio = SimpleNamespace(id=uuid4(), name="Synthetic")
    return instance, portfolio


@pytest.mark.parametrize("horizon", [7,14,21])
@pytest.mark.parametrize("kind", ["current", "planned", "legacy"])
def test_authoritative_baseline_same_horizon_composition(horizon, kind):
    instance, portfolio = portfolio_service(kind)
    forecasts = (asset("AAPL", horizon, point=.1, vol=.2), asset("MSFT", horizon, point=-.05, vol=.3))
    with patch.object(portfolio_module, "WeeklyForecastInferenceService") as constructor:
        constructor.return_value.predict.side_effect = forecasts
        result = instance.predict(portfolio, horizon_days=horizon)
    assert result.expected_return == pytest.approx(.6*.1 + .4*(-.05))
    correlation = historical_correlation(aligned_log_returns(portfolio_prices(), ("AAPL","MSFT"), TODAY))
    sigma, rc, shares = compose_volatility([.6,.4], [.2,.3], correlation)
    assert result.forecast_realized_volatility == pytest.approx(sigma)
    assert [row.forecast_volatility_contribution for row in result.components] == pytest.approx(rc)
    assert [row.forecast_volatility_contribution_share for row in result.components] == pytest.approx(shares)
    assert all(call.kwargs == {"horizon_days": horizon, "reference_date": TODAY}
               for call in constructor.return_value.predict.call_args_list)
    instance._baseline.resolve.assert_called_once_with(portfolio=portfolio, valuation_date=TODAY)
    assert result.baseline_kind == kind and result.correlation_observation_count == 252
    public = map_weekly_portfolio_outlook(result).model_dump()
    assert not any("interval" in key for key in public)
    assert {row["horizon_days"] for row in public["components"]} == {horizon}
    WeeklyPortfolioOutlookResponse.model_validate(public)


@pytest.mark.parametrize("changes", [{"horizon_days":14}, {"target_version":"forecast-targets-30d-v1"},
    {"artifact_version":"forecast-v1-20260917"}, {"expected_return":float("nan")},
    {"volatility_interval_lower":-1.}, {"market_data_age_days":5}, {"symbol":"GOOGL"}])
def test_bad_or_mixed_component_fails_whole_portfolio(changes):
    instance, portfolio = portfolio_service()
    with patch.object(portfolio_module, "WeeklyForecastInferenceService") as constructor:
        constructor.return_value.predict.side_effect = (asset(), replace(asset("MSFT"), **changes))
        with pytest.raises(ForecastPredictionError):
            instance.predict(portfolio, horizon_days=7)
    instance._market_data.get_range.assert_not_called()


def test_unusable_weights_no_inference():
    instance, portfolio = portfolio_service()
    instance._baseline.resolve.return_value.resolved_weights = ()
    with patch.object(portfolio_module, "WeeklyForecastInferenceService") as constructor:
        with pytest.raises(InvalidForecastPortfolioError):
            instance.predict(portfolio, horizon_days=7)
        constructor.assert_not_called()


def test_correlation_cutoff_uses_oldest_component_origin():
    instance, portfolio = portfolio_service()
    oldest = TODAY-timedelta(days=3)
    with patch.object(portfolio_module, "WeeklyForecastInferenceService") as constructor:
        constructor.return_value.predict.side_effect = (asset(), asset("MSFT", origin=oldest))
        result = instance.predict(portfolio, horizon_days=7)
    assert result.market_data_as_of == result.correlation_as_of_date == oldest
    instance._market_data.get_range.assert_called_once_with(("AAPL","MSFT"), date.min, oldest)


def test_failed_component_is_not_dropped_or_reweighted():
    instance, portfolio = portfolio_service()
    with patch.object(portfolio_module, "WeeklyForecastInferenceService") as constructor:
        constructor.return_value.predict.side_effect = (asset(), ForecastDataStaleError("stale"))
        with pytest.raises(ForecastDataStaleError):
            instance.predict(portfolio, horizon_days=7)
    instance._market_data.get_range.assert_not_called()


def test_zero_volatility_has_zero_contributions_and_shares():
    instance, portfolio = portfolio_service()
    with patch.object(portfolio_module, "WeeklyForecastInferenceService") as constructor:
        constructor.return_value.predict.side_effect = (asset(vol=0.), asset("MSFT", vol=0.))
        result = instance.predict(portfolio, horizon_days=7)
    assert result.forecast_realized_volatility == 0.
    assert all(c.forecast_volatility_contribution == c.forecast_volatility_contribution_share == 0.
               for c in result.components)


@pytest.mark.parametrize("changes", [{"expected_return":float("nan")}, {"horizon_days":30},
    {"horizon_days":7.0},
    {"market_data_age_days":5}, {"predictive_quality_approved":True}, {"experimental":False},
    {"limitations":[]}, {"return_warning_codes":["invented"]}, {"feature_version":"private"}])
def test_public_weekly_contract_rejects_bad_fields(changes):
    public = map_weekly_asset_outlook(asset()).model_dump()
    with pytest.raises(ValidationError):
        WeeklyAssetOutlookResponse.model_validate(dict(public, **changes))


def test_portfolio_schema_rejects_mixed_horizon():
    instance, portfolio = portfolio_service()
    with patch.object(portfolio_module, "WeeklyForecastInferenceService") as constructor:
        constructor.return_value.predict.side_effect = (asset(), asset("MSFT"))
        public = map_weekly_portfolio_outlook(instance.predict(portfolio, horizon_days=7)).model_dump()
    public["components"][0]["horizon_days"] = 14
    with pytest.raises(ValidationError):
        WeeklyPortfolioOutlookResponse.model_validate(public)
