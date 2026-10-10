"""Status mutations, real authentication and audit atomicity with synthetic storage."""

from datetime import UTC
from unittest.mock import patch
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from pydantic import SecretStr
import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.orm.attributes import set_committed_value
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_database_session
from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.database.models import AuditLog, User
from app.main import app
from app.services.audit_log_service import AuditLogService
from app.database.repositories.user_repository import UserRepository

PASSWORD = "synthetic-status-test-password"


@pytest.fixture
def harness():
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    User.__table__.create(engine)
    AuditLog.__table__.create(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    @event.listens_for(factory, "loaded_as_persistent")
    def sqlite_utc(session, user):
        if isinstance(user, User):
            for field in ("created_at", "updated_at"):
                timestamp = getattr(user, field)
                if timestamp.tzinfo is None:
                    set_committed_value(user, field, timestamp.replace(tzinfo=UTC))
    with factory() as session:
        encoded = hash_password(PASSWORD)
        session.add_all([
            User(id=UUID(int=1), email="admin@example.com", password_hash=encoded, role="ADMIN"),
            User(id=UUID(int=2), email="customer@example.com", password_hash=encoded),
            User(id=UUID(int=3)),
            User(id=UUID(int=4), email="second@example.com", password_hash=encoded, role="ADMIN"),
        ])
        session.commit()

    def sessions():
        with factory() as session:
            try:
                yield session
            except Exception:
                session.rollback()
                raise

    original = app.dependency_overrides.copy()
    app.dependency_overrides[get_database_session] = sessions
    try:
        with patch.object(settings, "jwt_secret_key", SecretStr("synthetic-account-status-signing-secret-32bytes")), TestClient(app) as client:
            yield client, factory
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original)
        engine.dispose()


def bearer(user_id=1, version=0):
    return {"Authorization": f"Bearer {create_access_token(UUID(int=user_id), auth_version=version)}"}


def change(client, target=2, status="SUSPENDED", headers=None, expected="ACTIVE"):
    return client.patch(f"/api/admin/users/{UUID(int=target)}/status", headers=headers or bearer(),
                        json={"status": status, "expected_status": expected})


def test_suspend_reactivate_audit_and_old_token_never_revives(harness):
    client, factory = harness
    old_token = bearer(2)
    assert client.get("/api/auth/me", headers=old_token).status_code == 200
    response = change(client)
    assert response.status_code == 200 and response.json()["status"] == "SUSPENDED"
    assert set(response.json()) == {"id", "status", "updated_at"}
    assert client.get("/api/auth/me", headers=old_token).status_code == 401
    assert client.get("/api/portfolios", headers=old_token).status_code == 401
    assert client.post("/api/auth/login", json={"email": "customer@example.com", "password": PASSWORD}).status_code == 401
    assert change(client).status_code == 200  # No duplicate event/session revocation.
    assert change(client, status="ACTIVE", expected="SUSPENDED").status_code == 200
    assert client.get("/api/auth/me", headers=old_token).status_code == 401
    login = client.post("/api/auth/login", json={"email": "customer@example.com", "password": PASSWORD})
    assert login.status_code == 200
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {login.json()['access_token']}"}).status_code == 200
    with factory() as session:
        assert not session.get(User, UUID(int=2)).is_suspended
        assert session.get(User, UUID(int=2)).auth_version == 1
        logs = session.scalars(select(AuditLog).order_by(AuditLog.created_at, AuditLog.id)).all()
        assert len(logs) == 2
        assert {log.action for log in logs} == {"USER_SUSPENDED", "USER_REACTIVATED"}
        assert all(log.actor_kind == "ADMIN" and log.actor_user_id == UUID(int=1) for log in logs)
    audit = client.get("/api/admin/audit-logs", headers=bearer(), params={"action": "USER_SUSPENDED"})
    assert audit.status_code == 200 and audit.json()["total"] == 1
    assert audit.json()["items"][0]["details"] == {"previous_status": "ACTIVE", "new_status": "SUSPENDED"}


@pytest.mark.parametrize("target", [1, 4])
def test_self_and_other_admin_safeguards(harness, target):
    client, _ = harness
    response = change(client, target=target)
    assert response.status_code == (409 if target == 1 else 200)
    if target == 4:
        assert client.get("/api/admin/me", headers=bearer(4)).status_code == 401
        assert change(client, target=1, headers=bearer(4)).status_code == 401


