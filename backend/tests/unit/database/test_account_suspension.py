"""Safe migration defaults and PostgreSQL mutation serialization."""

from unittest.mock import MagicMock, patch

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy.orm import Session

from backend.app.database.models import User
from backend.app.database.repositories.user_repository import UserRepository


def test_suspension_migration_defaults_and_reversible_scope():
    revision = ScriptDirectory.from_config(Config("backend/alembic.ini")).get_revision("b0c2d4e6f8a1").module
    assert revision.down_revision == "a9b1c3d5e7f0"
    with patch.object(revision.op, "add_column") as add, patch.object(revision.op, "create_check_constraint") as check:
        revision.upgrade()
    columns = [call.args[1] for call in add.call_args_list]
    assert [column.name for column in columns] == ["is_suspended", "auth_version"]
    assert all(not column.nullable for column in columns)
    assert str(columns[0].server_default.arg) == "false"
    assert str(columns[1].server_default.arg) == "0"
    check.assert_called_once_with("ck_users_auth_version", "users", "auth_version >= 0")
    assert User.__table__.c.is_suspended.default.arg is False
    assert User.__table__.c.auth_version.default.arg == 0
    with patch.object(revision.op, "drop_constraint"), patch.object(revision.op, "drop_column") as drop:
        revision.downgrade()
    assert [call.args for call in drop.call_args_list] == [("users", "auth_version"), ("users", "is_suspended")]


def test_status_lock_uses_same_transaction_lock_as_bootstrap():
    session = MagicMock(spec=Session)
    session.get_bind.return_value.dialect.name = "postgresql"
    UserRepository(session).lock_account_status_changes()
    assert str(session.execute.call_args.args[0]) == "LOCK TABLE users IN SHARE ROW EXCLUSIVE MODE"
    session.commit.assert_not_called()
