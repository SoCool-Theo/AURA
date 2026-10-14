"""Global read-only projections; customer ownership repositories stay unchanged."""

from uuid import UUID

from sqlalchemy import case, func, or_, select, true
from sqlalchemy.orm import Session

from ..models import Analysis, Holding, Portfolio, Simulation, User


class AdminPortfolioRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    @staticmethod
    def _matching(*conditions):
        return select(
            Portfolio.id, Portfolio.name, Portfolio.portfolio_type,
            Portfolio.plan_currency, Portfolio.source_plan_id,
            Portfolio.created_at, Portfolio.updated_at,
            User.id.label("owner_id"), User.email, User.display_name,
            case((User.email.is_not(None), "REGISTERED"), else_="LEGACY").label("account_type"),
            case((User.is_suspended.is_(True), "SUSPENDED"), else_="ACTIVE").label("status"),
        ).join(User, Portfolio.user_id == User.id).where(*conditions)

    @staticmethod
    def _counts(page):
        # Each correlated aggregate is evaluated for returned portfolios only.
        # It never loads snapshots or multiplies counts through holdings joins.
        return [
            select(func.count()).select_from(model).where(model.portfolio_id == page.c.id)
            .correlate(page).scalar_subquery().label(label)
            for model, label in [(Holding, "holding_count"), (Analysis, "saved_report_count"),
                                 (Simulation, "saved_simulation_count")]
        ]

    def list(self, *, limit, offset, q=None, portfolio_type=None, owner_id=None):
        conditions = []
        if portfolio_type is not None:
            conditions.append(Portfolio.portfolio_type == portfolio_type)
        if owner_id is not None:
            conditions.append(Portfolio.user_id == owner_id)
        if q is not None:
            conditions.append(or_(*[
                func.lower(column).contains(q.lower(), autoescape=True)
                for column in (Portfolio.name, User.email, User.display_name)
            ]))
        matching = self._matching(*conditions).cte("matching_admin_portfolios")
        page = select(matching).order_by(matching.c.created_at.desc(), matching.c.id.desc()).offset(offset).limit(limit).cte("admin_portfolios_page")
        total = select(func.count().label("total")).select_from(matching).cte("admin_portfolios_total")
        statement = select(*page.c, *self._counts(page), total.c.total).select_from(
            total.outerjoin(page, true())
        ).order_by(page.c.created_at.desc(), page.c.id.desc())
        rows = self._session.execute(statement).mappings().all()
        return [row for row in rows if row["id"] is not None], rows[0]["total"]

    def detail(self, portfolio_id: UUID):
        page = self._matching(Portfolio.id == portfolio_id).cte("admin_portfolio_detail")
        fields = ("id", "symbol", "weight", "shares", "proposed_amount", "invested_amount", "invested_currency", "purchase_date", "position")
        statement = select(*page.c, *self._counts(page), *[
            getattr(Holding, field).label("holding_" + field) for field in fields
        ]).select_from(page.outerjoin(Holding, Holding.portfolio_id == page.c.id)).order_by(Holding.position, Holding.id)
        return self._session.execute(statement).mappings().all()
