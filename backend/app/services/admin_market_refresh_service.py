"""Authorize durable requests; execution stays in Aura's existing worker."""

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from ..database.models import MarketDataRefreshRun, User
from ..database.repositories.market_data_refresh_repository import MarketDataRefreshRepository
from ..database.repositories.market_data_refresh_run_repository import MarketDataRefreshRunRepository
from ..database.repositories.user_repository import UserRepository
from ..schemas.admin_market_refresh import AdminMarketRefreshRequest, AdminMarketRefreshRunResponse, AdminMarketRefreshRunsResponse
from ..schemas.audit_log import AuditEventCreate, AuditMarketRefreshDetails
from .audit_log_service import AuditLogService


class AdminMarketRefreshError(ValueError):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        super().__init__(detail)


def run_response(row: MarketDataRefreshRun) -> AdminMarketRefreshRunResponse:
    values = {field: getattr(row, field) for field in AdminMarketRefreshRunResponse.model_fields}
    for field in ("requested_at", "started_at", "finished_at"):
        if values[field] is not None:
            values[field] = values[field].replace(tzinfo=UTC) if values[field].tzinfo is None else values[field].astimezone(UTC)
    return AdminMarketRefreshRunResponse(**values)


class AdminMarketRefreshService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.runs = MarketDataRefreshRunRepository(session)

    def request(self, actor: User, request: AdminMarketRefreshRequest) -> AdminMarketRefreshRunResponse:
        request = AdminMarketRefreshRequest.model_validate(request.model_dump())
        actor_id, actor_version = actor.id, actor.auth_version or 0
        users = UserRepository(self.session)
        users.lock_account_status_changes()
        actor = users.get_current_by_id(actor_id)
        if actor is None or actor.is_suspended or (actor.auth_version or 0) != actor_version:
            raise AdminMarketRefreshError(401, "Invalid or missing authentication credentials")
        if actor.role != "ADMIN" or not actor.email or not actor.password_hash:
            raise AdminMarketRefreshError(403, "Administrator access required")
        # The shared transaction advisory lock serializes API requests and excludes
        # worker/CLI writes. No provider, thread or background task starts here.
        existing = self.runs.get(request.request_id)
        if existing:
            if existing.trigger != "ADMIN" or existing.requested_by != actor_id:
                raise AdminMarketRefreshError(409, "Refresh request identifier already used")
            return run_response(existing)
        self.runs.lock_requests()
        state = MarketDataRefreshRepository(self.session).get()
        now = datetime.now(UTC)
        heartbeat = state.worker_heartbeat_at if state else None
        if heartbeat and heartbeat.tzinfo is None:
            heartbeat = heartbeat.replace(tzinfo=UTC)
        if not state or not state.worker_running or not heartbeat or not 0 <= (now - heartbeat).total_seconds() <= 180:
            raise AdminMarketRefreshError(409, "Market-data worker is offline")
        if self.runs.pending():
            raise AdminMarketRefreshError(409, "A market-data refresh is already pending")
        row = self.runs.create(id=request.request_id, trigger="ADMIN", requested_by=actor_id, status="queued", requested_at=now)
        AuditLogService(self.session).record(AuditEventCreate(actor_kind="ADMIN", actor_user_id=actor_id,
            action="MARKET_REFRESH_REQUESTED", target_type="MARKET_REFRESH", target_id=row.id, details=AuditMarketRefreshDetails()))
        return run_response(row)

    def history(self, *, limit: int, offset: int) -> AdminMarketRefreshRunsResponse:
        rows, total = self.runs.list(limit=limit, offset=offset)
        return AdminMarketRefreshRunsResponse(items=[run_response(row) for row in rows], total=total, limit=limit, offset=offset)
