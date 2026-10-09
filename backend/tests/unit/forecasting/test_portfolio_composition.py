"""Synthetic composition checks; no real fitting, artifacts, or databases."""

from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import numpy as np
import pytest
from sqlalchemy.orm import Session

from backend.app.database.models import Portfolio, Holding, MarketData
from backend.app.forecasting.inference import AssetForecast
from backend.app.forecasting.inference_errors import (
    ForecastArtifactMissingError, ForecastDataStaleError,
    ForecastHistoryInsufficientError, ForecastPredictionError,
    ForecastSymbolUnsupportedError, ForecastMarketDataUnavailableError,
)
from backend.app.forecasting import portfolio as module
from backend.app.services.portfolio_baseline_resolver import ResolvedPortfolioWeight
from backend.app.services.forecasting_response_mapper import map_portfolio_outlook


TODAY = datetime.now(UTC).date()
SYMBOLS = ("AAPL", "MSFT")


def asset(symbol, origin=TODAY, point=0.1, vol=0.2):
    return AssetForecast(
        symbol, origin, 30, point, -0.2, 0.4, vol, 0.0, 0.5, 0.80,
        "historical_average", "historical_average", "forecast-v1-20260917",
        "forecast-features-v1", "forecast-targets-v1", origin, (TODAY-origin).days,
    )


def prices(count=320):
    rows = []
    for j, symbol in enumerate(SYMBOLS):
        for i in range(count):
            # Different nonconstant log returns and deterministic stored dates.
            price = np.exp(4 + .001*i + .02*np.sin(i*(.37+j*.21)))
            rows.append(MarketData(symbol=symbol, date=TODAY-timedelta(days=count-1-i),
                                   adjusted_close=Decimal(str(price)), source="synthetic"))
    return rows


def weights(*values):
    return tuple(ResolvedPortfolioWeight(symbol, Decimal(str(value))) for symbol, value in zip(SYMBOLS, values))


@pytest.mark.parametrize("values", [(0.6, 0.4), (0.6, 0.40000000001), (0, 1)])
def test_weights_normalize_only_tiny_deviation_and_do_not_mutate(values):
    rows = weights(*values)
    original = tuple(row.weight for row in rows)
    symbols, actual = module.validated_weights(rows)
    assert symbols == SYMBOLS
    assert actual.sum() == pytest.approx(1)
    assert tuple(row.weight for row in rows) == original


@pytest.mark.parametrize("values", [(0.6, .41), (-.1, 1.1), (float("nan"), .4),
                                      (float("inf"), .4), (0, 0)])
def test_invalid_weights_rejected(values):
    with pytest.raises(module.InvalidForecastPortfolioError):
        module.validated_weights(weights(*values))


@pytest.mark.parametrize("rows", [(), (ResolvedPortfolioWeight("ASDF", Decimal(1)),),
    (ResolvedPortfolioWeight("AAPL", Decimal(".5")),)*2,
    (ResolvedPortfolioWeight("AAPL", True),)])
def test_empty_unsupported_duplicate_boolean_weights_rejected(rows):
    with pytest.raises(module.InvalidForecastPortfolioError):
        module.validated_weights(rows)


def test_log_returns_are_computed_before_common_date_alignment_without_fill():
    rows = prices(100)
    missing = TODAY-timedelta(days=20)
    rows = [r for r in rows if not (r.symbol == "MSFT" and r.date == missing)]
    original = [(r.symbol, r.date, r.adjusted_close) for r in rows]
    cutoff = TODAY-timedelta(days=2)
    result = module.aligned_log_returns(rows[::-1], SYMBOLS, cutoff)
    expected = {}
    for symbol in SYMBOLS:
        selected = sorted((r for r in rows if r.symbol == symbol and r.date <= cutoff), key=lambda r:r.date)
        expected[symbol] = {b.date: np.log(float(b.adjusted_close))-np.log(float(a.adjusted_close))
                            for a, b in zip(selected, selected[1:])}
    common = sorted(set(expected["AAPL"]) & set(expected["MSFT"]))
    assert missing not in common
    assert len(result) == 96
    np.testing.assert_allclose(result, [[expected[s][d] for s in SYMBOLS] for d in common])
    assert [(r.symbol,r.date,r.adjusted_close) for r in rows] == original


