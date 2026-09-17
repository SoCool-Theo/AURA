"""Deterministic target allocation for saved planned portfolios."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN, localcontext
from uuid import UUID

from ..database.models import Portfolio, PortfolioType


_WEIGHT_QUANTUM = Decimal("0.000000000000000001")
_ONE = Decimal("1.000000000000000000")
_SUPPORTED_PLAN_CURRENCIES = frozenset({"USD", "THB"})


class InvalidPlannedPortfolioError(ValueError):
    """Raised when a portfolio cannot produce a planned allocation."""


@dataclass(frozen=True, slots=True)
class PlannedAllocationHolding:
    """One ordered proposed amount and its exact canonical target weight."""

    holding_id: UUID
    symbol: str
    proposed_amount: Decimal
    target_allocation: Decimal
    position: int


@dataclass(frozen=True, slots=True)
class PlannedPortfolioAllocation:
    """Complete price-independent target allocation for one plan."""

    portfolio_id: UUID
    plan_currency: str
    total_proposed_amount: Decimal
    holdings: tuple[PlannedAllocationHolding, ...]


class PortfolioPlannedAllocationService:
    """Resolve proposed amounts without database writes or market data."""

    def resolve(self, portfolio: Portfolio) -> PlannedPortfolioAllocation:
        """Return deterministic 18-decimal weights in saved holding order."""
        if portfolio.portfolio_type != PortfolioType.PLANNED.value:
            raise InvalidPlannedPortfolioError(
                "target allocation is available only for planned portfolios"
            )
        if portfolio.plan_currency not in _SUPPORTED_PLAN_CURRENCIES:
            raise InvalidPlannedPortfolioError(
                "planned portfolio has invalid plan currency"
            )

        holdings = tuple(portfolio.holdings)
        if not holdings:
            raise InvalidPlannedPortfolioError(
                "planned portfolio must contain at least one holding"
            )

        amounts: list[Decimal] = []
        for holding in holdings:
            if (
                holding.id is None
                or holding.proposed_amount is None
                or holding.proposed_amount <= 0
                or holding.weight is not None
                or holding.invested_amount is not None
                or holding.invested_currency is not None
                or holding.shares is not None
                or holding.purchase_date is not None
            ):
                raise InvalidPlannedPortfolioError(
                    "planned portfolio contains mixed or incomplete holdings"
                )
            amounts.append(holding.proposed_amount)

        with localcontext() as context:
            context.prec = 80
            total = sum(amounts, start=Decimal("0"))
            if total <= 0:
                raise InvalidPlannedPortfolioError(
                    "planned portfolio total must be positive"
                )

            weights = [
                (amount / total).quantize(
                    _WEIGHT_QUANTUM,
                    rounding=ROUND_DOWN,
                )
                for amount in amounts[:-1]
            ]
            weights.append(_ONE - sum(weights, start=Decimal("0")))

        return PlannedPortfolioAllocation(
            portfolio_id=portfolio.id,
            plan_currency=portfolio.plan_currency,
            total_proposed_amount=total,
            holdings=tuple(
                PlannedAllocationHolding(
                    holding_id=holding.id,
                    symbol=holding.symbol,
                    proposed_amount=holding.proposed_amount,
                    target_allocation=weight,
                    position=holding.position,
                )
                for holding, weight in zip(holdings, weights, strict=True)
            ),
        )


__all__ = [
    "InvalidPlannedPortfolioError",
    "PlannedAllocationHolding",
    "PlannedPortfolioAllocation",
    "PortfolioPlannedAllocationService",
]
