"""Owner-scoped persistence; the request owns commit/rollback."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from ..models.notification import Notification, NotificationPreferences


class NotificationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def preferences(self, user_id: UUID) -> NotificationPreferences | None:
        return self._session.get(NotificationPreferences, user_id)

    def save_preferences(self, user_id: UUID, values: dict[str, bool]) -> None:
        cached = self.preferences(user_id)
        statement = insert(NotificationPreferences).values(user_id=user_id, **values)
        self._session.execute(statement.on_conflict_do_update(index_elements=["user_id"], set_=values))
        self._session.flush()
        if cached is not None:
            self._session.expire(cached)

    def record(self, *, user_id: UUID, portfolio_id: UUID, kind: str, resource_id: UUID) -> None:
        # The target's unique key makes repeated recording of one saved resource safe.
        target = "report_id" if kind == "analysis" else "simulation_id"
        statement = insert(Notification).values(user_id=user_id, portfolio_id=portfolio_id, kind=kind, **{target: resource_id})
        self._session.execute(statement.on_conflict_do_nothing(index_elements=[target]))
        self._session.flush()

    def list(self, user_id: UUID, *, limit: int, offset: int) -> list[Notification]:
        return list(self._session.scalars(select(Notification).where(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc(), Notification.id.desc()).offset(offset).limit(limit)).all())

    def counts(self, user_id: UUID) -> tuple[int, int]:
        total, unread = self._session.execute(select(func.count(Notification.id), func.count(Notification.id).filter(Notification.read_at.is_(None)))
            .where(Notification.user_id == user_id)).one()
        return total, unread

    def mark_read(self, user_id: UUID, notification_id: UUID) -> bool:
        item = self._session.scalars(select(Notification).where(Notification.user_id == user_id, Notification.id == notification_id)).one_or_none()
        if item is None:
            return False
        if item.read_at is None:
            item.read_at = datetime.now(UTC)
            self._session.flush()
        return True

    def mark_all_read(self, user_id: UUID) -> None:
        self._session.execute(update(Notification).where(Notification.user_id == user_id, Notification.read_at.is_(None)).values(read_at=datetime.now(UTC)))
        self._session.flush()

    def clear(self, user_id: UUID, notification_id: UUID) -> bool:
        """Remove only the owned inbox entry, never its linked saved result."""
        removed = self._session.execute(
            delete(Notification).where(
                Notification.user_id == user_id,
                Notification.id == notification_id,
            ).returning(Notification.id)
        ).scalar_one_or_none()
        self._session.flush()
        return removed is not None

    def clear_all(self, user_id: UUID) -> None:
        """Clear all pages of this account's inbox without touching preferences."""
        self._session.execute(delete(Notification).where(Notification.user_id == user_id))
        self._session.flush()
