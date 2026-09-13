"""Pydantic contracts for persisted portfolio-analysis reports."""

from datetime import date
from decimal import Decimal
import math
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import AwareDatetime, Field, model_validator

from .analytics import AssetMetrics, PortfolioAnalysisResponse, RiskDriverEntry
from .common import AnalysisPeriod, AuraBaseModel
from .portfolio import (
    PlannedPortfolioBaselineContext,
    PortfolioHoldingValuationResponse,
    PortfolioValuationFxResponse,
)


class PortfolioReportResponse(AuraBaseModel):
    """A persisted V1 report and its canonical analytics payload."""

    id: UUID
    portfolio_id: UUID
    created_at: AwareDatetime
    analysis: PortfolioAnalysisResponse


_PositiveValuationDecimal = Annotated[
    Decimal,
    Field(gt=Decimal("0"), allow_inf_nan=False),
]
_FiniteMonetaryDecimal = Annotated[
    Decimal,
    Field(allow_inf_nan=False),
]
_NonPositiveMonetaryDecimal = Annotated[
    Decimal,
    Field(le=Decimal("0"), allow_inf_nan=False),
]


class PortfolioReportMonetaryMetrics(AuraBaseModel):
    """Currency equivalents derived only from one saved report snapshot."""

    currency: Literal["USD", "THB"]
    basis: Literal["saved-current-valuation", "planned-proposed-amount"]
    reference_amount: _PositiveValuationDecimal
    cumulative_return_amount: _FiniteMonetaryDecimal
    annualized_return_amount: _FiniteMonetaryDecimal
    maximum_drawdown_amount: _NonPositiveMonetaryDecimal | None


class PortfolioReportV2ValuationContext(AuraBaseModel):
    """Immutable portfolio-level valuation facts captured for a V2 report."""

    valuation_currency: Literal["USD", "THB"]
    requested_date: date
    oldest_price_as_of: date
    newest_price_as_of: date
    total_current_value_usd: _PositiveValuationDecimal
    total_current_value: _PositiveValuationDecimal
    fx: PortfolioValuationFxResponse | None

    @model_validator(mode="after")
    def validate_context(self) -> Self:
        if self.oldest_price_as_of > self.newest_price_as_of:
            raise ValueError(
                "oldest_price_as_of must not be after newest_price_as_of"
            )
        if self.newest_price_as_of > self.requested_date:
            raise ValueError(
                "price observation dates must not be after requested_date"
            )
        if self.valuation_currency == "USD" and self.fx is not None:
            raise ValueError("USD valuation must not contain FX context")
        if self.valuation_currency == "THB" and self.fx is None:
            raise ValueError("THB valuation requires FX context")
        if self.fx is not None and self.fx.as_of > self.requested_date:
            raise ValueError("FX observation date must not be after requested_date")
        return self


class PortfolioReportV2Holding(PortfolioHoldingValuationResponse):
    """One immutable real holding with its existing analytics results."""

    asset_metrics: AssetMetrics
    risk_driver: RiskDriverEntry


class PortfolioReportV2Snapshot(AuraBaseModel):
    """Strict JSONB payload for a real-holding analysis report."""

    schema_version: Literal["portfolio-analysis-response-v2"]
    analysis: PortfolioAnalysisResponse
    valuation: PortfolioReportV2ValuationContext
    holdings: Annotated[list[PortfolioReportV2Holding], Field(min_length=1)]


class PortfolioReportV2Response(PortfolioReportV2Snapshot):
    """Persisted V2 report envelope and its immutable real-holding snapshot."""

    id: UUID
    portfolio_id: UUID
    created_at: AwareDatetime
    monetary_metrics: PortfolioReportMonetaryMetrics | None = None


class PortfolioReportV3Snapshot(AuraBaseModel):
    """Strict JSONB payload for a hypothetical planned analysis report."""

    schema_version: Literal["portfolio-analysis-response-v3"]
    analysis: PortfolioAnalysisResponse
    baseline: PlannedPortfolioBaselineContext

    @model_validator(mode="after")
    def validate_analysis_baseline(self) -> Self:
        metrics_by_symbol = {
            metric.symbol: metric for metric in self.analysis.asset_metrics
        }
        baseline_symbols = [
            holding.symbol for holding in self.baseline.holdings
        ]
        if set(metrics_by_symbol) != set(baseline_symbols):
            raise ValueError(
                "planned report baseline symbols do not match analysis"
            )
        for holding in self.baseline.holdings:
            if not math.isclose(
                metrics_by_symbol[holding.symbol].weight,
                float(holding.target_allocation),
                rel_tol=0.0,
                abs_tol=1e-12,
            ):
                raise ValueError(
                    "planned report baseline weight does not match analysis: "
                    f"{holding.symbol}"
                )
        return self


class PortfolioReportV3Response(PortfolioReportV3Snapshot):
    """Persisted V3 envelope and immutable planned-portfolio snapshot."""

    id: UUID
    portfolio_id: UUID
    created_at: AwareDatetime
    monetary_metrics: PortfolioReportMonetaryMetrics | None = None


PortfolioReportDetailResponse = (
    PortfolioReportResponse
    | PortfolioReportV2Response
    | PortfolioReportV3Response
)


class PortfolioReportSummary(AnalysisPeriod):
    """Relational metadata for one saved portfolio report."""

    id: UUID
    portfolio_id: UUID
    start_date: date
    end_date: date
    created_at: AwareDatetime


class PortfolioReportListResponse(AuraBaseModel):
    """An ordered collection of saved portfolio report summaries."""

    reports: list[PortfolioReportSummary]
