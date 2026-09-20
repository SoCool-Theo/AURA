"""Shared read-only resolution of every persisted portfolio baseline."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum

from sqlalchemy.orm import Session

from ..database.models import Holding, Portfolio, PortfolioType
from .portfolio_planned_allocation_service import (
    InvalidPlannedPortfolioError,
    PlannedPortfolioAllocation,
    PortfolioPlannedAllocationService,
)
from .portfolio_valuation_service import (
    InvalidHoldingModeError,
    PortfolioDisplayCurrency,
    PortfolioValuationResult,
    PortfolioValuationService,
)


class PortfolioBaselineKind(StrEnum):
    """Source used for a portfolio's fixed simulation or analysis weights."""

    LEGACY = "legacy"
    CURRENT = "current"
    REAL = "current"
    PLANNED = "planned"


@dataclass(frozen=True, slots=True)
class ResolvedPortfolioWeight:
    """One ordered exact weight resolved from saved or current state."""

    symbol: str
    weight: Decimal


@dataclass(frozen=True, slots=True)
class PortfolioBaselineResolution:
    """Immutable ordered baseline and optional authoritative valuation."""

    baseline_kind: PortfolioBaselineKind
    resolved_weights: tuple[ResolvedPortfolioWeight, ...]
    valuation: PortfolioValuationResult | None
    valuation_as_of: date | None
    planned_allocation: PlannedPortfolioAllocation | None = None


def _is_complete_legacy(holdings: tuple[Holding, ...]) -> bool:
    return bool(holdings) and all(
        holding.weight is not None
        and holding.proposed_amount is None
        and holding.invested_amount is None
        and holding.invested_currency is None
        and holding.shares is None
        and holding.purchase_date is None
        for holding in holdings
    )


class PortfolioBaselineResolutionService:
    """Resolve one fixed baseline without managing caller transactions."""

    def __init__(self, session: Session) -> None:
        self._valuation_service = PortfolioValuationService(session)
        self._planned_allocation_service = (
            PortfolioPlannedAllocationService()
        )

    def resolve(
        self,
        *,
        portfolio: Portfolio,
        valuation_date: date,
        display_currency: PortfolioDisplayCurrency = (
            PortfolioDisplayCurrency.USD
        ),
    ) -> PortfolioBaselineResolution:
        """Return one canonical ordered allocation with source provenance."""
        if type(valuation_date) is not date:
            raise TypeError("valuation_date must be a date")

        holdings = tuple(portfolio.holdings)
        portfolio_type = portfolio.portfolio_type
        if portfolio_type == PortfolioType.PLANNED.value:
            try:
                allocation = self._planned_allocation_service.resolve(portfolio)
            except InvalidPlannedPortfolioError as error:
                raise InvalidHoldingModeError(
                    "planned portfolio holdings are incomplete or mixed"
                ) from error
            return PortfolioBaselineResolution(
                baseline_kind=PortfolioBaselineKind.PLANNED,
                resolved_weights=tuple(
                    ResolvedPortfolioWeight(
                        symbol=holding.symbol,
                        weight=holding.target_allocation,
                    )
                    for holding in allocation.holdings
                ),
                valuation=None,
                valuation_as_of=None,
                planned_allocation=allocation,
            )

        legacy_shape = _is_complete_legacy(holdings)
        if portfolio_type == PortfolioType.LEGACY.value or (
            portfolio_type is None and legacy_shape
        ):
            if not legacy_shape:
                raise InvalidHoldingModeError(
                    "legacy portfolio holdings are incomplete or mixed"
                )
            return PortfolioBaselineResolution(
                baseline_kind=PortfolioBaselineKind.LEGACY,
                resolved_weights=tuple(
                    ResolvedPortfolioWeight(
                        symbol=holding.symbol,
                        weight=holding.weight,
                    )
                    for holding in holdings
                ),
                valuation=None,
                valuation_as_of=None,
            )

        if portfolio_type not in {None, PortfolioType.CURRENT.value}:
            raise InvalidHoldingModeError("unsupported portfolio type")
        if legacy_shape:
            raise InvalidHoldingModeError(
                "current portfolio cannot use saved-weight holdings"
            )

        valuation = self._valuation_service.value(
            holdings,
            requested_date=valuation_date,
            display_currency=display_currency,
        )
        return PortfolioBaselineResolution(
            baseline_kind=PortfolioBaselineKind.CURRENT,
            resolved_weights=tuple(
                ResolvedPortfolioWeight(
                    symbol=holding.symbol,
                    weight=holding.current_allocation,
                )
                for holding in valuation.holdings
            ),
            valuation=valuation,
            valuation_as_of=valuation.requested_date,
        )


__all__ = [
    "PortfolioBaselineKind",
    "PortfolioBaselineResolution",
    "PortfolioBaselineResolutionService",
    "ResolvedPortfolioWeight",
]
