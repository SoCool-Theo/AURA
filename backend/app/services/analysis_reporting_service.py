"""Orchestration for owned persisted portfolio-analysis reports."""

from uuid import UUID

from sqlalchemy.orm import Session

from ..database.repositories import AnalysisRepository
from ..schemas.common import AnalysisPeriod
from ..schemas.portfolio import PortfolioAnalysisRequest
from ..schemas.reporting import (
    PortfolioReportListResponse,
    PortfolioReportResponse,
)
from .analysis_reporting_mapper import (
    PORTFOLIO_ANALYSIS_RESPONSE_SCHEMA_VERSION,
    analysis_record_to_report_response,
    analysis_record_to_report_summary,
    analysis_response_to_snapshot,
)
from .analysis_service import AnalysisService
from .portfolio_service import PortfolioService


class ReportNotFoundError(Exception):
    """Raised when a report is absent from an established owned portfolio."""


class AnalysisReportingService:
    """Coordinate owned report workflows without managing transactions."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._portfolio_service = PortfolioService(session)
        self._analysis_service = AnalysisService(session)
        self._repository = AnalysisRepository(session)

    def create_report(
        self,
        *,
        user_id: UUID,
        portfolio_id: UUID,
        period: AnalysisPeriod,
    ) -> PortfolioReportResponse | None:
        """Run and persist an analysis for an owned portfolio, if present."""
        portfolio = self._portfolio_service.get(
            user_id=user_id,
            portfolio_id=portfolio_id,
        )
        if portfolio is None:
            return None

        request = PortfolioAnalysisRequest.model_validate(
            {
                "portfolio_name": portfolio.name,
                "holdings": [
                    {
                        "symbol": holding.symbol,
                        "weight": float(holding.weight),
                    }
                    for holding in portfolio.holdings
                ],
                "start_date": period.start_date,
                "end_date": period.end_date,
            }
        )
        response = self._analysis_service.analyze(request)
        snapshot = analysis_response_to_snapshot(response)
        analysis = self._repository.save_snapshot(
            portfolio_id=portfolio.id,
            start_date=response.start_date,
            end_date=response.end_date,
            schema_version=PORTFOLIO_ANALYSIS_RESPONSE_SCHEMA_VERSION,
            result_snapshot=snapshot,
        )
        return analysis_record_to_report_response(analysis)

    def list_reports(
        self,
        *,
        user_id: UUID,
        portfolio_id: UUID,
    ) -> PortfolioReportListResponse | None:
        """Return ordered report history for an owned portfolio, if present."""
        portfolio = self._portfolio_service.get(
            user_id=user_id,
            portfolio_id=portfolio_id,
        )
        if portfolio is None:
            return None

        analyses = self._repository.list_for_portfolio(portfolio.id)
        return PortfolioReportListResponse(
            reports=[
                analysis_record_to_report_summary(analysis)
                for analysis in analyses
            ]
        )

    def get_report(
        self,
        *,
        user_id: UUID,
        portfolio_id: UUID,
        report_id: UUID,
    ) -> PortfolioReportResponse | None:
        """Return one report, distinguishing parent and report absence."""
        portfolio = self._portfolio_service.get(
            user_id=user_id,
            portfolio_id=portfolio_id,
        )
        if portfolio is None:
            return None

        analysis = self._repository.get_by_id(report_id)
        if analysis is None or analysis.portfolio_id != portfolio.id:
            raise ReportNotFoundError
        return analysis_record_to_report_response(analysis)
