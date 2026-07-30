from dataclasses import dataclass

import numpy as np
import pandas as pd

from ._validation import (
    _validate_datetime_index,
    _validated_finite_real_values,
)


@dataclass(frozen=True, slots=True)
class MaxDrawdownResult:
    """Describe the maximum drawdown and its active peak-to-trough period."""

    max_drawdown: float
    peak_date: pd.Timestamp | None
    trough_date: pd.Timestamp | None


def _validated_portfolio_returns(portfolio_returns: pd.Series) -> np.ndarray:
    if not isinstance(portfolio_returns, pd.Series):
        raise TypeError("portfolio_returns must be a pandas Series")
    if portfolio_returns.empty:
        raise ValueError("portfolio_returns cannot be empty")

    _validate_datetime_index(portfolio_returns.index, "portfolio_returns")
    validated: list[float] = []

    for value in np.asarray(portfolio_returns.to_numpy(), dtype=object).flat:
        numeric_value = _validated_finite_real_values(
            value,
            "portfolio_returns",
        ).item()
        if numeric_value <= -1.0:
            raise ValueError(
                "portfolio_returns values must be greater than -1.0"
            )
        validated.append(numeric_value)

    return np.asarray(validated, dtype=float)


def _calculate_wealth_values(return_values: np.ndarray) -> np.ndarray:
    with np.errstate(over="ignore", invalid="ignore"):
        wealth_values = np.cumprod(1.0 + return_values)
    if not np.isfinite(wealth_values).all():
        raise ValueError("compounded wealth index values must be finite")
    return wealth_values


def _calculate_drawdown_values(wealth_values: np.ndarray) -> np.ndarray:
    running_peaks = np.maximum.accumulate(np.maximum(wealth_values, 1.0))
    return wealth_values / running_peaks - 1.0


def calculate_wealth_index(portfolio_returns: pd.Series) -> pd.Series:
    """Calculate compounded wealth from an initial portfolio value of 1.0."""
    return_values = _validated_portfolio_returns(portfolio_returns)
    wealth_values = _calculate_wealth_values(return_values)
    return pd.Series(
        wealth_values,
        index=portfolio_returns.index,
        name="wealth_index",
    )


def calculate_drawdown_series(portfolio_returns: pd.Series) -> pd.Series:
    """Calculate drawdowns from a running peak anchored at initial wealth."""
    return_values = _validated_portfolio_returns(portfolio_returns)
    wealth_values = _calculate_wealth_values(return_values)
    drawdown_values = _calculate_drawdown_values(wealth_values)
    return pd.Series(
        drawdown_values,
        index=portfolio_returns.index,
        name="drawdown",
    )


def calculate_max_drawdown(portfolio_returns: pd.Series) -> float:
    """Return the most negative drawdown across all observations."""
    return_values = _validated_portfolio_returns(portfolio_returns)
    wealth_values = _calculate_wealth_values(return_values)
    drawdown_values = _calculate_drawdown_values(wealth_values)
    return float(np.min(drawdown_values))


def calculate_max_drawdown_details(
    portfolio_returns: pd.Series,
) -> MaxDrawdownResult:
    """Return maximum drawdown with its active peak and first trough dates."""
    return_values = _validated_portfolio_returns(portfolio_returns)
    wealth_values = _calculate_wealth_values(return_values)
    drawdown_values = _calculate_drawdown_values(wealth_values)

    trough_position = int(np.argmin(drawdown_values))
    max_drawdown = float(drawdown_values[trough_position])
    if max_drawdown >= 0.0:
        return MaxDrawdownResult(0.0, None, None)

    wealth_through_trough = wealth_values[: trough_position + 1]
    peak_value = max(1.0, float(np.max(wealth_through_trough)))
    observed_peak_positions = np.flatnonzero(
        wealth_through_trough == peak_value
    )
    peak_date = (
        portfolio_returns.index[int(observed_peak_positions[-1])]
        if observed_peak_positions.size
        else None
    )

    return MaxDrawdownResult(
        max_drawdown=max_drawdown,
        peak_date=peak_date,
        trough_date=portfolio_returns.index[trough_position],
    )
