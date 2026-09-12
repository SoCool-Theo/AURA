from dataclasses import FrozenInstanceError, replace
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import UUID

import pandas as pd
import pytest
from sqlalchemy.orm import Session

import backend.app.services.analysis_service as analysis_module
import backend.app.services.portfolio_baseline_resolver as baseline_module
import backend.app.services.portfolio_analysis_preparation_service as preparation_module
import backend.app.services.portfolio_valuation_service as valuation_module
from backend.app.analytics import PortfolioAnalyticsResult
from backend.app.database.models import Holding, MarketData, Portfolio
from backend.app.schemas import (
    AnalysisPeriod,
    PortfolioAnalysisRequest,
    PortfolioAnalysisResponse,
)
from backend.app.services.analysis_service import AnalysisService
from backend.app.services.market_data_service import (
    MarketDataService,
    MarketDataUnavailableError,
)
from backend.app.services.portfolio_analysis_preparation_service import (
    PortfolioAnalysisBaselineKind,
    PortfolioAnalysisPreparationResult,
    PortfolioAnalysisPreparationService,
    ResolvedPortfolioAnalysisWeight,
    _build_analysis_request,
)
from backend.app.services.portfolio_valuation_service import (
    HoldingValuationResult,
    InvalidHoldingModeError,
    PortfolioDisplayCurrency,
    PortfolioFxContext,
    PortfolioValuationResult,
    PortfolioValuationService,
    UnsupportedHoldingInstrumentError,
)


PORTFOLIO_ID = UUID("51000000-0000-0000-0000-000000000001")
VALUATION_DATE = date(2026, 9, 12)


def _period() -> AnalysisPeriod:
    return AnalysisPeriod(
        start_date=date(2022, 1, 1),
        end_date=date(2022, 12, 31),
    )


def _legacy_holding(
    symbol: str,
    weight: Decimal,
    position: int,
) -> Holding:
    return Holding(
        id=UUID(f"52000000-0000-0000-0000-{position + 1:012d}"),
        portfolio_id=PORTFOLIO_ID,
        symbol=symbol,
        weight=weight,
        invested_amount=None,
        invested_currency=None,
        shares=None,
        purchase_date=None,
        position=position,
    )


def _real_holding(
    symbol: str,
    *,
    position: int,
    shares: Decimal,
    invested_amount: Decimal,
    invested_currency: str,
) -> Holding:
    return Holding(
        id=UUID(f"53000000-0000-0000-0000-{position + 1:012d}"),
        portfolio_id=PORTFOLIO_ID,
        symbol=symbol,
        weight=None,
        invested_amount=invested_amount,
        invested_currency=invested_currency,
        shares=shares,
        purchase_date=date(2026, 1, position + 1),
        position=position,
    )


def _portfolio(holdings: list[Holding]) -> Portfolio:
    portfolio = Portfolio(
        id=PORTFOLIO_ID,
        user_id=UUID("51000000-0000-0000-0000-000000000002"),
        name="Current Core",
    )
    portfolio.holdings.extend(holdings)
    return portfolio


def _valuation_result(
    allocations: tuple[Decimal, ...] = (
        Decimal("0.6000000000000000000000000000"),
        Decimal("0.4000000000000000000000000000"),
    ),
) -> PortfolioValuationResult:
    symbols = ("AAPL", "BND")
    holding_results = tuple(
        HoldingValuationResult(
            holding_id=UUID(
                f"53000000-0000-0000-0000-{position + 1:012d}"
            ),
            symbol=symbol,
            invested_amount=Decimal("999999.000000000000"),
            invested_currency="THB" if position == 0 else "USD",
            shares=Decimal("1.000000000000"),
            purchase_date=date(2026, 1, position + 1),
            position=position,
            asset_price=Decimal("100.000000000000"),
            asset_quote_currency="USD",
            price_as_of=VALUATION_DATE,
            current_value_usd=allocation * Decimal("100"),
            current_value=allocation * Decimal("100"),
            current_allocation=allocation,
        )
        for position, (symbol, allocation) in enumerate(
            zip(symbols, allocations, strict=True)
        )
    )
    return PortfolioValuationResult(
        display_currency=PortfolioDisplayCurrency.USD,
        requested_date=VALUATION_DATE,
        oldest_price_as_of=VALUATION_DATE,
        newest_price_as_of=VALUATION_DATE,
        total_current_value_usd=Decimal("100"),
        total_current_value=Decimal("100"),
        fx_context=None,
        holdings=holding_results,
    )


