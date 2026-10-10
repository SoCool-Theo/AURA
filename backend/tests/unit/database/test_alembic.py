from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
import psycopg
import pytest
from pydantic import PostgresDsn, TypeAdapter

from backend.app.core.config import settings
from backend.app.database.base import Base


BACKEND_ROOT = Path(__file__).resolve().parents[3]
ALEMBIC_CONFIG_PATH = BACKEND_ROOT / "alembic.ini"
ALEMBIC_DIRECTORY = BACKEND_ROOT / "alembic"
VERSIONS_DIRECTORY = ALEMBIC_DIRECTORY / "versions"
INITIAL_REVISION = "9f4c2a7b1d3e"
AUTHENTICATION_REVISION = "2b6e5d4a9c81"
SIMULATION_REVISION = "7c1e2f4a6b90"
REAL_HOLDING_REVISION = "d4a6f8c2e1b7"
PLANNED_PORTFOLIO_REVISION = "e5b7c9d2a4f1"
QUANTITY_ONLY_HOLDING_REVISION = "f2c8e9a1b3d4"
WATCHLIST_REVISION = "a8d3f1c6b2e7"
PROFILE_REVISION = "b9e4d2f7c1a6"
NOTIFICATION_REVISION = "c3d5e7f9a2b4"
REFRESH_REVISION = "d6e8f0a2b4c6"
ADMIN_ROLE_REVISION = "e7f9a1b3c5d8"


def _alembic_config() -> Config:
    return Config(ALEMBIC_CONFIG_PATH)


def test_backend_local_alembic_files_exist() -> None:
    assert ALEMBIC_CONFIG_PATH.is_file()
    assert (ALEMBIC_DIRECTORY / "env.py").is_file()
    assert (ALEMBIC_DIRECTORY / "script.py.mako").is_file()
    assert VERSIONS_DIRECTORY.is_dir()


def test_alembic_script_location_resolves_from_config_file() -> None:
    config = _alembic_config()

    script_location = Path(config.get_main_option("script_location"))

    assert script_location.resolve() == ALEMBIC_DIRECTORY.resolve()
    assert ScriptDirectory.from_config(config).dir == str(ALEMBIC_DIRECTORY)


def test_alembic_environment_uses_aura_base_metadata() -> None:
    environment_source = (ALEMBIC_DIRECTORY / "env.py").read_text(
        encoding="utf-8"
    )

    assert "from backend.app.database.base import Base" in environment_source
    assert "target_metadata = Base.metadata" in environment_source
    assert set(Base.metadata.tables) == {
        "market_data_refresh_state",
        "notifications",
        "notification_preferences",
        "analyses",
        "simulations",
        "users",
        "portfolios",
        "holdings",
        "market_data",
        "watchlist_items",
    }


def test_alembic_configuration_contains_no_database_url_or_credentials() -> None:
    configuration = ALEMBIC_CONFIG_PATH.read_text(encoding="utf-8").lower()

    assert "sqlalchemy.url" not in configuration
    assert "postgresql" not in configuration
    assert "password" not in configuration


def test_alembic_configuration_loads_without_connecting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_if_connected(*args: object, **kwargs: object) -> None:
        raise AssertionError("loading Alembic configuration must not connect")

    monkeypatch.setattr(psycopg, "connect", fail_if_connected)

    config = _alembic_config()
    script = ScriptDirectory.from_config(config)

    assert script.dir == str(ALEMBIC_DIRECTORY)
    assert len(list(script.walk_revisions())) == 11


def test_offline_migration_operation_does_not_connect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_if_connected(*args: object, **kwargs: object) -> None:
        raise AssertionError("offline migrations must not connect")

    database_url = TypeAdapter(PostgresDsn).validate_python(
        "postgresql+psycopg://aura:secret@127.0.0.1:1/aura_test"
    )
    monkeypatch.setattr(settings, "database_url", database_url)
    monkeypatch.setattr(psycopg, "connect", fail_if_connected)

    command.upgrade(_alembic_config(), "head", sql=True)


def test_quantity_only_revision_extends_planned_portfolios() -> None:
    revision_files = [
        path
        for path in VERSIONS_DIRECTORY.rglob("*.py")
        if path.name != "__init__.py"
    ]

    assert len(revision_files) == 11
    script = ScriptDirectory.from_config(_alembic_config())
    revisions = list(script.walk_revisions())
    assert [revision.revision for revision in revisions] == [
        ADMIN_ROLE_REVISION,
        REFRESH_REVISION,
        NOTIFICATION_REVISION,
        PROFILE_REVISION,
        WATCHLIST_REVISION,
        QUANTITY_ONLY_HOLDING_REVISION,
        PLANNED_PORTFOLIO_REVISION,
        REAL_HOLDING_REVISION,
        SIMULATION_REVISION,
        AUTHENTICATION_REVISION,
        INITIAL_REVISION,
    ]
    for index, revision in enumerate(revisions):
        assert revision.down_revision == (revisions[index + 1].revision if index + 1 < len(revisions) else None)
    assert script.get_current_head() == ADMIN_ROLE_REVISION
