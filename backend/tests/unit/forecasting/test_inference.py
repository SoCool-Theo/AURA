from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.exc import SQLAlchemyError

from backend.app.forecasting.data import build_price_histories
from backend.app.forecasting.evaluation import ForecastTargetType
from backend.app.forecasting.features import FEATURE_NAMES, build_feature_rows
from backend.app.forecasting.finalization import ForecastArtifactModel
from backend.app.forecasting.inference import ForecastInferenceService, arima_step_index
from backend.app.forecasting.inference_errors import (
    ForecastDataStaleError, ForecastHistoryInsufficientError,
    ForecastPredictionError, ForecastSymbolUnsupportedError,
    ForecastMarketDataUnavailableError,
)
from backend.app.forecasting.registry import LoadedForecastArtifact
from backend.app.forecasting.models import VolatilityArimaCandidate
from backend.app.core.config import Settings


CUTOFF = date(2026, 9, 17)


def records(dates, symbol="AAPL"):
    return [SimpleNamespace(symbol=symbol, date=observed,
                            adjusted_close=Decimal(100 + index), volume=100,
                            source="synthetic") for index, observed in enumerate(dates)]


def warmed(dates, symbol="AAPL"):
    prior = [CUTOFF - timedelta(days=index) for index in range(260, 0, -1)]
    return records(prior + dates, symbol)


def registry(return_model=None, volatility_model=None):
    result = MagicMock()
    result.artifact_version = "forecast-v1-20260917"
    models = {
        ForecastTargetType.RETURN: return_model or ForecastArtifactModel(
            "historical_average", ForecastTargetType.RETURN, "historical_average",
            constant_prediction=-0.05),
        ForecastTargetType.VOLATILITY: volatility_model or ForecastArtifactModel(
            "moving_average_90_calendar_days", ForecastTargetType.VOLATILITY,
            "moving_average", constant_prediction=-0.01),
    }
    result.get.side_effect = lambda symbol, target: LoadedForecastArtifact(
        models[target], CUTOFF, -0.1, 0.2,
    )
    return result


def service(rows, selected=None):
    instance = ForecastInferenceService(MagicMock(), registry=selected or registry())
    instance._market_data = MagicMock()
    instance._market_data.get_range.return_value = list(reversed(rows))
    return instance


def test_latest_origin_feature_reuse_intervals_and_no_result_cache():
    rows = warmed([CUTOFF, date(2026, 9, 18), date(2026, 9, 21)])
    instance = service(rows)
    with patch("backend.app.forecasting.inference.build_feature_rows", wraps=build_feature_rows) as builder:
        result = instance.predict("AAPL", reference_date=date(2026, 9, 22))
        assert builder.call_count == 1
    assert result.origin_date == result.market_data_as_of == date(2026, 9, 21)
    assert result.market_data_age_days == 1
    assert result.expected_return_30d == -0.05
    assert result.return_interval_lower == pytest.approx(-0.15)
    assert result.return_interval_upper == pytest.approx(0.15)
    assert result.forecast_realized_volatility_30d == 0
    assert result.volatility_interval_lower == 0
    assert result.volatility_interval_upper == 0.2
    assert result.interval_coverage == 0.80
    assert result.horizon_days == 30
    assert instance.predict("AAPL", reference_date=date(2026, 9, 22)) == result
    instance._market_data.get_range.return_value = rows + records([date(2026, 9, 22)])
    updated = instance.predict("AAPL", reference_date=date(2026, 9, 22))
    assert updated.origin_date == date(2026, 9, 22)
    instance._market_data.get_range.assert_called_with(("AAPL",), date.min, date(2026, 9, 22))


@pytest.mark.parametrize("age, stale", [(0, False), (4, False), (5, True)])
def test_freshness_boundary(age, stale):
    instance = service(warmed([CUTOFF]))
    if stale:
        with pytest.raises(ForecastDataStaleError):
            instance.predict("AAPL", reference_date=CUTOFF + timedelta(days=age))
        instance._registry.get.assert_not_called()
    else:
        assert instance.predict("AAPL", reference_date=CUTOFF + timedelta(days=age)).market_data_age_days == age


@pytest.mark.parametrize("rows", [[], records([CUTOFF])])
def test_missing_or_insufficient_history(rows):
    with pytest.raises(ForecastHistoryInsufficientError):
        service(rows).predict("AAPL", reference_date=CUTOFF)


def test_unsupported_symbol_never_reads_database():
    instance = service([])
    with pytest.raises(ForecastSymbolUnsupportedError):
        instance.predict("THB=X", reference_date=CUTOFF)
    instance._market_data.get_range.assert_not_called()


@pytest.mark.parametrize("candidate, family, target", [
    ("random_forest_v1", "random_forest", ForecastTargetType.RETURN),
    ("volatility_linear_regression_v1", "linear_regression", ForecastTargetType.VOLATILITY),
    ("volatility_random_forest_v1", "random_forest", ForecastTargetType.VOLATILITY),
])
def test_fitted_feature_models_receive_exact_latest_features_without_training(candidate, family, target):
    fitted = MagicMock()
    fitted.predict.return_value = (0.15,)
    model = ForecastArtifactModel(candidate, target, family, fitted_model=fitted)
    selected = registry(return_model=model) if target is ForecastTargetType.RETURN else registry(volatility_model=model)
    rows = warmed([CUTOFF])
    result = service(rows, selected).predict("AAPL", reference_date=CUTOFF)
    row = build_feature_rows(build_price_histories(rows)[0])[-1]
    fitted.predict.assert_called_once_with((tuple(getattr(row, name) for name in FEATURE_NAMES),))
    for name in ("fit", "partial_fit", "refit", "append", "extend", "update"):
        getattr(fitted, name).assert_not_called()
    assert (result.expected_return_30d if target is ForecastTargetType.RETURN else
            result.forecast_realized_volatility_30d) == 0.15


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_predictions_fail_without_candidate_fallback(bad):
    model = ForecastArtifactModel("historical_average", ForecastTargetType.RETURN,
                                 "historical_average", constant_prediction=bad)
    selected = registry(return_model=model)
    with pytest.raises(ForecastPredictionError):
        service(warmed([CUTOFF]), selected).predict("AAPL", reference_date=CUTOFF)
    assert selected.get.call_count == 1


