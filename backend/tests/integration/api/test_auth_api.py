from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import UUID

import jwt
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import app.api.dependencies as dependency_module
import app.api.routes.auth as route_module
from app.core.config import settings
from app.core.security import create_access_token, decode_access_token
from app.database.models import User
from app.main import app
from app.services.auth_service import (
    AuthService,
    DuplicateEmailError,
    InvalidCredentialsError,
)


USER_ID = UUID("30000000-0000-0000-0000-000000000001")
CREATED_AT = datetime(2026, 8, 18, 2, 30, tzinfo=UTC)
UPDATED_AT = datetime(2026, 8, 18, 3, 45, tzinfo=UTC)
JWT_SECRET = "phase-5-deterministic-test-secret"
PASSWORD = "correct-password"


@dataclass
class AuthApiHarness:
    client: TestClient
    session: MagicMock
    service: MagicMock


def _user() -> User:
    return User(
        id=USER_ID,
        email="user@example.com",
        password_hash="encoded-password-hash",
        created_at=CREATED_AT,
        updated_at=UPDATED_AT,
    )


def _authorization(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _encoded_claims(
    claims: dict[str, object],
    *,
    secret: str = JWT_SECRET,
) -> str:
    return jwt.encode(claims, secret, algorithm="HS256")


@pytest.fixture
def auth_api_harness() -> AuthApiHarness:
    session = MagicMock(spec=Session)
    session_factory = MagicMock(return_value=session)
    service = MagicMock(spec=AuthService)

    with (
        patch.object(
            dependency_module,
            "_get_session_factory",
            return_value=session_factory,
        ),
        patch.object(
            route_module,
            "AuthService",
            return_value=service,
        ),
        patch.object(
            settings,
            "jwt_secret_key",
            SecretStr(JWT_SECRET),
        ),
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        yield AuthApiHarness(client=client, session=session, service=service)


def test_auth_router_exposes_only_the_three_approved_endpoints() -> None:
    auth_paths = {
        path
        for path in app.openapi()["paths"]
        if path.startswith("/api/auth")
    }

    assert auth_paths == {
        "/api/auth/register",
        "/api/auth/login",
        "/api/auth/me",
    }


def test_register_returns_canonical_public_user_and_commits_once(
    auth_api_harness: AuthApiHarness,
) -> None:
    auth_api_harness.service.register.return_value = _user()

    response = auth_api_harness.client.post(
        "/api/auth/register",
        json={
            "email": "  User@Example.COM  ",
            "password": PASSWORD,
        },
    )

    assert response.status_code == 201
    assert response.json() == {
        "id": str(USER_ID),
        "email": "user@example.com",
        "created_at": "2026-08-18T02:30:00Z",
        "updated_at": "2026-08-18T03:45:00Z",
    }
    assert "password" not in response.json()
    assert "password_hash" not in response.json()
    request = auth_api_harness.service.register.call_args.args[0]
    assert str(request.email) == "user@example.com"
    auth_api_harness.session.commit.assert_called_once_with()
    auth_api_harness.session.rollback.assert_not_called()
    auth_api_harness.session.close.assert_called_once_with()


@pytest.mark.parametrize(
    "email",
    ["user@example.com", "  USER@EXAMPLE.COM  "],
)
def test_duplicate_canonical_registration_returns_conflict(
    auth_api_harness: AuthApiHarness,
    email: str,
) -> None:
    auth_api_harness.service.register.side_effect = DuplicateEmailError

    response = auth_api_harness.client.post(
        "/api/auth/register",
        json={"email": email, "password": PASSWORD},
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Email already registered"}
    request = auth_api_harness.service.register.call_args.args[0]
    assert str(request.email) == "user@example.com"
    auth_api_harness.session.commit.assert_not_called()
    auth_api_harness.session.rollback.assert_called_once_with()
    auth_api_harness.session.close.assert_called_once_with()


@pytest.mark.parametrize(
    "payload",
    [
        {"email": "not-an-email", "password": PASSWORD},
        {"email": "user@example.com", "password": "short"},
    ],
)
def test_invalid_registration_uses_schema_validation(
    auth_api_harness: AuthApiHarness,
    payload: dict[str, str],
) -> None:
    response = auth_api_harness.client.post(
        "/api/auth/register",
        json=payload,
    )

    assert response.status_code == 422
    auth_api_harness.service.register.assert_not_called()
    auth_api_harness.session.commit.assert_not_called()


def test_uniqueness_race_maps_to_conflict_and_request_boundary_rolls_back(
    auth_api_harness: AuthApiHarness,
) -> None:
    original = SimpleNamespace(
        diag=SimpleNamespace(constraint_name="uq_users_email")
    )
    integrity_error = IntegrityError("INSERT INTO users", {}, original)
    duplicate_error = DuplicateEmailError()
    duplicate_error.__cause__ = integrity_error
    auth_api_harness.service.register.side_effect = duplicate_error

    response = auth_api_harness.client.post(
        "/api/auth/register",
        json={"email": "user@example.com", "password": PASSWORD},
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Email already registered"}
    auth_api_harness.session.commit.assert_not_called()
    auth_api_harness.session.rollback.assert_called_once_with()
    auth_api_harness.session.close.assert_called_once_with()


def test_login_returns_decodable_bearer_token_without_committing(
    auth_api_harness: AuthApiHarness,
) -> None:
    user = _user()
    token = create_access_token(user.id)
    auth_api_harness.service.authenticate.return_value = user
    auth_api_harness.service.create_access_token_for_user.return_value = token

    response = auth_api_harness.client.post(
        "/api/auth/login",
        json={"email": "  USER@EXAMPLE.COM  ", "password": PASSWORD},
    )

    assert response.status_code == 200
    assert response.json() == {
        "access_token": token,
        "token_type": "bearer",
    }
    assert decode_access_token(response.json()["access_token"]) == USER_ID
    request = auth_api_harness.service.authenticate.call_args.args[0]
    assert str(request.email) == "user@example.com"
    auth_api_harness.service.create_access_token_for_user.assert_called_once_with(
        user
    )
    auth_api_harness.session.commit.assert_not_called()
    auth_api_harness.session.rollback.assert_not_called()
    auth_api_harness.session.close.assert_called_once_with()


@pytest.mark.parametrize(
    "credential_case",
    ["wrong password", "unknown email", "credential-less legacy user"],
)
def test_login_failures_are_indistinguishable_and_never_commit(
    auth_api_harness: AuthApiHarness,
    credential_case: str,
) -> None:
    auth_api_harness.service.authenticate.side_effect = (
        InvalidCredentialsError("Invalid credentials")
    )

    response = auth_api_harness.client.post(
        "/api/auth/login",
        json={
            "email": "user@example.com",
            "password": f"{credential_case}-password",
        },
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid email or password"}
    assert response.headers["www-authenticate"] == "Bearer"
    auth_api_harness.service.create_access_token_for_user.assert_not_called()
    auth_api_harness.session.commit.assert_not_called()
    auth_api_harness.session.rollback.assert_called_once_with()
    auth_api_harness.session.close.assert_called_once_with()


def test_me_returns_current_public_user_without_committing(
    auth_api_harness: AuthApiHarness,
) -> None:
    user = _user()
    auth_api_harness.session.get.return_value = user
    token = create_access_token(USER_ID)

    response = auth_api_harness.client.get(
        "/api/auth/me",
        headers=_authorization(token),
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": str(USER_ID),
        "email": "user@example.com",
        "created_at": "2026-08-18T02:30:00Z",
        "updated_at": "2026-08-18T03:45:00Z",
    }
    assert "password_hash" not in response.json()
    auth_api_harness.session.get.assert_called_once_with(User, USER_ID)
    auth_api_harness.session.commit.assert_not_called()
    auth_api_harness.session.rollback.assert_not_called()
    auth_api_harness.session.close.assert_called_once_with()


_NOW = datetime.now(UTC)
_INVALID_AUTHORIZATION_CASES = [
    pytest.param({}, "missing header", id="missing-header"),
    pytest.param(
        {"Authorization": "Basic abc123"},
        "wrong scheme",
        id="wrong-scheme",
    ),
    pytest.param(
        {"Authorization": "Bearer"},
        "missing token",
        id="missing-token",
    ),
    pytest.param(
        _authorization("not-a-jwt"),
        "malformed token",
        id="malformed-token",
    ),
    pytest.param(
        _authorization(
            _encoded_claims(
                {
                    "sub": str(USER_ID),
                    "iat": _NOW,
                    "exp": _NOW + timedelta(minutes=30),
                },
                secret="different-phase-5-signing-secret-value",
            )
        ),
        "invalid signature",
        id="invalid-signature",
    ),
    pytest.param(
        _authorization(
            _encoded_claims(
                {
                    "sub": str(USER_ID),
                    "iat": _NOW - timedelta(minutes=60),
                    "exp": _NOW - timedelta(minutes=30),
                }
            )
        ),
        "expired token",
        id="expired-token",
    ),
    pytest.param(
        _authorization(
            _encoded_claims(
                {"sub": str(USER_ID), "iat": _NOW}
            )
        ),
        "missing required claim",
        id="missing-claim",
    ),
    pytest.param(
        _authorization(
            _encoded_claims(
                {
                    "sub": "not-a-uuid",
                    "iat": _NOW,
                    "exp": _NOW + timedelta(minutes=30),
                }
            )
        ),
        "invalid UUID subject",
        id="invalid-uuid",
    ),
]


@pytest.mark.parametrize(("headers", "failure"), _INVALID_AUTHORIZATION_CASES)
def test_me_rejects_unusable_bearer_credentials_consistently(
    auth_api_harness: AuthApiHarness,
    headers: dict[str, str],
    failure: str,
) -> None:
    response = auth_api_harness.client.get(
        "/api/auth/me",
        headers=headers,
    )

    assert response.status_code == 401, failure
    assert response.json() == {
        "detail": "Invalid or missing authentication credentials"
    }
    assert response.headers["www-authenticate"] == "Bearer"
    auth_api_harness.session.get.assert_not_called()
    auth_api_harness.session.commit.assert_not_called()
    auth_api_harness.session.rollback.assert_called_once_with()
    auth_api_harness.session.close.assert_called_once_with()


def test_me_rejects_valid_token_for_deleted_user(
    auth_api_harness: AuthApiHarness,
) -> None:
    auth_api_harness.session.get.return_value = None

    response = auth_api_harness.client.get(
        "/api/auth/me",
        headers=_authorization(create_access_token(USER_ID)),
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid or missing authentication credentials"
    }
    assert response.headers["www-authenticate"] == "Bearer"
    auth_api_harness.session.get.assert_called_once_with(User, USER_ID)
    auth_api_harness.session.commit.assert_not_called()
    auth_api_harness.session.rollback.assert_called_once_with()


def test_health_remains_public_without_jwt_or_database_configuration() -> None:
    with (
        patch.object(settings, "jwt_secret_key", None),
        patch.object(
            dependency_module,
            "create_database_engine",
        ) as create_engine,
        TestClient(app) as client,
    ):
        response = client.get("/api/health")

    assert response.status_code == 200
    create_engine.assert_not_called()
