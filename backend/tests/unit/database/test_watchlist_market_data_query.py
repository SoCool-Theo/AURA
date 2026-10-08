from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.app.database.models import MarketData
from backend.app.database.repositories import MarketDataRepository


@pytest.fixture
def database_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    MarketData.__table__.create(engine)
    session = Session(engine, autoflush=False, expire_on_commit=False)
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _observation(symbol: str, day: date, price: str) -> MarketData:
    return MarketData(
        symbol=symbol,
        date=day,
        adjusted_close=Decimal(price),
        volume=None,
        source="watchlist-test",
    )


def test_price_change_query_returns_only_required_persisted_observations(
    database_session: Session,
) -> None:
    database_session.add_all(
        [
            _observation("AAPL", date(2025, 12, 31), "90"),
            _observation("AAPL", date(2026, 1, 2), "100"),
            _observation("AAPL", date(2026, 6, 1), "110"),
            _observation("AAPL", date(2026, 9, 18), "120"),
            _observation("AAPL", date(2026, 9, 21), "126"),
            _observation("MSFT", date(2026, 1, 5), "200"),
        ]
    )
    database_session.flush()

    rows = MarketDataRepository(
        database_session
    ).get_price_change_observations(["MSFT", "AAPL", "MSFT"])

    assert [(row.symbol, row.date) for row in rows] == [
        ("AAPL", date(2026, 1, 2)),
        ("AAPL", date(2026, 9, 18)),
        ("AAPL", date(2026, 9, 21)),
        ("MSFT", date(2026, 1, 5)),
    ]


def test_price_change_query_does_not_fill_or_fabricate_rows(
    database_session: Session,
) -> None:
    database_session.add_all(
        [
            _observation("AAPL", date(2026, 9, 18), "120"),
            _observation("AAPL", date(2026, 9, 21), "126"),
        ]
    )
    database_session.flush()

    rows = MarketDataRepository(
        database_session
    ).get_price_change_observations(["AAPL", "NVDA"])

    assert [(row.symbol, row.date) for row in rows] == [
        ("AAPL", date(2026, 9, 18)),
        ("AAPL", date(2026, 9, 21)),
    ]


def test_price_change_query_short_circuits_empty_symbols(
    database_session: Session,
) -> None:
    assert (
        MarketDataRepository(
            database_session
        ).get_price_change_observations([])
        == []
    )
