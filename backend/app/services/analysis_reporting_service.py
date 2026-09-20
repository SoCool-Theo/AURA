"""Orchestration for owned persisted portfolio-analysis reports."""

from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from ..database.models import Analysis
from ..database.repositories import AnalysisRepository
from ..schemas.common import AnalysisPeriod
from ..schemas.reporting import (
    PortfolioReportDetailResponse,
    PortfolioReportListResponse,
)
from .analysis_reporting_mapper import (
    PORTFOLIO_ANALYSIS_RESPONSE_SCHEMA_VERSION,
    PORTFOLIO_ANALYSIS_RESPONSE_V2_SCHEMA_VERSION,
    PORTFOLIO_ANALYSIS_RESPONSE_V3_SCHEMA_VERSION,
    analysis_record_to_report_response,
    analysis_record_to_report_summary,
    analysis_response_to_snapshot,
    enriched_analysis_to_v2_snapshot,
    enriched_analysis_to_v3_snapshot,
)
from .analysis_service import AnalysisService
from .portfolio_analysis_composition import compose_portfolio_analysis
from .portfolio_analysis_preparation_service import (
    PortfolioAnalysisBaselineKind,
    PortfolioAnalysisPreparationService,
)
from .portfolio_valuation_service import PortfolioDisplayCurrency
from .portfolio_service import PortfolioService


class ReportNotFoundError(Exception):
    """Raised when a report is absent from an established owned portfolio."""


class ReportAnalysisUnprocessableError(ValueError):
    """Raised when existing historical analytics cannot process a request."""


class AnalysisReportingService:
    """Coordinate owned report workflows without managing transactions."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._portfolio_service = PortfolioService(session)
        self._preparation_service = PortfolioAnalysisPreparationService(session)
        self._analysis_service = AnalysisService(session)
        self._repository = AnalysisRepository(session)

    def create_report(
        self,
        *,
        user_id: UUID,
        portfolio_id: UUID,
        period: AnalysisPeriod,
        valuation_date: date | None = None,
        display_currency: PortfolioDisplayCurrency = (
            PortfolioDisplayCurrency.USD
        ),
    ) -> PortfolioReportDetailResponse | None:
        """Run and persist an analysis for an owned portfolio, if present."""
        portfolio = self._portfolio_service.get(
            user_id=user_id,
            portfolio_id=portfolio_id,
        )
        if portfolio is None:
            return None

        selected_valuation_date = valuation_date or datetime.now(UTC).date()
        preparation = self._preparation_service.prepare(
            portfolio=portfolio,
            analysis_period=period,
            valuation_date=selected_valuation_date,
            display_currency=display_currency,
        )
        try:
            analysis_kwargs = (
                {
                    "share_quantities": dict(
                        preparation.current_share_quantities
                    )
                }
                if preparation.current_share_quantities is not None
                else {}
            )
            response = self._analysis_service.analyze(
                preparation.analysis_request,
                **analysis_kwargs,
            )
        except ValueError as error:
            raise ReportAnalysisUnprocessableError from error

        if preparation.baseline_kind is PortfolioAnalysisBaselineKind.LEGACY:
            schema_version = PORTFOLIO_ANALYSIS_RESPONSE_SCHEMA_VERSION
            snapshot = analysis_response_to_snapshot(response)
        elif preparation.baseline_kind is PortfolioAnalysisBaselineKind.PLANNED:
            enriched = compose_portfolio_analysis(preparation, response)
            schema_version = PORTFOLIO_ANALYSIS_RESPONSE_V3_SCHEMA_VERSION
            snapshot = enriched_analysis_to_v3_snapshot(enriched)
        else:
            enriched = compose_portfolio_analysis(preparation, response)
            schema_version = PORTFOLIO_ANALYSIS_RESPONSE_V2_SCHEMA_VERSION
            snapshot = enriched_analysis_to_v2_snapshot(enriched)

        analysis = self._repository.save_snapshot(
            portfolio_id=portfolio.id,
            start_date=response.start_date,
            end_date=response.end_date,
            schema_version=schema_version,
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
    ) -> PortfolioReportDetailResponse | None:
        """Return one report, distinguishing parent and report absence."""
        analysis = self._get_owned_report(
            user_id=user_id,
            portfolio_id=portfolio_id,
            report_id=report_id,
        )
        if analysis is None:
            return None
        return analysis_record_to_report_response(analysis)

    def _get_owned_report(
        self,
        *,
        user_id: UUID,
        portfolio_id: UUID,
        report_id: UUID,
    ) -> Analysis | None:
        """Return an associated report after preserving portfolio privacy."""
        portfolio = self._portfolio_service.get(
            user_id=user_id,
            portfolio_id=portfolio_id,
        )
        if portfolio is None:
            return None

        analysis = self._repository.get_by_id(report_id)
        if analysis is None or analysis.portfolio_id != portfolio.id:
            raise ReportNotFoundError
        return analysis

    def delete_report(
        self,
        *,
        user_id: UUID,
        portfolio_id: UUID,
        report_id: UUID,
    ) -> bool | None:
        """Delete one report after validating its owned portfolio association."""
        analysis = self._get_owned_report(
            user_id=user_id,
            portfolio_id=portfolio_id,
            report_id=report_id,
        )
        if analysis is None:
            return None
        if not self._repository.delete(report_id):
            raise ReportNotFoundError
        return True
