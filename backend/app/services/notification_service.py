"""Account preferences and notifications from successfully saved resources."""

from typing import Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database.models import Analysis, Portfolio, Simulation
from ..database.repositories.notification_repository import NotificationRepository
from ..schemas.notification import NotificationListResponse, NotificationPreferencesResponse, NotificationPreferencesUpdate, NotificationResponse


class NotificationService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._repository = NotificationRepository(session)

    def preferences(self, user_id: UUID) -> NotificationPreferencesResponse:
        saved = self._repository.preferences(user_id)
        if saved is None:
            return NotificationPreferencesResponse()
        return NotificationPreferencesResponse(enabled=saved.enabled, analysis_enabled=saved.analysis_enabled, simulation_enabled=saved.simulation_enabled)

    def update_preferences(self, user_id: UUID, request: NotificationPreferencesUpdate) -> NotificationPreferencesResponse:
        self._repository.save_preferences(user_id, request.model_dump())
        return NotificationPreferencesResponse(**request.model_dump())

    def record_saved(self, *, user_id: UUID, portfolio_id: UUID, kind: Literal["analysis", "simulation"], resource_id: UUID) -> None:
        # Never accept a client-authored message, URL, or another account's resource.
        model = Analysis if kind == "analysis" else Simulation
        owned = self._session.scalar(select(model.id).join(Portfolio, model.portfolio_id == Portfolio.id)
            .where(model.id == resource_id, Portfolio.id == portfolio_id, Portfolio.user_id == user_id))
        if owned is None:
            raise ValueError("Saved notification resource not found")
        prefs = self.preferences(user_id)
        category_enabled = prefs.analysis_enabled if kind == "analysis" else prefs.simulation_enabled
        if prefs.enabled and category_enabled:
            self._repository.record(user_id=user_id, portfolio_id=portfolio_id, kind=kind, resource_id=resource_id)

    def list(self, user_id: UUID, *, limit: int, offset: int) -> NotificationListResponse:
        total, unread = self._repository.counts(user_id)
        items = self._repository.list(user_id, limit=limit, offset=offset)
        return NotificationListResponse(total=total, unread_count=unread, items=[NotificationResponse(
            id=item.id, kind=item.kind,
            title="Analysis saved" if item.kind == "analysis" else "Simulation saved",
            message="Your analysis report is ready to view." if item.kind == "analysis" else "Your saved simulation is ready to view.",
            portfolio_id=item.portfolio_id, resource_id=item.report_id if item.kind == "analysis" else item.simulation_id,
            created_at=item.created_at, read_at=item.read_at,
        ) for item in items])

    def mark_read(self, user_id: UUID, notification_id: UUID) -> bool:
        return self._repository.mark_read(user_id, notification_id)

    def mark_all_read(self, user_id: UUID) -> None:
        self._repository.mark_all_read(user_id)
