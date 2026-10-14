"""Global metadata projections and a single saved snapshot; no writes."""

from uuid import UUID

from sqlalchemy import case, func, or_, select, true
from sqlalchemy.orm import Session

from ..models import Analysis, Portfolio, User


class AdminReportRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    @staticmethod
    def _version():
        return case(*[(Analysis.schema_version == f"portfolio-analysis-response-v{i}", f"V{i}") for i in (1, 2, 3)], else_="OTHER")

    @classmethod
    def _metadata(cls, *conditions):
        return select(
            Analysis.id, Analysis.portfolio_id, Analysis.start_date, Analysis.end_date,
            Analysis.created_at, Analysis.schema_version, cls._version().label("report_version"),
            Portfolio.name.label("portfolio_name"), User.id.label("owner_id"), User.email, User.display_name,
            case((User.email.is_not(None), "REGISTERED"), else_="LEGACY").label("account_type"),
            case((User.is_suspended.is_(True), "SUSPENDED"), else_="ACTIVE").label("status"),
        ).select_from(Analysis).join(Portfolio, Analysis.portfolio_id == Portfolio.id).join(User, Portfolio.user_id == User.id).where(*conditions)

    def list(self, *, limit, offset, q=None, owner_id=None, portfolio_id=None, report_version=None, created_from=None, created_to=None):
        conditions = []
        for column, value in ((Portfolio.user_id, owner_id), (Analysis.portfolio_id, portfolio_id), (self._version(), report_version)):
            if value is not None:
                conditions.append(column == value)
        if created_from is not None:
            conditions.append(Analysis.created_at >= created_from)
        if created_to is not None:
            conditions.append(Analysis.created_at <= created_to)
        if q is not None:
            conditions.append(or_(*[func.lower(column).contains(q.lower(), autoescape=True) for column in (Portfolio.name, User.email, User.display_name)]))
        matching = self._metadata(*conditions).cte("matching_admin_reports")
        page = select(matching).order_by(matching.c.created_at.desc(), matching.c.id.desc()).offset(offset).limit(limit).cte("admin_reports_page")
        total = select(func.count().label("total")).select_from(matching).cte("admin_reports_total")
        statement = select(*page.c, total.c.total).select_from(total.outerjoin(page, true())).order_by(page.c.created_at.desc(), page.c.id.desc())
        rows = self._session.execute(statement).mappings().all()
        return [row for row in rows if row["id"] is not None], rows[0]["total"]

    def detail(self, report_id: UUID):
        metadata = self._metadata(Analysis.id == report_id).cte("admin_report_detail")
        statement = select(*metadata.c, Analysis.result_snapshot).select_from(metadata.join(Analysis, Analysis.id == metadata.c.id))
        return self._session.execute(statement).mappings().one_or_none()
