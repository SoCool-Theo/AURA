"""Read-only administrator projections of retained portfolios."""

from uuid import UUID

from pydantic import Field, field_validator

from .admin import AdminAccountStatus, AdminAccountType
from .auth import CanonicalEmail
from .common import AuraBaseModel
from .portfolio import PortfolioResponse, PortfolioSummaryResponse
from ..database.models.portfolio import PortfolioType


class AdminPortfoliosQuery(AuraBaseModel):
    limit: int = Field(default=25, ge=1, le=100)
    offset: int = Field(default=0, ge=0, le=10000)
    q: str | None = Field(default=None, max_length=100)
    portfolio_type: PortfolioType | None = None
    owner_id: UUID | None = None

    @field_validator("q")
    @classmethod
    def trim_search(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None


class AdminPortfolioOwner(AuraBaseModel):
    id: UUID
    email: CanonicalEmail | None
    display_name: str | None
    account_type: AdminAccountType
    status: AdminAccountStatus


class AdminPortfolioSummary(PortfolioSummaryResponse):
    owner: AdminPortfolioOwner
    holding_count: int = Field(ge=0)
    saved_report_count: int = Field(ge=0)
    saved_simulation_count: int = Field(ge=0)


class AdminPortfoliosResponse(AuraBaseModel):
    items: list[AdminPortfolioSummary]
    total: int = Field(ge=0)
    limit: int
    offset: int


class AdminPortfolioDetail(PortfolioResponse):
    owner: AdminPortfolioOwner
    holding_count: int = Field(ge=0)
    saved_report_count: int = Field(ge=0)
    saved_simulation_count: int = Field(ge=0)
