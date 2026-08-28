import copy
import importlib
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.database.models import MarketData
from backend.app.database.repositories import MarketDataRepository
import backend.app.database.repositories.market_data_repository as repository_module


def _prepared_records() -> list[dict[str, object]]:
    return [
        {
            "symbol": "AAPL",
            "date": date(2026, 1, 2),
            "adjusted_close": Decimal("101.250000000000"),
            "volume": 1_000,
            "source": "yfinance",
        },
        {
            "symbol": "MSFT",
            "date": date(2026, 1, 2),
            "adjusted_close": Decimal("402.500000000000"),
            "volume": None,
            "source": "yfinance",
        },
    ]


def _compiled_sql(statement: object) -> str:
    return str(statement.compile(dialect=postgresql.dialect()))


def test_upsert_uses_injected_session_without_owning_transaction() -> None:
    session = MagicMock(spec=Session)

    count = MarketDataRepository(session).upsert_many(_prepared_records())

    assert count == 2
    session.execute.assert_called_once()
    session.commit.assert_not_called()
    session.rollback.assert_not_called()
    session.close.assert_not_called()


def test_repository_import_does_not_create_engine_or_connect() -> None:
    with (
        patch("sqlalchemy.create_engine") as create_database_engine,
        patch("psycopg.connect") as connect,
    ):
        importlib.reload(repository_module)

    create_database_engine.assert_not_called()
    connect.assert_not_called()
    assert not any(
        isinstance(value, Session)
        for value in vars(repository_module).values()
    )


def test_upsert_compiles_postgresql_conflict_identity_and_updates() -> None:
    session = MagicMock(spec=Session)

    MarketDataRepository(session).upsert_many(_prepared_records())

    statement = session.execute.call_args.args[0]
    sql = _compiled_sql(statement)
    assert "ON CONFLICT (symbol, date) DO UPDATE SET" in sql
    update_clause = sql.split("DO UPDATE SET", maxsplit=1)[1]
    assert "adjusted_close = excluded.adjusted_close" in update_clause
    assert "volume = excluded.volume" in update_clause
    assert "source = excluded.source" in update_clause
    assert "symbol =" not in update_clause
    assert "date =" not in update_clause


def test_upsert_does_not_mutate_prepared_input_records() -> None:
    session = MagicMock(spec=Session)
    records = _prepared_records()
    original = copy.deepcopy(records)

    MarketDataRepository(session).upsert_many(records)

    assert records == original
    assert records[0] is not session.execute.call_args.args[0]


def test_upsert_empty_input_is_a_safe_no_op() -> None:
    session = MagicMock(spec=Session)

    assert MarketDataRepository(session).upsert_many([]) == 0
    session.execute.assert_not_called()
    session.commit.assert_not_called()


def test_get_range_filters_inclusively_and_orders_deterministically() -> None:
    session = MagicMock(spec=Session)
    expected = [MagicMock(spec=MarketData), MagicMock(spec=MarketData)]
    session.scalars.return_value.all.return_value = expected
    symbols = ["MSFT", "AAPL"]
    symbols_before = list(symbols)
    start = date(2026, 1, 2)
    end = date(2026, 1, 31)

    result = MarketDataRepository(session).get_range(
        symbols,
        start,
        end,
    )

    assert result == expected
    assert symbols == symbols_before
    statement = session.scalars.call_args.args[0]
    compiled = statement.compile(dialect=postgresql.dialect())
    sql = str(compiled)
    assert "market_data.symbol IN (__[POSTCOMPILE_symbol_1])" in sql
    assert "market_data.date >= %(date_1)s" in sql
    assert "market_data.date <= %(date_2)s" in sql
    assert "ORDER BY market_data.symbol, market_data.date" in sql
    assert compiled.params == {
        "symbol_1": ["MSFT", "AAPL"],
        "date_1": start,
        "date_2": end,
    }


def test_get_range_empty_symbols_returns_without_querying() -> None:
    session = MagicMock(spec=Session)

    result = MarketDataRepository(session).get_range(
        [],
        date(2026, 1, 1),
        date(2026, 1, 31),
    )

    assert result == []
    session.scalars.assert_not_called()


def test_sqlalchemy_failure_propagates_without_rollback_or_commit() -> None:
    session = MagicMock(spec=Session)
    failure = SQLAlchemyError("upsert failed")
    session.execute.side_effect = failure

    with pytest.raises(SQLAlchemyError) as raised:
        MarketDataRepository(session).upsert_many(_prepared_records())

    assert raised.value is failure
    session.commit.assert_not_called()
    session.rollback.assert_not_called()
    session.close.assert_not_called()


def test_repository_has_no_pipeline_or_pydantic_schema_dependency() -> None:
    source = Path(repository_module.__file__).read_text(encoding="utf-8")

    assert "data_pipeline" not in source
    assert "pydantic" not in source
    assert "schemas" not in source
