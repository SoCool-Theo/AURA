from collections.abc import Callable, Sequence
from types import ModuleType
from unittest.mock import patch

from alembic.config import Config
from alembic.script import ScriptDirectory
import sqlalchemy as sa

from backend.app.database.models import User


PROFILE_REVISION = "b9e4d2f7c1a6"
WATCHLIST_REVISION = "a8d3f1c6b2e7"


def _revision_module() -> ModuleType:
    script = ScriptDirectory.from_config(Config("backend/alembic.ini"))
    revision = script.get_revision(PROFILE_REVISION)
    assert revision is not None
    return revision.module


def test_upgrade_adds_profile_columns_and_named_constraints() -> None:
    revision = _revision_module()

    with (
        patch.object(revision.op, "add_column") as add_column,
        patch.object(
            revision.op,
            "create_check_constraint",
        ) as create_check_constraint,
    ):
        revision.upgrade()

    assert revision.down_revision == WATCHLIST_REVISION
    columns = [call.args[1] for call in add_column.call_args_list]
    assert [column.name for column in columns] == [
        "display_name",
        "phone_number",
        "preferred_language",
        "timezone",
    ]
    assert all(isinstance(column.type, sa.Text) for column in columns)
    assert columns[0].nullable is True
    assert columns[1].nullable is True
    assert columns[2].nullable is False
    assert columns[3].nullable is False
    assert {call.args[0] for call in create_check_constraint.call_args_list} == {
        "ck_users_display_name_length",
        "ck_users_phone_number_length",
        "ck_users_preferred_language",
        "ck_users_timezone",
    }


def test_profile_constraints_match_user_model() -> None:
    constraints = {constraint.name for constraint in User.__table__.constraints}

    assert {
        "ck_users_display_name_length",
        "ck_users_phone_number_length",
        "ck_users_preferred_language",
        "ck_users_timezone",
    }.issubset(constraints)


def test_downgrade_removes_only_profile_persistence_objects() -> None:
    revision = _revision_module()
    operations: list[tuple[str, Sequence[object], dict[str, object]]] = []

    def record(operation: str) -> Callable[..., None]:
        def recorder(*args: object, **kwargs: object) -> None:
            operations.append((operation, args, kwargs))

        return recorder

    with (
        patch.object(
            revision.op,
            "drop_constraint",
            side_effect=record("drop_constraint"),
        ),
        patch.object(
            revision.op,
            "drop_column",
            side_effect=record("drop_column"),
        ),
    ):
        revision.downgrade()

    assert operations == [
        ("drop_constraint", ("ck_users_timezone", "users"), {"type_": "check"}),
        ("drop_constraint", ("ck_users_preferred_language", "users"), {"type_": "check"}),
        ("drop_constraint", ("ck_users_phone_number_length", "users"), {"type_": "check"}),
        ("drop_constraint", ("ck_users_display_name_length", "users"), {"type_": "check"}),
        ("drop_column", ("users", "timezone"), {}),
        ("drop_column", ("users", "preferred_language"), {}),
        ("drop_column", ("users", "phone_number"), {}),
        ("drop_column", ("users", "display_name"), {}),
    ]
