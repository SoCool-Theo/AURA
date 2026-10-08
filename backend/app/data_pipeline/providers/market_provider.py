"""Historical market-data provider interfaces and implementations."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Protocol, runtime_checkable

import pandas as pd


class MarketDataProviderError(RuntimeError):
    """Raised when a market-data provider cannot return usable data."""


@runtime_checkable
class MarketDataProvider(Protocol):
    """Provider contract used by Aura's historical market-data pipeline."""

    source_name: str

    def fetch_historical_prices(
        self,
        symbols: Iterable[str],
        start_date: date | datetime | str,
        end_date: date | datetime | str,
    ) -> pd.DataFrame:
        """Return provider-native daily historical rows for the date range."""


def _coerce_date(value: date | datetime | str, field_name: str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError as error:
            raise ValueError(
                f"{field_name} must use YYYY-MM-DD format"
            ) from error
    raise TypeError(f"{field_name} must be a date, datetime, or YYYY-MM-DD string")


def _normalize_symbols(symbols: Iterable[str]) -> list[str]:
    if isinstance(symbols, str):
        raise TypeError("symbols must be an iterable of symbol strings, not one string")

    normalized: list[str] = []
    seen: set[str] = set()
    for symbol in symbols:
        if not isinstance(symbol, str):
            raise TypeError("each symbol must be a string")
        value = symbol.strip().upper()
        if not value:
            raise ValueError("symbols cannot contain blank values")
        if value in seen:
            raise ValueError(f"duplicate symbol after normalization: {value}")
        normalized.append(value)
        seen.add(value)

    if not normalized:
        raise ValueError("at least one symbol is required")
    return normalized


def _load_yfinance():
    try:
        import yfinance as yf
    except ImportError as error:
        raise MarketDataProviderError(
            "yfinance is required for the default market-data provider. "
            "Install backend/requirements.txt inside the Aura virtual environment."
        ) from error
    return yf


@dataclass(frozen=True, slots=True)
class YFinanceMarketProvider:
    """Fetch daily historical prices from Yahoo Finance through yfinance."""

    source_name: str = "yfinance"
    timeout_seconds: float = 20.0

    def fetch_historical_prices(
        self,
        symbols: Iterable[str],
        start_date: date | datetime | str,
        end_date: date | datetime | str,
    ) -> pd.DataFrame:
        selected_symbols = _normalize_symbols(symbols)
        start = _coerce_date(start_date, "start_date")
        end = _coerce_date(end_date, "end_date")
        if start > end:
            raise ValueError("start_date must be on or before end_date")

        yf = _load_yfinance()
        frames: list[pd.DataFrame] = []
        failed_symbols: list[str] = []

        # yfinance treats end as exclusive. Aura's contracts use inclusive dates.
        provider_end = end + timedelta(days=1)

        for symbol in selected_symbols:
            try:
                data = yf.download(
                    symbol,
                    start=start.isoformat(),
                    end=provider_end.isoformat(),
                    interval="1d",
                    actions=False,
                    auto_adjust=False,
                    progress=False,
                    threads=False,
                    timeout=self.timeout_seconds,
                    multi_level_index=False,
                )
            except Exception:
                failed_symbols.append(symbol)
                continue

            if data is None or data.empty:
                failed_symbols.append(symbol)
                continue

            frame = data.copy()
            if isinstance(frame.columns, pd.MultiIndex):
                frame.columns = frame.columns.get_level_values(0)

            frame = frame.reset_index()
            frame["symbol"] = symbol
            frame["source"] = self.source_name
            frames.append(frame)

        if not frames:
            failed = ", ".join(failed_symbols) or ", ".join(selected_symbols)
            raise MarketDataProviderError(
                f"No historical market data was returned. Failed symbols: {failed}"
            )

        result = pd.concat(frames, ignore_index=True, sort=False)
        result.attrs["failed_symbols"] = tuple(failed_symbols)
        result.attrs["source"] = self.source_name
        return result
