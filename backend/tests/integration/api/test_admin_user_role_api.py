"""Role permissions, fresh login, protected transitions and audit atomicity."""

from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database.models import AuditLog, Portfolio, User
from app.database.repositories.user_repository import UserRepository
from app.services.audit_log_service import AuditLogService
from backend.tests.integration.api.test_admin_user_status_api import PASSWORD, bearer, harness


def change(client, target=2, role="ADMIN", expected="CUSTOMER", headers=None):
    return client.patch(f"/api/admin/users/{UUID(int=target)}/role", headers=headers if headers is not None else bearer(),
                        json={"role": role, "expected_role": expected})


def login(client, email):
    response = client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_promotion_demotion_and_repromotion_never_upgrade_or_revive_old_tokens(harness):
    client, factory = harness
    old_customer = bearer(2)
    response = change(client)
    assert response.status_code == 200
    assert set(response.json()) == {"id", "role", "updated_at"}
    assert response.json()["role"] == "ADMIN"
    assert client.get("/api/auth/me", headers=old_customer).status_code == 401
    assert client.get("/api/admin/me", headers=old_customer).status_code == 401
    promoted = login(client, "customer@example.com")
    assert client.get("/api/admin/me", headers=promoted).status_code == 200
    assert change(client).status_code == 200  # Lost-response retry, no additional audit/version.
    with factory() as session:
        assert session.get(User, UUID(int=2)).auth_version == 1
        assert len(session.scalars(select(AuditLog)).all()) == 1
    assert change(client, role="CUSTOMER", expected="ADMIN").status_code == 200
    assert client.get("/api/admin/me", headers=promoted).status_code == 401
    demoted = login(client, "customer@example.com")
    assert client.get("/api/auth/me", headers=demoted).status_code == 200
    assert client.get("/api/admin/me", headers=demoted).status_code == 403
    assert change(client).status_code == 200
    assert client.get("/api/admin/me", headers=promoted).status_code == 401
    assert client.get("/api/admin/me", headers=demoted).status_code == 401
    with factory() as session:
        assert session.get(User, UUID(int=2)).auth_version == 3
    audit = client.get("/api/admin/audit-logs", headers=bearer(), params={"action": "USER_ROLE_CHANGED"}).json()
    assert audit["total"] == 3
    assert all(item["actor_user_id"] == str(UUID(int=1)) and item["target_id"] == str(UUID(int=2)) for item in audit["items"])
    assert {tuple(item["details"].values()) for item in audit["items"]} == {("CUSTOMER", "ADMIN"), ("ADMIN", "CUSTOMER")}


def test_self_demotion_and_last_active_admin_safeguards(harness):
    client, factory = harness
    assert change(client, target=1, role="CUSTOMER", expected="ADMIN").status_code == 409
    assert change(client, target=1, role="ADMIN", expected="ADMIN").status_code == 200
    with patch.object(UserRepository, "has_other_active_admin", return_value=False):
        assert change(client, target=4, role="CUSTOMER", expected="ADMIN").status_code == 409
    with factory() as session:
        assert session.get(User, UUID(int=1)).role == "ADMIN"
        assert session.get(User, UUID(int=4)).role == "ADMIN"
        assert session.scalar(select(AuditLog.id)) is None


def test_legacy_and_suspended_accounts_cannot_be_promoted(harness):
    client, factory = harness
    assert change(client, target=3).status_code == 409
    with factory() as session:
        session.get(User, UUID(int=2)).is_suspended = True
        session.commit()
    response = change(client)
    assert response.status_code == 409 and response.json()["detail"] == "Reactivate the account before granting administrator access"
    with factory() as session:
        assert session.get(User, UUID(int=2)).role == "CUSTOMER"
        assert session.scalar(select(AuditLog.id)) is None


