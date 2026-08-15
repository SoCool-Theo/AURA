"""Pure conversion helpers for prepared Aura market data."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

import pandas as pd


_CANONICAL_COLUMNS: tuple[str, ...] = (
    "date",
    "symbol",
    "adjusted_close",
    "volume",
    "source",
)
_ADJUSTED_CLOSE_QUANTUM = Decimal("0.000000000001")


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
