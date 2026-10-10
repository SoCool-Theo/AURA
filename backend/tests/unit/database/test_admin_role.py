from unittest.mock import MagicMock, patch

from alembic.config import Config
from alembic.script import ScriptDirectory
import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.database.models import User
from backend.app.database.repositories.user_repository import UserRepository


@pytest.fixture
def session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    User.__table__.create(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def test_registration_explicitly_creates_customer_and_default_covers_legacy(session):
    user = UserRepository(session).create(email="user@example.com", password_hash="encoded")
    legacy = User()
    session.add(legacy)
    session.flush()
    assert user.role == legacy.role == "CUSTOMER"


@pytest.mark.parametrize("role,email,password", [
    ("OWNER", "user@example.com", "encoded"),
    ("admin", "user@example.com", "encoded"),
    ("ADMIN", None, None),
])
def test_database_rejects_invalid_roles_and_credentialless_admin(session, role, email, password):
    session.add(User(role=role, email=email, password_hash=password))
    with pytest.raises(IntegrityError):
        session.flush()


def test_role_promotion_persists_only_with_caller_commit(session):
    repository = UserRepository(session)
    first = repository.create(email="first@example.com", password_hash="encoded")
    second = repository.create(email="second@example.com", password_hash="encoded")
    session.commit()
    assert not repository.has_other_admin(second.id)
    repository.promote_to_admin(first)
    assert repository.has_other_admin(second.id)
    assert not repository.has_other_admin(first.id)
    session.rollback()
    assert repository.get_by_id(first.id).role == "CUSTOMER"
    repository.promote_to_admin(first)
    session.commit()
    session.expire_all()
    assert repository.get_by_id(first.id).role == "ADMIN"


def test_bootstrap_lock_is_transaction_scoped_without_repository_commit():
    session = MagicMock(spec=Session)
    UserRepository(session).lock_admin_bootstrap()
    assert str(session.execute.call_args.args[0]) == "LOCK TABLE users IN SHARE ROW EXCLUSIVE MODE"
    session.commit.assert_not_called()


def test_admin_migration_matches_model_and_is_reversible():
    scripts = ScriptDirectory.from_config(Config("backend/alembic.ini"))
    revision = scripts.get_revision("e7f9a1b3c5d8").module
    assert revision.down_revision == "d6e8f0a2b4c6"
    with patch.object(revision.op, "add_column") as add, patch.object(revision.op, "create_check_constraint") as checks:
        revision.upgrade()
    column = add.call_args.args[1]
    assert column.name == "role" and column.nullable is False
    assert column.server_default.arg == "CUSTOMER"
    assert User.__table__.c.role.default.arg == "CUSTOMER"
    model_constraints = {c.name: str(c.sqltext) for c in User.__table__.constraints if hasattr(c, "sqltext")}
    for call in checks.call_args_list:
        assert call.args[2] == model_constraints[call.args[0]]
    with patch.object(revision.op, "drop_constraint") as drop, patch.object(revision.op, "drop_column") as drop_column:
        revision.downgrade()
    assert [c.args[0] for c in drop.call_args_list] == ["ck_users_admin_credentials", "ck_users_role"]
    drop_column.assert_called_once_with("users", "role")
