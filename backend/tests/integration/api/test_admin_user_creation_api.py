"""Credential-safe account creation, permissions and atomic audit rollback."""

from unittest.mock import patch
from uuid import UUID

import pytest
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.database.models import AuditLog, Portfolio, User
from app.database.repositories.user_repository import UserRepository
from app.services.audit_log_service import AuditLogService
from backend.tests.integration.api.test_admin_user_status_api import PASSWORD, bearer, harness


def create(client, headers=None, **fields):
    return client.post("/api/admin/users", headers=headers if headers is not None else bearer(),
                       json={"email": "created@example.com", "password": PASSWORD, **fields})


def test_creation_reuses_shared_auth_customer_defaults_and_private_audit(harness):
    client, factory = harness
    Portfolio.__table__.create(factory.kw["bind"])
    response = create(client, email="  Created@Example.COM  ", display_name="  New Aura User  ")
    assert response.status_code == 201
    data = response.json()
    assert set(data) == {"id", "email", "display_name", "role", "account_type", "status", "created_at", "updated_at", "portfolio_count"}
    assert data["email"] == "created@example.com" and data["display_name"] == "New Aura User"
    assert (data["role"], data["account_type"], data["status"], data["portfolio_count"]) == ("CUSTOMER", "REGISTERED", "ACTIVE", 0)
    assert PASSWORD not in response.text and "password_hash" not in response.text
    with factory() as session:
        user = session.get(User, UUID(data["id"]))
        assert user.password_hash != PASSWORD and verify_password(PASSWORD, user.password_hash)
        assert user.auth_version == 0 and not user.is_suspended
        logs = session.scalars(select(AuditLog)).all()
        assert len(logs) == 1 and logs[0].action == "USER_CREATED"
        assert logs[0].actor_user_id == UUID(int=1) and logs[0].target_id == user.id
        assert logs[0].details == {"role": "CUSTOMER", "account_type": "REGISTERED"}
    login = client.post("/api/auth/login", json={"email": data["email"], "password": PASSWORD})
    assert login.status_code == 200
    new_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    assert client.get("/api/auth/me", headers=new_headers).status_code == 200
    assert client.get("/api/admin/me", headers=new_headers).status_code == 403
    directory = client.get("/api/admin/users", headers=bearer(), params={"q": data["email"]}).json()
    assert directory["total"] == 1 and directory["items"][0] == data
    audit = client.get("/api/admin/audit-logs", headers=bearer(), params={"action": "USER_CREATED"})
    assert audit.status_code == 200 and audit.json()["total"] == 1
    assert PASSWORD not in audit.text and data["email"] not in audit.text and data["display_name"] not in audit.text


def test_optional_name_and_no_token_or_impersonation(harness):
    client, _ = harness
    response = create(client)
    assert response.status_code == 201 and response.json()["display_name"] is None
    assert "access_token" not in response.text and "token_type" not in response.text
    assert client.get("/api/admin/me", headers=bearer()).json()["id"] == str(UUID(int=1))


@pytest.mark.parametrize("email", ["customer@example.com", "  CUSTOMER@EXAMPLE.COM  "])
def test_duplicate_email_never_overwrites_existing_credentials_or_audits(harness, email):
    client, factory = harness
    response = create(client, email=email, password="different-synthetic-password")
    assert response.status_code == 409 and response.json() == {"detail": "Email already registered"}
    with factory() as session:
        user = session.get(User, UUID(int=2))
        assert verify_password(PASSWORD, user.password_hash) and user.role == "CUSTOMER"
        assert len(session.scalars(select(User)).all()) == 4
        assert session.scalar(select(AuditLog.id)) is None


def test_lost_response_retry_creates_only_one_account(harness):
    client, factory = harness
    assert create(client).status_code == 201
    assert create(client).status_code == 409
    with factory() as session:
        assert len(session.scalars(select(User).where(User.email == "created@example.com")).all()) == 1
        assert len(session.scalars(select(AuditLog)).all()) == 1


@pytest.mark.parametrize("headers,code", [({}, 401), ("customer", 403)])
def test_anonymous_and_customer_callers_cannot_create(harness, headers, code):
    client, factory = harness
    assert create(client, headers=bearer(2) if headers == "customer" else headers).status_code == code
    with factory() as session:
        assert len(session.scalars(select(User)).all()) == 4
        assert session.scalar(select(AuditLog.id)) is None


@pytest.mark.parametrize("fields", [{"email": "invalid"}, {"password": "short"}, {"display_name": " "}, {"display_name": "x"*101},
    {"role": "ADMIN"}, {"status": "SUSPENDED"}, {"auth_version": 0}, {"password_hash": "private"}])
def test_invalid_or_extra_fields_return_sanitized_422(harness, fields):
    client, factory = harness
    response = create(client, **fields)
    assert response.status_code == 422 and response.json() == {"detail": "Invalid account details"}
    assert PASSWORD not in response.text and "short" not in response.text
    with factory() as session: assert session.scalar(select(AuditLog.id)) is None


@pytest.mark.parametrize("body", [None, [], "credential-bearing private payload", {"password": PASSWORD}, {"email": "created@example.com"}])
def test_malformed_or_missing_body_never_echoes_credential_input(harness, body):
    client, _ = harness
    response = client.post("/api/admin/users", headers=bearer(), json=body)
    assert response.status_code == 422 and response.json() == {"detail": "Invalid account details"}


@pytest.mark.parametrize("operation", ["audit", "commit", "hash"])
def test_audit_commit_or_hash_failure_rolls_back_and_hides_secrets(harness, operation):
    client, factory = harness
    if operation == "hash":
        context = patch("app.services.auth_service.hash_password", side_effect=RuntimeError("private password"))
    else:
        target, name = (AuditLogService, "record") if operation == "audit" else (Session, "commit")
        context = patch.object(target, name, side_effect=SQLAlchemyError("private credentials"))
    with context: response = create(client)
    assert response.status_code == 503 and response.json() == {"detail": "Account creation unavailable"}
    with factory() as session:
        assert session.scalars(select(User).where(User.email == "created@example.com")).first() is None
        assert session.scalar(select(AuditLog.id)) is None


@pytest.mark.parametrize("fields,code", [({"is_suspended": True}, 401), ({"auth_version": 1}, 401), ({"role": "CUSTOMER"}, 403)])
def test_actor_is_rechecked_under_shared_account_lock(harness, fields, code):
    client, factory = harness
    actor = User(id=UUID(int=1), email="admin@example.com", password_hash="synthetic", role="ADMIN", is_suspended=False, auth_version=0)
    for field, value in fields.items(): setattr(actor, field, value)
    with patch.object(UserRepository, "get_current_by_id", return_value=actor):
        assert create(client).status_code == code
    with factory() as session: assert len(session.scalars(select(User)).all()) == 4
