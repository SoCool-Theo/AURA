from copy import deepcopy
from decimal import Decimal
from uuid import UUID

import pytest

from backend.app.database.models import Holding, Portfolio, PortfolioType
from backend.app.services.portfolio_planned_allocation_service import (
    InvalidPlannedPortfolioError,
    PortfolioPlannedAllocationService,
)


PORTFOLIO_ID = UUID("71000000-0000-0000-0000-000000000001")
USER_ID = UUID("72000000-0000-0000-0000-000000000001")


def _planned_portfolio(
    amounts: tuple[tuple[str, str], ...] = (
        ("AAPL", "4000.000000000000"),
        ("NVDA", "3000.000000000000"),
        ("BND", "2000.000000000000"),
        ("GLD", "1000.000000000000"),
    ),
) -> Portfolio:
    portfolio = Portfolio(
        id=PORTFOLIO_ID,
        user_id=USER_ID,
        name="Plan",
        portfolio_type=PortfolioType.PLANNED.value,
        plan_currency="USD",
    )
    portfolio.holdings.extend(
        Holding(
            id=UUID(f"73000000-0000-0000-0000-{position + 1:012d}"),
            symbol=symbol,
            proposed_amount=Decimal(amount),
            position=position,
        )
        for position, (symbol, amount) in enumerate(amounts)
    )
    return portfolio


def test_resolve_derives_expected_weights_without_market_data() -> None:
    portfolio = _planned_portfolio()
    snapshot = deepcopy(
        [
            (holding.symbol, holding.proposed_amount, holding.position)
            for holding in portfolio.holdings
        ]
    )

    result = PortfolioPlannedAllocationService().resolve(portfolio)

    assert result.portfolio_id == PORTFOLIO_ID
    assert result.plan_currency == "USD"
    assert result.total_proposed_amount == Decimal("10000.000000000000")
    assert [holding.symbol for holding in result.holdings] == [
        "AAPL",
        "NVDA",
        "BND",
        "GLD",
    ]
    assert [holding.target_allocation for holding in result.holdings] == [
        Decimal("0.400000000000000000"),
        Decimal("0.300000000000000000"),
        Decimal("0.200000000000000000"),
        Decimal("0.100000000000000000"),
    ]
    assert [
        (holding.symbol, holding.proposed_amount, holding.position)
        for holding in portfolio.holdings
    ] == snapshot


def test_resolve_rounds_deterministically_and_weights_sum_exactly_to_one(
) -> None:
    portfolio = _planned_portfolio(
        (("AAPL", "1"), ("MSFT", "1"), ("BND", "1"))
    )

    result = PortfolioPlannedAllocationService().resolve(portfolio)
    weights = [holding.target_allocation for holding in result.holdings]

    assert weights == [
        Decimal("0.333333333333333333"),
        Decimal("0.333333333333333333"),
        Decimal("0.333333333333333334"),
    ]
    assert sum(weights, start=Decimal("0")) == Decimal("1")


@pytest.mark.parametrize(
    "portfolio",
    [
        Portfolio(
            id=PORTFOLIO_ID,
            user_id=USER_ID,
            name="Current",
            portfolio_type=PortfolioType.CURRENT.value,
        ),
        Portfolio(
            id=PORTFOLIO_ID,
            user_id=USER_ID,
            name="Empty plan",
            portfolio_type=PortfolioType.PLANNED.value,
            plan_currency="USD",
        ),
        Portfolio(
            id=PORTFOLIO_ID,
            user_id=USER_ID,
            name="Invalid currency",
            portfolio_type=PortfolioType.PLANNED.value,
            plan_currency=None,
        ),
    ],
)
def test_resolve_rejects_wrong_type_or_incomplete_plan(
    portfolio: Portfolio,
) -> None:
    with pytest.raises(InvalidPlannedPortfolioError):
        PortfolioPlannedAllocationService().resolve(portfolio)


def test_resolve_rejects_mixed_or_incomplete_holding() -> None:
    portfolio = _planned_portfolio((("AAPL", "1000"),))
    portfolio.holdings[0].shares = Decimal("1")

    with pytest.raises(
        InvalidPlannedPortfolioError,
        match="mixed or incomplete",
    ):
        PortfolioPlannedAllocationService().resolve(portfolio)
