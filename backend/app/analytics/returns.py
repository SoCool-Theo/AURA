import math
from collections.abc import Mapping
from numbers import Real

import numpy as np
import pandas as pd

from ._validation import (
    _validate_datetime_index,
    _validate_positive_integer,
    _validated_finite_real_values,
)


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
        numeric_value = _validated_finite_real_values(
            value,
            input_name,
        ).item()
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


def _validate_share_quantities(
    share_quantities: Mapping[str, float], asset_symbols: pd.Index
) -> np.ndarray:
    if not isinstance(share_quantities, Mapping):
        raise TypeError("share_quantities must implement Mapping")

    quantity_items = list(share_quantities.items())
    quantity_keys = [key for key, _ in quantity_items]
    if set(quantity_keys) != set(asset_symbols):
        raise ValueError(
            "share quantity symbols must exactly match the price columns"
        )

    validated_quantities: dict[str, float] = {}
    for symbol, value in quantity_items:
        if not isinstance(symbol, str):
            raise TypeError("share quantity symbols must be strings")
        if not symbol or not symbol.strip() or symbol != symbol.strip():
            raise ValueError("share quantity symbols must be normalized")
        if isinstance(value, (bool, np.bool_)):
            raise TypeError("share quantity values cannot be Boolean")
        if isinstance(value, (complex, np.complexfloating)):
            raise TypeError("share quantity values cannot be complex")
        if not isinstance(value, Real):
            raise TypeError("share quantity values must be real numeric values")
        numeric_value = float(value)
        if not math.isfinite(numeric_value) or numeric_value <= 0.0:
            raise ValueError(
                "share quantity values must be positive and finite"
            )
        validated_quantities[symbol] = numeric_value

    return np.asarray(
        [validated_quantities[symbol] for symbol in asset_symbols],
        dtype=float,
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


def calculate_fixed_share_portfolio_values(
    prices: pd.DataFrame,
    share_quantities: Mapping[str, float],
) -> pd.Series:
    """Value fixed owned quantities at every supplied historical price date."""
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
    aligned_quantities = _validate_share_quantities(
        share_quantities,
        prices.columns,
    )
    portfolio_values = price_values @ aligned_quantities

    return pd.Series(
        portfolio_values,
        index=prices.index,
        name="portfolio_value",
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
    validated_periods = _validate_positive_integer(
        periods_per_year,
        "periods_per_year",
    )

    return_values = _validate_portfolio_return_series(portfolio_returns)
    cumulative_return = float(np.prod(1.0 + return_values) - 1.0)
    exponent = validated_periods / len(return_values)
    return float((1.0 + cumulative_return) ** exponent - 1.0)
