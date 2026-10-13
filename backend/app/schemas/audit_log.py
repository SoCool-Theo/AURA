"""Internal event allowlist and read-only administration contracts."""

from datetime import UTC
from typing import Literal, Self
from uuid import UUID

from pydantic import AwareDatetime, Field, model_validator

from .common import AuraBaseModel


AuditAction = Literal["ADMIN_BOOTSTRAPPED", "USER_SUSPENDED", "USER_REACTIVATED", "MARKET_REFRESH_REQUESTED", "USER_ROLE_CHANGED"]
AuditActorKind = Literal["OPERATOR", "ADMIN"]
AuditTargetType = Literal["USER", "MARKET_REFRESH"]


class AuditRoleChangeDetails(AuraBaseModel):
    """No free text, credentials, tokens, or arbitrary nested metadata."""

    previous_role: Literal["CUSTOMER", "ADMIN"]
    new_role: Literal["CUSTOMER", "ADMIN"]


class AuditStatusChangeDetails(AuraBaseModel):
    previous_status: Literal["ACTIVE", "SUSPENDED"]
    new_status: Literal["ACTIVE", "SUSPENDED"]


class AuditMarketRefreshDetails(AuraBaseModel):
    mode: Literal["daily"] = "daily"


class AuditEventCreate(AuraBaseModel):
    """Trusted internal callers only; not an HTTP request model."""

    actor_kind: AuditActorKind
    actor_user_id: UUID | None = None
    action: AuditAction
    target_type: AuditTargetType
    target_id: UUID
    details: AuditRoleChangeDetails | AuditStatusChangeDetails | AuditMarketRefreshDetails

    @model_validator(mode="after")
    def validate_actor(self) -> Self:
        if self.action == "MARKET_REFRESH_REQUESTED":
            if self.actor_kind != "ADMIN" or self.actor_user_id is None or self.target_type != "MARKET_REFRESH" or not isinstance(self.details, AuditMarketRefreshDetails):
                raise ValueError("Refresh requests require administrator, refresh target and daily mode")
            return self
        if self.target_type != "USER":
            raise ValueError("Account changes require a user target")
        if self.action == "ADMIN_BOOTSTRAPPED":
            if self.actor_kind != "OPERATOR" or self.actor_user_id is not None:
                raise ValueError("First-admin provisioning requires an operator actor")
            if not isinstance(self.details, AuditRoleChangeDetails) or (self.details.previous_role, self.details.new_role) != ("CUSTOMER", "ADMIN"):
                raise ValueError("Bootstrap requires role details")
        elif self.action == "USER_ROLE_CHANGED":
            if self.actor_kind != "ADMIN" or self.actor_user_id is None:
                raise ValueError("Role changes require an administrator actor")
            if not isinstance(self.details, AuditRoleChangeDetails) or self.details.previous_role == self.details.new_role:
                raise ValueError("Role details must describe a transition")
        else:
            if self.actor_kind != "ADMIN" or self.actor_user_id is None:
                raise ValueError("Status changes require an administrator actor")
            expected = ("ACTIVE", "SUSPENDED") if self.action == "USER_SUSPENDED" else ("SUSPENDED", "ACTIVE")
            if not isinstance(self.details, AuditStatusChangeDetails) or (
                self.details.previous_status, self.details.new_status
            ) != expected:
                raise ValueError("Status details must match the action")
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
