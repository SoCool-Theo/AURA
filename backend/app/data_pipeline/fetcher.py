"""Historical market-data fetching orchestration."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime

import pandas as pd

from .providers import MarketDataProvider, YFinanceMarketProvider


DEFAULT_SYMBOLS: tuple[str, ...] = (
    "AAPL",
    "MSFT",
    "TSLA",
    "NVDA",
    "AMZN",
    "GOOGL",
    "META",
    "SPY",
    "QQQ",
    "DIA",
    "VTI",
    "GLD",
    "SLV",
    "BND",
    "TLT",
    "BTC-USD",
    "ETH-USD",
)
DEFAULT_START_DATE = "2010-01-01"


def fetch_historical_prices(
    symbols: Iterable[str] | None = None,
    start_date: date | datetime | str = DEFAULT_START_DATE,
    end_date: date | datetime | str | None = None,
    *,
    provider: MarketDataProvider | None = None,
) -> pd.DataFrame:
    """Fetch raw daily market data without cleaning or persistence."""
    selected_symbols = tuple(symbols) if symbols is not None else DEFAULT_SYMBOLS
    selected_end_date = end_date if end_date is not None else date.today()
    selected_provider = provider or YFinanceMarketProvider()

    return selected_provider.fetch_historical_prices(
        selected_symbols,
        start_date,
        selected_end_date,
    )
