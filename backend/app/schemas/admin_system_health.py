"""Evidence-based operational checks; unprobed services never claim health."""

from typing import Annotated, Literal

from pydantic import AwareDatetime, Field

from .common import AuraBaseModel
from .market_data_status import MarketDataStatusResponse


HealthComponent = Literal[
    "api", "authentication", "database", "market_data_worker", "market_data", "market_data_refresh",
    "market_data_provider", "analytics",
]
HealthStatus = Literal["healthy", "degraded", "unavailable", "unknown", "not_checked"]
HealthReason = Literal[
    "request_received", "admin_authorized", "database_query_succeeded",
    "database_query_failed", "database_unavailable", "worker_online",
    "worker_offline", "worker_unknown", "observations_current",
    "observations_stale", "observations_missing", "market_status_unavailable",
    "refresh_never_run", "refresh_running", "refresh_success", "refresh_partial",
    "refresh_failed", "probe_not_run",
]


class AdminHealthCheck(AuraBaseModel):
    component: HealthComponent
    status: HealthStatus
    reason: HealthReason
    latency_ms: Annotated[float, Field(ge=0, allow_inf_nan=False)] | None = None


class AdminSystemHealthResponse(AuraBaseModel):
    checked_at: AwareDatetime
    status: Literal["healthy", "degraded", "unavailable", "unknown"]
    coverage: Literal["partial"] = "partial"
    checks: list[AdminHealthCheck]
    market_data: MarketDataStatusResponse | None
