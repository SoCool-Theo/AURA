from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session

import backend.app.services.audit_log_service as module
from backend.app.database.models import AuditLog
from backend.app.schemas.audit_log import AuditEventCreate, AuditLogQuery


def payload() -> dict:
    return {
        "actor_kind": "OPERATOR", "action": "ADMIN_BOOTSTRAPPED",
        "target_type": "USER", "target_id": uuid4(),
        "details": {"previous_role": "CUSTOMER", "new_role": "ADMIN"},
    }


@pytest.mark.parametrize("secret_key", ["password", "password_hash", "token", "email", "details"])
def test_event_details_reject_unknown_or_sensitive_fields(secret_key: str) -> None:
    data = payload()
    data["details"][secret_key] = "private-value"
    with pytest.raises(ValidationError):
        AuditEventCreate.model_validate(data)


@pytest.mark.parametrize("change", [
    {"action": "password-secret"}, {"target_type": "TOKEN"}, {"actor_kind": "ADMIN", "actor_user_id": uuid4()},
    {"actor_user_id": uuid4()}, {"created_at": datetime.now(UTC)},
    {"details": {"previous_role": "CUSTOMER", "new_role": "password-secret"}},
])
def test_event_only_accepts_allowlisted_shape(change: dict) -> None:
    data = payload()
    data.update(change)
    with pytest.raises(ValidationError):
        AuditEventCreate.model_validate(data)


def test_recorder_revalidates_constructed_models_before_repository_call() -> None:
    session = MagicMock(spec=Session)
    with patch.object(module, "AuditLogRepository") as repository:
        service = module.AuditLogService(session)
        validated = AuditEventCreate.model_validate(payload())
        invalid = validated.model_copy(update={"action": "UNSUPPORTED"})
        with pytest.raises(ValidationError):
            service.record(invalid)
    repository.return_value.record.assert_not_called()


@pytest.mark.parametrize("query", [
    {"limit": 0}, {"limit": 101}, {"offset": -1}, {"offset": 10001},
    {"action": "UNKNOWN"}, {"target_type": "TOKEN"}, {"actor_kind": "CUSTOMER"},
    {"created_from": "2026-10-10T00:00:00"},
    {"created_from": "2026-10-11T00:00:00Z", "created_to": "2026-10-10T00:00:00Z"},
])
def test_query_rejects_invalid_filters(query: dict) -> None:
    with pytest.raises(ValidationError):
        AuditLogQuery(**query)


def test_query_normalizes_timezone_offsets() -> None:
    query = AuditLogQuery(created_from="2026-10-10T07:00:00+07:00", created_to="2026-10-10T00:00:00Z")
    assert query.created_from == query.created_to == datetime(2026, 10, 10, tzinfo=UTC)


def test_response_refuses_corrupted_secret_details() -> None:
    row = AuditLog(id=uuid4(), **payload(), created_at=datetime.now(UTC))
    row.details["token"] = "private-value"
    with patch.object(module, "AuditLogRepository") as repository:
        repository.return_value.list.return_value = ([row], 1)
        with pytest.raises(ValidationError):
            module.AuditLogService(MagicMock(spec=Session)).list(AuditLogQuery())
