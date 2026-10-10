from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

import backend.app.services.admin_access_service as module
from backend.app.database.models import User


@pytest.fixture
def harness():
    session = MagicMock(spec=Session)
    repository = MagicMock(spec=module.UserRepository)
    user = User(id=uuid4(), email="admin@example.com", password_hash="encoded", role="CUSTOMER")
    repository.get_by_id.return_value = user
    repository.has_other_admin.return_value = False
    with (
        patch.object(module, "UserRepository", return_value=repository),
        patch.object(module, "AuditLogService"),
    ):
        yield module.AdminAccessService(session), session, repository, user


def test_bootstrap_locks_before_query_and_leaves_transaction_to_caller(harness):
    service, session, repository, user = harness
    assert service.bootstrap_first_admin(user.id) is user
    assert repository.mock_calls == [
        (("lock_admin_bootstrap", (), {})),
        (("get_by_id", (user.id,), {})),
        (("has_other_admin", (user.id,), {})),
        (("promote_to_admin", (user,), {})),
    ]
    session.commit.assert_not_called()
    session.rollback.assert_not_called()
    session.close.assert_not_called()
    payload = service._audit.record.call_args.args[0]
    assert payload.actor_kind == "OPERATOR" and payload.actor_user_id is None
    assert payload.target_id == user.id and payload.action == "ADMIN_BOOTSTRAPPED"
    assert payload.details.model_dump() == {"previous_role": "CUSTOMER", "new_role": "ADMIN"}


@pytest.mark.parametrize("invalid", ["missing", "email", "password_hash", "role", "other_admin"])
def test_bootstrap_refuses_unsafe_account_or_second_admin(harness, invalid):
    service, session, repository, user = harness
    if invalid == "missing":
        repository.get_by_id.return_value = None
    elif invalid == "other_admin":
        repository.has_other_admin.return_value = True
    elif invalid == "role":
        user.role = "OWNER"
    else:
        setattr(user, invalid, None)
    with pytest.raises(module.AdminBootstrapError):
        service.bootstrap_first_admin(user.id)
    repository.promote_to_admin.assert_not_called()
    service._audit.record.assert_not_called()
    session.commit.assert_not_called()


def test_same_first_admin_is_idempotent(harness):
    service, _, repository, user = harness
    user.role = "ADMIN"
    assert service.bootstrap_first_admin(user.id) is user
    repository.promote_to_admin.assert_not_called()
    service._audit.record.assert_not_called()
