"""Administrative aggregates and safe directory projections; no mutations."""

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from sqlalchemy import Date, case, func, literal, or_, select, true, type_coerce, union_all
from sqlalchemy.orm import Session

from ..models import Analysis, Portfolio, Simulation, User


class AdminOverviewRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_users(
        self, *, limit: int, offset: int, q: str | None = None,
        role: str | None = None, account_type: str | None = None,
    ) -> tuple[list[Mapping[str, Any]], int]:
        kind = case((User.email.is_not(None), "REGISTERED"), else_="LEGACY")
        conditions = []
        if role is not None:
            conditions.append(User.role == role)
        if account_type is not None:
            conditions.append(kind == account_type)
        if q is not None:
            conditions.append(or_(
                func.lower(User.email).contains(q.lower(), autoescape=True),
                func.lower(User.display_name).contains(q.lower(), autoescape=True),
            ))
        # Project only directory fields: never load other accounts' hashes,
        # phone numbers, preferences, holdings, or immutable result payloads.
        matching = select(
            User.id, User.email, User.display_name, User.role,
            kind.label("account_type"), User.created_at, User.updated_at,
        ).where(*conditions).cte("matching_admin_users")
        page = (
            select(matching).order_by(matching.c.created_at.desc(), matching.c.id.desc())
            .offset(offset).limit(limit).cte("admin_users_page")
        )
        total = select(func.count().label("total")).select_from(matching).cte("admin_users_total")
        counts = (
            select(Portfolio.user_id, func.count().label("portfolio_count"))
            .where(Portfolio.user_id.in_(select(page.c.id)))
            .group_by(Portfolio.user_id).cte("admin_user_portfolio_counts")
        )
        statement = (
            select(*page.c, func.coalesce(counts.c.portfolio_count, 0).label("portfolio_count"), total.c.total)
            .select_from(total.outerjoin(page, true()).outerjoin(counts, counts.c.user_id == page.c.id))
            .order_by(page.c.created_at.desc(), page.c.id.desc())
        )
        rows = self._session.execute(statement).mappings().all()
        return [row for row in rows if row["id"] is not None], rows[0]["total"]

    def dashboard(
        self, *, today: datetime, tomorrow: datetime, yesterday: datetime,
        week_start: datetime, window_start: datetime,
    ) -> list[Mapping[str, Any]]:
        def count_in(column, start, end):
            return func.count().filter(column >= start, column < end)

        users = select(
            func.count().label("users_total"),
            func.count().filter(User.role == "CUSTOMER").label("users_customers"),
            func.count().filter(User.role == "ADMIN").label("users_admins"),
            func.count().filter(User.email.is_not(None)).label("users_registered"),
            func.count().filter(User.email.is_(None)).label("users_legacy"),
            count_in(User.created_at, week_start, tomorrow).label("users_new_last_7_days"),
        ).select_from(User).subquery("admin_user_totals")
        portfolios = select(
            func.count().label("portfolios_total"),
            func.count().filter(Portfolio.portfolio_type == "CURRENT").label("portfolios_current"),
            func.count().filter(Portfolio.portfolio_type == "PLANNED").label("portfolios_planned"),
            func.count().filter(Portfolio.portfolio_type == "LEGACY").label("portfolios_legacy"),
            count_in(Portfolio.created_at, week_start, tomorrow).label("portfolios_new_last_7_days"),
        ).select_from(Portfolio).subquery("admin_portfolio_totals")

        def saved_totals(model, prefix):
            return select(
                func.count().label(f"{prefix}_total"),
                count_in(model.created_at, today, tomorrow).label(f"{prefix}_today"),
                count_in(model.created_at, yesterday, today).label(f"{prefix}_yesterday"),
                count_in(model.created_at, week_start, tomorrow).label(f"{prefix}_last_7_days"),
            ).select_from(model).subquery(f"admin_{prefix}_totals")

        reports = saved_totals(Analysis, "reports")
        simulations = saved_totals(Simulation, "simulations")
        groups = []
        for model, metric in [
            (User, "new_users"), (Portfolio, "new_portfolios"),
            (Analysis, "saved_reports"), (Simulation, "saved_simulations"),
        ]:
            # PostgreSQL buckets are explicitly UTC, independent of the server's
            # session timezone. SQLite fixtures store synthetic UTC timestamps.
            day = (
                type_coerce(func.date(model.created_at), Date())
                if self._session.get_bind().dialect.name == "sqlite"
                else func.timezone("UTC", model.created_at).cast(Date())
            )
            groups.append(select(
                day.label("day"), literal(metric).label("metric"), func.count().label("count"),
            ).select_from(model).where(
                model.created_at >= window_start, model.created_at < tomorrow,
            ).group_by(day))
        trend = union_all(*groups).cte("admin_daily_counts")
        # Aggregate independently before joining to avoid multiplication by
        # holdings/results. All totals and daily rows share one SQL snapshot.
        statement = select(
            *users.c, *portfolios.c, *reports.c, *simulations.c, *trend.c,
        ).select_from(
            users.join(portfolios, true()).join(reports, true()).join(simulations, true())
            .outerjoin(trend, true())
        ).order_by(trend.c.day, trend.c.metric)
        return self._session.execute(statement).mappings().all()
