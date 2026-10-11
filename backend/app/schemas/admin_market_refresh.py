"""Safe fixed-universe refresh requests and persisted operational outcomes."""

from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, Field

from .common import AuraBaseModel


class AdminMarketRefreshRequest(AuraBaseModel):
    request_id: UUID


class AdminMarketRefreshRunResponse(AuraBaseModel):
    id: UUID
    trigger: Literal["ADMIN", "SCHEDULED", "CATCH_UP", "OPERATOR"]
    requested_by: UUID | None
    status: Literal["queued", "running", "success", "partial", "failed"]
    requested_at: AwareDatetime
    started_at: AwareDatetime | None
    finished_at: AwareDatetime | None
    attempt_count: int = Field(ge=0)
    stored_count: int = Field(ge=0)
    updated_symbols: list[str]
    failed_symbols: list[str]
    error_code: Literal["provider_unavailable", "database_unavailable", "validation_failed", "update_failed", "lock_lost", "incomplete_coverage", "authorization_changed"] | None


class AdminMarketRefreshRunsResponse(AuraBaseModel):
    items: list[AdminMarketRefreshRunResponse]
    total: int = Field(ge=0)
    limit: int
    offset: int
