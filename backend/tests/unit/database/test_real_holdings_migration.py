from collections.abc import Callable, Sequence
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

from alembic.config import Config
from alembic.script import ScriptDirectory
import pytest
import sqlalchemy as sa


BACKEND_ROOT = Path(__file__).resolve().parents[3]
REVISION = "d4a6f8c2e1b7"
PREVIOUS_REVISION = "7c1e2f4a6b90"


def _revision_module() -> ModuleType:
    script = ScriptDirectory.from_config(Config(BACKEND_ROOT / "alembic.ini"))
    revision = script.get_revision(REVISION)
    assert revision is not None
    return revision.module


def test_upgrade_adds_nullable_fields_and_approved_constraints() -> None:
    revision = _revision_module()

    with (
        patch.object(revision.op, "add_column") as add_column,
        patch.object(revision.op, "alter_column") as alter_column,
        patch.object(
            revision.op,
            "create_check_constraint",
        ) as create_check_constraint,
    ):
        revision.upgrade()

    assert revision.down_revision == PREVIOUS_REVISION
    columns = [call.args[1] for call in add_column.call_args_list]
    assert [column.name for column in columns] == [
        "invested_amount",
        "invested_currency",
        "shares",
        "purchase_date",
    ]
    assert all(column.nullable is True for column in columns)
    for column_name in ("invested_amount", "shares"):
        column_type = next(
            column.type for column in columns if column.name == column_name
        )
        assert isinstance(column_type, sa.Numeric)
        assert column_type.precision == 28
        assert column_type.scale == 12
    assert isinstance(columns[1].type, sa.Text)
    assert isinstance(columns[3].type, sa.Date)
    alter_column.assert_called_once()
    assert alter_column.call_args.args == ("holdings", "weight")
    assert alter_column.call_args.kwargs["nullable"] is True
    existing_type = alter_column.call_args.kwargs["existing_type"]
    assert isinstance(existing_type, sa.Numeric)
    assert existing_type.precision == 20
    assert existing_type.scale == 18
    assert {
        call.args[0]: call.args[2]
        for call in create_check_constraint.call_args_list
    } == {
        "ck_holdings_invested_amount_positive": (
            "invested_amount IS NULL OR invested_amount > 0"
        ),
        "ck_holdings_shares_positive": "shares IS NULL OR shares > 0",
        "ck_holdings_invested_currency": (
            "invested_currency IS NULL OR "
            "invested_currency IN ('USD', 'THB')"
        ),
        "ck_holdings_complete_mode": (
            "(weight IS NOT NULL AND invested_amount IS NULL AND "
            "invested_currency IS NULL AND shares IS NULL AND "
            "purchase_date IS NULL) OR "
            "(weight IS NULL AND invested_amount IS NOT NULL AND "
            "invested_currency IS NOT NULL AND shares IS NOT NULL AND "
            "purchase_date IS NOT NULL)"
        ),
    }


def test_downgrade_refuses_non_legacy_rows_before_schema_changes() -> None:
    revision = _revision_module()
    connection = MagicMock()
    connection.scalar.return_value = True

    with (
        patch.object(
            revision.context,
            "is_offline_mode",
            return_value=False,
        ),
        patch.object(revision.op, "get_bind", return_value=connection),
        patch.object(revision.op, "drop_constraint") as drop_constraint,
        patch.object(revision.op, "alter_column") as alter_column,
        patch.object(revision.op, "drop_column") as drop_column,
        pytest.raises(RuntimeError, match="no weights will be fabricated"),
    ):
        revision.downgrade()

    connection.scalar.assert_called_once()
    drop_constraint.assert_not_called()
    alter_column.assert_not_called()
    drop_column.assert_not_called()


def test_downgrade_restores_weight_only_schema_for_legacy_rows() -> None:
    revision = _revision_module()
    connection = MagicMock()
    connection.scalar.return_value = False
    operations: list[tuple[str, Sequence[object], dict[str, object]]] = []

    def record(operation: str) -> Callable[..., None]:
        def recorder(*args: object, **kwargs: object) -> None:
            operations.append((operation, args, kwargs))

        return recorder

    with (
        patch.object(
            revision.context,
            "is_offline_mode",
            return_value=False,
        ),
        patch.object(revision.op, "get_bind", return_value=connection),
        patch.object(
            revision.op,
            "drop_constraint",
            side_effect=record("drop_constraint"),
        ),
        patch.object(
            revision.op,
            "alter_column",
            side_effect=record("alter_column"),
        ),
        patch.object(
            revision.op,
            "drop_column",
            side_effect=record("drop_column"),
        ),
    ):
        revision.downgrade()

    assert [operation for operation, _, _ in operations] == [
        "drop_constraint",
        "drop_constraint",
        "drop_constraint",
        "drop_constraint",
        "alter_column",
        "drop_column",
        "drop_column",
        "drop_column",
        "drop_column",
    ]
    assert [args[0] for _, args, _ in operations[:4]] == [
        "ck_holdings_complete_mode",
        "ck_holdings_invested_currency",
        "ck_holdings_shares_positive",
        "ck_holdings_invested_amount_positive",
    ]
    _, alter_args, alter_kwargs = operations[4]
    assert alter_args == ("holdings", "weight")
    assert alter_kwargs["nullable"] is False
    assert [args[1] for _, args, _ in operations[5:]] == [
        "purchase_date",
        "shares",
        "invested_currency",
        "invested_amount",
    ]


def test_offline_downgrade_emits_database_side_safety_guard() -> None:
    revision = _revision_module()

    with (
        patch.object(
            revision.context,
            "is_offline_mode",
            return_value=True,
        ),
        patch.object(revision.op, "execute") as execute,
        patch.object(revision.op, "get_bind") as get_bind,
        patch.object(revision.op, "drop_constraint"),
        patch.object(revision.op, "alter_column"),
        patch.object(revision.op, "drop_column"),
    ):
        revision.downgrade()

    get_bind.assert_not_called()
    execute.assert_called_once()
    guard_sql = str(execute.call_args.args[0])
    assert "IF EXISTS" in guard_sql
    assert "non-legacy holdings exist" in guard_sql
    assert guard_sql.index("IF EXISTS") < guard_sql.index("RAISE EXCEPTION")
