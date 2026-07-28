import math
from collections.abc import Mapping
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


def _validate_symbols(symbols: pd.Index, input_name: str) -> None:
    if not symbols.is_unique:
        raise ValueError(f"{input_name} symbols must be unique")

    for symbol in symbols:
        if not isinstance(symbol, str):
            raise TypeError(f"{input_name} symbols must be strings")
        if not symbol:
            raise ValueError(f"{input_name} symbols cannot be empty")
        if not symbol.strip():
            raise ValueError(f"{input_name} symbols cannot be whitespace-only")
        if symbol != symbol.strip():
            raise ValueError(
                f"{input_name} symbols cannot contain leading or trailing whitespace"
            )


def _validated_real_values(
    values: np.ndarray, input_name: str, *, require_positive: bool = False
) -> np.ndarray:
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
        if require_positive and numeric_value <= 0.0:
            raise ValueError(f"{input_name} values must be strictly greater than zero")
        validated.append(numeric_value)

    return np.asarray(validated, dtype=float).reshape(values.shape)


def _validate_asset_returns(asset_returns: pd.DataFrame) -> np.ndarray:
    if not isinstance(asset_returns, pd.DataFrame):
        raise TypeError("asset_returns must be a pandas DataFrame")
    if len(asset_returns.index) == 0:
        raise ValueError("asset_returns must contain at least one row")
    if len(asset_returns.columns) == 0:
        raise ValueError("asset_returns must contain at least one asset column")

    _validate_datetime_index(asset_returns.index, "asset_returns")
    _validate_symbols(asset_returns.columns, "asset_returns")
    return _validated_real_values(asset_returns.to_numpy(), "asset_returns")


def _validate_weights(
    weights: Mapping[str, float], asset_symbols: pd.Index
) -> np.ndarray:
    if not isinstance(weights, Mapping):
        raise TypeError("weights must implement Mapping")

    weight_items = list(weights.items())
    weight_keys = [key for key, _ in weight_items]

    for key in weight_keys:
        if not isinstance(key, str):
            raise TypeError("weight symbols must be strings")
        if not key:
            raise ValueError("weight symbols cannot be empty")
        if not key.strip():
            raise ValueError("weight symbols cannot be whitespace-only")
        if key != key.strip():
            raise ValueError(
                "weight symbols cannot contain leading or trailing whitespace"
            )

    if len(weight_keys) != len(set(weight_keys)):
        raise ValueError("weight symbols must be unique")
    if set(weight_keys) != set(asset_symbols):
        raise ValueError(
            "weight symbols must exactly match the asset-return columns"
        )

    validated_weights: dict[str, float] = {}
    for symbol, value in weight_items:
        if isinstance(value, (bool, np.bool_)):
            raise TypeError("weight values cannot be Boolean")
        if isinstance(value, (complex, np.complexfloating)):
            raise TypeError("weight values cannot be complex")
        if not isinstance(value, Real):
            raise TypeError("weight values must be real numeric values")

        numeric_value = float(value)
        if not math.isfinite(numeric_value):
            raise ValueError("weight values must be finite")
        if numeric_value < 0.0 or numeric_value > 1.0:
            raise ValueError("each weight must be between 0.0 and 1.0 inclusive")
        validated_weights[symbol] = numeric_value

    if not any(value > 0.0 for value in validated_weights.values()):
        raise ValueError("at least one weight must be greater than zero")

    total_weight = math.fsum(validated_weights.values())
    if abs(total_weight - 1.0) > 1e-6:
        raise ValueError("total weight must equal 1.0 within a tolerance of 1e-6")

    return np.asarray(
        [validated_weights[symbol] for symbol in asset_symbols], dtype=float
    )


def _validate_portfolio_return_series(portfolio_returns: pd.Series) -> np.ndarray:
    if not isinstance(portfolio_returns, pd.Series):
        raise TypeError("portfolio_returns must be a pandas Series")
    if portfolio_returns.empty:
        raise ValueError("portfolio_returns cannot be empty")

    values = _validated_real_values(
        portfolio_returns.to_numpy(), "portfolio_returns"
    ).reshape(-1)
    if np.any(values <= -1.0):
        raise ValueError("portfolio returns must be greater than -1.0")
    return values


def calculate_asset_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """Calculate simple periodic returns for each asset price column."""
    if not isinstance(prices, pd.DataFrame):
        raise TypeError("prices must be a pandas DataFrame")
    if len(prices.index) < 2:
        raise ValueError("prices must contain at least two rows")
    if len(prices.columns) == 0:
        raise ValueError("prices must contain at least one asset column")

    _validate_datetime_index(prices.index, "prices")
    _validate_symbols(prices.columns, "price")
    price_values = _validated_real_values(
        prices.to_numpy(), "price", require_positive=True
    )

    return_values = price_values[1:] / price_values[:-1] - 1.0
    return pd.DataFrame(
        return_values,
        index=prices.index[1:],
        columns=prices.columns,
    )


def calculate_portfolio_returns(
    asset_returns: pd.DataFrame, weights: Mapping[str, float]
) -> pd.Series:
    """Calculate periodically rebalanced portfolio returns by asset label."""
    return_values = _validate_asset_returns(asset_returns)
    aligned_weights = _validate_weights(weights, asset_returns.columns)
    portfolio_values = return_values @ aligned_weights

    return pd.Series(
        portfolio_values,
        index=asset_returns.index,
        name="portfolio_return",
    )


def calculate_cumulative_return(portfolio_returns: pd.Series) -> float:
    """Calculate the compounded return across all supplied periods."""
    return_values = _validate_portfolio_return_series(portfolio_returns)
    return float(np.prod(1.0 + return_values) - 1.0)


def calculate_annualized_return(
    portfolio_returns: pd.Series, periods_per_year: int = 252
) -> float:
    """Annualize compounded periodic portfolio returns."""
    if isinstance(periods_per_year, (bool, np.bool_)) or not isinstance(
        periods_per_year, Integral
    ):
        raise TypeError("periods_per_year must be an integer")
    if periods_per_year <= 0:
        raise ValueError("periods_per_year must be greater than zero")

    return_values = _validate_portfolio_return_series(portfolio_returns)
    cumulative_return = float(np.prod(1.0 + return_values) - 1.0)
    exponent = int(periods_per_year) / len(return_values)
    return float((1.0 + cumulative_return) ** exponent - 1.0)
