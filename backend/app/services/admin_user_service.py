"""Account status changes and audit recording in the caller's transaction."""

from datetime import UTC
from uuid import UUID

from sqlalchemy.orm import Session

from ..database.models import User
from ..database.repositories.user_repository import UserRepository
from ..schemas.admin import AdminUserStatusRequest, AdminUserStatusResponse
from ..schemas.audit_log import AuditEventCreate, AuditStatusChangeDetails
from .audit_log_service import AuditLogService


class AdminUserStatusError(ValueError):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        super().__init__(detail)


class AdminUserService:
    def __init__(self, session: Session) -> None:
        self._repository = UserRepository(session)
        self._audit = AuditLogService(session)

    def set_status(self, actor: User, user_id: UUID, request: AdminUserStatusRequest) -> AdminUserStatusResponse:
        request = AdminUserStatusRequest.model_validate(request.model_dump())
        # Preserve the authenticated session generation before refreshing the
        # identity map: a suspend/reactivate race must not revive an old caller.
        actor_id, actor_version = actor.id, actor.auth_version or 0
        self._repository.lock_account_status_changes()
        current_actor = self._repository.get_current_by_id(actor_id)
        if current_actor is None or current_actor.is_suspended or (current_actor.auth_version or 0) != actor_version:
            raise AdminUserStatusError(401, "Invalid or missing authentication credentials")
        if current_actor.role != "ADMIN" or not current_actor.email or not current_actor.password_hash:
            raise AdminUserStatusError(403, "Administrator access required")
        user = self._repository.get_current_by_id(user_id)
        if user is None:
            raise AdminUserStatusError(404, "Account not found")
        previous = "SUSPENDED" if user.is_suspended else "ACTIVE"
        if user.id == actor_id and request.status == "SUSPENDED":
            raise AdminUserStatusError(409, "You cannot suspend your own account")
        if previous == request.status:
            # Idempotent retries never duplicate an event or revoke sessions twice.
            return self._response(user)
        if previous != request.expected_status:
            raise AdminUserStatusError(409, "Account status changed. Refresh the directory and try again")
        if request.status == "SUSPENDED" and user.role == "ADMIN" and not self._repository.has_other_active_admin(user.id):
            raise AdminUserStatusError(409, "The last active administrator cannot be suspended")
        self._repository.set_suspension(user, suspended=request.status == "SUSPENDED")
        self._audit.record(AuditEventCreate(
            actor_kind="ADMIN", actor_user_id=actor_id,
            action="USER_SUSPENDED" if request.status == "SUSPENDED" else "USER_REACTIVATED",
            target_type="USER", target_id=user.id,
            details=AuditStatusChangeDetails(previous_status=previous, new_status=request.status),
        ))
        return self._response(user)

    @staticmethod
    def _response(user: User) -> AdminUserStatusResponse:
        timestamp = user.updated_at
        timestamp = timestamp.replace(tzinfo=UTC) if timestamp.tzinfo is None else timestamp.astimezone(UTC)
        return AdminUserStatusResponse(id=user.id, status="SUSPENDED" if user.is_suspended else "ACTIVE", updated_at=timestamp)
