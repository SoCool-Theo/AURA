from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.database.models import User, WatchlistItem
from backend.app.database.repositories import WatchlistRepository


@pytest.fixture
def database_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    User.__table__.create(engine)
    WatchlistItem.__table__.create(engine)
    session = Session(engine, autoflush=False, expire_on_commit=False)
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _user(session: Session) -> User:
    user = User(id=uuid4())
    session.add(user)
    session.flush()
    return user


def test_repository_create_list_find_delete_and_owner_isolation(
    database_session: Session,
) -> None:
    first_user = _user(database_session)
    second_user = _user(database_session)
    repository = WatchlistRepository(database_session)
    start = datetime(2026, 9, 24, 1, tzinfo=UTC)

    later = repository.create(user_id=first_user.id, symbol="MSFT")
    earlier = repository.create(user_id=first_user.id, symbol="AAPL")
    other = repository.create(user_id=second_user.id, symbol="AAPL")
    later.created_at = start + timedelta(seconds=1)
    earlier.created_at = start
    other.created_at = start
    database_session.flush()

    assert repository.list_for_user(first_user.id) == [earlier, later]
    assert repository.find_for_user_by_symbol(
        user_id=first_user.id,
        symbol="AAPL",
    ) is earlier
    assert repository.find_for_user_by_symbol(
        user_id=first_user.id,
        symbol=" aapl ",
    ) is None
    assert repository.find_for_user_by_symbol(
        user_id=second_user.id,
        symbol="MSFT",
    ) is None
    assert repository.delete_for_user_by_symbol(
        user_id=first_user.id,
        symbol="AAPL",
    ) is True
    assert repository.find_for_user_by_symbol(
        user_id=first_user.id,
        symbol="AAPL",
    ) is None
    assert repository.find_for_user_by_symbol(
        user_id=second_user.id,
        symbol="AAPL",
    ) is other


def test_repository_database_constraint_prevents_owner_duplicate(
    database_session: Session,
) -> None:
    user = _user(database_session)
    repository = WatchlistRepository(database_session)
    repository.create(user_id=user.id, symbol="AAPL")

    with pytest.raises(IntegrityError):
        repository.create(user_id=user.id, symbol="AAPL")

    database_session.rollback()


def test_repository_never_owns_session_lifecycle() -> None:
    from unittest.mock import MagicMock

    session = MagicMock(spec=Session)
    repository = WatchlistRepository(session)

    repository.create(user_id=uuid4(), symbol="AAPL")

    session.commit.assert_not_called()
    session.rollback.assert_not_called()
    session.close.assert_not_called()
