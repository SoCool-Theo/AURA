"""Pydantic contracts for persisted portfolio-analysis reports."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
import math
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import AwareDatetime, Field, model_validator

from .analytics import AssetMetrics, PortfolioAnalysisResponse, RiskDriverEntry
from .common import AnalysisPeriod, AssetSymbol, AuraBaseModel
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
    basis: Literal[
        "fixed-shares-historical-value",
        "saved-current-valuation",
        "planned-proposed-amount",
    ]
    reference_amount: _PositiveValuationDecimal
    cumulative_return_amount: _FiniteMonetaryDecimal
    annualized_return_amount: _FiniteMonetaryDecimal
    maximum_drawdown_amount: _NonPositiveMonetaryDecimal | None
    estimated_ending_value: _PositiveValuationDecimal | None = None

    @model_validator(mode="after")
    def validate_estimated_ending_value(self) -> Self:
        if self.estimated_ending_value is None:
            return self
        if self.basis != "planned-proposed-amount":
            raise ValueError(
                "estimated ending value is available only for planned reports"
            )
        expected_value = self.reference_amount + self.cumulative_return_amount
        if self.estimated_ending_value != expected_value:
            raise ValueError(
                "estimated ending value must equal reference amount plus "
                "cumulative return amount"
            )
        return self


class PortfolioReportAssetMonetaryMetrics(AuraBaseModel):
    """Currency equivalents for one asset in a saved report snapshot."""

    symbol: AssetSymbol
    currency: Literal["USD", "THB"]
    basis: Literal["saved-current-value", "planned-proposed-amount"]
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
    asset_monetary_metrics: list[
        PortfolioReportAssetMonetaryMetrics
    ] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_asset_monetary_metrics(self) -> Self:
        if not self.asset_monetary_metrics:
            return self

        expected_symbols = [
            metric.symbol for metric in self.analysis.asset_metrics
        ]
        actual_symbols = [
            metric.symbol for metric in self.asset_monetary_metrics
        ]
        if actual_symbols != expected_symbols:
            raise ValueError(
                "asset monetary metrics must match analysis asset order"
            )

        holdings_by_symbol = {
            holding.symbol: holding for holding in self.holdings
        }
        for metric in self.asset_monetary_metrics:
            if metric.currency != self.valuation.valuation_currency:
                raise ValueError(
                    "asset monetary currency must match report valuation"
                )
            if metric.basis != "saved-current-value":
                raise ValueError(
                    "V2 asset monetary basis must use saved current value"
                )
            holding = holdings_by_symbol.get(metric.symbol)
            if (
                holding is None
                or metric.reference_amount != holding.current_value
            ):
                raise ValueError(
                    "asset monetary reference must match saved current value"
                )
        return self


class PortfolioReportV3Snapshot(AuraBaseModel):
    """Strict JSONB payload for a hypothetical planned analysis report."""

    schema_version: Literal["portfolio-analysis-response-v3"]
    analysis: PortfolioAnalysisResponse
    baseline: PlannedPortfolioBaselineContext
    currency_conversion: PortfolioReportV3CurrencyConversionContext | None = (
        None
    )

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


class PortfolioReportV3CurrencyConversionContext(AuraBaseModel):
    """Frozen USD/THB rate available for saved-report display only."""

    requested_date: date
    fx: PortfolioValuationFxResponse

    @model_validator(mode="after")
    def validate_fx_date(self) -> Self:
        if self.fx.as_of > self.requested_date:
            raise ValueError("FX observation date must not be after requested_date")
        return self


class PortfolioReportV3CurrencyHolding(AuraBaseModel):
    """One backend-converted planned amount for display."""

    symbol: AssetSymbol
    proposed_amount: _PositiveValuationDecimal


class PortfolioReportV3CurrencyView(AuraBaseModel):
    """One complete backend-owned currency view of a planned report."""

    currency: Literal["USD", "THB"]
    total_proposed_amount: _PositiveValuationDecimal
    holdings: Annotated[
        list[PortfolioReportV3CurrencyHolding],
        Field(min_length=1),
    ]
    monetary_metrics: PortfolioReportMonetaryMetrics
    asset_monetary_metrics: Annotated[
        list[PortfolioReportAssetMonetaryMetrics],
        Field(min_length=1),
    ]

    @model_validator(mode="after")
    def validate_currency_view(self) -> Self:
        if self.monetary_metrics.currency != self.currency:
            raise ValueError("portfolio monetary currency must match view")
        if any(
            metric.currency != self.currency
            for metric in self.asset_monetary_metrics
        ):
            raise ValueError("asset monetary currency must match view")
        if {holding.symbol for holding in self.holdings} != {
            metric.symbol for metric in self.asset_monetary_metrics
        }:
            raise ValueError("currency-view holdings and assets must match")
        return self


class PortfolioReportV3Response(PortfolioReportV3Snapshot):
    """Persisted V3 envelope and immutable planned-portfolio snapshot."""

    id: UUID
    portfolio_id: UUID
    created_at: AwareDatetime
    monetary_metrics: PortfolioReportMonetaryMetrics | None = None
    asset_monetary_metrics: list[
        PortfolioReportAssetMonetaryMetrics
    ] = Field(default_factory=list)
    currency_views: list[PortfolioReportV3CurrencyView] = Field(
        default_factory=list
    )

    @model_validator(mode="after")
    def validate_asset_monetary_metrics(self) -> Self:
        if not self.asset_monetary_metrics:
            return self

        expected_symbols = [
            metric.symbol for metric in self.analysis.asset_metrics
        ]
        actual_symbols = [
            metric.symbol for metric in self.asset_monetary_metrics
        ]
        if actual_symbols != expected_symbols:
            raise ValueError(
                "asset monetary metrics must match analysis asset order"
            )

        holdings_by_symbol = {
            holding.symbol: holding for holding in self.baseline.holdings
        }
        for metric in self.asset_monetary_metrics:
            if metric.currency != self.baseline.plan_currency:
                raise ValueError(
                    "asset monetary currency must match plan currency"
                )
            if metric.basis != "planned-proposed-amount":
                raise ValueError(
                    "V3 asset monetary basis must use proposed amount"
                )
            holding = holdings_by_symbol.get(metric.symbol)
            if (
                holding is None
                or metric.reference_amount != holding.proposed_amount
            ):
                raise ValueError(
                    "asset monetary reference must match proposed amount"
                )
        return self

    @model_validator(mode="after")
    def validate_currency_views(self) -> Self:
        if not self.currency_views:
            return self
        currencies = [view.currency for view in self.currency_views]
        if len(currencies) != len(set(currencies)):
            raise ValueError("planned report currency views must be unique")
        if currencies[0] != self.baseline.plan_currency:
            raise ValueError("first currency view must match plan currency")
        expected_symbols = [
            holding.symbol for holding in self.baseline.holdings
        ]
        if any(
            [holding.symbol for holding in view.holdings]
            != expected_symbols
            for view in self.currency_views
        ):
            raise ValueError("currency-view holdings must match the plan")
        return self


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
