"""Persist a complete fetch-clean-validate historical market-data update."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from .cleaner import clean_market_data
from .fetcher import DEFAULT_START_DATE, DEFAULT_SYMBOLS, fetch_historical_prices
from .providers import MarketDataProvider
from .validator import raise_if_invalid


PROJECT_ROOT = Path(__file__).resolve().parents[3]
RAW_DATA_PATH = PROJECT_ROOT / "data" / "raw" / "market_prices_raw.csv"
PROCESSED_DATA_PATH = (
    PROJECT_ROOT / "data" / "processed" / "market_prices_clean.csv"
)


@dataclass(frozen=True, slots=True)
class MarketDataUpdateResult:
    """Summary returned after a successful historical market-data update."""

    raw_path: Path
    processed_path: Path
    row_count: int
    symbols: tuple[str, ...]
    failed_symbols: tuple[str, ...]
    requested_start_date: str
    requested_end_date: str
    actual_start_date: str
    actual_end_date: str


def _date_text(value: date | datetime | str) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return value


def _atomic_write_csv(data: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_name(f".{path.name}.tmp")
    try:
        data.to_csv(temporary_path, index=False)
        temporary_path.replace(path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def update_market_data(
    symbols: Iterable[str] | None = None,
    start_date: date | datetime | str = DEFAULT_START_DATE,
    end_date: date | datetime | str | None = None,
    *,
    provider: MarketDataProvider | None = None,
    raw_path: Path = RAW_DATA_PATH,
    processed_path: Path = PROCESSED_DATA_PATH,
) -> MarketDataUpdateResult:
    """Fetch, persist raw, clean, validate, and persist processed market data."""
    selected_symbols = tuple(symbols) if symbols is not None else DEFAULT_SYMBOLS
    selected_end_date = end_date if end_date is not None else date.today()

    raw_data = fetch_historical_prices(
        symbols=selected_symbols,
        start_date=start_date,
        end_date=selected_end_date,
        provider=provider,
    )
    failed_symbols = tuple(raw_data.attrs.get("failed_symbols", ()))

    # Preserve the provider response before any Aura-specific transformation.
    _atomic_write_csv(raw_data, raw_path)

    clean_data = clean_market_data(raw_data)
    raise_if_invalid(clean_data)
    _atomic_write_csv(clean_data, processed_path)

    dates = pd.to_datetime(clean_data["date"])
    output_symbols = tuple(clean_data["symbol"].drop_duplicates().tolist())

    return MarketDataUpdateResult(
        raw_path=raw_path,
        processed_path=processed_path,
        row_count=int(len(clean_data)),
        symbols=output_symbols,
        failed_symbols=failed_symbols,
        requested_start_date=_date_text(start_date),
        requested_end_date=_date_text(selected_end_date),
        actual_start_date=dates.min().date().isoformat(),
        actual_end_date=dates.max().date().isoformat(),
    )