def test_suspended_admin_can_be_demoted_without_reactivating_account(harness):
    client, factory = harness
    with factory() as session:
        session.get(User, UUID(int=4)).is_suspended = True
        session.commit()
    assert change(client, target=4, role="CUSTOMER", expected="ADMIN").status_code == 200
    with factory() as session:
        target = session.get(User, UUID(int=4))
        assert target.is_suspended and target.role == "CUSTOMER" and target.auth_version == 1


def test_missing_and_customer_callers_and_unknown_targets(harness):
    client, _ = harness
    assert change(client, headers={}).status_code == 401
    assert change(client, headers=bearer(2)).status_code == 403
    assert client.patch(f"/api/admin/users/{uuid4()}/role", headers=bearer(), json={"role": "ADMIN", "expected_role": "CUSTOMER"}).status_code == 404


@pytest.mark.parametrize("body", [{}, {"role": "ADMIN"}, {"role": "SUPERADMIN", "expected_role": "CUSTOMER"},
    {"role": "ADMIN", "expected_role": "UNKNOWN"}, {"role": "ADMIN", "expected_role": "CUSTOMER", "auth_version": 0},
    {"role": "ADMIN", "expected_role": "CUSTOMER", "status": "ACTIVE"}])
def test_role_requests_reject_unsupported_or_extra_fields(harness, body):
    client, _ = harness
    assert client.patch(f"/api/admin/users/{UUID(int=2)}/role", headers=bearer(), json=body).status_code == 422


def test_stale_confirmation_preserves_role_and_sessions(harness):
    client, factory = harness
    assert change(client, expected="ADMIN").status_code == 409
    with factory() as session:
        assert session.get(User, UUID(int=2)).auth_version == 0
        assert session.scalar(select(AuditLog.id)) is None


@pytest.mark.parametrize("operation", ["audit", "commit"])
def test_failure_rolls_back_role_session_generation_and_event(harness, operation):
    client, factory = harness
    target, name = (AuditLogService, "record") if operation == "audit" else (Session, "commit")
    with patch.object(target, name, side_effect=SQLAlchemyError("private credentials")):
        response = change(client)
    assert response.status_code == 503 and response.json() == {"detail": "Account role update unavailable"}
    with factory() as session:
        target = session.get(User, UUID(int=2))
        assert target.role == "CUSTOMER" and target.auth_version == 0
        assert session.scalar(select(AuditLog.id)) is None


@pytest.mark.parametrize("fields,code", [({"is_suspended": True}, 401), ({"auth_version": 1}, 401), ({"role": "CUSTOMER"}, 403)])
def test_actor_authority_is_refreshed_under_the_shared_users_lock(harness, fields, code):
    client, factory = harness
    actor = User(id=UUID(int=1), email="admin@example.com", password_hash="synthetic", role="ADMIN", is_suspended=False, auth_version=0)
    for field, value in fields.items(): setattr(actor, field, value)
    with patch.object(UserRepository, "get_current_by_id", return_value=actor):
        assert change(client).status_code == code
    with factory() as session:
        assert session.get(User, UUID(int=2)).role == "CUSTOMER"


def test_role_filter_reports_server_state_and_preserves_owned_records(harness):
    client, factory = harness
    Portfolio.__table__.create(factory.kw["bind"])
    with factory() as session:
        session.add(Portfolio(id=UUID(int=100), user_id=UUID(int=2), name="Retained portfolio"))
        session.commit()
    assert change(client).status_code == 200
    directory = client.get("/api/admin/users", headers=bearer(), params={"role": "ADMIN"}).json()
    target = next(item for item in directory["items"] if item["id"] == str(UUID(int=2)))
    assert target["role"] == "ADMIN" and target["portfolio_count"] == 1
    assert "auth_version" not in target and "password_hash" not in target
    assert change(client, role="CUSTOMER", expected="ADMIN").status_code == 200
    with factory() as session:
        assert session.get(Portfolio, UUID(int=100)).user_id == UUID(int=2)
