"""Pure adapters for Aura's future portfolio-analysis service."""

from collections.abc import Sequence

import pandas as pd

from ..database.models import MarketData


_MISSING_MARKET_DATA_PREFIX = (
    "market data is unavailable for requested symbols: "
)


def _build_price_frame(
    records: Sequence[MarketData],
    symbols: Sequence[str],
) -> pd.DataFrame:
    """Return exact-date-aligned adjusted closes in requested symbol order."""
    requested_symbols = tuple(symbols)
    prices_by_symbol = {symbol: {} for symbol in requested_symbols}

    for record in records:
        if record.symbol in prices_by_symbol:
            prices_by_symbol[record.symbol][record.date] = float(
                record.adjusted_close
            )

    missing_symbols = [
        symbol
        for symbol in requested_symbols
        if not prices_by_symbol[symbol]
    ]
    if missing_symbols:
        raise ValueError(
            _MISSING_MARKET_DATA_PREFIX + ", ".join(missing_symbols)
        )

    if not requested_symbols:
        return pd.DataFrame(index=pd.DatetimeIndex([]))

    common_dates = set.intersection(
        *(set(prices_by_symbol[symbol]) for symbol in requested_symbols)
    )
    ordered_dates = sorted(common_dates)
    values = [
        [
            prices_by_symbol[symbol][observation_date]
            for symbol in requested_symbols
        ]
        for observation_date in ordered_dates
    ]

    return pd.DataFrame(
        values,
        index=pd.DatetimeIndex(ordered_dates),
        columns=requested_symbols,
        dtype=float,
    )
