"""Module-local authentication request and response contracts."""

from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BeforeValidator,
    EmailStr,
    Field,
    SecretStr,
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
    created_at: AwareDatetime
    updated_at: AwareDatetime


class AccessTokenResponse(AuraBaseModel):
    """Minimal future bearer-token response contract."""

    access_token: Annotated[str, Field(min_length=1)]
    token_type: Literal["bearer"] = "bearer"
