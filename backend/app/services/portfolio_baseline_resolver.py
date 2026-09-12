"""Shared read-only resolution of legacy and real portfolio baselines."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum

from sqlalchemy.orm import Session

from ..database.models import Holding, Portfolio
from .portfolio_valuation_service import (
    PortfolioDisplayCurrency,
    PortfolioValuationResult,
    PortfolioValuationService,
)


class PortfolioBaselineKind(StrEnum):
    """Source used for a portfolio's fixed simulation or analysis weights."""

    LEGACY = "legacy"
    REAL = "real"


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


def _is_complete_legacy(holdings: tuple[Holding, ...]) -> bool:
    return bool(holdings) and all(
        holding.weight is not None
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

    def resolve(
        self,
        *,
        portfolio: Portfolio,
        valuation_date: date,
        display_currency: PortfolioDisplayCurrency = (
            PortfolioDisplayCurrency.USD
        ),
    ) -> PortfolioBaselineResolution:
        """Return saved legacy weights or one current real valuation."""
        if type(valuation_date) is not date:
            raise TypeError("valuation_date must be a date")

        holdings = tuple(portfolio.holdings)
        if _is_complete_legacy(holdings):
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

        valuation = self._valuation_service.value(
            holdings,
            requested_date=valuation_date,
            display_currency=display_currency,
        )
        return PortfolioBaselineResolution(
            baseline_kind=PortfolioBaselineKind.REAL,
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
