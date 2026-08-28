"""Pure conversion helpers for persisted portfolio-analysis reports."""

from typing import Any

from ..database.models import Analysis
from ..schemas.analytics import PortfolioAnalysisResponse
from ..schemas.reporting import PortfolioReportResponse, PortfolioReportSummary


PORTFOLIO_ANALYSIS_RESPONSE_SCHEMA_VERSION = (
    "portfolio-analysis-response-v1"
)


def analysis_response_to_snapshot(
    response: PortfolioAnalysisResponse,
) -> dict[str, Any]:
    """Return a fresh strict-JSON-compatible analytics snapshot."""
    return response.model_dump(mode="json")


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
) -> PortfolioReportResponse:
    """Validate a stored snapshot and map its complete report envelope."""
    if analysis.schema_version != PORTFOLIO_ANALYSIS_RESPONSE_SCHEMA_VERSION:
        raise ValueError(
            "unsupported portfolio analysis snapshot schema version: "
            f"{analysis.schema_version!r}"
        )

    validated_analysis = PortfolioAnalysisResponse.model_validate(
        analysis.result_snapshot
    )
    if validated_analysis.start_date != analysis.start_date:
        raise ValueError(
            "analysis snapshot start_date does not match relational "
            "start_date"
        )
    if validated_analysis.end_date != analysis.end_date:
        raise ValueError(
            "analysis snapshot end_date does not match relational end_date"
        )

    return PortfolioReportResponse(
        id=analysis.id,
        portfolio_id=analysis.portfolio_id,
        created_at=analysis.created_at,
        analysis=validated_analysis,
    )
