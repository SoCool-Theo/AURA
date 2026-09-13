"""Pure conversion helpers for persisted portfolio-analysis reports."""

from typing import Any

from ..database.models import Analysis
from ..schemas.analytics import PortfolioAnalysisResponse
from ..schemas.portfolio import PortfolioValuationFxResponse
from ..schemas.reporting import (
    PortfolioReportDetailResponse,
    PortfolioReportResponse,
    PortfolioReportSummary,
    PortfolioReportV2Holding,
    PortfolioReportV2Response,
    PortfolioReportV2Snapshot,
    PortfolioReportV2ValuationContext,
    PortfolioReportV3Response,
    PortfolioReportV3Snapshot,
)
from .planned_snapshot_mapper import planned_allocation_to_snapshot_baseline
from .portfolio_analysis_composition import PortfolioEnrichedAnalysisResult
from .portfolio_analysis_preparation_service import (
    PortfolioAnalysisBaselineKind,
)


PORTFOLIO_ANALYSIS_RESPONSE_SCHEMA_VERSION = (
    "portfolio-analysis-response-v1"
)
PORTFOLIO_ANALYSIS_RESPONSE_V2_SCHEMA_VERSION = (
    "portfolio-analysis-response-v2"
)
PORTFOLIO_ANALYSIS_RESPONSE_V3_SCHEMA_VERSION = (
    "portfolio-analysis-response-v3"
)


def analysis_response_to_snapshot(
    response: PortfolioAnalysisResponse,
) -> dict[str, Any]:
    """Return a fresh strict-JSON-compatible analytics snapshot."""
    return response.model_dump(mode="json")


def enriched_analysis_to_v2_snapshot(
    enriched: PortfolioEnrichedAnalysisResult,
) -> dict[str, Any]:
    """Map authoritative composed values into a strict JSON-safe V2 snapshot."""
    if (
        enriched.baseline_kind is not PortfolioAnalysisBaselineKind.REAL
        or enriched.valuation is None
    ):
        raise ValueError("V2 snapshots require a real valuation result")

    valuation = enriched.valuation
    fx = (
        None
        if valuation.fx_context is None
        else PortfolioValuationFxResponse(
            pair=valuation.fx_context.pair,
            provider_symbol=valuation.fx_context.provider_symbol,
            rate=valuation.fx_context.rate,
            as_of=valuation.fx_context.as_of,
        )
    )
    snapshot = PortfolioReportV2Snapshot(
        schema_version=PORTFOLIO_ANALYSIS_RESPONSE_V2_SCHEMA_VERSION,
        analysis=enriched.analysis,
        valuation=PortfolioReportV2ValuationContext(
            valuation_currency=valuation.display_currency.value,
            requested_date=valuation.requested_date,
            oldest_price_as_of=valuation.oldest_price_as_of,
            newest_price_as_of=valuation.newest_price_as_of,
            total_current_value_usd=valuation.total_current_value_usd,
            total_current_value=valuation.total_current_value,
            fx=fx,
        ),
        holdings=[
            PortfolioReportV2Holding(
                id=holding.holding_id,
                symbol=holding.symbol,
                invested_amount=holding.invested_amount,
                invested_currency=holding.invested_currency,
                shares=holding.shares,
                purchase_date=holding.purchase_date,
                position=holding.position,
                asset_price=holding.asset_price,
                asset_quote_currency=holding.asset_quote_currency,
                price_as_of=holding.price_as_of,
                current_value_usd=holding.current_value_usd,
                current_value=holding.current_value,
                current_allocation=holding.current_allocation,
                asset_metrics=holding.asset_metrics,
                risk_driver=holding.risk_driver_entry,
            )
            for holding in enriched.holdings
        ],
    )
    return snapshot.model_dump(mode="json")


def enriched_analysis_to_v3_snapshot(
    enriched: PortfolioEnrichedAnalysisResult,
) -> dict[str, Any]:
    """Map a planned analysis and its immutable target-allocation baseline."""
    if (
        enriched.baseline_kind is not PortfolioAnalysisBaselineKind.PLANNED
        or enriched.valuation is not None
        or enriched.planned_allocation is None
    ):
        raise ValueError("V3 snapshots require a planned allocation result")

    snapshot = PortfolioReportV3Snapshot(
        schema_version=PORTFOLIO_ANALYSIS_RESPONSE_V3_SCHEMA_VERSION,
        analysis=enriched.analysis,
        baseline=planned_allocation_to_snapshot_baseline(
            enriched.planned_allocation
        ),
    )
    return snapshot.model_dump(mode="json")


def analysis_record_to_report_summary(
    analysis: Analysis,
) -> PortfolioReportSummary:
    """Map relational report metadata without inspecting its snapshot."""
    return PortfolioReportSummary(
        id=analysis.id,
        portfolio_id=analysis.portfolio_id,
        start_date=analysis.start_date,
        end_date=analysis.end_date,
        created_at=analysis.created_at,
    )


def analysis_record_to_report_response(
    analysis: Analysis,
) -> PortfolioReportDetailResponse:
    """Validate a stored snapshot and map its complete report envelope."""
    if analysis.schema_version == PORTFOLIO_ANALYSIS_RESPONSE_SCHEMA_VERSION:
        validated_analysis = PortfolioAnalysisResponse.model_validate(
            analysis.result_snapshot
        )
        _validate_relational_period(analysis, validated_analysis)
        return PortfolioReportResponse(
            id=analysis.id,
            portfolio_id=analysis.portfolio_id,
            created_at=analysis.created_at,
            analysis=validated_analysis,
        )

    if analysis.schema_version == PORTFOLIO_ANALYSIS_RESPONSE_V2_SCHEMA_VERSION:
        validated_snapshot = PortfolioReportV2Snapshot.model_validate(
            analysis.result_snapshot
        )
        _validate_relational_period(analysis, validated_snapshot.analysis)
        return PortfolioReportV2Response(
            id=analysis.id,
            portfolio_id=analysis.portfolio_id,
            created_at=analysis.created_at,
            **validated_snapshot.model_dump(),
        )

    if analysis.schema_version == PORTFOLIO_ANALYSIS_RESPONSE_V3_SCHEMA_VERSION:
        validated_snapshot = PortfolioReportV3Snapshot.model_validate(
            analysis.result_snapshot
        )
        _validate_relational_period(analysis, validated_snapshot.analysis)
        return PortfolioReportV3Response(
            id=analysis.id,
            portfolio_id=analysis.portfolio_id,
            created_at=analysis.created_at,
            **validated_snapshot.model_dump(),
        )

    raise ValueError(
        "unsupported portfolio analysis snapshot schema version: "
        f"{analysis.schema_version!r}"
    )


def _validate_relational_period(
    analysis: Analysis,
    validated_analysis: PortfolioAnalysisResponse,
) -> None:
    """Ensure immutable payload dates agree with relational lookup metadata."""
    if validated_analysis.start_date != analysis.start_date:
        raise ValueError(
            "analysis snapshot start_date does not match relational "
            "start_date"
        )
    if validated_analysis.end_date != analysis.end_date:
        raise ValueError(
            "analysis snapshot end_date does not match relational end_date"
        )
