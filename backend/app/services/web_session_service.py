"""Web refresh sessions with fixed maximum lifetime and one-use rotation."""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
import re
from uuid import UUID

from sqlalchemy.orm import Session

from ..core.config import settings
from ..core.security import create_access_token, generate_refresh_token, hash_refresh_token
from ..database.models import User, WebRefreshToken, WebSession
from ..database.repositories.web_session_repository import WebSessionRepository
from .auth_service import InvalidCredentialsError


class InvalidRefreshSessionError(Exception):
    """The refresh credential cannot renew a valid session."""


class RefreshConflictError(Exception):
    """A recent concurrent rotation must retry with the browser's latest cookie."""


@dataclass(frozen=True)
class WebSessionTokens:
    access_token: str = field(repr=False)
    refresh_token: str = field(repr=False)
    cookie_max_age: int


class WebSessionService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._repository = WebSessionRepository(session)

    def start(self, user: User, previous_token: str | None = None) -> WebSessionTokens:
        now = datetime.now(UTC)
        # Serialize issuance with password changes, then recheck authenticated credentials.
        password_hash = user.password_hash
        locked_user = self._repository.lock_user(user.id)
        if locked_user is None or locked_user.password_hash != password_hash:
            raise InvalidCredentialsError
        if previous_token:
            self.logout(previous_token)
        record = WebSession(
            user_id=user.id, created_at=now, last_activity_at=now,
            expires_at=now + timedelta(days=settings.refresh_session_max_days),
        )
        self._repository.add(record)
        return self._issue(record, now)

    def refresh(self, token: str | None) -> WebSessionTokens:
        digest = self._digest(token)
        record = self._repository.find_by_token_hash(digest) if digest else None
        if record is None:
            raise InvalidRefreshSessionError
        # Password changes take the same user lock before revoking sessions.
        if self._repository.lock_user(record.user_id) is None:
            raise InvalidRefreshSessionError
        record = self._repository.lock_session(record.id)
        now = datetime.now(UTC)
        if record is None or not self._active(record, now):
            raise InvalidRefreshSessionError
        previous = self._repository.get_token(digest)
        if previous is None:
            raise InvalidRefreshSessionError
        if previous.used_at is not None:
            # Never issue credentials for a used token. Brief races get a retryable
            # conflict; later replay revokes the entire original sign-in session.
            if now - previous.used_at < timedelta(seconds=5):
                raise RefreshConflictError
            record.revoked_at = now
            raise InvalidRefreshSessionError
        previous.used_at = now
        record.last_activity_at = max(record.last_activity_at, now)
        return self._issue(record, now)

    def logout(self, token: str | None, *, expected_session_id: UUID | None = None) -> bool:
        digest = self._digest(token)
        record = self._repository.find_by_token_hash(digest) if digest else None
        if record is not None and expected_session_id is not None and record.id != expected_session_id:
            return False
        if record is not None:
            record = self._repository.lock_session(record.id)
            if record is not None and record.revoked_at is None:
                record.revoked_at = datetime.now(UTC)
        return True

    def record_activity(self, session_id: UUID, user_id: UUID) -> bool:
        now = datetime.now(UTC)
        return self._repository.record_activity(
            session_id, user_id, now,
            now - timedelta(days=settings.refresh_session_idle_days),
        )

    def _active(self, record: WebSession, now: datetime) -> bool:
        return (
            record.revoked_at is None and now < record.expires_at
            and now < record.last_activity_at + timedelta(days=settings.refresh_session_idle_days)
        )

    def _issue(self, record: WebSession, now: datetime) -> WebSessionTokens:
        token = generate_refresh_token()
        self._repository.add(WebRefreshToken(
            token_hash=hash_refresh_token(token), session_id=record.id, created_at=now,
        ))
        cookie_expiration = min(
            record.expires_at, now + timedelta(days=settings.refresh_session_idle_days),
        )
        return WebSessionTokens(
            create_access_token(record.user_id, issued_at=now, session_id=record.id,
                                maximum_expires_at=record.expires_at),
            token, max(0, int((cookie_expiration - now).total_seconds())),
        )

    @staticmethod
    def _digest(token: str | None) -> str | None:
        if token is None or re.fullmatch(r"[A-Za-z0-9_-]{43}", token) is None:
            return None
        return hash_refresh_token(token)
