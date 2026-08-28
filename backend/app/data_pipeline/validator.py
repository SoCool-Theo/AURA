"""Validation for cleaned Aura historical market data."""

from __future__ import annotations

import math

import pandas as pd


REQUIRED_COLUMNS: tuple[str, ...] = (
    "date",
    "symbol",
    "adjusted_close",
    "volume",
    "source",
)


def validate_market_data(data: pd.DataFrame) -> list[str]:
    """Return validation errors; an empty list means the data is valid."""
    errors: list[str] = []

    if not isinstance(data, pd.DataFrame):
        return ["Market data must be a pandas DataFrame."]
    if data.empty:
        return ["Market data is empty."]

    missing = [column for column in REQUIRED_COLUMNS if column not in data.columns]
    if missing:
        return [f"Missing required columns: {missing}"]

    parsed_dates = pd.to_datetime(data["date"], errors="coerce")
    if parsed_dates.isna().any():
        errors.append("Some rows have missing or invalid dates.")

    symbols = data["symbol"].astype("string")
    if symbols.isna().any() or symbols.str.strip().eq("").any():
        errors.append("Some rows have missing or blank symbols.")
    elif (~symbols.eq(symbols.str.strip().str.upper())).any():
        errors.append("Symbols must be trimmed and uppercase.")

    sources = data["source"].astype("string")
    if sources.isna().any() or sources.str.strip().eq("").any():
        errors.append("Some rows have missing or blank sources.")
    elif (~sources.eq(sources.str.strip())).any():
        errors.append("Sources must not contain leading or trailing whitespace.")

    prices = pd.to_numeric(data["adjusted_close"], errors="coerce")
    if prices.isna().any():
        errors.append("Some adjusted_close values are missing or not numeric.")
    else:
        finite_prices = prices.map(lambda value: math.isfinite(float(value)))
        if (~finite_prices).any():
            errors.append("Some adjusted_close values are not finite.")
        if (prices <= 0).any():
            errors.append("Some adjusted_close values are zero or negative.")

    volume = pd.to_numeric(data["volume"], errors="coerce")
    invalid_volume_text = data["volume"].notna() & volume.isna()
    if invalid_volume_text.any():
        errors.append("Some volume values are not numeric.")
    non_null_volume = volume.dropna()
    if (non_null_volume < 0).any():
        errors.append("Some volume values are negative.")
    if ((non_null_volume % 1) != 0).any():
        errors.append("Some volume values are not whole numbers.")

    duplicate_count = int(
        pd.DataFrame({"date": parsed_dates, "symbol": symbols}).duplicated().sum()
    )
    if duplicate_count:
        errors.append(f"Found {duplicate_count} duplicate date-symbol rows.")

    if not parsed_dates.isna().any() and not symbols.isna().any():
        order_frame = pd.DataFrame(
            {"symbol": symbols.astype(str), "date": parsed_dates}
        )
        for symbol, group in order_frame.groupby("symbol", sort=False):
            if not group["date"].is_monotonic_increasing:
                errors.append(f"Dates for {symbol} are not in increasing order.")

    return errors


def raise_if_invalid(data: pd.DataFrame) -> None:
    """Raise ValueError containing all market-data validation failures."""
    errors = validate_market_data(data)
    if errors:
        details = "\n".join(f"- {error}" for error in errors)
        raise ValueError(f"Market data validation failed:\n{details}")
