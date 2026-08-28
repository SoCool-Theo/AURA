"""Portfolio analysis-reporting endpoints."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import CurrentUser, DatabaseSession
from app.schemas.common import AnalysisPeriod
from app.schemas.reporting import (
    PortfolioReportListResponse,
    PortfolioReportResponse,
)
from app.services.analysis_reporting_service import (
    AnalysisReportingService,
    ReportNotFoundError,
)


router = APIRouter(
    prefix="/portfolios/{portfolio_id}/reports",
    tags=["Reports"],
)


def _internal_error(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=detail,
    )


def _portfolio_not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Portfolio not found",
    )


def _report_not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Report not found",
    )


@router.post(
    "",
    response_model=PortfolioReportResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_report(
    portfolio_id: UUID,
    request: AnalysisPeriod,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> PortfolioReportResponse:
    try:
        report = AnalysisReportingService(session).create_report(
            user_id=current_user.id,
            portfolio_id=portfolio_id,
            period=request,
        )
    except Exception as error:
        raise _internal_error("Unable to create report") from error

    if report is None:
        raise _portfolio_not_found()

    try:
        session.commit()
    except Exception as error:
        raise _internal_error("Unable to create report") from error
    return report


@router.get(
    "",
    response_model=PortfolioReportListResponse,
    status_code=status.HTTP_200_OK,
)
def list_reports(
    portfolio_id: UUID,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> PortfolioReportListResponse:
    try:
        reports = AnalysisReportingService(session).list_reports(
            user_id=current_user.id,
            portfolio_id=portfolio_id,
        )
    except Exception as error:
        raise _internal_error("Unable to list reports") from error

    if reports is None:
        raise _portfolio_not_found()
    return reports


@router.get(
    "/{report_id}",
    response_model=PortfolioReportResponse,
    status_code=status.HTTP_200_OK,
)
def get_report(
    portfolio_id: UUID,
    report_id: UUID,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> PortfolioReportResponse:
    try:
        report = AnalysisReportingService(session).get_report(
            user_id=current_user.id,
            portfolio_id=portfolio_id,
            report_id=report_id,
        )
    except ReportNotFoundError as error:
        raise _report_not_found() from error
    except Exception as error:
        raise _internal_error("Unable to retrieve report") from error

    if report is None:
        raise _portfolio_not_found()
    return report
