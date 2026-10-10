"""Internal event allowlist and read-only administration contracts."""

from datetime import UTC
from typing import Literal, Self
from uuid import UUID

from pydantic import AwareDatetime, Field, model_validator

from .common import AuraBaseModel


AuditAction = Literal["ADMIN_BOOTSTRAPPED"]
AuditActorKind = Literal["OPERATOR", "ADMIN"]
AuditTargetType = Literal["USER"]


class AuditRoleChangeDetails(AuraBaseModel):
    """No free text, credentials, tokens, or arbitrary nested metadata."""

    previous_role: Literal["CUSTOMER"]
    new_role: Literal["ADMIN"]


class AuditEventCreate(AuraBaseModel):
    """Trusted internal callers only; not an HTTP request model."""

    actor_kind: AuditActorKind
    actor_user_id: UUID | None = None
    action: AuditAction
    target_type: AuditTargetType
    target_id: UUID
    details: AuditRoleChangeDetails

    @model_validator(mode="after")
    def validate_actor(self) -> Self:
        if self.actor_kind != "OPERATOR" or self.actor_user_id is not None:
            raise ValueError("First-admin provisioning requires an operator actor")
        return self


class AuditLogQuery(AuraBaseModel):
    limit: int = Field(default=25, ge=1, le=100)
    offset: int = Field(default=0, ge=0, le=10000)
    action: AuditAction | None = None
    actor_kind: AuditActorKind | None = None
    actor_user_id: UUID | None = None
    target_type: AuditTargetType | None = None
    target_id: UUID | None = None
    created_from: AwareDatetime | None = None
    created_to: AwareDatetime | None = None

    @model_validator(mode="after")
    def validate_time_range(self) -> Self:
        if self.created_from is not None:
            self.created_from = self.created_from.astimezone(UTC)
        if self.created_to is not None:
            self.created_to = self.created_to.astimezone(UTC)
        if (
            self.created_from is not None
            and self.created_to is not None
            and self.created_from > self.created_to
        ):
            raise ValueError("created_from must be on or before created_to")
        return self


class AuditLogResponse(AuditEventCreate):
    id: UUID
    created_at: AwareDatetime


class AuditLogListResponse(AuraBaseModel):
    items: list[AuditLogResponse]
    total: int = Field(ge=0)
    limit: int
    offset: int
