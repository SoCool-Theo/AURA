import pytest
from pydantic import ValidationError

from backend.app.core.config import Settings


def test_settings_allow_database_url_to_be_unconfigured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)

    configured = Settings(_env_file=None)

    assert configured.database_url is None


def test_settings_accept_psycopg_postgresql_url() -> None:
    configured = Settings(
        _env_file=None,
        database_url=(
            "postgresql+psycopg://aura:secret@localhost:5432/aura_test"
        ),
    )

    assert configured.database_url is not None
    assert configured.database_url.scheme == "postgresql+psycopg"
    assert configured.database_url.hosts()[0]["host"] == "localhost"


@pytest.mark.parametrize(
    "database_url",
    [
        "postgresql+asyncpg://aura:secret@localhost/aura",
        "postgresql+psycopg2://aura:secret@localhost/aura",
    ],
)
def test_settings_reject_non_psycopg3_driver(database_url: str) -> None:
    with pytest.raises(
        ValidationError,
        match="DATABASE_URL must use the postgresql\\+psycopg driver",
    ):
        Settings(_env_file=None, database_url=database_url)
