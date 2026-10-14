"""Caller-owned transactions for web-session persistence and row locking."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from ..models import User, WebRefreshToken, WebSession


class WebSessionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_by_token_hash(self, token_hash: str) -> WebSession | None:
        return self._session.scalar(
            select(WebSession).join(WebRefreshToken).where(WebRefreshToken.token_hash == token_hash)
        )

    def lock_user(self, user_id: UUID) -> User | None:
        return self._session.scalar(
            select(User).where(User.id == user_id).with_for_update()
            .execution_options(populate_existing=True)
        )

    def lock_session(self, session_id: UUID) -> WebSession | None:
        return self._session.scalar(
            select(WebSession).where(WebSession.id == session_id).with_for_update()
            .execution_options(populate_existing=True)
        )

    def get_token(self, token_hash: str) -> WebRefreshToken | None:
        return self._session.get(WebRefreshToken, token_hash, populate_existing=True)

    def add(self, record: WebSession | WebRefreshToken) -> None:
        self._session.add(record)
        self._session.flush()

    def revoke_for_user(self, user_id: UUID, now: datetime) -> None:
        self._session.execute(
            update(WebSession).where(WebSession.user_id == user_id, WebSession.revoked_at.is_(None))
            .values(revoked_at=now)
        )

    def record_activity(self, session_id: UUID, user_id: UUID, now: datetime, cutoff: datetime) -> bool:
        """Atomically reject expired/revoked sessions before extending activity."""
        return self._session.scalar(
            update(WebSession).where(
                WebSession.id == session_id, WebSession.user_id == user_id,
                WebSession.revoked_at.is_(None), WebSession.expires_at > now,
                WebSession.last_activity_at > cutoff,
            ).values(last_activity_at=func.greatest(WebSession.last_activity_at, now))
            .returning(WebSession.id)
        ) is not None
