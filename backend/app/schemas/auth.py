"""Module-local authentication request and response contracts."""

import re
from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BeforeValidator,
    EmailStr,
    Field,
    SecretStr,
    model_validator,
)

from .common import AuraBaseModel


def _trim_email(value: object) -> object:
    if not isinstance(value, str):
        return value
    return value.strip()


def _casefold_email(value: str) -> str:
    return value.casefold()


CanonicalEmail = Annotated[
    EmailStr,
    BeforeValidator(_trim_email),
    AfterValidator(_casefold_email),
]
PlaintextPassword = Annotated[SecretStr, Field(min_length=8)]


def _trim_text(value: object) -> object:
    if not isinstance(value, str):
        return value
    return value.strip()


def _validate_phone(value: str) -> str:
    if not re.fullmatch(r"[0-9+().\-\s]+", value):
        raise ValueError("phone number contains unsupported characters")
    return value


DisplayName = Annotated[
    str,
    BeforeValidator(_trim_text),
    Field(min_length=1, max_length=100),
]
PhoneNumber = Annotated[
    str,
    BeforeValidator(_trim_text),
    Field(min_length=4, max_length=32),
    AfterValidator(_validate_phone),
]
PreferredLanguage = Literal["en", "th"]
ProfileTimezone = Literal["Asia/Bangkok", "Asia/Yangon"]


class _EmailPasswordRequest(AuraBaseModel):
    """Shared canonical email and secret password input contract."""

    email: CanonicalEmail
    password: PlaintextPassword


class RegistrationRequest(_EmailPasswordRequest):
    """Validated input for future account registration."""


class LoginRequest(_EmailPasswordRequest):
    """Validated input for future email/password authentication."""


class AuthenticatedUserResponse(AuraBaseModel):
    """Public representation of an authentication-capable User."""

    id: UUID
    email: CanonicalEmail
    display_name: str | None
    phone_number: str | None
    preferred_language: PreferredLanguage
    timezone: ProfileTimezone
    created_at: AwareDatetime
    updated_at: AwareDatetime


class ProfileUpdateRequest(AuraBaseModel):
    """Partial authenticated profile update with protected email changes."""

    display_name: DisplayName | None = None
    email: CanonicalEmail | None = None
    phone_number: PhoneNumber | None = None
    preferred_language: PreferredLanguage | None = None
    timezone: ProfileTimezone | None = None
    current_password: PlaintextPassword | None = None

    @model_validator(mode="after")
    def validate_requested_changes(self) -> "ProfileUpdateRequest":
        changed_fields = self.model_fields_set - {"current_password"}
        if not changed_fields:
            raise ValueError("at least one profile field is required")
        if "email" in self.model_fields_set:
            if self.email is None:
                raise ValueError("email cannot be null")
            if self.current_password is None:
                raise ValueError(
                    "current_password is required to change email"
                )
        elif self.current_password is not None:
            raise ValueError(
                "current_password is accepted only with an email change"
            )
        return self


class PasswordChangeRequest(AuraBaseModel):
    """Authenticated password replacement requiring the current secret."""

    current_password: PlaintextPassword
    new_password: PlaintextPassword

    @model_validator(mode="after")
    def require_a_different_password(self) -> "PasswordChangeRequest":
        if (
            self.current_password.get_secret_value()
            == self.new_password.get_secret_value()
        ):
            raise ValueError("new_password must differ from current_password")
        return self


class AccessTokenResponse(AuraBaseModel):
    """Minimal future bearer-token response contract."""

    access_token: Annotated[str, Field(min_length=1)]
    token_type: Literal["bearer"] = "bearer"
