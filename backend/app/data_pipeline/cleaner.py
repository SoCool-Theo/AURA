"""Normalize provider-native market data into Aura's canonical row format."""

from __future__ import annotations

import math

import pandas as pd


OUTPUT_COLUMNS: tuple[str, ...] = (
    "date",
    "symbol",
    "adjusted_close",
    "volume",
    "source",
)


def _normalize_column_name(column: object) -> str:
    if isinstance(column, tuple):
        column = next((part for part in column if str(part).strip()), "")
    return str(column).strip().lower().replace(" ", "_").replace("-", "_")


def clean_market_data(raw_data: pd.DataFrame) -> pd.DataFrame:
    """Return canonical daily rows: date, symbol, adjusted_close, volume, source."""
    if not isinstance(raw_data, pd.DataFrame):
        raise TypeError("raw_data must be a pandas DataFrame")
    if raw_data.empty:
        raise ValueError("raw market data cannot be empty")

    data = raw_data.copy(deep=True)
    if "date" not in data.columns and "datetime" not in data.columns:
        if isinstance(data.index, pd.DatetimeIndex):
            data = data.reset_index()

    data.columns = [_normalize_column_name(column) for column in data.columns]

    if "datetime" in data.columns and "date" not in data.columns:
        data = data.rename(columns={"datetime": "date"})

    if "adjusted_close" not in data.columns:
        if "adj_close" in data.columns:
            data["adjusted_close"] = data["adj_close"]
        elif "close" in data.columns:
            data["adjusted_close"] = data["close"]
        else:
            raise ValueError(
                "raw market data must contain adjusted_close, Adj Close, or Close"
            )

    if "volume" not in data.columns:
        data["volume"] = pd.NA

    missing = [
        column
        for column in ("date", "symbol", "adjusted_close", "source")
        if column not in data.columns
    ]
    if missing:
        raise ValueError(f"raw market data is missing required columns: {missing}")

    clean = data[list(OUTPUT_COLUMNS)].copy()
    clean["date"] = pd.to_datetime(clean["date"], errors="coerce").dt.normalize()
    clean["symbol"] = clean["symbol"].astype("string").str.strip().str.upper()
    clean["source"] = clean["source"].astype("string").str.strip()
    clean["adjusted_close"] = pd.to_numeric(
        clean["adjusted_close"], errors="coerce"
    )
    clean["volume"] = pd.to_numeric(clean["volume"], errors="coerce")

    valid_price = clean["adjusted_close"].map(
        lambda value: pd.notna(value)
        and math.isfinite(float(value))
        and float(value) > 0.0
    )
    clean = clean[
        clean["date"].notna()
        & clean["symbol"].notna()
        & clean["symbol"].ne("")
        & clean["source"].notna()
        & clean["source"].ne("")
        & valid_price
    ].copy()

    clean["adjusted_close"] = clean["adjusted_close"].astype(float)

    # Volume is optional in Aura's public contract. Invalid provider volume is
    # represented as missing instead of inventing a value.
    invalid_volume = clean["volume"].notna() & (
        (clean["volume"] < 0)
        | ((clean["volume"] % 1) != 0)
    )
    clean.loc[invalid_volume, "volume"] = pd.NA
    clean["volume"] = clean["volume"].astype("Int64")

    clean = clean.drop_duplicates(subset=["symbol", "date"], keep="last")
    clean = clean.sort_values(["symbol", "date"], kind="stable").reset_index(
        drop=True
    )

    return clean[list(OUTPUT_COLUMNS)]
