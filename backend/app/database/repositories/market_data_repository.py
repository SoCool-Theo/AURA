"""Persistence operations for prepared Aura market-data records."""

from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from typing import TypedDict

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from ..models import MarketData


class _MarketDataValues(TypedDict):
    symbol: str
    date: date
    adjusted_close: Decimal
    volume: int | None
    source: str


class MarketDataRepository:
    """Persist prepared market data within a caller-owned session."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def upsert_many(
        self,
        records: Sequence[_MarketDataValues],
    ) -> int:
        """Insert or update prepared rows without committing."""
        values = [dict(record) for record in records]
        if not values:
            return 0

        statement = insert(MarketData).values(values)
        statement = statement.on_conflict_do_update(
            index_elements=[MarketData.symbol, MarketData.date],
            set_={
                "adjusted_close": statement.excluded.adjusted_close,
                "volume": statement.excluded.volume,
                "source": statement.excluded.source,
            },
        )
        self._session.execute(statement)
        return len(values)

    def get_range(
        self,
        symbols: Sequence[str],
        start_date: date,
        end_date: date,
    ) -> list[MarketData]:
        """Return requested rows over an inclusive deterministic range."""
        selected_symbols = tuple(symbols)
        if not selected_symbols:
            return []

        statement = (
            select(MarketData)
            .where(
                MarketData.symbol.in_(selected_symbols),
                MarketData.date >= start_date,
                MarketData.date <= end_date,
            )
            .order_by(MarketData.symbol, MarketData.date)
        )
        return list(self._session.scalars(statement).all())
