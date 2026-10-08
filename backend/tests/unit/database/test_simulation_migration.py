from pathlib import Path
from types import ModuleType
from unittest.mock import patch

from alembic.config import Config
from alembic.script import ScriptDirectory
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from backend.app.database.models import Simulation


BACKEND_ROOT = Path(__file__).resolve().parents[3]
REVISION = "7c1e2f4a6b90"
PREVIOUS_REVISION = "2b6e5d4a9c81"


def _revision_module() -> ModuleType:
    script = ScriptDirectory.from_config(Config(BACKEND_ROOT / "alembic.ini"))
    revision = script.get_revision(REVISION)
    assert revision is not None
    return revision.module


def test_upgrade_matches_simulation_model_metadata() -> None:
    revision = _revision_module()
    with (
        patch.object(revision.op, "create_table") as create_table,
        patch.object(revision.op, "create_index") as create_index,
    ):
        revision.upgrade()

    assert revision.down_revision == PREVIOUS_REVISION
    create_table.assert_called_once()
    call = create_table.call_args
    table = sa.Table(call.args[0], sa.MetaData(), *call.args[1:])
    model = Simulation.__table__
    dialect = postgresql.dialect()

    assert tuple(table.c.keys()) == tuple(model.c.keys())
    for name in model.c.keys():
        assert table.c[name].type.compile(dialect=dialect) == (
            model.c[name].type.compile(dialect=dialect)
        )
        assert table.c[name].nullable is model.c[name].nullable
    assert {
        (constraint.name, str(constraint.sqltext))
        for constraint in table.constraints
        if isinstance(constraint, sa.CheckConstraint)
    } == {
        (constraint.name, str(constraint.sqltext))
        for constraint in model.constraints
        if isinstance(constraint, sa.CheckConstraint)
    }
    foreign_key = next(iter(table.foreign_key_constraints))
    assert foreign_key.ondelete == "CASCADE"
    assert next(iter(foreign_key.elements)).target_fullname == "portfolios.id"
    create_index.assert_called_once_with(
        "ix_simulations_portfolio_created_at",
        "simulations",
        ["portfolio_id", "created_at"],
        unique=False,
    )


def test_downgrade_removes_only_revision_owned_index_and_table() -> None:
    revision = _revision_module()
    operations: list[tuple[str, str]] = []

    with (
        patch.object(
            revision.op,
            "drop_index",
            side_effect=lambda name, **kwargs: operations.append(("index", name)),
        ),
        patch.object(
            revision.op,
            "drop_table",
            side_effect=lambda name: operations.append(("table", name)),
        ),
    ):
        revision.downgrade()

    assert operations == [
        ("index", "ix_simulations_portfolio_created_at"),
        ("table", "simulations"),
    ]
