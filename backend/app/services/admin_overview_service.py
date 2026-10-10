"""Backend-owned administrative counts and safe user directory mapping."""

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from ..database.repositories.admin_overview_repository import AdminOverviewRepository
from ..schemas.admin import (
    AdminDashboardDay,
    AdminDashboardResponse,
    AdminPortfolioCounts,
    AdminSavedResultCounts,
    AdminUserCounts,
    AdminUserResponse,
    AdminUsersListResponse,
    AdminUsersQuery,
)


def _utc(value: datetime) -> datetime:
    # PostgreSQL is aware; synthetic SQLite persistence drops timezone metadata.
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class AdminOverviewService:
    def __init__(self, session: Session) -> None:
        self._repository = AdminOverviewRepository(session)

    def list_users(self, query: AdminUsersQuery) -> AdminUsersListResponse:
        validated = AdminUsersQuery.model_validate(query.model_dump())
        rows, total = self._repository.list_users(**validated.model_dump())
        items = [
            AdminUserResponse(
                id=row["id"],
                email=row["email"],
                display_name=row["display_name"],
                role=row["role"],
                account_type=row["account_type"],
                created_at=_utc(row["created_at"]),
                updated_at=_utc(row["updated_at"]),
                portfolio_count=row["portfolio_count"],
            )
            for row in rows
        ]
        return AdminUsersListResponse(
            items=items, total=total, limit=validated.limit, offset=validated.offset
        )

    def dashboard(self) -> AdminDashboardResponse:
        now = datetime.now(UTC)
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        start = today - timedelta(days=29)
        rows = self._repository.dashboard(
            today=today,
            tomorrow=today + timedelta(days=1),
            yesterday=today - timedelta(days=1),
            week_start=today - timedelta(days=6),
            window_start=start,
        )
        first = rows[0]

        def values(prefix, names):
            return {name: first[f"{prefix}_{name}"] for name in names}

        daily = {
            (start + timedelta(days=index)).date(): {
                "new_users": 0, "new_portfolios": 0, "saved_reports": 0, "saved_simulations": 0,
            } for index in range(30)
        }
        for row in rows:
            if row["day"] is not None:
                daily[row["day"]][row["metric"]] = row["count"]
        return AdminDashboardResponse(
            generated_at=now,
            window_start=start.date(),
            window_end=today.date(),
            users=AdminUserCounts(**values(
                "users", ["total", "customers", "admins", "registered", "legacy", "new_last_7_days"]
            )),
            portfolios=AdminPortfolioCounts(**values(
                "portfolios", ["total", "current", "planned", "legacy", "new_last_7_days"]
            )),
            saved_reports=AdminSavedResultCounts(**values(
                "reports", ["total", "today", "yesterday", "last_7_days"]
            )),
            saved_simulations=AdminSavedResultCounts(**values(
                "simulations", ["total", "today", "yesterday", "last_7_days"]
            )),
            daily=[AdminDashboardDay(date=day, **counts) for day, counts in daily.items()],
        )
