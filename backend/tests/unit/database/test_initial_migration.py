from collections.abc import Iterable
from io import StringIO
from pathlib import Path
from types import ModuleType
from unittest.mock import patch

from alembic import command
from alembic.config import Config
from alembic.script import Script, ScriptDirectory
import psycopg
import pytest
from pydantic import PostgresDsn, TypeAdapter
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from backend.app.core.config import settings
from backend.app.database import Base


BACKEND_ROOT = Path(__file__).resolve().parents[3]
ALEMBIC_CONFIG_PATH = BACKEND_ROOT / "alembic.ini"
EXPECTED_TABLES = {
    "users",
    "portfolios",
    "holdings",
    "market_data",
    "analyses",
    "simulations",
}
INITIAL_REVISION = "9f4c2a7b1d3e"
AUTHENTICATION_REVISION = "2b6e5d4a9c81"
SIMULATION_REVISION = "7c1e2f4a6b90"
REAL_HOLDING_REVISION = "d4a6f8c2e1b7"


def _script_directory() -> ScriptDirectory:
    return ScriptDirectory.from_config(Config(ALEMBIC_CONFIG_PATH))


def _initial_revision() -> Script:
    script = _script_directory()
    revision = script.get_revision(INITIAL_REVISION)
    assert revision is not None
    return revision


def _authentication_revision() -> Script:
    revision = _script_directory().get_revision(AUTHENTICATION_REVISION)
    assert revision is not None
    return revision


def _simulation_revision() -> Script:
    revision = _script_directory().get_revision(SIMULATION_REVISION)
    assert revision is not None
    return revision


def _real_holding_revision() -> Script:
    revision = _script_directory().get_revision(REAL_HOLDING_REVISION)
    assert revision is not None
    return revision


def _revision_module() -> ModuleType:
    return _initial_revision().module


def _captured_upgrade() -> tuple[
    sa.MetaData,
    list[tuple[str, str, tuple[str, ...], bool]],
]:
    revision = _revision_module()
    with (
        patch.object(revision.op, "create_table") as create_table,
        patch.object(revision.op, "create_index") as create_index,
        patch.object(revision.op, "execute") as execute,
    ):
        revision.upgrade()

    execute.assert_not_called()
    metadata = sa.MetaData()
    for create_call in create_table.call_args_list:
        table_name = create_call.args[0]
        sa.Table(table_name, metadata, *create_call.args[1:])

    indexes = [
        (
            create_call.args[1],
            create_call.args[0],
            tuple(create_call.args[2]),
            create_call.kwargs.get("unique", False),
        )
        for create_call in create_index.call_args_list
    ]

    authentication_revision = _authentication_revision().module
    with (
        patch.object(authentication_revision.op, "add_column") as add_column,
        patch.object(
            authentication_revision.op,
            "create_unique_constraint",
        ) as create_unique_constraint,
        patch.object(
            authentication_revision.op,
            "create_check_constraint",
        ) as create_check_constraint,
    ):
        authentication_revision.upgrade()

    for add_call in add_column.call_args_list:
        metadata.tables[add_call.args[0]].append_column(add_call.args[1])
    for create_call in create_unique_constraint.call_args_list:
        metadata.tables[create_call.args[1]].append_constraint(
            sa.UniqueConstraint(
                *create_call.args[2],
                name=create_call.args[0],
            )
        )
    for create_call in create_check_constraint.call_args_list:
        metadata.tables[create_call.args[1]].append_constraint(
            sa.CheckConstraint(
                create_call.args[2],
                name=create_call.args[0],
            )
        )

    simulation_revision = _simulation_revision().module
    with (
        patch.object(simulation_revision.op, "create_table") as create_table,
        patch.object(simulation_revision.op, "create_index") as create_index,
    ):
        simulation_revision.upgrade()

    for create_call in create_table.call_args_list:
        sa.Table(create_call.args[0], metadata, *create_call.args[1:])
    indexes.extend(
        (
            create_call.args[1],
            create_call.args[0],
            tuple(create_call.args[2]),
            create_call.kwargs.get("unique", False),
        )
        for create_call in create_index.call_args_list
    )

    real_holding_revision = _real_holding_revision().module
    with (
        patch.object(real_holding_revision.op, "add_column") as add_column,
        patch.object(real_holding_revision.op, "alter_column") as alter_column,
        patch.object(
            real_holding_revision.op,
            "create_check_constraint",
        ) as create_check_constraint,
    ):
        real_holding_revision.upgrade()

    for add_call in add_column.call_args_list:
        metadata.tables[add_call.args[0]].append_column(add_call.args[1])
    for alter_call in alter_column.call_args_list:
        metadata.tables[alter_call.args[0]].c[
            alter_call.args[1]
        ].nullable = alter_call.kwargs["nullable"]
    for create_call in create_check_constraint.call_args_list:
        metadata.tables[create_call.args[1]].append_constraint(
            sa.CheckConstraint(
                create_call.args[2],
                name=create_call.args[0],
            )
        )
    return metadata, indexes


