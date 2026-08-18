"""Pydantic contracts for persisted portfolio-analysis reports."""

from datetime import date
from uuid import UUID

from pydantic import AwareDatetime

from .analytics import PortfolioAnalysisResponse
from .common import AnalysisPeriod, AuraBaseModel


class PortfolioReportResponse(AuraBaseModel):
    """A persisted report and its canonical analytics payload."""

    id: UUID
    portfolio_id: UUID
    created_at: AwareDatetime
    analysis: PortfolioAnalysisResponse


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
