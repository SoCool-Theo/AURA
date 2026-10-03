"""In-app inbox and account preference contracts."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import StrictBool

from .common import AuraBaseModel


class NotificationPreferencesResponse(AuraBaseModel):
    enabled: StrictBool = True
    analysis_enabled: StrictBool = True
    simulation_enabled: StrictBool = True


class NotificationPreferencesUpdate(AuraBaseModel):
    enabled: StrictBool
    analysis_enabled: StrictBool
    simulation_enabled: StrictBool


class NotificationResponse(AuraBaseModel):
    id: UUID
    kind: Literal["analysis", "simulation"]
    title: str
    message: str
    portfolio_id: UUID
    resource_id: UUID
    created_at: datetime
    read_at: datetime | None


class NotificationListResponse(AuraBaseModel):
    items: list[NotificationResponse]
    total: int
    unread_count: int
