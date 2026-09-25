"""Caller-transaction-owned persistence operations for Aura Users."""

from collections.abc import Mapping
from typing import Any

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

    def update_profile(
        self,
        user: User,
        changes: Mapping[str, Any],
    ) -> User:
        """Apply service-approved profile fields and flush without committing."""
        allowed_fields = {
            "display_name",
            "email",
            "phone_number",
            "preferred_language",
            "timezone",
        }
        unexpected = set(changes) - allowed_fields
        if unexpected:
            raise ValueError(f"unsupported User profile fields: {unexpected}")
        for field, value in changes.items():
            setattr(user, field, value)
        self._session.flush()
        return user

    def update_password(self, user: User, *, password_hash: str) -> None:
        """Replace one already-validated password hash without committing."""
        user.password_hash = password_hash
        self._session.flush()