def test_latest_252_aligned_returns_only_and_cutoff_future_invariance():
    rows = prices(320)
    cutoff = TODAY-timedelta(days=3)
    actual = module.aligned_log_returns(rows, SYMBOLS, cutoff)
    assert actual.shape == (252, 2)
    retained = [r for r in rows if r.date <= cutoff]
    np.testing.assert_array_equal(actual, module.aligned_log_returns(retained, SYMBOLS, cutoff))
    complete = module.aligned_log_returns(rows, SYMBOLS, TODAY)
    assert not np.array_equal(complete, actual)


@pytest.mark.parametrize("count", [0, 1, 60])
def test_requires_at_least_60_returns(count):
    with pytest.raises(ForecastHistoryInsufficientError):
        module.aligned_log_returns(prices(count), SYMBOLS, TODAY)


def test_exactly_60_returns_and_one_asset_are_supported():
    returns = module.aligned_log_returns(prices(61), ("AAPL",), TODAY)
    assert returns.shape == (60,1)
    np.testing.assert_allclose(module.historical_correlation(returns), [[1]])


@pytest.mark.parametrize("matrix", [np.zeros((60,2)), np.full((60,2), np.nan)])
def test_undefined_nonfinite_correlations_rejected(matrix):
    with pytest.raises(ForecastPredictionError):
        module.historical_correlation(matrix)


@pytest.mark.parametrize("matrix", [np.eye(3), [[1,np.nan],[np.nan,1]], [[1,2],[2,1]],
    [[1,.2],[.3,1]], [[.9,0],[0,1]], [[1,-.9,-.9],[-.9,1,-.9],[-.9,-.9,1]]])
def test_invalid_matrices_not_repaired(matrix):
    size = 3 if np.shape(matrix) == (3,3) and not np.array_equal(matrix,np.eye(3)) else 2
    with pytest.raises(ForecastPredictionError):
        module.validate_correlation(np.array(matrix), size)


def test_covariance_diversification_and_euler_contributions():
    w = np.array([.6,.4]); v = np.array([.2,.3]); r = np.array([[1,.25],[.25,1]])
    before = (w.copy(),v.copy(),r.copy())
    covariance = np.diag(v) @ r @ np.diag(v)
    sigma, rc, shares = module.compose_volatility(w,v,r)
    expected = np.sqrt(w @ covariance @ w)
    assert sigma == pytest.approx(expected)
    assert sigma < w @ v
    np.testing.assert_allclose(rc, w*(covariance@w)/expected)
    assert rc.sum() == pytest.approx(sigma)
    assert shares.sum() == pytest.approx(1)
    for actual, original in zip((w,v,r),before):
        np.testing.assert_array_equal(actual,original)


def test_negative_contributions_are_preserved():
    sigma, rc, shares = module.compose_volatility([.9,.1],[.2,.1],[[1,-.8],[-.8,1]])
    assert rc[1] < 0 and shares[1] < 0
    assert rc.sum() == pytest.approx(sigma)
    assert shares.sum() == pytest.approx(1)


@pytest.mark.parametrize("v,r", [([0,0],np.eye(2)), ([.2,.2],[[1,-1],[-1,1]])])
def test_zero_volatility_contributions_are_defined(v,r):
    sigma, rc, shares = module.compose_volatility([.5,.5],v,r)
    assert sigma == 0
    np.testing.assert_array_equal(rc,[0,0]); np.testing.assert_array_equal(shares,[0,0])


def test_only_tiny_negative_variance_is_floored():
    assert module.variance_to_volatility(-module.VARIANCE_EPSILON/2) == 0
    assert module.variance_to_volatility(0) == 0
    assert module.variance_to_volatility(.04) == pytest.approx(.2)


@pytest.mark.parametrize("value", [-1e-8,float("nan"),float("inf")])
def test_invalid_variance_rejected(value):
    with pytest.raises(ForecastPredictionError):
        module.variance_to_volatility(value)


@pytest.mark.parametrize("vols", [[float("nan"),.2],[-.1,.2],[1e308,1e308]])
def test_invalid_covariance_result_rejected(vols):
    with pytest.raises(ForecastPredictionError):
        module.compose_volatility([.5,.5],vols,np.eye(2))


