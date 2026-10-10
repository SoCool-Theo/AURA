"""Exercise real Bearer authentication and persisted-role authorization."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4

import jwt
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.orm import Session

import app.api.dependencies as dependencies
from app.core.config import settings
from app.core.security import create_access_token
from app.database.models import Portfolio, User
from app.main import app


SECRET = "admin-access-test-secret-with-at-least-32-characters"


@pytest.fixture
def harness():
    session = MagicMock(spec=Session)
    user = User(id=uuid4(), email="admin@example.com", password_hash="encoded-hash",
                display_name="Administrator", role="ADMIN",
                created_at=datetime.now(UTC), updated_at=datetime.now(UTC))
    session.get.return_value = user
    with (
        patch.object(dependencies, "_get_session_factory", return_value=lambda: session),
        patch.object(settings, "jwt_secret_key", SecretStr(SECRET)),
        TestClient(app) as client,
    ):
        yield client, session, user


def bearer(user):
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


def test_admin_identity_is_safe_and_read_only(harness):
    client, session, user = harness
    response = client.get("/api/admin/me", headers=bearer(user))
    assert response.status_code == 200
    assert response.json() == {"id": str(user.id), "email": user.email,
                               "display_name": user.display_name, "role": "ADMIN"}
    session.get.assert_called_once_with(User, user.id)
    session.commit.assert_not_called()
    session.flush.assert_not_called()
    session.close.assert_called_once()


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Basic abc"},
                                      {"Authorization": "Bearer invalid"},
                                      {"X-User-ID": str(uuid4())}])
def test_invalid_or_missing_credentials_are_401(harness, headers):
    client, session, _ = harness
    response = client.get("/api/admin/me", headers=headers)
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    session.get.assert_not_called()


@pytest.mark.parametrize("role", ["CUSTOMER", None, "admin", "OWNER"])
def test_only_exact_persisted_admin_role_is_allowed(harness, role):
    client, session, user = harness
    user.role = role
    response = client.get("/api/admin/me", headers=bearer(user))
    assert response.status_code == 403
    assert response.json() == {"detail": "Administrator access required"}
    session.commit.assert_not_called()


def test_deleted_account_is_401(harness):
    client, session, user = harness
    session.get.return_value = None
    assert client.get("/api/admin/me", headers=bearer(user)).status_code == 401


def test_old_token_loses_admin_access_when_persisted_role_changes(harness):
    client, _, user = harness
    headers = bearer(user)
    assert client.get("/api/admin/me", headers=headers).status_code == 200
    user.role = "CUSTOMER"
    assert client.get("/api/admin/me", headers=headers).status_code == 403
    # Customer identity remains available with the same valid token.
    assert client.get("/api/auth/me", headers=headers).status_code == 200


def test_admin_claim_in_signed_token_cannot_promote_customer(harness):
    client, _, user = harness
    user.role = "CUSTOMER"
    claims = jwt.decode(create_access_token(user.id), SECRET, algorithms=["HS256"])
    claims["role"] = "ADMIN"
    token = jwt.encode(claims, SECRET, algorithm="HS256")
    assert client.get("/api/admin/me", headers={"Authorization": f"Bearer {token}"}).status_code == 403


@pytest.mark.parametrize("path,method,payload", [
    ("/api/auth/register", "post", {"email": "user@example.com", "password": "test-password", "role": "ADMIN"}),
    ("/api/auth/me", "patch", {"display_name": "User", "role": "ADMIN"}),
])
def test_public_requests_cannot_set_role(harness, path, method, payload):
    client, session, user = harness
    response = getattr(client, method)(path, headers=bearer(user), json=payload)
    assert response.status_code == 422
    session.flush.assert_not_called()
    session.commit.assert_not_called()


@pytest.mark.parametrize("field", ["email", "password_hash"])
def test_credentialless_admin_cannot_access(harness, field):
    client, _, user = harness
    setattr(user, field, None)
    assert client.get("/api/admin/me", headers=bearer(user)).status_code == 403


@pytest.mark.parametrize("invalid", ["expired", "wrong_signature"])
def test_invalid_signed_token_cannot_access_admin(harness, invalid):
    client, session, user = harness
    claims = jwt.decode(create_access_token(user.id), SECRET, algorithms=["HS256"])
    secret = SECRET
    if invalid == "expired":
        claims["exp"] = datetime.now(UTC) - timedelta(minutes=1)
    else:
        secret = "another-secret-with-at-least-32-characters"
    token = jwt.encode(claims, secret, algorithm="HS256")
    response = client.get("/api/admin/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    session.get.assert_not_called()


def test_admin_role_does_not_bypass_customer_portfolio_ownership(harness):
    client, session, user = harness
    portfolio = Portfolio(id=uuid4(), user_id=uuid4(), name="Private portfolio")
    session.scalars.return_value.one_or_none.return_value = portfolio
    response = client.get(f"/api/portfolios/{portfolio.id}", headers=bearer(user))
    assert response.status_code == 404
    session.commit.assert_not_called()
    session.flush.assert_not_called()


def test_admin_openapi_requires_bearer_and_exposes_no_role_write():
    paths = {path: methods for path, methods in app.openapi()["paths"].items()
             if path.startswith("/api/admin")}
    assert set(paths) == {"/api/admin/me", "/api/admin/audit-logs"}
    assert set(paths["/api/admin/me"]) == {"get"}
    operation = paths["/api/admin/me"]["get"]
    assert operation["security"] == [{"HTTPBearer": []}]
    assert "requestBody" not in operation
