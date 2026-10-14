"""Reuse the immutable version-aware report reader without live analysis."""

from datetime import UTC
from uuid import UUID

from sqlalchemy.orm import Session

from ..database.models import Analysis
from ..database.repositories.admin_report_repository import AdminReportRepository
from ..schemas.admin_portfolio import AdminPortfolioOwner
from ..schemas.admin_report import AdminReportDetail, AdminReportSummary, AdminReportsQuery, AdminReportsResponse
from .analysis_reporting_mapper import analysis_record_to_report_response


class AdminReportService:
    def __init__(self, session: Session) -> None:
        self._repository = AdminReportRepository(session)

    @staticmethod
    def _summary(row):
        created = row["created_at"]
        created = created.replace(tzinfo=UTC) if created.tzinfo is None else created.astimezone(UTC)
        return dict(id=row["id"], portfolio_id=row["portfolio_id"], portfolio_name=row["portfolio_name"],
            start_date=row["start_date"], end_date=row["end_date"], created_at=created,
            schema_version=row["schema_version"], report_version=row["report_version"],
            owner=AdminPortfolioOwner(id=row["owner_id"], email=row["email"], display_name=row["display_name"], account_type=row["account_type"], status=row["status"]))

    def list(self, query: AdminReportsQuery) -> AdminReportsResponse:
        query = AdminReportsQuery.model_validate(query.model_dump())
        rows, total = self._repository.list(**query.model_dump())
        return AdminReportsResponse(items=[AdminReportSummary(**self._summary(row)) for row in rows], total=total, limit=query.limit, offset=query.offset)

    def detail(self, report_id: UUID) -> AdminReportDetail | None:
        row = self._repository.detail(report_id)
        if row is None:
            return None
        summary = self._summary(row)
        # A detached record is passed to the established pure snapshot mapper.
        # No live holdings, prices, FX, analysis service or provider are queried.
        record = Analysis(**{field: summary[field] for field in ("id", "portfolio_id", "created_at", "start_date", "end_date", "schema_version")}, result_snapshot=row["result_snapshot"])
        return AdminReportDetail(**summary, report=analysis_record_to_report_response(record))