@pytest.fixture
def composition():
    session = MagicMock(spec=Session)
    portfolio = Portfolio(id=uuid4(),name="Synthetic",user_id=uuid4(),portfolio_type="CURRENT")
    service = module.PortfolioForecastService(session)
    service._baseline = MagicMock()
    service._baseline.resolve.return_value = SimpleNamespace(
        resolved_weights=weights(.6,.4), baseline_kind=SimpleNamespace(value="current"),
        valuation=SimpleNamespace(total_current_value_usd=Decimal("10000"), requested_date=TODAY,
            oldest_price_as_of=TODAY-timedelta(days=2), newest_price_as_of=TODAY,
            holdings=(SimpleNamespace(symbol="AAPL", current_value_usd=Decimal("6000"), price_as_of=TODAY),
                SimpleNamespace(symbol="MSFT", current_value_usd=Decimal("4000"), price_as_of=TODAY-timedelta(days=2)))),
        valuation_as_of=TODAY, planned_allocation=None)
    service._market_data = MagicMock()
    service._market_data.get_range.return_value = prices()
    inference = MagicMock()
    inference.predict.side_effect = [asset("AAPL", point=.1),asset("MSFT",TODAY-timedelta(days=2),point=-.05,vol=.3)]
    with patch.object(module,"ForecastInferenceService",return_value=inference) as constructor:
        yield service, portfolio, session, inference, constructor


def test_authoritative_weights_arithmetic_return_origins_and_reused_inference(composition):
    service, portfolio, session, inference, constructor = composition
    with (
        patch("backend.app.forecasting.finalization.train_deployment_artifact",side_effect=AssertionError("training")) as training,
        patch("backend.app.data_pipeline.providers.market_provider.YFinanceMarketProvider.fetch_historical_prices",side_effect=AssertionError("provider")) as provider,
        patch("backend.app.forecasting.registry.joblib.load",side_effect=AssertionError("real artifacts")) as artifacts,
    ):
        result = service.predict(portfolio)
    training.assert_not_called(); provider.assert_not_called(); artifacts.assert_not_called()
    constructor.assert_called_once_with(session)
    assert [c.current_weight for c in result.components] == [.6,.4]
    assert result.expected_return_30d == pytest.approx(.6*.1+.4*(-.05))
    assert result.expected_return_30d != pytest.approx((1+.6*.1)*(1+.4*(-.05))-1)
    assert result.correlation_as_of_date == TODAY-timedelta(days=2)
    assert result.market_data_as_of == result.correlation_as_of_date
    assert result.components[0].forecast.origin_date == TODAY
    service._market_data.get_range.assert_called_once_with(SYMBOLS,date.min,result.correlation_as_of_date)
    service._baseline.resolve.assert_called_once_with(portfolio=portfolio,valuation_date=TODAY)
    assert [call.args for call in inference.predict.call_args_list] == [("AAPL",),("MSFT",)]
    assert all(call.kwargs == {"reference_date": TODAY} for call in inference.predict.call_args_list)
    response = map_portfolio_outlook(result)
    assert response.baseline_kind == "current"
    assert response.monetary_projection.baseline_amount == Decimal("10000")
    assert response.monetary_projection.expected_change_amount == Decimal(str(result.expected_return_30d)) * 10000
    assert response.monetary_projection.valuation_requested_date == TODAY
    assert response.monetary_projection.oldest_price_as_of == TODAY-timedelta(days=2)
    assert [c.monetary_projection.baseline_amount for c in response.components] == [Decimal("6000"), Decimal("4000")]
    assert [c.monetary_projection.expected_change_amount for c in response.components] == [Decimal("600"), Decimal("-200")]
    assert [c.monetary_projection.estimated_ending_value for c in response.components] == [Decimal("6600"), Decimal("3800")]
    assert response.components[1].monetary_projection.oldest_price_as_of == TODAY-timedelta(days=2)
    assert response.components[0].return_prediction_interval.lower == -.2
    assert not any("interval" in key for key in response.model_dump())
    for name in ("commit","add","delete","execute"):
        getattr(session,name).assert_not_called()


@pytest.mark.parametrize("error", [ForecastDataStaleError,ForecastArtifactMissingError,ForecastSymbolUnsupportedError])
def test_component_failure_fails_entire_portfolio_no_drop_or_retry(composition,error):
    service, portfolio, _, inference, _ = composition
    inference.predict.side_effect = [asset("AAPL"),error("synthetic failure")]
    with pytest.raises(error):
        service.predict(portfolio)
    assert inference.predict.call_count == 2
    service._market_data.get_range.assert_not_called()


@pytest.mark.parametrize("change", [{"expected_return_30d":float("nan")},
    {"forecast_realized_volatility_30d":float("inf")}, {"artifact_version":"forecast-v2-20260917"},
    {"origin_date":TODAY-timedelta(days=5)}, {"return_interval_lower":float("inf")},
    {"symbol":"GOOGL"}, {"expected_return_30d":"invalid"}, {"expected_return_30d":True}])
def test_invalid_component_or_inconsistent_provenance_rejected(composition,change):
    service, portfolio, _, inference, _ = composition
    inference.predict.side_effect = [asset("AAPL"),replace(asset("MSFT"),**change)]
    with pytest.raises(ForecastPredictionError):
        service.predict(portfolio)


