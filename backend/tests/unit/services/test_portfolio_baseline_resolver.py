from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import UUID

from sqlalchemy.orm import Session

import backend.app.services.portfolio_baseline_resolver as resolver_module
from backend.app.database.models import Holding, PortfolioType
from backend.app.services.portfolio_baseline_resolver import (
    PortfolioBaselineKind,
    PortfolioBaselineResolutionService,
    ResolvedPortfolioWeight,
)
from backend.app.services.portfolio_valuation_service import (
    PortfolioDisplayCurrency,
    PortfolioValuationService,
)
from backend.tests.unit.services.test_portfolio_analysis_preparation_service import (
    VALUATION_DATE,
    _legacy_holding,
    _portfolio,
    _real_holding,
    _valuation_result,
)


def _service() -> tuple[
    PortfolioBaselineResolutionService,
    MagicMock,
    MagicMock,
]:
    session = MagicMock(spec=Session)
    valuation_service = MagicMock(spec=PortfolioValuationService)
    with patch.object(
        resolver_module,
        "PortfolioValuationService",
        return_value=valuation_service,
    ):
        service = PortfolioBaselineResolutionService(session)
    return service, session, valuation_service


def test_legacy_resolution_preserves_exact_saved_order_without_valuation() -> None:
    service, session, valuation_service = _service()
    weights = (Decimal("0.375"), Decimal("0.625"))
    portfolio = _portfolio(
        [
            _legacy_holding("BND", weights[0], 0),
            _legacy_holding("AAPL", weights[1], 1),
        ]
    )

    result = service.resolve(
        portfolio=portfolio,
        valuation_date=VALUATION_DATE,
    )

    assert result.baseline_kind is PortfolioBaselineKind.LEGACY
    assert result.resolved_weights == (
        ResolvedPortfolioWeight("BND", weights[0]),
        ResolvedPortfolioWeight("AAPL", weights[1]),
    )
    assert result.resolved_weights[0].weight is weights[0]
    assert result.resolved_weights[1].weight is weights[1]
    assert result.valuation is None
    assert result.valuation_as_of is None
    valuation_service.value.assert_not_called()
    session.commit.assert_not_called()
    session.rollback.assert_not_called()
    session.close.assert_not_called()


def test_real_resolution_calls_one_explicit_usd_valuation_and_keeps_decimals() -> None:
    service, session, valuation_service = _service()
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
    valuation = _valuation_result(
        (
            Decimal("0.6123456789012345678901234567"),
            Decimal("0.3876543210987654321098765433"),
        )
    )
    valuation_service.value.return_value = valuation

    result = service.resolve(
        portfolio=portfolio,
        valuation_date=VALUATION_DATE,
        display_currency=PortfolioDisplayCurrency.USD,
    )

    assert result.baseline_kind is PortfolioBaselineKind.REAL
    assert result.valuation is valuation
    assert result.valuation_as_of == VALUATION_DATE
    assert [item.symbol for item in result.resolved_weights] == ["AAPL", "BND"]
    assert [item.weight for item in result.resolved_weights] == [
        holding.current_allocation for holding in valuation.holdings
    ]
    assert result.resolved_weights[0].weight is (
        valuation.holdings[0].current_allocation
    )
    assert valuation.fx_context is None
    valuation_service.value.assert_called_once_with(
        tuple(portfolio.holdings),
        requested_date=VALUATION_DATE,
        display_currency=PortfolioDisplayCurrency.USD,
    )
    session.commit.assert_not_called()
    session.rollback.assert_not_called()
    session.close.assert_not_called()


def test_planned_resolution_uses_proposed_amounts_without_market_data() -> None:
    service, session, valuation_service = _service()
    portfolio = _portfolio([])
    portfolio.portfolio_type = PortfolioType.PLANNED.value
    portfolio.plan_currency = "USD"
    portfolio.holdings.extend(
        [
            Holding(
                id=None,
                symbol="AAPL",
                proposed_amount=Decimal("4000"),
                position=0,
            ),
            Holding(
                id=None,
                symbol="BND",
                proposed_amount=Decimal("1000"),
                position=1,
            ),
        ]
    )
    for position, holding in enumerate(portfolio.holdings, start=1):
        holding.id = UUID(
            f"83000000-0000-0000-0000-{position:012d}"
        )

    result = service.resolve(
        portfolio=portfolio,
        valuation_date=VALUATION_DATE,
        display_currency=PortfolioDisplayCurrency.THB,
    )

    assert result.baseline_kind is PortfolioBaselineKind.PLANNED
    assert result.resolved_weights == (
        ResolvedPortfolioWeight(
            "AAPL",
            Decimal("0.800000000000000000"),
        ),
        ResolvedPortfolioWeight(
            "BND",
            Decimal("0.200000000000000000"),
        ),
    )
    assert result.valuation is None
    assert result.valuation_as_of is None
    assert result.planned_allocation is not None
    assert result.planned_allocation.plan_currency == "USD"
    valuation_service.value.assert_not_called()
    session.commit.assert_not_called()
    session.rollback.assert_not_called()


def test_resolution_requires_an_explicit_plain_date() -> None:
    service, _, valuation_service = _service()
    portfolio = _portfolio([_legacy_holding("AAPL", Decimal("1"), 0)])

    try:
        service.resolve(
            portfolio=portfolio,
            valuation_date="2026-09-12",  # type: ignore[arg-type]
        )
    except TypeError as error:
        assert str(error) == "valuation_date must be a date"
    else:
        raise AssertionError("non-date valuation_date was accepted")

    valuation_service.value.assert_not_called()
