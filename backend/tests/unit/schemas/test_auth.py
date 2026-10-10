from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import SecretStr, ValidationError

import backend.app.schemas as schemas_package
from backend.app.schemas.auth import (
    AccessTokenResponse,
    AuthenticatedUserResponse,
    LoginRequest,
    PasswordChangeRequest,
    ProfileUpdateRequest,
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
            "display_name": "Aura Investor",
            "phone_number": "+66 81 234 5678",
            "preferred_language": "en",
            "timezone": "Asia/Bangkok",
            "created_at": timestamp,
            "updated_at": timestamp,
        }
    )

    assert set(response.model_dump()) == {
        "id",
        "email",
        "display_name",
        "phone_number",
        "preferred_language",
        "timezone",
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


def test_profile_update_normalizes_fields_and_requires_password_for_email() -> None:
    request = ProfileUpdateRequest.model_validate(
        {
            "display_name": "  Aura Investor  ",
            "email": " NEW@Example.COM ",
            "phone_number": "  +66 81 234 5678  ",
            "preferred_language": "th",
            "timezone": "Asia/Yangon",
            "current_password": "current-password",
        }
    )

    assert request.display_name == "Aura Investor"
    assert request.email == "new@example.com"
    assert request.phone_number == "+66 81 234 5678"
    assert request.preferred_language == "th"
    assert request.timezone == "Asia/Yangon"
    assert "current-password" not in request.model_dump_json()

    with pytest.raises(ValidationError):
        ProfileUpdateRequest(email="new@example.com")


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"display_name": "   "},
        {"phone_number": "call-me"},
        {"preferred_language": "fr"},
        {"timezone": "UTC"},
        {"current_password": "current-password", "display_name": "Name"},
    ],
)
def test_profile_update_rejects_invalid_or_ambiguous_payloads(
    payload: dict[str, str],
) -> None:
    with pytest.raises(ValidationError):
        ProfileUpdateRequest.model_validate(payload)


def test_profile_update_can_clear_optional_public_fields() -> None:
    request = ProfileUpdateRequest(
        display_name=None,
        phone_number=None,
    )

    assert request.model_fields_set == {"display_name", "phone_number"}


def test_password_change_requires_distinct_secrets_and_never_serializes_them(
) -> None:
    request = PasswordChangeRequest(
        current_password="current-password",
        new_password="replacement-password",
    )

    assert request.current_password.get_secret_value() == "current-password"
    assert request.new_password.get_secret_value() == "replacement-password"
    serialized = request.model_dump_json()
    assert "current-password" not in serialized
    assert "replacement-password" not in serialized

    with pytest.raises(ValidationError):
        PasswordChangeRequest(
            current_password="same-password",
            new_password="same-password",
        )


def test_auth_schemas_do_not_expand_stable_package_exports() -> None:
    assert not {
        "RegistrationRequest",
        "LoginRequest",
        "AuthenticatedUserResponse",
        "AccessTokenResponse",
        "ProfileUpdateRequest",
        "PasswordChangeRequest",
    }.intersection(schemas_package.__all__)
