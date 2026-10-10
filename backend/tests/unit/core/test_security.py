from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
import pytest
from pwdlib import PasswordHash
from pydantic import SecretStr

import backend.app.core.security as security_module
from backend.app.core.security import (
    InvalidAccessTokenError,
    SecurityConfigurationError,
    create_access_token,
    decode_access_token,
    decode_access_token_session,
    hash_password,
    verify_dummy_password,
    verify_password,
)


TEST_SECRET = "test-only-signing-secret-with-at-least-thirty-two-bytes"
OTHER_TEST_SECRET = "other-test-only-signing-secret-with-thirty-two-bytes"


@pytest.fixture(autouse=True)
def configured_security(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        security_module.settings,
        "jwt_secret_key",
        SecretStr(TEST_SECRET),
    )
    monkeypatch.setattr(security_module.settings, "jwt_algorithm", "HS256")
    monkeypatch.setattr(
        security_module.settings,
        "access_token_expire_minutes",
        30,
    )


def _claims(
    subject: UUID | str,
    *,
    issued_at: datetime | None = None,
) -> dict[str, object]:
    now = issued_at or datetime.now(UTC)
    return {
        "sub": str(subject),
        "iat": now,
        "exp": now + timedelta(minutes=30),
    }


def test_password_hash_differs_from_plaintext_and_verifies() -> None:
    plaintext = "correct horse battery staple"

    encoded = hash_password(plaintext)

    assert encoded != plaintext
    assert verify_password(plaintext, encoded) is True
    assert verify_password("incorrect password", encoded) is False
    assert plaintext == "correct horse battery staple"


def test_generated_hash_is_pwdlib_compatible_and_salted() -> None:
    plaintext = "same caller-owned password"

    first = hash_password(plaintext)
    second = hash_password(plaintext)

    assert first != second
    verifier = PasswordHash.recommended()
    assert verifier.verify(plaintext, first) is True
    assert verifier.verify(plaintext, second) is True
    assert plaintext == "same caller-owned password"


@pytest.mark.parametrize(
    "malformed_hash",
    ["not-a-password-hash", "$argon2id$malformed"],
)
def test_malformed_password_hash_fails_safely(malformed_hash: str) -> None:
    assert verify_password("candidate", malformed_hash) is False


def test_dummy_password_verification_is_non_authenticating() -> None:
    candidate = "unknown-account-password"

    result = verify_dummy_password(candidate)

    assert result is None
    assert candidate == "unknown-account-password"


def test_valid_access_token_round_trip_returns_original_uuid() -> None:
    subject = uuid4()
    original_subject = subject

    token = create_access_token(subject)

    assert decode_access_token(token) == subject
    assert subject == original_subject


@pytest.mark.parametrize("missing_claim", ["sub", "iat", "exp"])
def test_access_token_requires_all_approved_claims(
    missing_claim: str,
) -> None:
    claims = _claims(uuid4())
    del claims[missing_claim]
    token = jwt.encode(claims, TEST_SECRET, algorithm="HS256")

    with pytest.raises(InvalidAccessTokenError):
        decode_access_token(token)


def test_expired_access_token_is_rejected() -> None:
    now = datetime.now(UTC)
    claims = _claims(uuid4(), issued_at=now - timedelta(minutes=2))
    claims["exp"] = now - timedelta(minutes=1)
    token = jwt.encode(claims, TEST_SECRET, algorithm="HS256")

    with pytest.raises(InvalidAccessTokenError):
        decode_access_token(token)


def test_access_token_with_invalid_signature_is_rejected() -> None:
    token = jwt.encode(
        _claims(uuid4()),
        OTHER_TEST_SECRET,
        algorithm="HS256",
    )

    with pytest.raises(InvalidAccessTokenError):
        decode_access_token(token)


def test_malformed_access_token_is_rejected() -> None:
    with pytest.raises(InvalidAccessTokenError):
        decode_access_token("not-a-jwt")


def test_non_uuid_subject_is_rejected() -> None:
    token = jwt.encode(
        _claims("not-a-uuid"),
        TEST_SECRET,
        algorithm="HS256",
    )

    with pytest.raises(InvalidAccessTokenError):
        decode_access_token(token)


def test_access_token_signed_with_unapproved_algorithm_is_rejected() -> None:
    token = jwt.encode(
        _claims(uuid4()),
        TEST_SECRET,
        algorithm="HS384",
    )

    with pytest.raises(InvalidAccessTokenError):
        decode_access_token(token)


def test_access_token_uses_configured_expiration_and_session_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        security_module.settings,
        "access_token_expire_minutes",
        7,
    )
    subject = uuid4()
    issued_at = datetime(2030, 1, 1, tzinfo=UTC)
    original_issued_at = issued_at

    token = create_access_token(subject, issued_at=issued_at)
    claims = jwt.decode(
        token,
        TEST_SECRET,
        algorithms=["HS256"],
        options={"verify_exp": False, "verify_iat": False},
    )

    assert set(claims) == {"sub", "iat", "exp", "ver"}
    assert claims["ver"] == 0
    assert claims["sub"] == str(subject)
    assert claims["exp"] - claims["iat"] == 7 * 60
    assert issued_at == original_issued_at


def test_session_version_and_legacy_tokens():
    subject = uuid4()
    assert decode_access_token_session(create_access_token(subject, auth_version=3)) == (subject, 3)
    legacy = jwt.encode(_claims(subject), TEST_SECRET, algorithm="HS256")
    assert decode_access_token_session(legacy) == (subject, 0)


@pytest.mark.parametrize("version", [-1, True, 1.5, "1", None])
def test_invalid_session_versions_are_rejected(version):
    claims = {**_claims(uuid4()), "ver": version}
    with pytest.raises(InvalidAccessTokenError):
        decode_access_token_session(jwt.encode(claims, TEST_SECRET, algorithm="HS256"))
    with pytest.raises(ValueError):
        create_access_token(uuid4(), auth_version=version)


@pytest.mark.parametrize(
    "configured_secret",
    [None, SecretStr(""), SecretStr("   ")],
)
def test_missing_or_empty_jwt_secret_fails_at_token_operation_time(
    monkeypatch: pytest.MonkeyPatch,
    configured_secret: SecretStr | None,
) -> None:
    monkeypatch.setattr(
        security_module.settings,
        "jwt_secret_key",
        configured_secret,
    )

    with pytest.raises(SecurityConfigurationError):
        create_access_token(uuid4())
    with pytest.raises(SecurityConfigurationError):
        decode_access_token("not-a-jwt")
