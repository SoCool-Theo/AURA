from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.app.database.models import User
from backend.app.database.repositories import UserRepository
import backend.app.database.repositories.user_repository as repository_module


@pytest.fixture
def database_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    User.__table__.create(engine)
    session = Session(engine, autoflush=False, expire_on_commit=False)
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def test_lookup_by_canonical_email_returns_expected_user(
    database_session: Session,
) -> None:
    expected = User(
        email="user@example.com",
        password_hash="already-encoded-hash",
    )
    database_session.add(expected)
    database_session.flush()

    result = UserRepository(database_session).get_by_email(
        "user@example.com"
    )

    assert result is expected


def test_unknown_canonical_email_returns_none(
    database_session: Session,
) -> None:
    assert (
        UserRepository(database_session).get_by_email("missing@example.com")
        is None
    )


def test_create_adds_and_flushes_without_owning_session_lifecycle() -> None:
    session = MagicMock(spec=Session)

    created = UserRepository(session).create(
        email="user@example.com",
        password_hash="already-encoded-hash",
    )

    assert created.email == "user@example.com"
    assert created.password_hash == "already-encoded-hash"
    session.add.assert_called_once_with(created)
    session.flush.assert_called_once_with()
    session.commit.assert_not_called()
    session.rollback.assert_not_called()
    session.close.assert_not_called()


def test_repository_does_not_normalize_email_or_hash_password() -> None:
    session = MagicMock(spec=Session)

    created = UserRepository(session).create(
        email="Mixed.Case@Example.COM",
        password_hash="caller-supplied-value",
    )

    assert created.email == "Mixed.Case@Example.COM"
    assert created.password_hash == "caller-supplied-value"


def test_credentialless_legacy_users_remain_unaffected(
    database_session: Session,
) -> None:
    first = User()
    second = User(id=uuid4())
    database_session.add_all([first, second])
    database_session.flush()

    repository = UserRepository(database_session)

    assert repository.get_by_email("missing@example.com") is None
    assert first.email is first.password_hash is None
    assert second.email is second.password_hash is None


def test_repository_has_no_schema_or_security_dependency() -> None:
    source = Path(repository_module.__file__).read_text(encoding="utf-8")

    assert "schemas" not in source
    assert "security" not in source
    assert "hash_password" not in source