@pytest.mark.parametrize("dates, symbol", [
    ([CUTOFF], "AAPL"),
    ([CUTOFF, date(2026, 9, 18)], "AAPL"),
    ([CUTOFF, date(2026, 9, 18), date(2026, 9, 21), date(2026, 9, 22)], "AAPL"),
    ([CUTOFF + timedelta(days=index) for index in range(6)], "BTC-USD"),
    ([date(2026, 9, 21), date(2026, 9, 22)], "AAPL"),
])
def test_arima_uses_persisted_steps_final_value_and_frozen_state(dates, symbol):
    fitted = MagicMock()
    fitted.forecast.side_effect = lambda *, steps: tuple(index / 100 for index in range(1, steps + 1))
    model = ForecastArtifactModel("volatility_arima_1_0_1_v1", ForecastTargetType.VOLATILITY,
                                 "arima", fitted_model=fitted)
    instance = service(warmed(dates, symbol), registry(volatility_model=model))
    first = instance.predict(symbol, reference_date=dates[-1])
    assert first.forecast_realized_volatility_30d == len(dates) / 100
    fitted.forecast.assert_called_with(steps=len(dates))
    assert instance.predict(symbol, reference_date=dates[-1]) == first
    for name in ("fit", "partial_fit", "refit", "append", "extend", "update"):
        getattr(fitted, name).assert_not_called()


def test_arima_missing_deployment_observation_and_predeployment_origin_fail():
    history = build_price_histories(records([CUTOFF - timedelta(days=1)]))[0]
    with pytest.raises(ForecastHistoryInsufficientError):
        arima_step_index(history, CUTOFF, history.observations[-1].date)
    history = build_price_histories(records([CUTOFF - timedelta(days=1), CUTOFF]))[0]
    with pytest.raises(ForecastHistoryInsufficientError):
        arima_step_index(history, CUTOFF, CUTOFF - timedelta(days=1))


def test_arima_production_order_matches_evaluation_and_ignores_training_origin_gap():
    origins = [CUTOFF, date(2026, 9, 18), date(2026, 9, 21)]
    training = [SimpleNamespace(
        features=SimpleNamespace(origin_date=date(2026, 8, 1)),
        target=SimpleNamespace(endpoint_date=date(2026, 8, 31), realized_volatility_30d=0.1),
    )]
    evaluation = [SimpleNamespace(features=SimpleNamespace(origin_date=origin)) for origin in origins]
    fitted = MagicMock()
    fitted.forecast.side_effect = lambda *, steps: tuple(index / 100 for index in range(1, steps + 1))
    with patch("backend.app.forecasting.models.arima._fit_arima_with_warning_metadata",
               return_value=(fitted, False)):
        evaluated = VolatilityArimaCandidate().predict(
            training_rows=training, evaluation_rows=evaluation,
            target_type=ForecastTargetType.VOLATILITY, information_cutoff=CUTOFF,
        )
    fitted.forecast.assert_called_once_with(steps=3)
    history = build_price_histories(warmed(origins))[0]
    production = tuple(fitted.forecast(steps=arima_step_index(history, CUTOFF, origin))[-1]
                       for origin in origins)
    assert production == evaluated.values


def test_artifact_configuration_default_override_and_path_guard(monkeypatch):
    monkeypatch.delenv("FORECASTING_ARTIFACT_VERSION", raising=False)
    assert Settings(_env_file=None).forecasting_artifact_version == "forecast-v1-20260917"
    monkeypatch.setenv("FORECASTING_ARTIFACT_VERSION", "forecast-v2-20261001")
    assert Settings(_env_file=None).forecasting_artifact_version == "forecast-v2-20261001"
    with pytest.raises(ValueError):
        Settings(_env_file=None, forecasting_artifact_version="../outside")


def test_market_data_failure_and_prediction_failure_are_sanitized():
    instance = service([])
    instance._market_data.get_range.side_effect = SQLAlchemyError("synthetic private database details")
    with pytest.raises(ForecastMarketDataUnavailableError) as caught:
        instance.predict("AAPL", reference_date=CUTOFF)
    assert "private" not in str(caught.value)
    assert caught.value.__suppress_context__
    fitted = MagicMock()
    fitted.predict.side_effect = RuntimeError("synthetic private model details")
    model = ForecastArtifactModel("random_forest_v1", ForecastTargetType.RETURN,
                                 "random_forest", fitted_model=fitted)
    with pytest.raises(ForecastPredictionError) as caught:
        service(warmed([CUTOFF]), registry(return_model=model)).predict("AAPL", reference_date=CUTOFF)
    assert "private" not in str(caught.value)


def test_inference_never_calls_offline_model_training_or_target_builders():
    with (
        patch("backend.app.forecasting.finalization.train_deployment_artifact", side_effect=AssertionError("training")),
        patch("backend.app.forecasting.targets.build_target_rows", side_effect=AssertionError("targets")),
        patch("backend.app.forecasting.models.arima._fit_arima_with_warning_metadata", side_effect=AssertionError("fit")),
    ):
        instance = service(warmed([CUTOFF]))
        assert instance.predict("AAPL", reference_date=CUTOFF).horizon_days == 30