def test_last_active_admin_check_refuses_unsafe_decision(harness):
    client, factory = harness
    # Exercise the invariant separately from the overlapping self guard.
    with patch.object(UserRepository, "has_other_active_admin", return_value=False):
        assert change(client, target=4).status_code == 409
    with factory() as session:
        assert not session.get(User, UUID(int=4)).is_suspended
        assert session.scalar(select(AuditLog.id)) is None


def test_audit_failure_rolls_back_status_and_session_version(harness):
    client, factory = harness
    with patch.object(AuditLogService, "record", side_effect=SQLAlchemyError("private database credential")):
        response = change(client)
    assert response.status_code == 503
    assert response.json() == {"detail": "Account status update unavailable"}
    with factory() as session:
        user = session.get(User, UUID(int=2))
        assert not user.is_suspended and user.auth_version == 0
        assert session.scalar(select(AuditLog.id)) is None


def test_commit_failure_rolls_back_and_reports_no_success(harness):
    client, factory = harness
    with patch.object(Session, "commit", side_effect=SQLAlchemyError("private details")):
        assert change(client).status_code == 503
    with factory() as session:
        assert not session.get(User, UUID(int=2)).is_suspended
        assert session.scalar(select(AuditLog.id)) is None


def test_missing_customer_and_unknown_account_are_rejected(harness):
    client, _ = harness
    path = f"/api/admin/users/{UUID(int=2)}/status"
    body = {"status": "SUSPENDED", "expected_status": "ACTIVE"}
    assert client.patch(path, json=body).status_code == 401
    assert client.patch(path, headers=bearer(2), json=body).status_code == 403
    assert client.patch(f"/api/admin/users/{uuid4()}/status", headers=bearer(), json=body).status_code == 404


@pytest.mark.parametrize("body", [{}, {"status": "DELETED", "expected_status": "ACTIVE"},
    {"status": "SUSPENDED"}, {"status": "SUSPENDED", "expected_status": "ACTIVE", "role": "ADMIN"}])
def test_invalid_status_or_extra_privileges_are_422(harness, body):
    client, _ = harness
    assert client.patch(f"/api/admin/users/{UUID(int=2)}/status", headers=bearer(), json=body).status_code == 422


def test_stale_confirmation_and_legacy_status(harness):
    client, factory = harness
    assert change(client, status="SUSPENDED", expected="SUSPENDED").status_code == 409
    assert change(client, target=3).status_code == 200
    assert client.get("/api/auth/me", headers=bearer(3)).status_code == 401
    with factory() as session:
        assert session.get(User, UUID(int=3)).role == "CUSTOMER"


def test_directory_status_filters(harness):
    client, _ = harness
    # The directory requires portfolios for its projection; no portfolio data is exposed.
    from app.database.models import Portfolio
    factory = harness[1]
    Portfolio.__table__.create(factory.kw["bind"])
    assert change(client).status_code == 200
    suspended = client.get("/api/admin/users", headers=bearer(), params={"status": "SUSPENDED"})
    assert suspended.status_code == 200 and suspended.json()["total"] == 1
    assert suspended.json()["items"][0]["status"] == "SUSPENDED"
    assert "auth_version" not in suspended.json()["items"][0]
    assert client.get("/api/admin/users", headers=bearer(), params={"status": "ACTIVE"}).json()["total"] == 3


@pytest.mark.parametrize("change_fields,code", [({"is_suspended": True}, 401), ({"auth_version": 1}, 401), ({"role": "CUSTOMER"}, 403)])
def test_actor_is_rechecked_after_lock(harness, change_fields, code):
    client, factory = harness
    actor = User(id=UUID(int=1), email="admin@example.com", password_hash="encoded", role="ADMIN", is_suspended=False, auth_version=0)
    for field, value in change_fields.items():
        setattr(actor, field, value)
    with patch.object(UserRepository, "get_current_by_id", return_value=actor):
        assert change(client).status_code == code
    with factory() as session:
        assert not session.get(User, UUID(int=2)).is_suspended
        assert session.scalar(select(AuditLog.id)) is None
