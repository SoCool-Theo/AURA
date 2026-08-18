"""Caller-transaction-owned persistence operations for Aura Users."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import User


class UserRepository:
    """Persist and retrieve User credentials without application processing."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_email(self, email: str) -> User | None:
        """Return the User matching an already-canonical email, if present."""
        statement = select(User).where(User.email == email)
        return self._session.scalars(statement).one_or_none()

    def create(self, *, email: str, password_hash: str) -> User:
        """Add and flush an already-canonical, already-hashed User."""
        user = User(email=email, password_hash=password_hash)
        self._session.add(user)
        self._session.flush()
        return user
