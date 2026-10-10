from pathlib import Path
from unittest.mock import patch

from alembic.config import Config
from alembic.script import ScriptDirectory
import sqlalchemy as sa


BACKEND_ROOT = Path(__file__).resolve().parents[3]
ALEMBIC_CONFIG_PATH = BACKEND_ROOT / "alembic.ini"
REVISION = "a8d3f1c6b2e7"
PREVIOUS_REVISION = "f2c8e9a1b3d4"
CURRENT_HEAD = "e7f9a1b3c5d8"


def _revision_module():  # type: ignore[no-untyped-def]
    script = ScriptDirectory.from_config(Config(ALEMBIC_CONFIG_PATH))
    revision = script.get_revision(REVISION)
    assert revision is not None
    return revision.module


def test_watchlist_revision_extends_current_head() -> None:
    script = ScriptDirectory.from_config(Config(ALEMBIC_CONFIG_PATH))
    revision = script.get_revision(REVISION)

    assert revision is not None
    assert revision.down_revision == PREVIOUS_REVISION
    assert script.get_current_head() == CURRENT_HEAD


def test_watchlist_upgrade_creates_exact_reversible_table_contract() -> None:
    revision = _revision_module()

    with patch.object(revision.op, "create_table") as create_table:
        revision.upgrade()

    create_table.assert_called_once()
    call = create_table.call_args
    assert call.args[0] == "watchlist_items"
    metadata = sa.MetaData()
    table = sa.Table(call.args[0], metadata, *call.args[1:])
    assert tuple(table.c.keys()) == ("id", "user_id", "symbol", "created_at")
    assert tuple(column.name for column in table.primary_key.columns) == ("id",)
    unique_constraints = {
        constraint.name: tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, sa.UniqueConstraint)
    }
    foreign_keys = {
        constraint.name: (
            tuple(column.name for column in constraint.columns),
            tuple(element.target_fullname for element in constraint.elements),
            constraint.ondelete,
        )
        for constraint in table.foreign_key_constraints
    }
    assert unique_constraints == {
        "uq_watchlist_items_user_symbol": ("user_id", "symbol")
    }
    assert foreign_keys == {
        "fk_watchlist_items_user_id_users": (
            ("user_id",),
            ("users.id",),
            "CASCADE",
        )
    }


def test_watchlist_downgrade_drops_only_watchlist_table() -> None:
    revision = _revision_module()

    with patch.object(revision.op, "drop_table") as drop_table:
        revision.downgrade()

    drop_table.assert_called_once_with("watchlist_items")
