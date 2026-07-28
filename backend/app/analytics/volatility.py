import math
from numbers import Integral, Real

import numpy as np
import pandas as pd


def _validate_datetime_index(index: pd.Index, input_name: str) -> None:
    if not isinstance(index, pd.DatetimeIndex):
        raise TypeError(f"{input_name} index must be a pandas DatetimeIndex")
    if index.hasnans:
        raise ValueError(f"{input_name} index cannot contain NaT")
    if index.tz is not None:
        raise ValueError(f"{input_name} index must be timezone-naive")
    if index.has_duplicates:
        raise ValueError(f"{input_name} index cannot contain duplicate timestamps")
    if not index.is_monotonic_increasing:
        raise ValueError(f"{input_name} index must be strictly increasing")


def _validate_symbols(symbols: pd.Index) -> None:
    if not symbols.is_unique:
        raise ValueError("asset symbols must be unique")

    for symbol in symbols:
        if not isinstance(symbol, str):
            raise TypeError("asset symbols must be strings")
        if not symbol:
            raise ValueError("asset symbols cannot be empty")
        if not symbol.strip():
            raise ValueError("asset symbols cannot be whitespace-only")
        if symbol != symbol.strip():
            raise ValueError(
                "asset symbols cannot contain leading or trailing whitespace"
            )


def _validated_return_values(values: np.ndarray, input_name: str) -> np.ndarray:
    validated: list[float] = []

    for value in np.asarray(values, dtype=object).flat:
        if isinstance(value, (bool, np.bool_)):
            raise TypeError(f"{input_name} values cannot be Boolean")
        if isinstance(value, (complex, np.complexfloating)):
            raise TypeError(f"{input_name} values cannot be complex")
        if pd.isna(value):
            raise ValueError(f"{input_name} values cannot be missing")
        if not isinstance(value, Real):
            raise TypeError(f"{input_name} values must be real numeric values")

        numeric_value = float(value)
        if not math.isfinite(numeric_value):
            raise ValueError(f"{input_name} values must be finite")
        if numeric_value <= -1.0:
            raise ValueError(f"{input_name} values must be greater than -1.0")
        validated.append(numeric_value)

    return np.asarray(validated, dtype=float).reshape(values.shape)


def _validate_return_series(returns: pd.Series) -> np.ndarray:
    if not isinstance(returns, pd.Series):
        raise TypeError("returns must be a pandas Series")
    if len(returns) < 2:
        raise ValueError("returns must contain at least two observations")

    _validate_datetime_index(returns.index, "returns")
    return _validated_return_values(returns.to_numpy(), "return").reshape(-1)


def _validate_asset_returns(asset_returns: pd.DataFrame) -> np.ndarray:
    if not isinstance(asset_returns, pd.DataFrame):
        raise TypeError("asset_returns must be a pandas DataFrame")
    if len(asset_returns.index) < 2:
        raise ValueError("asset_returns must contain at least two rows")
    if len(asset_returns.columns) == 0:
        raise ValueError("asset_returns must contain at least one asset column")

    _validate_datetime_index(asset_returns.index, "asset_returns")
    _validate_symbols(asset_returns.columns)
    return _validated_return_values(
        asset_returns.to_numpy(), "asset_returns"
    )


def _validate_periods_per_year(periods_per_year: int) -> int:
    if isinstance(periods_per_year, (bool, np.bool_)) or not isinstance(
        periods_per_year, Integral
    ):
        raise TypeError("periods_per_year must be an integer")
    if periods_per_year <= 0:
        raise ValueError("periods_per_year must be greater than zero")
    return int(periods_per_year)


def calculate_periodic_volatility(returns: pd.Series) -> float:
    """Calculate sample volatility for periodic returns."""
    return_values = _validate_return_series(returns)
    return float(np.std(return_values, ddof=1))


def calculate_annualized_volatility(
    returns: pd.Series, periods_per_year: int = 252
) -> float:
    """Annualize the sample volatility of periodic returns."""
    annualization_factor = _validate_periods_per_year(periods_per_year)
    periodic_volatility = calculate_periodic_volatility(returns)
    return float(periodic_volatility * math.sqrt(annualization_factor))


def calculate_asset_volatilities(
    asset_returns: pd.DataFrame, periods_per_year: int = 252
) -> pd.Series:
    """Calculate annualized sample volatility for each asset column."""
    annualization_factor = _validate_periods_per_year(periods_per_year)
    return_values = _validate_asset_returns(asset_returns)
    annualized_values = np.std(return_values, axis=0, ddof=1) * math.sqrt(
        annualization_factor
    )

    return pd.Series(
        annualized_values,
        index=asset_returns.columns,
        name="annualized_volatility",
    )
