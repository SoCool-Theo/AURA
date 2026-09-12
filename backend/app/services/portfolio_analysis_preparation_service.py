"""Prepare saved portfolio holdings for the existing analytics boundary."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum

from sqlalchemy.orm import Session

from ..database.models import Holding, Portfolio
from ..schemas import AnalysisPeriod, PortfolioAnalysisRequest
from .portfolio_valuation_service import (
    PortfolioDisplayCurrency,
    PortfolioValuationResult,
    PortfolioValuationService,
)


class PortfolioAnalysisBaselineKind(StrEnum):
    """Source used for the fixed weights passed to historical analytics."""

    LEGACY = "legacy"
    REAL = "real"


@dataclass(frozen=True, slots=True)
class ResolvedPortfolioAnalysisWeight:
    """One ordered Decimal weight before the legacy float schema boundary."""

    symbol: str
    weight: Decimal


@dataclass(frozen=True, slots=True)
class PortfolioAnalysisPreparationResult:
    """Immutable context and validated request for one analysis baseline."""

    baseline_kind: PortfolioAnalysisBaselineKind
    resolved_weights: tuple[ResolvedPortfolioAnalysisWeight, ...]
    valuation: PortfolioValuationResult | None
    valuation_as_of: date | None
    analysis_request: PortfolioAnalysisRequest


def _is_complete_legacy(holdings: tuple[Holding, ...]) -> bool:
    return bool(holdings) and all(
        holding.weight is not None
        and holding.invested_amount is None
        and holding.invested_currency is None
        and holding.shares is None
        and holding.purchase_date is None
        for holding in holdings
    )


def _build_analysis_request(
    *,
    portfolio_name: str,
    resolved_weights: tuple[ResolvedPortfolioAnalysisWeight, ...],
    analysis_period: AnalysisPeriod,
) -> PortfolioAnalysisRequest:
    """Convert Decimal weights only at the existing request boundary."""
    return PortfolioAnalysisRequest.model_validate(
        {
            "portfolio_name": portfolio_name,
            "holdings": [
                {
                    "symbol": holding.symbol,
                    "weight": float(holding.weight),
                }
                for holding in resolved_weights
            ],
            "start_date": analysis_period.start_date,
            "end_date": analysis_period.end_date,
        }
    )


class PortfolioAnalysisPreparationService:
    """Resolve current saved holdings for unchanged historical analytics."""

    def __init__(self, session: Session) -> None:
        self._valuation_service = PortfolioValuationService(session)

    def prepare(
        self,
        *,
        portfolio: Portfolio,
        analysis_period: AnalysisPeriod,
        valuation_date: date,
    ) -> PortfolioAnalysisPreparationResult:
        """Return a validated fixed-weight request and its source context."""
        if type(valuation_date) is not date:
            raise TypeError("valuation_date must be a date")

        holdings = tuple(portfolio.holdings)
        valuation: PortfolioValuationResult | None = None
        valuation_as_of: date | None = None

        if _is_complete_legacy(holdings):
            baseline_kind = PortfolioAnalysisBaselineKind.LEGACY
            resolved_weights = tuple(
                ResolvedPortfolioAnalysisWeight(
                    symbol=holding.symbol,
                    weight=holding.weight,
                )
                for holding in holdings
            )
        else:
            baseline_kind = PortfolioAnalysisBaselineKind.REAL
            valuation = self._valuation_service.value(
                holdings,
                requested_date=valuation_date,
                display_currency=PortfolioDisplayCurrency.USD,
            )
            valuation_as_of = valuation.requested_date
            resolved_weights = tuple(
                ResolvedPortfolioAnalysisWeight(
                    symbol=holding.symbol,
                    weight=holding.current_allocation,
                )
                for holding in valuation.holdings
            )

        analysis_request = _build_analysis_request(
            portfolio_name=portfolio.name,
            resolved_weights=resolved_weights,
            analysis_period=analysis_period,
        )
        return PortfolioAnalysisPreparationResult(
            baseline_kind=baseline_kind,
            resolved_weights=resolved_weights,
            valuation=valuation,
            valuation_as_of=valuation_as_of,
            analysis_request=analysis_request,
        )


__all__ = [
    "PortfolioAnalysisBaselineKind",
    "PortfolioAnalysisPreparationResult",
    "PortfolioAnalysisPreparationService",
    "ResolvedPortfolioAnalysisWeight",
]