def _service_with_mocked_valuation() -> tuple[
    PortfolioAnalysisPreparationService,
    MagicMock,
    MagicMock,
]:
    session = MagicMock(spec=Session)
    valuation_service = MagicMock(spec=PortfolioValuationService)
    with patch.object(
        baseline_module,
        "PortfolioValuationService",
        return_value=valuation_service,
    ):
        service = PortfolioAnalysisPreparationService(session)
    return service, session, valuation_service


def _holding_snapshot(
    holdings: list[Holding],
) -> list[tuple[object, ...]]:
    return [
        (
            holding.id,
            holding.symbol,
            holding.weight,
            holding.invested_amount,
            holding.invested_currency,
            holding.shares,
            holding.purchase_date,
            holding.position,
        )
        for holding in holdings
    ]


def test_complete_legacy_baseline_preserves_saved_weights_and_order() -> None:
    service, session, valuation_service = _service_with_mocked_valuation()
    first_weight = Decimal("0.700000000000000000")
    second_weight = Decimal("0.300000000000000000")
    portfolio = _portfolio(
        [
            _legacy_holding("MSFT", first_weight, 0),
            _legacy_holding("AAPL", second_weight, 1),
        ]
    )
    period = _period()
    holdings_snapshot = _holding_snapshot(portfolio.holdings)
    period_snapshot = period.model_dump()

    result = service.prepare(
        portfolio=portfolio,
        analysis_period=period,
        valuation_date=VALUATION_DATE,
    )

    assert result.baseline_kind is PortfolioAnalysisBaselineKind.LEGACY
    assert result.resolved_weights == (
        ResolvedPortfolioAnalysisWeight("MSFT", first_weight),
        ResolvedPortfolioAnalysisWeight("AAPL", second_weight),
    )
    assert result.resolved_weights[0].weight is first_weight
    assert result.resolved_weights[1].weight is second_weight
    assert result.valuation is None
    assert result.valuation_as_of is None
    assert [
        (holding.symbol, holding.weight)
        for holding in result.analysis_request.holdings
    ] == [("MSFT", 0.7), ("AAPL", 0.3)]
    assert result.analysis_request.start_date == period.start_date
    assert result.analysis_request.end_date == period.end_date
    valuation_service.value.assert_not_called()
    assert _holding_snapshot(portfolio.holdings) == holdings_snapshot
    assert period.model_dump() == period_snapshot
    session.commit.assert_not_called()
    session.rollback.assert_not_called()
    session.close.assert_not_called()


def test_real_baseline_calls_one_explicit_usd_valuation_and_keeps_context() -> None:
    service, session, valuation_service = _service_with_mocked_valuation()
    portfolio = _portfolio(
        [
            _real_holding(
                "AAPL",
                position=0,
                shares=Decimal("2"),
                invested_amount=Decimal("1"),
                invested_currency="THB",
            ),
            _real_holding(
                "BND",
                position=1,
                shares=Decimal("4"),
                invested_amount=Decimal("999999"),
                invested_currency="USD",
            ),
        ]
    )
    period = _period()
    valuation = _valuation_result()
    valuation_service.value.return_value = valuation
    holdings_snapshot = _holding_snapshot(portfolio.holdings)
    period_snapshot = period.model_dump()

    result = service.prepare(
        portfolio=portfolio,
        analysis_period=period,
        valuation_date=VALUATION_DATE,
    )

    assert result.baseline_kind is PortfolioAnalysisBaselineKind.REAL
    assert result.valuation is valuation
    assert result.valuation_as_of == VALUATION_DATE
    assert result.resolved_weights == (
        ResolvedPortfolioAnalysisWeight(
            "AAPL", Decimal("0.6000000000000000000000000000")
        ),
        ResolvedPortfolioAnalysisWeight(
            "BND", Decimal("0.4000000000000000000000000000")
        ),
    )
    valuation_service.value.assert_called_once_with(
        tuple(portfolio.holdings),
        requested_date=VALUATION_DATE,
        display_currency=PortfolioDisplayCurrency.USD,
    )
    assert result.analysis_request.start_date == date(2022, 1, 1)
    assert result.analysis_request.end_date == date(2022, 12, 31)
    assert result.valuation_as_of > result.analysis_request.end_date
    assert [
        (holding.symbol, holding.weight)
        for holding in result.analysis_request.holdings
    ] == [("AAPL", 0.6), ("BND", 0.4)]
    assert _holding_snapshot(portfolio.holdings) == holdings_snapshot
    assert period.model_dump() == period_snapshot
    session.commit.assert_not_called()
    session.rollback.assert_not_called()
    session.close.assert_not_called()


