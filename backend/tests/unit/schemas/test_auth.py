from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import SecretStr, ValidationError

import backend.app.schemas as schemas_package
from backend.app.schemas.auth import (
    AccessTokenResponse,
    AuthenticatedUserResponse,
    LoginRequest,
    RegistrationRequest,
)


def test_registration_accepts_and_canonicalizes_valid_credentials() -> None:
    request = RegistrationRequest.model_validate(
        {
            "email": "  User@Example.COM  ",
            "password": "password",
        }
    )

    assert request.email == "user@example.com"
    assert isinstance(request.password, SecretStr)
    assert request.password.get_secret_value() == "password"


def test_registration_and_login_share_identical_email_canonicalization() -> None:
    payload = {
        "email": "  Mixed.Case@Example.COM  ",
        "password": "password",
    }

    registration = RegistrationRequest.model_validate(payload)
    login = LoginRequest.model_validate(payload)

    assert registration.email == login.email == "mixed.case@example.com"
    assert payload == {
        "email": "  Mixed.Case@Example.COM  ",
        "password": "password",
    }


@pytest.mark.parametrize("request_type", [RegistrationRequest, LoginRequest])
def test_auth_requests_reject_invalid_email(request_type: type[object]) -> None:
    with pytest.raises(ValidationError):
        request_type.model_validate(
            {"email": "not-an-email", "password": "password"}
        )


@pytest.mark.parametrize("request_type", [RegistrationRequest, LoginRequest])
def test_auth_requests_reject_password_shorter_than_eight(
    request_type: type[object],
) -> None:
    with pytest.raises(ValidationError):
        request_type.model_validate(
            {"email": "user@example.com", "password": "short"}
        )


def test_password_secret_is_not_exposed_in_schema_representation() -> None:
    plaintext = "private-password"
    request = RegistrationRequest(
        email="user@example.com",
        password=plaintext,
    )

    assert plaintext not in repr(request)
    assert plaintext not in request.model_dump_json()
    assert request.password.get_secret_value() == plaintext


@pytest.mark.parametrize("request_type", [RegistrationRequest, LoginRequest])
def test_auth_requests_reject_extra_fields(request_type: type[object]) -> None:
    with pytest.raises(ValidationError):
        request_type.model_validate(
            {
                "email": "user@example.com",
                "password": "password",
                "display_name": "Not approved",
            }
        )


def test_authenticated_user_response_exposes_only_public_fields() -> None:
    timestamp = datetime(2026, 8, 18, tzinfo=UTC)
    response = AuthenticatedUserResponse.model_validate(
        {
            "id": uuid4(),
            "email": "User@Example.COM",
            "created_at": timestamp,
            "updated_at": timestamp,
        }
    )

    assert set(response.model_dump()) == {
        "id",
        "email",
        "created_at",
        "updated_at",
    }
    assert response.email == "user@example.com"
    assert "password" not in response.model_dump_json()

    with pytest.raises(ValidationError):
        AuthenticatedUserResponse.model_validate(
            {
                **response.model_dump(),
                "password_hash": "$argon2id$not-public",
            }
        )


def test_access_token_response_uses_bearer_type() -> None:
    response = AccessTokenResponse(access_token="encoded-token")

    assert response.model_dump() == {
        "access_token": "encoded-token",
        "token_type": "bearer",
    }


def test_auth_schemas_do_not_expand_stable_package_exports() -> None:
    assert not {
        "RegistrationRequest",
        "LoginRequest",
        "AuthenticatedUserResponse",
        "AccessTokenResponse",
    }.intersection(schemas_package.__all__)
