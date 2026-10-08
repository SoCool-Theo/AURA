"""Read-only, credential-free daily market-data operational status."""

from datetime import date
from typing import Annotated, Literal

from pydantic import AwareDatetime, Field

from .common import AuraBaseModel


class MarketObservationStatus(AuraBaseModel):
    symbol: str
    kind: Literal["asset", "fx"]
    latest_price_date: date | None
    age_days: Annotated[int, Field(ge=0)] | None
    is_current: bool


class MarketDataStatusResponse(AuraBaseModel):
    mode: Literal["daily"] = "daily"
    checked_at: AwareDatetime
    update_time_utc: str
    next_scheduled_at: AwareDatetime
    worker_status: Literal["unknown", "online", "offline"]
    worker_last_seen_at: AwareDatetime | None
    last_run_status: Literal["never", "running", "success", "partial", "failed"]
    last_attempt_at: AwareDatetime | None
    last_finished_at: AwareDatetime | None
    last_complete_at: AwareDatetime | None
    attempt_count: Annotated[int, Field(ge=0)]
    stored_count: Annotated[int, Field(ge=0)]
    updated_symbols: list[str]
    failed_symbols: list[str]
    error_code: Literal["provider_unavailable", "database_unavailable", "validation_failed", "update_failed", "lock_lost", "incomplete_coverage"] | None
    data_status: Literal["current", "stale", "missing"]
    observations: list[MarketObservationStatus]