def _server_default(column: sa.Column[object]) -> str | None:
    if column.server_default is None:
        return None
    return str(column.server_default.arg)


def _check_constraints(table: sa.Table) -> set[tuple[str | None, str]]:
    return {
        (constraint.name, str(constraint.sqltext))
        for constraint in table.constraints
        if isinstance(constraint, sa.CheckConstraint)
    }


def _unique_constraints(table: sa.Table) -> set[tuple[str | None, tuple[str, ...]]]:
    return {
        (
            constraint.name,
            tuple(column.name for column in constraint.columns),
        )
        for constraint in table.constraints
        if isinstance(constraint, sa.UniqueConstraint)
    }


def _foreign_keys(
    table: sa.Table,
) -> set[tuple[tuple[str, ...], tuple[str, ...], str | None]]:
    return {
        (
            tuple(column.name for column in constraint.columns),
            tuple(element.target_fullname for element in constraint.elements),
            constraint.ondelete,
        )
        for constraint in table.foreign_key_constraints
    }


def _model_indexes() -> set[tuple[str, str, tuple[str, ...], bool]]:
    return {
        (
            table.name,
            index.name,
            tuple(column.name for column in index.columns),
            index.unique,
        )
        for table in Base.metadata.tables.values()
        for index in table.indexes
    }


def test_revisions_form_a_single_real_holding_head() -> None:
    script = _script_directory()
    revisions = list(script.walk_revisions())

    assert [revision.revision for revision in revisions] == [
        REAL_HOLDING_REVISION,
        SIMULATION_REVISION,
        AUTHENTICATION_REVISION,
        INITIAL_REVISION,
    ]
    assert script.get_current_head() == REAL_HOLDING_REVISION
    assert revisions[0].down_revision == SIMULATION_REVISION
    assert revisions[0].module.down_revision == SIMULATION_REVISION
    assert revisions[1].down_revision == AUTHENTICATION_REVISION
    assert revisions[1].module.down_revision == AUTHENTICATION_REVISION
    assert revisions[2].down_revision == INITIAL_REVISION
    assert revisions[2].module.down_revision == INITIAL_REVISION
    assert revisions[3].down_revision is None
    assert revisions[3].module.down_revision is None
    assert all(callable(revision.module.upgrade) for revision in revisions)
    assert all(callable(revision.module.downgrade) for revision in revisions)


def test_upgrade_creates_exactly_the_model_tables_in_fk_safe_order() -> None:
    revision = _revision_module()
    operations: list[tuple[str, str]] = []

    def record_table(name: str, *args: object, **kwargs: object) -> None:
        operations.append(("table", name))

    def record_index(
        name: str,
        table_name: str,
        columns: Iterable[str],
        **kwargs: object,
    ) -> None:
        operations.append(("index", name))

    with (
        patch.object(revision.op, "create_table", side_effect=record_table),
        patch.object(revision.op, "create_index", side_effect=record_index),
    ):
        revision.upgrade()

    assert operations == [
        ("table", "users"),
        ("table", "portfolios"),
        ("table", "holdings"),
        ("table", "market_data"),
        ("index", "ix_market_data_date"),
        ("table", "analyses"),
        ("index", "ix_analyses_portfolio_created_at"),
    ]