def test_real_thb_baseline_uses_one_requested_currency_valuation() -> None:
    service, session, valuation_service = _service_with_mocked_valuation()
    portfolio = _portfolio(
        [
            _real_holding(
                "AAPL",
                position=0,
                shares=Decimal("2"),
                invested_amount=Decimal("1"),
                invested_currency="THB",
            ),
            _real_holding(
                "BND",
                position=1,
                shares=Decimal("4"),
                invested_amount=Decimal("999999"),
                invested_currency="USD",
            ),
        ]
    )
    usd_valuation = _valuation_result()
    thb_valuation = replace(
        usd_valuation,
        display_currency=PortfolioDisplayCurrency.THB,
        total_current_value=Decimal("3250"),
        fx_context=PortfolioFxContext(
            pair="USD/THB",
            provider_symbol="THB=X",
            rate=Decimal("32.50"),
            as_of=VALUATION_DATE,
        ),
    )
    valuation_service.value.return_value = thb_valuation

    result = service.prepare(
        portfolio=portfolio,
        analysis_period=_period(),
        valuation_date=VALUATION_DATE,
        display_currency=PortfolioDisplayCurrency.THB,
    )

    valuation_service.value.assert_called_once_with(
        tuple(portfolio.holdings),
        requested_date=VALUATION_DATE,
        display_currency=PortfolioDisplayCurrency.THB,
    )
    assert result.valuation is thb_valuation
    assert [weight.weight for weight in result.resolved_weights] == [
        holding.current_allocation for holding in thb_valuation.holdings
    ]
    assert result.analysis_request.end_date == date(2022, 12, 31)
    assert result.valuation_as_of == date(2026, 9, 12)
    session.commit.assert_not_called()


def test_real_baseline_uses_canonical_usd_without_fx_lookup() -> None:
    session = MagicMock(spec=Session)
    market_data_service = MagicMock(spec=MarketDataService)
    market_data_service.get_latest_usd_asset_observations.return_value = [
        MarketData(
            symbol="AAPL",
            date=VALUATION_DATE,
            adjusted_close=Decimal("30"),
            volume=None,
            source="test",
        ),
        MarketData(
            symbol="BND",
            date=VALUATION_DATE,
            adjusted_close=Decimal("10"),
            volume=None,
            source="test",
        ),
    ]
    portfolio = _portfolio(
        [
            _real_holding(
                "AAPL",
                position=0,
                shares=Decimal("2"),
                invested_amount=Decimal("999999"),
                invested_currency="THB",
            ),
            _real_holding(
                "BND",
                position=1,
                shares=Decimal("4"),
                invested_amount=Decimal("1"),
                invested_currency="USD",
            ),
        ]
    )

    with patch.object(
        valuation_module,
        "MarketDataService",
        return_value=market_data_service,
    ):
        result = PortfolioAnalysisPreparationService(session).prepare(
            portfolio=portfolio,
            analysis_period=_period(),
            valuation_date=VALUATION_DATE,
        )

    assert [weight.weight for weight in result.resolved_weights] == [
        Decimal("0.6"),
        Decimal("0.4"),
    ]
    assert [holding.weight for holding in result.analysis_request.holdings] == [
        0.6,
        0.4,
    ]
    market_data_service.get_latest_usd_asset_observations.assert_called_once_with(
        ["AAPL", "BND"],
        VALUATION_DATE,
    )
    market_data_service.get_latest_usd_thb_fx_observation.assert_not_called()


def test_decimal_allocations_convert_only_when_analysis_request_is_built() -> None:
    first = Decimal("0.3333333333333333333333333333")
    second = Decimal("0.6666666666666666666666666667")
    resolved = (
        ResolvedPortfolioAnalysisWeight("AAPL", first),
        ResolvedPortfolioAnalysisWeight("BND", second),
    )
    period = _period()

    request = _build_analysis_request(
        portfolio_name="Core",
        resolved_weights=resolved,
        analysis_period=period,
    )

    assert [weight.weight for weight in resolved] == [first, second]
    assert all(
        type(weight.weight) is Decimal for weight in resolved
    )
    assert [holding.weight for holding in request.holdings] == [
        float(first),
        float(second),
    ]
    assert all(type(holding.weight) is float for holding in request.holdings)
    assert sum(holding.weight for holding in request.holdings) == pytest.approx(
        1.0,
        abs=1e-9,
    )


