"""Account access changes and audit recording in the caller's transaction."""

from datetime import UTC
from uuid import UUID

from sqlalchemy.orm import Session

from ..database.models import User
from ..database.repositories.user_repository import UserRepository
from ..schemas.admin import AdminUserStatusRequest, AdminUserStatusResponse, AdminUserRoleRequest, AdminUserRoleResponse, AdminUserCreateRequest, AdminUserResponse
from ..schemas.audit_log import AuditEventCreate, AuditStatusChangeDetails, AuditRoleChangeDetails, AuditUserCreatedDetails
from ..schemas.auth import RegistrationRequest
from .audit_log_service import AuditLogService
from .auth_service import AuthService


class AdminUserStatusError(ValueError):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        super().__init__(detail)


class AdminUserService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._repository = UserRepository(session)
        self._audit = AuditLogService(session)

    def create(self, actor: User, request: AdminUserCreateRequest) -> AdminUserResponse:
        request = AdminUserCreateRequest.model_validate(request.model_dump())
        actor_id = self._authorize_actor(actor)
        user = AuthService(self._session).register(RegistrationRequest(email=request.email, password=request.password))
        if request.display_name is not None:
            self._repository.update_profile(user, {"display_name": request.display_name})
        self._audit.record(AuditEventCreate(actor_kind="ADMIN", actor_user_id=actor_id, action="USER_CREATED",
            target_type="USER", target_id=user.id, details=AuditUserCreatedDetails(role="CUSTOMER", account_type="REGISTERED")))
        created = user.created_at.replace(tzinfo=UTC) if user.created_at.tzinfo is None else user.created_at.astimezone(UTC)
        updated = user.updated_at.replace(tzinfo=UTC) if user.updated_at.tzinfo is None else user.updated_at.astimezone(UTC)
        return AdminUserResponse(id=user.id, email=user.email, display_name=user.display_name, role="CUSTOMER",
            account_type="REGISTERED", status="ACTIVE", created_at=created, updated_at=updated, portfolio_count=0)

    def set_status(self, actor: User, user_id: UUID, request: AdminUserStatusRequest) -> AdminUserStatusResponse:
        request = AdminUserStatusRequest.model_validate(request.model_dump())
        actor_id = self._authorize_actor(actor)
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

    def set_role(self, actor: User, user_id: UUID, request: AdminUserRoleRequest) -> AdminUserRoleResponse:
        request = AdminUserRoleRequest.model_validate(request.model_dump())
        actor_id = self._authorize_actor(actor)
        user = self._repository.get_current_by_id(user_id)
        if user is None:
            raise AdminUserStatusError(404, "Account not found")
        previous = user.role
        if user.id == actor_id and request.role == "CUSTOMER":
            raise AdminUserStatusError(409, "You cannot remove your own administrator access")
        if previous == request.role:
            return self._role_response(user)
        if previous != request.expected_role:
            raise AdminUserStatusError(409, "Account role changed. Refresh the directory and try again")
        if request.role == "ADMIN" and (not user.email or not user.password_hash):
            raise AdminUserStatusError(409, "Only registered accounts can become administrators")
        if request.role == "ADMIN" and user.is_suspended:
            raise AdminUserStatusError(409, "Reactivate the account before granting administrator access")
        if request.role == "CUSTOMER" and not self._repository.has_other_active_admin(user.id):
            raise AdminUserStatusError(409, "The last active administrator cannot be demoted")
        self._repository.set_role(user, role=request.role)
        self._audit.record(AuditEventCreate(actor_kind="ADMIN", actor_user_id=actor_id,
            action="USER_ROLE_CHANGED", target_type="USER", target_id=user.id,
            details=AuditRoleChangeDetails(previous_role=previous, new_role=request.role)))
        return self._role_response(user)

    def _authorize_actor(self, actor: User) -> UUID:
        # Preserve the authenticated session generation before refreshing the
        # identity map: a suspend/reactivate race must not revive an old caller.
        actor_id, actor_version = actor.id, actor.auth_version or 0
        self._repository.lock_account_status_changes()
        current_actor = self._repository.get_current_by_id(actor_id)
        if current_actor is None or current_actor.is_suspended or (current_actor.auth_version or 0) != actor_version:
            raise AdminUserStatusError(401, "Invalid or missing authentication credentials")
        if current_actor.role != "ADMIN" or not current_actor.email or not current_actor.password_hash:
            raise AdminUserStatusError(403, "Administrator access required")
        return actor_id

    @staticmethod
    def _role_response(user: User) -> AdminUserRoleResponse:
        timestamp = user.updated_at
        timestamp = timestamp.replace(tzinfo=UTC) if timestamp.tzinfo is None else timestamp.astimezone(UTC)
        return AdminUserRoleResponse(id=user.id, role=user.role, updated_at=timestamp)

    @staticmethod
    def _response(user: User) -> AdminUserStatusResponse:
        timestamp = user.updated_at
        timestamp = timestamp.replace(tzinfo=UTC) if timestamp.tzinfo is None else timestamp.astimezone(UTC)
        return AdminUserStatusResponse(id=user.id, status="SUSPENDED" if user.is_suspended else "ACTIVE", updated_at=timestamp)