def test_migration_table_metadata_matches_existing_base_metadata() -> None:
    migration_metadata, migration_indexes = _captured_upgrade()
    dialect = postgresql.dialect()

    assert set(migration_metadata.tables) == EXPECTED_TABLES
    assert set(Base.metadata.tables) == EXPECTED_TABLES

    for table_name in EXPECTED_TABLES:
        migration_table = migration_metadata.tables[table_name]
        model_table = Base.metadata.tables[table_name]

        assert set(migration_table.c.keys()) == set(model_table.c.keys())
        if table_name != "holdings":
            assert tuple(migration_table.c.keys()) == tuple(
                model_table.c.keys()
            )
        assert tuple(
            column.name for column in migration_table.primary_key.columns
        ) == tuple(column.name for column in model_table.primary_key.columns)

        for column_name in model_table.c.keys():
            migration_column = migration_table.c[column_name]
            model_column = model_table.c[column_name]
            assert migration_column.type.compile(dialect=dialect) == (
                model_column.type.compile(dialect=dialect)
            )
            assert migration_column.nullable is model_column.nullable
            assert _server_default(migration_column) == _server_default(
                model_column
            )

        assert _check_constraints(migration_table) == _check_constraints(
            model_table
        )
        assert _unique_constraints(migration_table) == _unique_constraints(
            model_table
        )
        assert _foreign_keys(migration_table) == _foreign_keys(model_table)

    assert set(migration_indexes) == _model_indexes()


def test_uuid_identifiers_have_no_database_generated_defaults() -> None:
    migration_metadata, _ = _captured_upgrade()

    for table_name in (
        "users",
        "portfolios",
        "holdings",
        "analyses",
        "simulations",
    ):
        id_column = migration_metadata.tables[table_name].c.id
        assert isinstance(id_column.type, sa.Uuid)
        assert id_column.server_default is None


def test_downgrade_reverses_every_upgrade_object_in_safe_order() -> None:
    revision = _revision_module()
    operations: list[tuple[str, str]] = []

    def record_index(name: str, **kwargs: object) -> None:
        operations.append(("index", name))

    def record_table(name: str, **kwargs: object) -> None:
        operations.append(("table", name))

    with (
        patch.object(revision.op, "drop_index", side_effect=record_index),
        patch.object(revision.op, "drop_table", side_effect=record_table),
    ):
        revision.downgrade()

    assert operations == [
        ("index", "ix_analyses_portfolio_created_at"),
        ("table", "analyses"),
        ("index", "ix_market_data_date"),
        ("table", "market_data"),
        ("table", "holdings"),
        ("table", "portfolios"),
        ("table", "users"),
    ]


def test_postgresql_offline_upgrade_and_downgrade_sql_without_connection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_if_connected(*args: object, **kwargs: object) -> None:
        raise AssertionError("offline migrations must not connect")

    database_url = TypeAdapter(PostgresDsn).validate_python(
        "postgresql+psycopg://aura:secret@127.0.0.1:1/aura_test"
    )
    monkeypatch.setattr(settings, "database_url", database_url)
    monkeypatch.setattr(psycopg, "connect", fail_if_connected)

    upgrade_output = StringIO()
    upgrade_config = Config(
        ALEMBIC_CONFIG_PATH,
        output_buffer=upgrade_output,
    )
    command.upgrade(upgrade_config, "head", sql=True)
    upgrade_sql = upgrade_output.getvalue()

    for table_name in EXPECTED_TABLES:
        assert f"CREATE TABLE {table_name}" in upgrade_sql
    assert "JSONB" in upgrade_sql
    assert "PRIMARY KEY (symbol, date)" in upgrade_sql
    assert "ON DELETE CASCADE" in upgrade_sql
    assert "ADD COLUMN email TEXT" in upgrade_sql
    assert "ADD COLUMN password_hash TEXT" in upgrade_sql
    assert "CONSTRAINT uq_users_email UNIQUE (email)" in upgrade_sql
    assert "CONSTRAINT ck_users_credentials_complete CHECK" in upgrade_sql
    assert "gen_random_uuid" not in upgrade_sql
    assert "uuid_generate" not in upgrade_sql

    downgrade_output = StringIO()
    downgrade_config = Config(
        ALEMBIC_CONFIG_PATH,
        output_buffer=downgrade_output,
    )
    command.downgrade(downgrade_config, "head:base", sql=True)
    downgrade_sql = downgrade_output.getvalue()

    for table_name in EXPECTED_TABLES:
        assert f"DROP TABLE {table_name}" in downgrade_sql
    assert "DROP INDEX ix_analyses_portfolio_created_at" in downgrade_sql
    assert "DROP INDEX ix_simulations_portfolio_created_at" in downgrade_sql
    assert "DROP INDEX ix_market_data_date" in downgrade_sql
    assert "DROP CONSTRAINT ck_users_credentials_complete" in downgrade_sql
    assert "DROP CONSTRAINT uq_users_email" in downgrade_sql
    assert "DROP COLUMN password_hash" in downgrade_sql
    assert "DROP COLUMN email" in downgrade_sql
