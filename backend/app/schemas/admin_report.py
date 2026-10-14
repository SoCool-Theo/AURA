"""Read-only global saved-analysis report contracts."""

from datetime import UTC
from typing import Literal, Self
from uuid import UUID

from pydantic import AwareDatetime, Field, field_validator, model_validator

from .admin_portfolio import AdminPortfolioOwner
from .common import AnalysisPeriod, AuraBaseModel
from .reporting import PortfolioReportDetailResponse


AdminReportVersion = Literal["V1", "V2", "V3", "OTHER"]


class AdminReportsQuery(AuraBaseModel):
    limit: int = Field(default=25, ge=1, le=100)
    offset: int = Field(default=0, ge=0, le=10000)
    q: str | None = Field(default=None, max_length=100)
    owner_id: UUID | None = None
    portfolio_id: UUID | None = None
    report_version: AdminReportVersion | None = None
    created_from: AwareDatetime | None = None
    created_to: AwareDatetime | None = None

    @field_validator("q")
    @classmethod
    def trim_search(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None

    @model_validator(mode="after")
    def validate_time_range(self) -> Self:
        if self.created_from is not None:
            self.created_from = self.created_from.astimezone(UTC)
        if self.created_to is not None:
            self.created_to = self.created_to.astimezone(UTC)
        if self.created_from is not None and self.created_to is not None and self.created_from > self.created_to:
            raise ValueError("created_from must be on or before created_to")
        return self


class AdminReportSummary(AnalysisPeriod):
    id: UUID
    portfolio_id: UUID
    portfolio_name: str  # Current directory name; not an immutable report field.
    owner: AdminPortfolioOwner
    created_at: AwareDatetime
    schema_version: str
    report_version: AdminReportVersion


class AdminReportsResponse(AuraBaseModel):
    items: list[AdminReportSummary]
    total: int = Field(ge=0)
    limit: int
    offset: int


class AdminReportDetail(AdminReportSummary):
    report: PortfolioReportDetailResponse

    @model_validator(mode="after")
    def validate_snapshot_identity(self) -> Self:
        if (self.report.id, self.report.portfolio_id, self.report.created_at,
            self.report.analysis.start_date, self.report.analysis.end_date) != (
            self.id, self.portfolio_id, self.created_at, self.start_date, self.end_date
        ):
            raise ValueError("Report metadata must match saved detail")
        return self
