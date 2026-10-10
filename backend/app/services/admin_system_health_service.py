"""Aggregate observed checks without provider requests, calculations, or writes."""

from datetime import UTC, datetime
from time import perf_counter

from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..database.repositories.admin_system_health_repository import AdminSystemHealthRepository
from ..schemas.admin_system_health import AdminHealthCheck, AdminSystemHealthResponse
from .market_data_status_service import MarketDataStatusService


class AdminSystemHealthService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._repository = AdminSystemHealthRepository(session)

    def get(self) -> AdminSystemHealthResponse:
        now = datetime.now(UTC)
        # This service is called only after the router's persisted-role guard.
        # These two observations concern this request, not uptime or login POST.
        checks = [
            AdminHealthCheck(component="api", status="healthy", reason="request_received"),
            AdminHealthCheck(component="authentication", status="healthy", reason="admin_authorized"),
        ]
        started = perf_counter()
        try:
            database_ok = self._repository.database_responds()
        except SQLAlchemyError:
            database_ok = False
        checks.append(AdminHealthCheck(
            component="database", status="healthy" if database_ok else "unavailable",
            reason="database_query_succeeded" if database_ok else "database_query_failed",
            latency_ms=round((perf_counter() - started) * 1000, 3),
        ))
        market = None
        if not database_ok:
            # A failed PostgreSQL transaction cannot safely perform more reads.
            # Its lifecycle/rollback stays with the request's session owner.
            checks.extend([
                AdminHealthCheck(component="market_data_worker", status="unknown", reason="database_unavailable"),
                AdminHealthCheck(component="market_data", status="unknown", reason="database_unavailable"),
                AdminHealthCheck(component="market_data_refresh", status="unknown", reason="database_unavailable"),
            ])
        else:
            try:
                market = MarketDataStatusService(self._session).get(now=now)
            except (SQLAlchemyError, ValidationError):
                checks.extend([
                    AdminHealthCheck(component="market_data_worker", status="unavailable", reason="market_status_unavailable"),
                    AdminHealthCheck(component="market_data", status="unavailable", reason="market_status_unavailable"),
                    AdminHealthCheck(component="market_data_refresh", status="unavailable", reason="market_status_unavailable"),
                ])
            else:
                checks.append(AdminHealthCheck(
                    component="market_data_worker",
                    status={"online": "healthy", "offline": "degraded", "unknown": "unknown"}[market.worker_status],
                    reason={"online": "worker_online", "offline": "worker_offline", "unknown": "worker_unknown"}[market.worker_status],
                ))
                checks.append(AdminHealthCheck(
                    component="market_data",
                    status="healthy" if market.data_status == "current" else "degraded",
                    reason={"current": "observations_current", "stale": "observations_stale", "missing": "observations_missing"}[market.data_status],
                ))
                checks.append(AdminHealthCheck(
                    component="market_data_refresh",
                    status={"never": "unknown", "running": "unknown", "success": "healthy",
                            "partial": "degraded", "failed": "degraded"}[market.last_run_status],
                    reason={"never": "refresh_never_run", "running": "refresh_running", "success": "refresh_success",
                            "partial": "refresh_partial", "failed": "refresh_failed"}[market.last_run_status],
                ))
        checks.extend([
            AdminHealthCheck(component="market_data_provider", status="not_checked", reason="probe_not_run"),
            AdminHealthCheck(component="analytics", status="not_checked", reason="probe_not_run"),
        ])
        if not database_ok:
            status = "unavailable"
        elif any(check.status in {"degraded", "unavailable"} for check in checks):
            status = "degraded"
        elif any(check.status == "unknown" for check in checks):
            status = "unknown"
        else:
            status = "healthy"
        return AdminSystemHealthResponse(checked_at=now, status=status, checks=checks, market_data=market)
