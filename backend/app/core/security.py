"""Pure password and JWT security primitives for Aura authentication."""

from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe
from uuid import UUID

import jwt
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError

from .config import settings


_PASSWORD_HASH = PasswordHash.recommended()
_DUMMY_PASSWORD_HASH = _PASSWORD_HASH.hash(token_urlsafe(32))
_REQUIRED_ACCESS_TOKEN_CLAIMS = ("sub", "iat", "exp")


class SecurityConfigurationError(RuntimeError):
    """Raised when a required security setting is unavailable."""


class InvalidAccessTokenError(ValueError):
    """Raised when an access token cannot produce a trusted UUID subject."""


def hash_password(plaintext_password: str) -> str:
    """Return a recommended, salted password hash for caller-owned text."""
    return _PASSWORD_HASH.hash(plaintext_password)


def verify_password(
    plaintext_password: str,
    encoded_password_hash: str,
) -> bool:
    """Safely verify a password candidate against a supported hash."""
    try:
        return _PASSWORD_HASH.verify(
            plaintext_password,
            encoded_password_hash,
        )
    except (UnknownHashError, ValueError):
        return False


def verify_dummy_password(plaintext_password: str) -> None:
    """Perform one password verification without authenticating an account."""
    _PASSWORD_HASH.verify(plaintext_password, _DUMMY_PASSWORD_HASH)


def create_access_token(
    subject: UUID,
    *,
    issued_at: datetime | None = None,
    auth_version: int = 0,
) -> str:
    """Issue a signed subject/expiry token with a revocable session version."""
    if type(auth_version) is not int or auth_version < 0:
        raise ValueError("auth_version must be a nonnegative integer")
    secret = _configured_jwt_secret()
    issued_at_utc = _utc_datetime(issued_at)
    expires_at = issued_at_utc + timedelta(
        minutes=int(settings.access_token_expire_minutes)
    )
    return jwt.encode(
        {
            "sub": str(subject),
            "iat": issued_at_utc,
            "exp": expires_at,
            "ver": auth_version,
        },
        secret,
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> UUID:
    """Validate a signed access token and return its UUID subject."""
    return decode_access_token_session(token)[0]


def decode_access_token_session(token: str) -> tuple[UUID, int]:
    """Return trusted subject/version; pre-migration tokens have version zero."""
    secret = _configured_jwt_secret()
    try:
        claims = jwt.decode(
            token,
            secret,
            algorithms=[settings.jwt_algorithm],
            options={"require": list(_REQUIRED_ACCESS_TOKEN_CLAIMS)},
        )
        subject = claims["sub"]
        if not isinstance(subject, str):
            raise ValueError("access-token subject must be a string")
        version = claims.get("ver", 0)
        if type(version) is not int or version < 0:
            raise ValueError("invalid access-token version")
        return UUID(subject), version
    except (InvalidTokenError, KeyError, TypeError, ValueError) as error:
        raise InvalidAccessTokenError from error


def _configured_jwt_secret() -> str:
    configured_secret = settings.jwt_secret_key
    if configured_secret is None:
        raise SecurityConfigurationError("JWT secret is not configured")

    secret = configured_secret.get_secret_value()
    if not secret.strip():
        raise SecurityConfigurationError("JWT secret is not configured")
    return secret


def _utc_datetime(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(UTC)
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("issued_at must be timezone-aware")
    return value.astimezone(UTC)
