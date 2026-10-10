from collections.abc import Iterable
from io import StringIO
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

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
    "ai_request_logs",
    "audit_logs",
    "market_data_refresh_state",
    "notifications",
    "notification_preferences",
    "users",
    "portfolios",
    "holdings",
    "market_data",
    "analyses",
    "simulations",
    "watchlist_items",
}
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
AUDIT_REVISION = "f8a0b2c4d6e9"
AI_MONITORING_REVISION = "a9b1c3d5e7f0"


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


def _planned_portfolio_revision() -> Script:
    revision = _script_directory().get_revision(PLANNED_PORTFOLIO_REVISION)
    assert revision is not None
    return revision


def _quantity_only_holding_revision() -> Script:
    revision = _script_directory().get_revision(QUANTITY_ONLY_HOLDING_REVISION)
    assert revision is not None
    return revision


def _watchlist_revision() -> Script:
    revision = _script_directory().get_revision(WATCHLIST_REVISION)
    assert revision is not None
    return revision


def _profile_revision() -> Script:
    revision = _script_directory().get_revision(PROFILE_REVISION)
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

    planned_revision = _planned_portfolio_revision().module
    connection = MagicMock()
    connection.scalar.return_value = False
    with (
        patch.object(
            planned_revision.context,
            "is_offline_mode",
            return_value=False,
        ),
        patch.object(planned_revision.op, "get_bind", return_value=connection),
        patch.object(planned_revision.op, "add_column") as add_column,
        patch.object(
            planned_revision.op,
            "create_foreign_key",
        ) as create_foreign_key,
        patch.object(planned_revision.op, "execute"),
        patch.object(planned_revision.op, "drop_constraint") as drop_constraint,
        patch.object(
            planned_revision.op,
            "create_check_constraint",
        ) as create_check_constraint,
    ):
        planned_revision.upgrade()

    for add_call in add_column.call_args_list:
        metadata.tables[add_call.args[0]].append_column(add_call.args[1])
    for drop_call in drop_constraint.call_args_list:
        table = metadata.tables[drop_call.args[1]]
        existing = next(
            constraint
            for constraint in table.constraints
            if constraint.name == drop_call.args[0]
        )
        table.constraints.remove(existing)
    for create_call in create_foreign_key.call_args_list:
        metadata.tables[create_call.args[1]].append_constraint(
            sa.ForeignKeyConstraint(
                create_call.args[3],
                [
                    f"{create_call.args[2]}.{column_name}"
                    for column_name in create_call.args[4]
                ],
                name=create_call.args[0],
                ondelete=create_call.kwargs.get("ondelete"),
            )
        )
    for create_call in create_check_constraint.call_args_list:
        metadata.tables[create_call.args[1]].append_constraint(
            sa.CheckConstraint(
                create_call.args[2],
                name=create_call.args[0],
            )
        )

    quantity_only_revision = _quantity_only_holding_revision().module
    with (
        patch.object(
            quantity_only_revision.op,
            "drop_constraint",
        ) as quantity_drop_constraint,
        patch.object(
            quantity_only_revision.op,
            "create_check_constraint",
        ) as quantity_create_check_constraint,
    ):
        quantity_only_revision.upgrade()

    watchlist_revision = _watchlist_revision().module
    with patch.object(watchlist_revision.op, "create_table") as create_table:
        watchlist_revision.upgrade()
    for create_call in create_table.call_args_list:
        sa.Table(create_call.args[0], metadata, *create_call.args[1:])

    profile_revision = _profile_revision().module
    with (
        patch.object(profile_revision.op, "add_column") as add_column,
        patch.object(
            profile_revision.op,
            "create_check_constraint",
        ) as profile_create_check_constraint,
    ):
        profile_revision.upgrade()
    for add_call in add_column.call_args_list:
        metadata.tables[add_call.args[0]].append_column(add_call.args[1])
    for create_call in profile_create_check_constraint.call_args_list:
        metadata.tables[create_call.args[1]].append_constraint(
            sa.CheckConstraint(
                create_call.args[2],
                name=create_call.args[0],
            )
        )

    for drop_call in quantity_drop_constraint.call_args_list:
        table = metadata.tables[drop_call.args[1]]
        existing = next(
            constraint
            for constraint in table.constraints
            if constraint.name == drop_call.args[0]
        )
        table.constraints.remove(existing)
    for create_call in quantity_create_check_constraint.call_args_list:
        metadata.tables[create_call.args[1]].append_constraint(
            sa.CheckConstraint(
                create_call.args[2],
                name=create_call.args[0],
            )
        )
    notification_revision = _script_directory().get_revision(NOTIFICATION_REVISION).module
    with (
        patch.object(notification_revision.op, "create_table") as notification_tables,
        patch.object(notification_revision.op, "create_index") as notification_indexes,
    ):
        notification_revision.upgrade()
    for create_call in notification_tables.call_args_list:
        sa.Table(create_call.args[0], metadata, *create_call.args[1:])
    indexes.extend((call.args[1], call.args[0], tuple(call.args[2]), call.kwargs.get("unique", False)) for call in notification_indexes.call_args_list)
    refresh_revision = _script_directory().get_revision(REFRESH_REVISION).module
    with patch.object(refresh_revision.op, "create_table") as refresh_table:
        refresh_revision.upgrade()
    for create_call in refresh_table.call_args_list:
        sa.Table(create_call.args[0], metadata, *create_call.args[1:])
    admin_revision = _script_directory().get_revision(ADMIN_ROLE_REVISION).module
    with (
        patch.object(admin_revision.op, "add_column") as admin_column,
        patch.object(admin_revision.op, "create_check_constraint") as admin_checks,
    ):
        admin_revision.upgrade()
    for add_call in admin_column.call_args_list:
        metadata.tables[add_call.args[0]].append_column(add_call.args[1])
    for create_call in admin_checks.call_args_list:
        metadata.tables[create_call.args[1]].append_constraint(
            sa.CheckConstraint(create_call.args[2], name=create_call.args[0])
        )
    audit_revision = _script_directory().get_revision(AUDIT_REVISION).module
    with (
        patch.object(audit_revision.op, "create_table") as audit_table,
        patch.object(audit_revision.op, "create_index") as audit_indexes,
    ):
        audit_revision.upgrade()
    for create_call in audit_table.call_args_list:
        sa.Table(create_call.args[0], metadata, *create_call.args[1:])
    indexes.extend(
        (call.args[1], call.args[0], tuple(call.args[2]), call.kwargs.get("unique", False))
        for call in audit_indexes.call_args_list
    )
    ai_revision = _script_directory().get_revision(AI_MONITORING_REVISION).module
    with patch.object(ai_revision.op, "create_table") as ai_table, patch.object(ai_revision.op, "create_index") as ai_indexes:
        ai_revision.upgrade()
    for create_call in ai_table.call_args_list:
        sa.Table(create_call.args[0], metadata, *create_call.args[1:])
    indexes.extend(
        (call.args[1], call.args[0], tuple(call.args[2]), call.kwargs.get("unique", False))
        for call in ai_indexes.call_args_list
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


def test_revisions_form_a_single_ai_monitoring_head() -> None:
    script = _script_directory()
    revisions = list(script.walk_revisions())

    assert [revision.revision for revision in revisions] == [
        AI_MONITORING_REVISION,
        AUDIT_REVISION,
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
    assert script.get_current_head() == AI_MONITORING_REVISION
    for index, revision in enumerate(revisions):
        expected_parent = revisions[index + 1].revision if index + 1 < len(revisions) else None
        assert revision.down_revision == expected_parent
        assert revision.module.down_revision == expected_parent
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
        if table_name not in {"holdings", "portfolios"}:
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
        "watchlist_items",
        "notifications",
        "audit_logs",
        "ai_request_logs",
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
    assert "ADD COLUMN role TEXT DEFAULT 'CUSTOMER' NOT NULL" in upgrade_sql
    assert "CONSTRAINT ck_users_role CHECK (role IN ('CUSTOMER', 'ADMIN'))" in upgrade_sql
    assert "CONSTRAINT ck_users_admin_credentials CHECK" in upgrade_sql
    assert "CONSTRAINT ck_audit_logs_actor CHECK" in upgrade_sql
    assert "CREATE INDEX ix_audit_logs_created_at ON audit_logs (created_at, id)" in upgrade_sql
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
    assert "DROP CONSTRAINT ck_users_admin_credentials" in downgrade_sql
    assert "DROP CONSTRAINT ck_users_role" in downgrade_sql
    assert "DROP COLUMN role" in downgrade_sql
    assert "DROP INDEX ix_audit_logs_created_at" in downgrade_sql
    assert "DROP CONSTRAINT uq_users_email" in downgrade_sql
    assert "DROP COLUMN password_hash" in downgrade_sql
    assert "DROP COLUMN email" in downgrade_sql
