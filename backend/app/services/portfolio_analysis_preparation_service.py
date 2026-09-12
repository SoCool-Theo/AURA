"""Prepare saved portfolio holdings for the existing analytics boundary."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from ..database.models import Portfolio
from ..schemas import AnalysisPeriod, PortfolioAnalysisRequest
from .portfolio_baseline_resolver import (
    PortfolioBaselineKind,
    PortfolioBaselineResolutionService,
    ResolvedPortfolioWeight,
)
from .portfolio_valuation_service import (
    PortfolioDisplayCurrency,
    PortfolioValuationResult,
)


PortfolioAnalysisBaselineKind = PortfolioBaselineKind
ResolvedPortfolioAnalysisWeight = ResolvedPortfolioWeight


@dataclass(frozen=True, slots=True)
class PortfolioAnalysisPreparationResult:
    """Immutable context and validated request for one analysis baseline."""

    baseline_kind: PortfolioAnalysisBaselineKind
    resolved_weights: tuple[ResolvedPortfolioAnalysisWeight, ...]
    valuation: PortfolioValuationResult | None
    valuation_as_of: date | None
    analysis_request: PortfolioAnalysisRequest


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
        self._baseline_resolver = PortfolioBaselineResolutionService(session)

    def prepare(
        self,
        *,
        portfolio: Portfolio,
        analysis_period: AnalysisPeriod,
        valuation_date: date,
        display_currency: PortfolioDisplayCurrency = (
            PortfolioDisplayCurrency.USD
        ),
    ) -> PortfolioAnalysisPreparationResult:
        """Return a validated fixed-weight request and its source context."""
        if type(valuation_date) is not date:
            raise TypeError("valuation_date must be a date")

        resolution = self._baseline_resolver.resolve(
            portfolio=portfolio,
            valuation_date=valuation_date,
            display_currency=display_currency,
        )

        analysis_request = _build_analysis_request(
            portfolio_name=portfolio.name,
            resolved_weights=resolution.resolved_weights,
            analysis_period=analysis_period,
        )
        return PortfolioAnalysisPreparationResult(
            baseline_kind=resolution.baseline_kind,
            resolved_weights=resolution.resolved_weights,
            valuation=resolution.valuation,
            valuation_as_of=resolution.valuation_as_of,
            analysis_request=analysis_request,
        )


__all__ = [
    "PortfolioAnalysisBaselineKind",
    "PortfolioAnalysisPreparationResult",
    "PortfolioAnalysisPreparationService",
    "ResolvedPortfolioAnalysisWeight",
]
