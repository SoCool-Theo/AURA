"""Administrator-only identity contract; customer contracts remain unchanged."""

from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, Field, field_validator

from .auth import CanonicalEmail
from .common import AuraBaseModel


class AdminIdentityResponse(AuraBaseModel):
    id: UUID
    email: CanonicalEmail
    display_name: str | None
    role: Literal["ADMIN"]


AdminUserRole = Literal["CUSTOMER", "ADMIN"]
AdminAccountType = Literal["REGISTERED", "LEGACY"]


class AdminUsersQuery(AuraBaseModel):
    limit: int = Field(default=25, ge=1, le=100)
    offset: int = Field(default=0, ge=0, le=10000)
    q: str | None = Field(default=None, max_length=100)
    role: AdminUserRole | None = None
    account_type: AdminAccountType | None = None

    @field_validator("q")
    @classmethod
    def trim_search(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None


class AdminUserResponse(AuraBaseModel):
    id: UUID
    email: CanonicalEmail | None
    display_name: str | None
    role: AdminUserRole
    account_type: AdminAccountType
    created_at: AwareDatetime
    updated_at: AwareDatetime
    portfolio_count: int = Field(ge=0)


class AdminUsersListResponse(AuraBaseModel):
    items: list[AdminUserResponse]
    total: int = Field(ge=0)
    limit: int
    offset: int


class AdminUserCounts(AuraBaseModel):
    total: int = Field(ge=0)
    customers: int = Field(ge=0)
    admins: int = Field(ge=0)
    registered: int = Field(ge=0)
    legacy: int = Field(ge=0)
    new_last_7_days: int = Field(ge=0)


class AdminPortfolioCounts(AuraBaseModel):
    total: int = Field(ge=0)
    current: int = Field(ge=0)
    planned: int = Field(ge=0)
    legacy: int = Field(ge=0)
    new_last_7_days: int = Field(ge=0)


class AdminSavedResultCounts(AuraBaseModel):
    total: int = Field(ge=0)
    today: int = Field(ge=0)
    yesterday: int = Field(ge=0)
    last_7_days: int = Field(ge=0)


class AdminDashboardDay(AuraBaseModel):
    date: date
    new_users: int = Field(ge=0)
    new_portfolios: int = Field(ge=0)
    saved_reports: int = Field(ge=0)
    saved_simulations: int = Field(ge=0)


class AdminDashboardResponse(AuraBaseModel):
    generated_at: AwareDatetime
    timezone: Literal["UTC"] = "UTC"
    window_start: date
    window_end: date
    users: AdminUserCounts
    portfolios: AdminPortfolioCounts
    saved_reports: AdminSavedResultCounts
    saved_simulations: AdminSavedResultCounts
    daily: list[AdminDashboardDay]
