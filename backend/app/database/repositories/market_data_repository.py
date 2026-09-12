"""Persistence operations for prepared Aura market-data records."""

from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from typing import TypedDict

from sqlalchemy import and_, func, select
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

    def get_latest_on_or_before(
        self,
        symbols: Sequence[str],
        requested_date: date,
    ) -> list[MarketData]:
        """Return at most one latest row per symbol in requested order."""
        selected_symbols = tuple(dict.fromkeys(symbols))
        if not selected_symbols:
            return []

        latest_dates = (
            select(
                MarketData.symbol.label("symbol"),
                func.max(MarketData.date).label("latest_date"),
            )
            .where(
                MarketData.symbol.in_(selected_symbols),
                MarketData.date <= requested_date,
            )
            .group_by(MarketData.symbol)
            .subquery()
        )
        statement = select(MarketData).join(
            latest_dates,
            and_(
                MarketData.symbol == latest_dates.c.symbol,
                MarketData.date == latest_dates.c.latest_date,
            ),
        )
        rows = list(self._session.scalars(statement).all())
        rows_by_symbol = {row.symbol: row for row in rows}
        return [
            rows_by_symbol[symbol]
            for symbol in selected_symbols
            if symbol in rows_by_symbol
        ]
