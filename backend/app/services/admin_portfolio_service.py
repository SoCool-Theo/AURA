"""Safe saved portfolio facts, without valuation or analytics execution."""

from datetime import UTC
from uuid import UUID

from sqlalchemy.orm import Session

from ..database.repositories.admin_portfolio_repository import AdminPortfolioRepository
from ..schemas.admin_portfolio import AdminPortfolioDetail, AdminPortfolioOwner, AdminPortfolioSummary, AdminPortfoliosQuery, AdminPortfoliosResponse
from ..schemas.portfolio import PortfolioHoldingResponse


class AdminPortfolioService:
    def __init__(self, session: Session) -> None:
        self._repository = AdminPortfolioRepository(session)

    @staticmethod
    def _summary(row):
        def utc(value):
            return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
        return dict(
            id=row["id"], name=row["name"], portfolio_type=row["portfolio_type"], plan_currency=row["plan_currency"],
            created_at=utc(row["created_at"]), updated_at=utc(row["updated_at"]),
            owner=AdminPortfolioOwner(id=row["owner_id"], email=row["email"], display_name=row["display_name"], account_type=row["account_type"], status=row["status"]),
            holding_count=row["holding_count"], saved_report_count=row["saved_report_count"], saved_simulation_count=row["saved_simulation_count"],
        )

    def list(self, query: AdminPortfoliosQuery) -> AdminPortfoliosResponse:
        query = AdminPortfoliosQuery.model_validate(query.model_dump())
        rows, total = self._repository.list(**query.model_dump())
        return AdminPortfoliosResponse(items=[AdminPortfolioSummary(**self._summary(row)) for row in rows], total=total, limit=query.limit, offset=query.offset)

    def detail(self, portfolio_id: UUID) -> AdminPortfolioDetail | None:
        rows = self._repository.detail(portfolio_id)
        if not rows:
            return None
        fields = ("id", "symbol", "weight", "shares", "proposed_amount", "invested_amount", "invested_currency", "purchase_date", "position")
        holdings = []
        for row in rows:
            if row["holding_id"] is None:
                continue
            values = {field: row["holding_" + field] for field in fields}
            if values["weight"] is not None:
                values["weight"] = float(values["weight"])
            holdings.append(PortfolioHoldingResponse(**values))
        return AdminPortfolioDetail(**self._summary(rows[0]), source_plan_id=rows[0]["source_plan_id"], holdings=holdings)
