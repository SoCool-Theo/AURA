"""Storage coordination and pure conversion for prepared market data."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

import pandas as pd
from sqlalchemy.orm import Session

from ..database.models import MarketData
from ..database.repositories import MarketDataRepository


_CANONICAL_COLUMNS: tuple[str, ...] = (
    "date",
    "symbol",
    "adjusted_close",
    "volume",
    "source",
)
_ADJUSTED_CLOSE_QUANTUM = Decimal("0.000000000001")
_DEFAULT_BATCH_SIZE = 1_000


def _to_market_data_records(data: pd.DataFrame) -> list[dict[str, object]]:
    """Return repository-ready records from validated canonical rows."""
    records: list[dict[str, object]] = []
    canonical_rows = data.loc[:, _CANONICAL_COLUMNS].itertuples(
        index=False,
        name=None,
    )

    for observation_date, symbol, adjusted_close, volume, source in canonical_rows:
        records.append(
            {
                "symbol": symbol,
                "date": observation_date.date(),
                "adjusted_close": Decimal(str(adjusted_close)).quantize(
                    _ADJUSTED_CLOSE_QUANTUM,
                    rounding=ROUND_HALF_UP,
                ),
                "volume": None if pd.isna(volume) else int(volume),
                "source": source,
            }
        )

    return records


class MarketDataService:
    """Coordinate market-data persistence within a caller-owned session."""

    def __init__(self, session: Session) -> None:
        self._repository = MarketDataRepository(session)

    def store(self, data: pd.DataFrame) -> int:
        """Submit validated canonical rows in bounded repository batches."""
        records = _to_market_data_records(data)
        stored_count = 0

        for start in range(0, len(records), _DEFAULT_BATCH_SIZE):
            batch = records[start : start + _DEFAULT_BATCH_SIZE]
            stored_count += self._repository.upsert_many(batch)

        return stored_count

    def get_range(
        self,
        symbols: Sequence[str],
        start_date: date,
        end_date: date,
    ) -> list[MarketData]:
        """Return the repository's inclusive ordered historical range."""
        return self._repository.get_range(symbols, start_date, end_date)
