"""Pydantic contracts for persisted portfolio-analysis reports."""

from datetime import date
from decimal import Decimal
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import AwareDatetime, Field, model_validator

from .analytics import AssetMetrics, PortfolioAnalysisResponse, RiskDriverEntry
from .common import AnalysisPeriod, AuraBaseModel
from .portfolio import PortfolioHoldingValuationResponse, PortfolioValuationFxResponse


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


PortfolioReportDetailResponse = PortfolioReportResponse | PortfolioReportV2Response


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
