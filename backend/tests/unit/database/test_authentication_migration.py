from collections.abc import Callable, Sequence
from types import ModuleType
from unittest.mock import patch

from alembic.config import Config
from alembic.script import ScriptDirectory
import sqlalchemy as sa

from backend.app.database.models import User


AUTHENTICATION_REVISION = "2b6e5d4a9c81"
INITIAL_REVISION = "9f4c2a7b1d3e"


def _revision_module() -> ModuleType:
    script = ScriptDirectory.from_config(Config("backend/alembic.ini"))
    revision = script.get_revision(AUTHENTICATION_REVISION)
    assert revision is not None
    return revision.module


def test_upgrade_adds_credential_columns_and_named_constraints(
) -> None:
    revision = _revision_module()

    with (
        patch.object(revision.op, "add_column") as add_column,
        patch.object(
            revision.op,
            "create_unique_constraint",
        ) as create_unique_constraint,
        patch.object(
            revision.op,
            "create_check_constraint",
        ) as create_check_constraint,
    ):
        revision.upgrade()

    assert revision.down_revision == INITIAL_REVISION
    added_columns = [call.args for call in add_column.call_args_list]
    assert [arguments[0] for arguments in added_columns] == ["users", "users"]
    assert [arguments[1].name for arguments in added_columns] == [
        "email",
        "password_hash",
    ]
    assert all(
        isinstance(arguments[1].type, sa.Text)
        and arguments[1].nullable is True
        for arguments in added_columns
    )
    create_unique_constraint.assert_called_once_with(
        "uq_users_email",
        "users",
        ["email"],
    )
    create_check_constraint.assert_called_once_with(
        "ck_users_credentials_complete",
        "users",
        "(email IS NULL AND password_hash IS NULL) OR "
        "(email IS NOT NULL AND password_hash IS NOT NULL)",
    )


def test_migration_constraints_match_user_model() -> None:
    constraints = {constraint.name for constraint in User.__table__.constraints}

    assert "uq_users_email" in constraints
    assert "ck_users_credentials_complete" in constraints


def test_downgrade_removes_only_authentication_persistence_objects() -> None:
    revision = _revision_module()
    operations: list[tuple[str, Sequence[object], dict[str, object]]] = []

    def record(
        operation: str,
    ) -> Callable[..., None]:
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
        (
            "drop_constraint",
            ("ck_users_credentials_complete", "users"),
            {"type_": "check"},
        ),
        (
            "drop_constraint",
            ("uq_users_email", "users"),
            {"type_": "unique"},
        ),
        ("drop_column", ("users", "password_hash"), {}),
        ("drop_column", ("users", "email"), {}),
    ]
