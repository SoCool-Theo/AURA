"""Operator-only bootstrap within a caller-owned transaction."""

from uuid import UUID

from sqlalchemy.orm import Session

from ..database.models import User
from ..database.repositories.user_repository import UserRepository


class AdminBootstrapError(ValueError):
    """First-admin provisioning cannot safely proceed."""


class AdminAccessService:
    def __init__(self, session: Session) -> None:
        self._repository = UserRepository(session)

    def bootstrap_first_admin(self, user_id: UUID) -> User:
        """Promote one existing account; concurrent attempts are serialized."""
        self._repository.lock_admin_bootstrap()
        user = self._repository.get_by_id(user_id)
        if user is None or not user.email or not user.password_hash:
            raise AdminBootstrapError("An existing credential-bearing account is required")
        if self._repository.has_other_admin(user_id):
            raise AdminBootstrapError("An administrator already exists; bootstrap is closed")
        if user.role == "ADMIN":
            return user
        if user.role != "CUSTOMER":
            raise AdminBootstrapError("Account role is not eligible for bootstrap")
        self._repository.promote_to_admin(user)
        return user
