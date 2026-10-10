from collections.abc import Callable, Sequence
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

from alembic.config import Config
from alembic.script import ScriptDirectory
import pytest
import sqlalchemy as sa


BACKEND_ROOT = Path(__file__).resolve().parents[3]
REVISION = "e5b7c9d2a4f1"
PREVIOUS_REVISION = "d4a6f8c2e1b7"


def _revision_module() -> ModuleType:
    script = ScriptDirectory.from_config(Config(BACKEND_ROOT / "alembic.ini"))
    revision = script.get_revision(REVISION)
    assert revision is not None
    return revision.module


def test_upgrade_adds_planned_foundation_and_backfills_legacy_type() -> None:
    revision = _revision_module()
    connection = MagicMock()
    connection.scalar.return_value = False

    with (
        patch.object(
            revision.context,
            "is_offline_mode",
            return_value=False,
        ),
        patch.object(revision.op, "get_bind", return_value=connection),
        patch.object(revision.op, "add_column") as add_column,
        patch.object(revision.op, "create_foreign_key") as create_foreign_key,
        patch.object(revision.op, "execute") as execute,
        patch.object(revision.op, "drop_constraint") as drop_constraint,
        patch.object(
            revision.op,
            "create_check_constraint",
        ) as create_check_constraint,
    ):
        revision.upgrade()

    assert revision.down_revision == PREVIOUS_REVISION
    connection.scalar.assert_called_once()
    added = [(call.args[0], call.args[1]) for call in add_column.call_args_list]
    assert [(table, column.name) for table, column in added] == [
        ("portfolios", "portfolio_type"),
        ("portfolios", "plan_currency"),
        ("portfolios", "source_plan_id"),
        ("holdings", "proposed_amount"),
    ]
    portfolio_type = added[0][1]
    assert isinstance(portfolio_type.type, sa.Text)
    assert portfolio_type.nullable is False
    assert str(portfolio_type.server_default.arg) == "'CURRENT'"
    proposed_amount = added[3][1]
    assert isinstance(proposed_amount.type, sa.Numeric)
    assert proposed_amount.type.precision == 28
    assert proposed_amount.type.scale == 12
    assert proposed_amount.nullable is True

    create_foreign_key.assert_called_once_with(
        "fk_portfolios_source_plan_id_portfolios",
        "portfolios",
        "portfolios",
        ["source_plan_id"],
        ["id"],
        ondelete="SET NULL",
    )
    execute.assert_called_once()
    backfill_sql = str(execute.call_args.args[0])
    assert "UPDATE portfolios SET portfolio_type = 'LEGACY'" in backfill_sql
    assert "holdings.weight IS NOT NULL" in backfill_sql
    drop_constraint.assert_called_once_with(
        "ck_holdings_complete_mode",
        "holdings",
        type_="check",
    )
    constraints = {
        call.args[0]: (call.args[1], call.args[2])
        for call in create_check_constraint.call_args_list
    }
    assert set(constraints) == {
        "ck_portfolios_type",
        "ck_portfolios_plan_currency_by_type",
        "ck_portfolios_source_plan",
        "ck_holdings_proposed_amount_positive",
        "ck_holdings_complete_mode",
    }
    assert "proposed_amount IS NOT NULL" in constraints[
        "ck_holdings_complete_mode"
    ][1]


def test_upgrade_refuses_mixed_or_incomplete_existing_portfolios() -> None:
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
        patch.object(revision.op, "add_column") as add_column,
        patch.object(revision.op, "create_foreign_key") as create_foreign_key,
        patch.object(revision.op, "execute") as execute,
        patch.object(revision.op, "drop_constraint") as drop_constraint,
        patch.object(
            revision.op,
            "create_check_constraint",
        ) as create_check_constraint,
        pytest.raises(RuntimeError, match="made no changes"),
    ):
        revision.upgrade()

    add_column.assert_not_called()
    create_foreign_key.assert_not_called()
    execute.assert_not_called()
    drop_constraint.assert_not_called()
    create_check_constraint.assert_not_called()


def test_downgrade_refuses_planned_data_or_source_provenance() -> None:
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
        patch.object(
            revision.op,
            "create_check_constraint",
        ) as create_check_constraint,
        patch.object(revision.op, "drop_column") as drop_column,
        pytest.raises(RuntimeError, match="no planned data will be discarded"),
    ):
        revision.downgrade()

    drop_constraint.assert_not_called()
    create_check_constraint.assert_not_called()
    drop_column.assert_not_called()


def test_safe_downgrade_restores_real_holding_schema() -> None:
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
            "create_check_constraint",
            side_effect=record("create_check_constraint"),
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
        "create_check_constraint",
        "drop_column",
        "drop_constraint",
        "drop_constraint",
        "drop_constraint",
        "drop_constraint",
        "drop_column",
        "drop_column",
        "drop_column",
    ]
    assert operations[0][1][0] == "ck_holdings_complete_mode"
    assert operations[1][1][0] == "ck_holdings_proposed_amount_positive"
    assert operations[2][1][0] == "ck_holdings_complete_mode"
    assert operations[3][1][1] == "proposed_amount"
    assert operations[7][1][0] == (
        "fk_portfolios_source_plan_id_portfolios"
    )
    assert [operation[1][1] for operation in operations[8:]] == [
        "source_plan_id",
        "plan_currency",
        "portfolio_type",
    ]


def test_offline_upgrade_and_downgrade_emit_database_guards() -> None:
    revision = _revision_module()

    with (
        patch.object(
            revision.context,
            "is_offline_mode",
            return_value=True,
        ),
        patch.object(revision.op, "execute") as execute,
        patch.object(revision.op, "get_bind") as get_bind,
        patch.object(revision.op, "add_column"),
        patch.object(revision.op, "create_foreign_key"),
        patch.object(revision.op, "drop_constraint"),
        patch.object(revision.op, "create_check_constraint"),
    ):
        revision.upgrade()

    get_bind.assert_not_called()
    assert execute.call_count == 2
    upgrade_guard = str(execute.call_args_list[0].args[0])
    assert "mixed or incomplete portfolio holdings" in upgrade_guard
    assert "RAISE EXCEPTION" in upgrade_guard

    with (
        patch.object(
            revision.context,
            "is_offline_mode",
            return_value=True,
        ),
        patch.object(revision.op, "execute") as execute,
        patch.object(revision.op, "get_bind") as get_bind,
        patch.object(revision.op, "drop_constraint"),
        patch.object(revision.op, "create_check_constraint"),
        patch.object(revision.op, "drop_column"),
    ):
        revision.downgrade()

    get_bind.assert_not_called()
    execute.assert_called_once()
    downgrade_guard = str(execute.call_args.args[0])
    assert "planned portfolio data or source-plan provenance" in downgrade_guard
    assert "RAISE EXCEPTION" in downgrade_guard