@pytest.mark.parametrize(
    "failure",
    [
        InvalidHoldingModeError("mixed legacy and real holdings"),
        InvalidHoldingModeError("incomplete real holding AAPL"),
        MarketDataUnavailableError("latest market data is stale for AAPL"),
        UnsupportedHoldingInstrumentError("unsupported holding symbol"),
    ],
    ids=["mixed", "incomplete", "stale-price", "unsupported-symbol"],
)
def test_real_baseline_propagates_valuation_failures_without_fallback(
    failure: Exception,
) -> None:
    service, session, valuation_service = _service_with_mocked_valuation()
    portfolio = _portfolio(
        [
            _real_holding(
                "AAPL",
                position=0,
                shares=Decimal("2"),
                invested_amount=Decimal("100"),
                invested_currency="USD",
            )
        ]
    )
    valuation_service.value.side_effect = failure

    with pytest.raises(type(failure)) as raised:
        service.prepare(
            portfolio=portfolio,
            analysis_period=_period(),
            valuation_date=VALUATION_DATE,
        )

    assert raised.value is failure
    valuation_service.value.assert_called_once()
    session.commit.assert_not_called()
    session.rollback.assert_not_called()
    session.close.assert_not_called()


@pytest.mark.parametrize("baseline_kind", ["legacy", "real"])
def test_existing_analysis_service_accepts_prepared_request_unchanged(
    baseline_kind: str,
) -> None:
    preparation_service, session, valuation_service = (
        _service_with_mocked_valuation()
    )
    if baseline_kind == "legacy":
        portfolio = _portfolio(
            [
                _legacy_holding("AAPL", Decimal("0.6"), 0),
                _legacy_holding("BND", Decimal("0.4"), 1),
            ]
        )
    else:
        portfolio = _portfolio(
            [
                _real_holding(
                    "AAPL",
                    position=0,
                    shares=Decimal("2"),
                    invested_amount=Decimal("100"),
                    invested_currency="USD",
                ),
                _real_holding(
                    "BND",
                    position=1,
                    shares=Decimal("4"),
                    invested_amount=Decimal("200"),
                    invested_currency="THB",
                ),
            ]
        )
        valuation_service.value.return_value = _valuation_result()
    preparation = preparation_service.prepare(
        portfolio=portfolio,
        analysis_period=_period(),
        valuation_date=VALUATION_DATE,
    )
    request_snapshot = preparation.analysis_request.model_dump()
    historical_prices = pd.DataFrame({"sentinel": [1.0]})
    analytics_result = MagicMock(spec=PortfolioAnalyticsResult)
    response = MagicMock(spec=PortfolioAnalysisResponse)
    historical_market_data = MagicMock(spec=MarketDataService)
    historical_market_data.get_range.return_value = []

    with (
        patch.object(
            analysis_module,
            "MarketDataService",
            return_value=historical_market_data,
        ),
        patch.object(
            analysis_module,
            "_build_price_frame",
            return_value=historical_prices,
        ),
        patch.object(
            analysis_module,
            "analyze_portfolio",
            return_value=analytics_result,
        ) as analyze_portfolio,
        patch.object(
            analysis_module,
            "_map_analysis_response",
            return_value=response,
        ) as map_response,
    ):
        result = AnalysisService(session).analyze(
            preparation.analysis_request
        )

    assert result is response
    historical_market_data.get_range.assert_called_once_with(
        ["AAPL", "BND"],
        date(2022, 1, 1),
        date(2022, 12, 31),
    )
    analyze_portfolio.assert_called_once_with(
        historical_prices,
        {"AAPL": 0.6, "BND": 0.4},
    )
    map_response.assert_called_once_with(
        preparation.analysis_request,
        analytics_result,
    )
    assert preparation.analysis_request.model_dump() == request_snapshot


def test_preparation_result_contract_is_frozen() -> None:
    result = PortfolioAnalysisPreparationResult(
        baseline_kind=PortfolioAnalysisBaselineKind.LEGACY,
        resolved_weights=(
            ResolvedPortfolioAnalysisWeight("AAPL", Decimal("1")),
        ),
        valuation=None,
        valuation_as_of=None,
        analysis_request=PortfolioAnalysisRequest.model_validate(
            {
                "portfolio_name": "Core",
                "holdings": [{"symbol": "AAPL", "weight": 1.0}],
                "start_date": "2022-01-01",
                "end_date": "2022-12-31",
            }
        ),
    )

    with pytest.raises(FrozenInstanceError):
        result.baseline_kind = PortfolioAnalysisBaselineKind.REAL


def test_prepare_rejects_non_date_valuation_boundary_before_valuation() -> None:
    service, _, valuation_service = _service_with_mocked_valuation()
    portfolio = _portfolio(
        [_legacy_holding("AAPL", Decimal("1"), 0)]
    )

    with pytest.raises(TypeError, match="valuation_date must be a date"):
        service.prepare(
            portfolio=portfolio,
            analysis_period=_period(),
            valuation_date="2026-09-12",  # type: ignore[arg-type]
        )

    valuation_service.value.assert_not_called()