@pytest.mark.parametrize("mode,currency", [("LEGACY",None),("PLANNED","USD"),("PLANNED","THB"),("CURRENT",None)])
def test_real_baseline_infrastructure_preserves_supported_modes(mode, currency):
    session = MagicMock(spec=Session)
    portfolio = Portfolio(id=uuid4(),name="Modes",portfolio_type=mode,plan_currency=currency)
    portfolio.holdings = [Holding(id=uuid4(),symbol=s,position=i,
        weight=Decimal(w) if mode=="LEGACY" else None,
        proposed_amount=Decimal(a) if mode=="PLANNED" else None,
        shares=Decimal(q) if mode=="CURRENT" else None,
        invested_amount=Decimal("9999") if mode=="CURRENT" else None,
        invested_currency="THB" if mode=="CURRENT" else None,
        purchase_date=TODAY-timedelta(days=100) if mode=="CURRENT" else None)
        for i,(s,w,a,q) in enumerate([("AAPL",".6","60","3"),("MSFT",".4","40","1")])]
    service = module.PortfolioForecastService(session)
    observations = [MarketData(symbol="AAPL",date=TODAY,adjusted_close=Decimal(20)),
                    MarketData(symbol="MSFT",date=TODAY,adjusted_close=Decimal(40))]
    with (
        patch("backend.app.services.portfolio_valuation_service.MarketDataService.get_latest_usd_asset_observations",return_value=observations) as valuation,
        patch.object(service._market_data,"get_range",return_value=prices()),
        patch.object(module,"ForecastInferenceService") as constructor,
    ):
        constructor.return_value.predict.side_effect = [asset("AAPL"),asset("MSFT")]
        result = service.predict(portfolio)
    assert [c.current_weight for c in result.components] == pytest.approx([.6,.4])
    assert result.baseline_kind == mode.lower()
    assert valuation.call_count == (1 if mode=="CURRENT" else 0)
    if mode == "LEGACY":
        assert result.monetary_projection is None
        assert all(c.monetary_projection is None for c in result.components)
    else:
        money = result.monetary_projection
        assert money.baseline_amount == Decimal("100")  # Shares x latest price, not purchase cost.
        assert money.currency == (currency or "USD")
        assert money.expected_change_amount == Decimal("10")
        assert money.estimated_ending_value == Decimal("110")
        assert money.hypothetical == (mode == "PLANNED")
        assert money.assumes_unchanged_fx == (currency == "THB")
        assert [c.monetary_projection.baseline_amount for c in result.components] == [Decimal("60"), Decimal("40")]
        assert [c.monetary_projection.expected_change_amount for c in result.components] == [Decimal("6"), Decimal("4")]
    map_portfolio_outlook(result)  # Validate production resolver provenance as well as the calculation.


@pytest.mark.parametrize("mode", ["CURRENT","LEGACY","PLANNED"])
def test_empty_saved_portfolio_rejected_before_inference(mode):
    from backend.app.services.portfolio_valuation_service import PortfolioValuationError
    service = module.PortfolioForecastService(MagicMock(spec=Session))
    portfolio = Portfolio(id=uuid4(),portfolio_type=mode,plan_currency="USD",holdings=[])
    with patch.object(module,"ForecastInferenceService") as inference:
        with pytest.raises((module.InvalidForecastPortfolioError,PortfolioValuationError)):
            service.predict(portfolio)
        inference.assert_not_called()


def test_roundoff_negative_variance_is_zero_in_actual_composition():
    sigma, rc, shares = module.compose_volatility([.5,.5],[.2,.2],[[1,-1-1e-14],[-1-1e-14,1]])
    assert sigma == 0
    np.testing.assert_array_equal(rc,[0,0])
    np.testing.assert_array_equal(shares,[0,0])


def test_correlation_storage_failure_is_controlled(composition):
    from sqlalchemy.exc import SQLAlchemyError
    service, portfolio, _, _, _ = composition
    service._market_data.get_range.side_effect = SQLAlchemyError("private database details")
    with pytest.raises(ForecastMarketDataUnavailableError,match="correlation market data unavailable"):
        service.predict(portfolio)


def test_missing_component_history_not_dropped(composition):
    service, portfolio, _, _, _ = composition
    service._market_data.get_range.return_value = [r for r in prices() if r.symbol == "AAPL"]
    with pytest.raises(ForecastHistoryInsufficientError):
        service.predict(portfolio)
