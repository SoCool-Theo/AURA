from unittest.mock import MagicMock, Mock

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from backend.app.database.base import Base
from backend.app.database.connection import (
    check_database_connection,
    create_database_engine,
    create_session_factory,
    session_scope,
)


DATABASE_URL = (
    "postgresql+psycopg://aura:secret@localhost:5432/aura_test"
)


def test_declarative_base_contains_registered_domain_tables() -> None:
    assert set(Base.metadata.tables) == {
        "users",
        "portfolios",
        "holdings",
        "market_data",
    }


def test_engine_uses_postgresql_psycopg_without_connecting() -> None:
    engine = create_database_engine(DATABASE_URL)
    try:
        assert engine.url.drivername == "postgresql+psycopg"
        assert engine.dialect.name == "postgresql"
        assert engine.dialect.driver == "psycopg"
    finally:
        engine.dispose()


def test_engine_requires_configured_database_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "backend.app.database.connection.settings.database_url",
        None,
    )

    with pytest.raises(RuntimeError, match="DATABASE_URL is not configured"):
        create_database_engine()


def test_engine_rejects_non_psycopg_postgresql_url() -> None:
    with pytest.raises(
        ValueError,
        match="database URL must use the postgresql\\+psycopg driver",
    ):
        create_database_engine("sqlite+pysqlite:///:memory:")


def test_session_factory_has_predictable_configuration() -> None:
    engine = Mock(spec=Engine)

    factory = create_session_factory(engine)

    assert factory.kw["bind"] is engine
    assert factory.kw["autoflush"] is False
    assert factory.kw["expire_on_commit"] is False
    assert issubclass(factory.class_, Session)


def test_session_scope_closes_without_automatic_commit() -> None:
    session = MagicMock(spec=Session)
    factory = Mock(return_value=session)

    with session_scope(factory) as yielded_session:
        assert yielded_session is session

    session.commit.assert_not_called()
    session.rollback.assert_not_called()
    session.close.assert_called_once_with()


def test_session_scope_rolls_back_closes_and_preserves_exception() -> None:
    session = MagicMock(spec=Session)
    factory = Mock(return_value=session)
    failure = RuntimeError("repository operation failed")

    with pytest.raises(RuntimeError) as raised:
        with session_scope(factory):
            raise failure

    assert raised.value is failure
    session.commit.assert_not_called()
    session.rollback.assert_called_once_with()
    session.close.assert_called_once_with()


def test_connectivity_check_executes_select_and_closes_connection() -> None:
    engine = MagicMock(spec=Engine)
    connection = engine.connect.return_value.__enter__.return_value

    assert check_database_connection(engine) is True

    statement = connection.execute.call_args.args[0]
    assert str(statement) == "SELECT 1"
    engine.connect.return_value.__exit__.assert_called_once()


def test_connectivity_check_closes_connection_and_propagates_failure() -> None:
    engine = MagicMock(spec=Engine)
    connection = engine.connect.return_value.__enter__.return_value
    failure = RuntimeError("database unavailable")
    connection.execute.side_effect = failure

    with pytest.raises(RuntimeError) as raised:
        check_database_connection(engine)

    assert raised.value is failure
    engine.connect.return_value.__exit__.assert_called_once()
