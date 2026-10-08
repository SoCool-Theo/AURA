from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

from alembic.config import Config
from alembic.script import ScriptDirectory
import pytest


BACKEND_ROOT = Path(__file__).resolve().parents[3]
REVISION = "f2c8e9a1b3d4"
PREVIOUS_REVISION = "e5b7c9d2a4f1"


def _revision_module() -> ModuleType:
    script = ScriptDirectory.from_config(Config(BACKEND_ROOT / "alembic.ini"))
    revision = script.get_revision(REVISION)
    assert revision is not None
    return revision.module


def test_upgrade_extends_planned_mode_constraint_for_quantity_only_current() -> None:
    revision = _revision_module()
    with (
        patch.object(revision.op, "drop_constraint") as drop_constraint,
        patch.object(revision.op, "create_check_constraint") as create_check_constraint,
    ):
        revision.upgrade()

    assert revision.down_revision == PREVIOUS_REVISION
    drop_constraint.assert_called_once_with(
        "ck_holdings_complete_mode", "holdings", type_="check"
    )
    create_check_constraint.assert_called_once_with(
        "ck_holdings_complete_mode", "holdings", revision._NEW_MODE_CHECK
    )
    assert "shares IS NOT NULL" in revision._NEW_MODE_CHECK
    assert "proposed_amount IS NOT NULL" in revision._NEW_MODE_CHECK
    assert "invested_amount IS NULL" in revision._NEW_MODE_CHECK


def test_downgrade_refuses_when_quantity_only_rows_exist() -> None:
    revision = _revision_module()
    connection = MagicMock()
    connection.scalar.return_value = True
    with (
        patch.object(revision.context, "is_offline_mode", return_value=False),
        patch.object(revision.op, "get_bind", return_value=connection),
        patch.object(revision.op, "drop_constraint") as drop_constraint,
        patch.object(revision.op, "create_check_constraint") as create_check_constraint,
        pytest.raises(RuntimeError, match="quantity-only rows exist"),
    ):
        revision.downgrade()
    drop_constraint.assert_not_called()
    create_check_constraint.assert_not_called()


def test_downgrade_restores_prior_planned_constraint_when_safe() -> None:
    revision = _revision_module()
    connection = MagicMock()
    connection.scalar.return_value = False
    with (
        patch.object(revision.context, "is_offline_mode", return_value=False),
        patch.object(revision.op, "get_bind", return_value=connection),
        patch.object(revision.op, "drop_constraint") as drop_constraint,
        patch.object(revision.op, "create_check_constraint") as create_check_constraint,
    ):
        revision.downgrade()
    drop_constraint.assert_called_once()
    create_check_constraint.assert_called_once_with(
        "ck_holdings_complete_mode", "holdings", revision._OLD_MODE_CHECK
    )
    assert "proposed_amount IS NOT NULL" in revision._OLD_MODE_CHECK
