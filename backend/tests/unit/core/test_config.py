import pytest
from pydantic import SecretStr, ValidationError

from backend.app.core.config import Settings


def test_authentication_settings_are_optional_with_secure_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for variable in (
        "JWT_SECRET_KEY",
        "JWT_ALGORITHM",
        "ACCESS_TOKEN_EXPIRE_MINUTES",
    ):
        monkeypatch.delenv(variable, raising=False)

    configured = Settings(_env_file=None)

    assert configured.jwt_secret_key is None
    assert configured.jwt_algorithm == "HS256"
    assert configured.access_token_expire_minutes == 30


def test_authentication_settings_follow_environment_conventions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    test_secret = "test-only-secret-value-not-a-production-credential"
    monkeypatch.setenv("JWT_SECRET_KEY", test_secret)
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "45")

    configured = Settings(_env_file=None)

    assert isinstance(configured.jwt_secret_key, SecretStr)
    assert configured.jwt_secret_key.get_secret_value() == test_secret
    assert test_secret not in repr(configured)
    assert configured.jwt_algorithm == "HS256"
    assert configured.access_token_expire_minutes == 45


def test_empty_jwt_secret_does_not_break_settings_construction() -> None:
    configured = Settings(_env_file=None, jwt_secret_key="")

    assert configured.jwt_secret_key is not None
    assert configured.jwt_secret_key.get_secret_value() == ""


def test_settings_reject_unapproved_jwt_algorithm() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, jwt_algorithm="HS384")


@pytest.mark.parametrize("minutes", [0, -1])
def test_settings_require_positive_access_token_lifetime(minutes: int) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, access_token_expire_minutes=minutes)


def test_refresh_defaults_and_environment(monkeypatch):
    for name in ("REFRESH_SESSION_IDLE_DAYS", "REFRESH_SESSION_MAX_DAYS", "REFRESH_COOKIE_SECURE", "REFRESH_COOKIE_SAMESITE"):
        monkeypatch.delenv(name, raising=False)
    configured = Settings(_env_file=None)
    assert (configured.refresh_session_idle_days, configured.refresh_session_max_days) == (7, 30)
    assert configured.refresh_cookie_secure is True
    monkeypatch.setenv("REFRESH_SESSION_IDLE_DAYS", "4")
    monkeypatch.setenv("REFRESH_SESSION_MAX_DAYS", "14")
    monkeypatch.setenv("REFRESH_COOKIE_SECURE", "false")
    configured = Settings(_env_file=None)
    assert (configured.refresh_session_idle_days, configured.refresh_session_max_days) == (4, 14)
    assert configured.refresh_cookie_secure is False


@pytest.mark.parametrize("options", [
    {"refresh_session_idle_days": 0}, {"refresh_session_max_days": 0},
    {"refresh_session_idle_days": 31, "refresh_session_max_days": 30},
    {"refresh_cookie_samesite": "none", "refresh_cookie_secure": False},
    {"app_env": "production", "refresh_cookie_secure": False},
])
def test_invalid_refresh_configuration_is_rejected(options):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **options)
