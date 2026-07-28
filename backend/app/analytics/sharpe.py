"""Sharpe-ratio calculation for validated periodic portfolio returns."""

import math
from numbers import Integral, Real

import numpy as np
import pandas as pd


def _validate_datetime_index(index: pd.Index) -> None:
    if not isinstance(index, pd.DatetimeIndex):
        raise TypeError("returns index must be a pandas DatetimeIndex")
    if index.hasnans:
        raise ValueError("returns index cannot contain NaT")
    if index.tz is not None:
        raise ValueError("returns index must be timezone-naive")
    if index.has_duplicates:
        raise ValueError("returns index cannot contain duplicate timestamps")
    if not index.is_monotonic_increasing:
        raise ValueError("returns index must be strictly increasing")


def _validated_returns(returns: pd.Series) -> np.ndarray:
    if not isinstance(returns, pd.Series):
        raise TypeError("returns must be a pandas Series")
    if len(returns) < 2:
        raise ValueError("returns must contain at least two observations")

    _validate_datetime_index(returns.index)

    validated_values: list[float] = []
    for value in np.asarray(returns, dtype=object).flat:
        if isinstance(value, (bool, np.bool_)):
            raise TypeError("return values must be real numeric values, not Boolean")
        if isinstance(value, (complex, np.complexfloating)):
            raise TypeError("return values must be real numeric values, not complex")
        if pd.isna(value):
            raise ValueError("return values cannot contain missing values")
        if not isinstance(value, Real):
            raise TypeError("return values must be real numeric values")

        numeric_value = float(value)
        if not math.isfinite(numeric_value):
            raise ValueError("return values must be finite")
        if numeric_value <= -1.0:
            raise ValueError("simple return values must be greater than -1.0")
        validated_values.append(numeric_value)

    return np.asarray(validated_values, dtype=float)


def _validate_annual_risk_free_rate(annual_risk_free_rate: float) -> float:
    if isinstance(annual_risk_free_rate, (bool, np.bool_)):
        raise TypeError("annual_risk_free_rate must be a real numeric value, not Boolean")
    if isinstance(annual_risk_free_rate, (complex, np.complexfloating)):
        raise TypeError("annual_risk_free_rate must be a real numeric value, not complex")
    if not isinstance(annual_risk_free_rate, Real):
        raise TypeError("annual_risk_free_rate must be a real numeric value")

    validated_rate = float(annual_risk_free_rate)
    if not math.isfinite(validated_rate):
        raise ValueError("annual_risk_free_rate must be finite")
    if validated_rate <= -1.0:
        raise ValueError("annual_risk_free_rate must be greater than -1.0")
    return validated_rate


def _validate_periods_per_year(periods_per_year: int) -> int:
    if isinstance(periods_per_year, (bool, np.bool_)) or not isinstance(
        periods_per_year, Integral
    ):
        raise TypeError("periods_per_year must be an integer")
    if periods_per_year <= 0:
        raise ValueError("periods_per_year must be greater than zero")
    return int(periods_per_year)


def calculate_sharpe_ratio(
    returns: pd.Series,
    annual_risk_free_rate: float = 0.0,
    periods_per_year: int = 252,
) -> float:
    """Calculate the annualized Sharpe ratio using sample volatility."""
    return_values = _validated_returns(returns)
    validated_rate = _validate_annual_risk_free_rate(annual_risk_free_rate)
    validated_periods = _validate_periods_per_year(periods_per_year)

    periodic_risk_free_rate = (
        (1.0 + validated_rate) ** (1.0 / validated_periods) - 1.0
    )
    mean_excess_return = float(np.mean(return_values - periodic_risk_free_rate))
    periodic_volatility = float(np.std(return_values, ddof=1))

    if math.isclose(
        periodic_volatility,
        0.0,
        rel_tol=0.0,
        abs_tol=np.finfo(float).eps,
    ):
        raise ValueError(
            "Sharpe ratio is undefined when return volatility is zero"
        )

    sharpe_ratio = (
        mean_excess_return / periodic_volatility * math.sqrt(validated_periods)
    )
    if not math.isfinite(sharpe_ratio):
        raise ValueError("calculated Sharpe ratio must be finite")
    return float(sharpe_ratio)
