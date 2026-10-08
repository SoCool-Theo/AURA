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
    CurrentPasswordMismatchError,
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
        display_name="Aura Investor",
        phone_number="+66 81 234 5678",
        preferred_language="en",
        timezone="Asia/Bangkok",
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


def _public_user_payload() -> dict[str, str]:
    return {
        "id": str(USER_ID),
        "email": "user@example.com",
        "display_name": "Aura Investor",
        "phone_number": "+66 81 234 5678",
        "preferred_language": "en",
        "timezone": "Asia/Bangkok",
        "created_at": "2026-08-18T02:30:00Z",
        "updated_at": "2026-08-18T03:45:00Z",
    }


def test_auth_router_exposes_profile_and_password_endpoints() -> None:
    auth_paths = {
        path
        for path in app.openapi()["paths"]
        if path.startswith("/api/auth")
    }

    assert auth_paths == {
        "/api/auth/register",
        "/api/auth/login",
        "/api/auth/me",
        "/api/auth/me/password",
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
    assert response.json() == _public_user_payload()
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
    assert response.json() == _public_user_payload()
    assert "password_hash" not in response.json()
    auth_api_harness.session.get.assert_called_once_with(User, USER_ID)
    auth_api_harness.session.commit.assert_not_called()
    auth_api_harness.session.rollback.assert_not_called()
    auth_api_harness.session.close.assert_called_once_with()


def test_profile_update_is_authenticated_validated_and_committed(
    auth_api_harness: AuthApiHarness,
) -> None:
    current = _user()
    updated = _user()
    updated.email = "new@example.com"
    updated.display_name = "Updated Investor"
    updated.phone_number = None
    updated.preferred_language = "th"
    updated.timezone = "Asia/Yangon"
    auth_api_harness.session.get.return_value = current
    auth_api_harness.service.update_profile.return_value = updated

    response = auth_api_harness.client.patch(
        "/api/auth/me",
        headers=_authorization(create_access_token(USER_ID)),
        json={
            "email": " NEW@Example.COM ",
            "display_name": "  Updated Investor  ",
            "phone_number": None,
            "preferred_language": "th",
            "timezone": "Asia/Yangon",
            "current_password": PASSWORD,
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        **_public_user_payload(),
        "email": "new@example.com",
        "display_name": "Updated Investor",
        "phone_number": None,
        "preferred_language": "th",
        "timezone": "Asia/Yangon",
    }
    request = auth_api_harness.service.update_profile.call_args.args[1]
    assert request.email == "new@example.com"
    assert request.display_name == "Updated Investor"
    auth_api_harness.session.commit.assert_called_once_with()


def test_profile_email_conflict_and_wrong_password_are_sanitized(
    auth_api_harness: AuthApiHarness,
) -> None:
    auth_api_harness.session.get.return_value = _user()
    token = create_access_token(USER_ID)
    auth_api_harness.service.update_profile.side_effect = DuplicateEmailError

    conflict = auth_api_harness.client.patch(
        "/api/auth/me",
        headers=_authorization(token),
        json={"email": "taken@example.com", "current_password": PASSWORD},
    )

    assert conflict.status_code == 409
    assert conflict.json() == {"detail": "Email already registered"}

    auth_api_harness.service.update_profile.side_effect = (
        CurrentPasswordMismatchError
    )
    forbidden = auth_api_harness.client.patch(
        "/api/auth/me",
        headers=_authorization(token),
        json={"email": "new@example.com", "current_password": PASSWORD},
    )

    assert forbidden.status_code == 403
    assert forbidden.json() == {"detail": "Current password is incorrect"}


def test_password_change_requires_auth_and_commits_no_response_body(
    auth_api_harness: AuthApiHarness,
) -> None:
    user = _user()
    auth_api_harness.session.get.return_value = user

    response = auth_api_harness.client.put(
        "/api/auth/me/password",
        headers=_authorization(create_access_token(USER_ID)),
        json={
            "current_password": PASSWORD,
            "new_password": "replacement-password",
        },
    )

    assert response.status_code == 204
    assert response.content == b""
    request = auth_api_harness.service.change_password.call_args.args[1]
    assert request.current_password.get_secret_value() == PASSWORD
    assert request.new_password.get_secret_value() == "replacement-password"
    auth_api_harness.session.commit.assert_called_once_with()


def test_profile_writes_reject_invalid_payloads_before_service(
    auth_api_harness: AuthApiHarness,
) -> None:
    auth_api_harness.session.get.return_value = _user()
    token = create_access_token(USER_ID)

    empty_profile = auth_api_harness.client.patch(
        "/api/auth/me",
        headers=_authorization(token),
        json={},
    )
    same_password = auth_api_harness.client.put(
        "/api/auth/me/password",
        headers=_authorization(token),
        json={
            "current_password": PASSWORD,
            "new_password": PASSWORD,
        },
    )

    assert empty_profile.status_code == 422
    assert same_password.status_code == 422
    auth_api_harness.service.update_profile.assert_not_called()
    auth_api_harness.service.change_password.assert_not_called()


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


def test_delete_account_commits_once_and_returns_empty_204(auth_api_harness) -> None:
    user = _user()
    auth_api_harness.session.get.return_value = user
    response = auth_api_harness.client.request(
        "DELETE", "/api/auth/me", headers=_authorization(create_access_token(USER_ID)),
        json={"current_password": PASSWORD},
    )
    assert response.status_code == 204
    assert response.content == b""
    deleted_user, request = auth_api_harness.service.delete_account.call_args.args
    assert deleted_user is user
    assert request.current_password.get_secret_value() == PASSWORD
    assert PASSWORD not in repr(request)
    auth_api_harness.session.commit.assert_called_once_with()
    auth_api_harness.session.rollback.assert_not_called()


@pytest.mark.parametrize("failure,code,detail", [
    (CurrentPasswordMismatchError(), 403, "Current password is incorrect"),
    (RuntimeError("sensitive internal failure"), 500, "Unable to delete account"),
])
def test_delete_account_failures_roll_back_and_are_sanitized(auth_api_harness, failure, code, detail):
    auth_api_harness.session.get.return_value = _user()
    auth_api_harness.service.delete_account.side_effect = failure
    response = auth_api_harness.client.request(
        "DELETE", "/api/auth/me", headers=_authorization(create_access_token(USER_ID)),
        json={"current_password": PASSWORD},
    )
    assert response.status_code == code
    assert response.json() == {"detail": detail}
    auth_api_harness.session.commit.assert_not_called()
    auth_api_harness.session.rollback.assert_called_once_with()


def test_delete_account_commit_failure_rolls_back(auth_api_harness):
    auth_api_harness.session.get.return_value = _user()
    auth_api_harness.session.commit.side_effect = RuntimeError("internal failure")
    response = auth_api_harness.client.request(
        "DELETE", "/api/auth/me", headers=_authorization(create_access_token(USER_ID)),
        json={"current_password": PASSWORD},
    )
    assert response.status_code == 500
    assert response.json() == {"detail": "Unable to delete account"}
    auth_api_harness.session.rollback.assert_called_once_with()


def test_deleted_account_token_cannot_read_or_delete_again(auth_api_harness):
    auth_api_harness.session.get.return_value = None
    headers = _authorization(create_access_token(USER_ID))
    assert auth_api_harness.client.get("/api/auth/me", headers=headers).status_code == 401
    response = auth_api_harness.client.request(
        "DELETE", "/api/auth/me", headers=headers, json={"current_password": PASSWORD},
    )
    assert response.status_code == 401
    auth_api_harness.service.delete_account.assert_not_called()
    auth_api_harness.session.commit.assert_not_called()


@pytest.mark.parametrize("payload", [{}, {"current_password": "short"},
    {"current_password": None}, {"current_password": PASSWORD, "user_id": str(USER_ID)}])
def test_delete_account_rejects_invalid_or_owner_override_payload(auth_api_harness, payload):
    auth_api_harness.session.get.return_value = _user()
    response = auth_api_harness.client.request(
        "DELETE", "/api/auth/me", headers=_authorization(create_access_token(USER_ID)), json=payload,
    )
    assert response.status_code == 422
    auth_api_harness.service.delete_account.assert_not_called()
    auth_api_harness.session.commit.assert_not_called()


@pytest.mark.parametrize("headers,failure", _INVALID_AUTHORIZATION_CASES)
def test_delete_account_requires_valid_authentication(auth_api_harness, headers, failure):
    response = auth_api_harness.client.request(
        "DELETE", "/api/auth/me", headers=headers, json={"current_password": PASSWORD},
    )
    assert response.status_code == 401, failure
    auth_api_harness.service.delete_account.assert_not_called()
    auth_api_harness.session.commit.assert_not_called()
