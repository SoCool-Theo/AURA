"""Pure deterministic calculations for historical portfolio simulations."""

from collections.abc import Mapping
from dataclasses import dataclass
import math

import pandas as pd

from ..analytics.drawdown import (
    MaxDrawdownResult,
    calculate_max_drawdown_details,
    calculate_wealth_index,
)
from ..analytics.returns import (
    calculate_asset_returns,
    calculate_cumulative_return,
    calculate_portfolio_returns,
)
from ..analytics.sharpe import calculate_sharpe_ratio
from ..analytics.volatility import calculate_annualized_volatility


_NORMALIZED_STARTING_VALUE = 1.0
_UNDEFINED_SHARPE_ERROR = (
    "Sharpe ratio is undefined when return volatility is zero"
)


@dataclass(frozen=True, slots=True)
class HistoricalTrajectoryPoint:
    """One internal normalized portfolio value on an effective price date."""

    date: pd.Timestamp
    normalized_value: float


@dataclass(frozen=True, slots=True)
class HistoricalSimulationResult:
    """Immutable pure result for one prepared historical price period."""

    effective_start_date: pd.Timestamp
    effective_end_date: pd.Timestamp
    price_observation_count: int
    return_observation_count: int
    normalized_starting_value: float
    normalized_ending_value: float
    cumulative_return: float
    annualized_volatility: float
    sharpe_ratio: float | None
    maximum_drawdown: MaxDrawdownResult
    trajectory: tuple[HistoricalTrajectoryPoint, ...]


@dataclass(frozen=True, slots=True)
class AllocationComparisonResult:
    """Immutable results and modified-minus-original allocation deltas."""

    original: HistoricalSimulationResult
    modified: HistoricalSimulationResult
    normalized_ending_value_delta: float
    cumulative_return_delta: float
    annualized_volatility_delta: float
    sharpe_ratio_delta: float | None
    maximum_drawdown_delta: float


def _calculate_nullable_sharpe(portfolio_returns: pd.Series) -> float | None:
    try:
        return calculate_sharpe_ratio(portfolio_returns)
    except ValueError as error:
        if str(error) != _UNDEFINED_SHARPE_ERROR:
            raise
        return None


def _require_finite_result(value: float, *, result_name: str) -> float:
    numeric_value = float(value)
    if not math.isfinite(numeric_value):
        raise ValueError(f"calculated {result_name} must be finite")
    return numeric_value


def simulate_historical_scenario(
    prices: pd.DataFrame,
    weights: Mapping[str, float],
) -> HistoricalSimulationResult:
    """Simulate fixed periodically rebalanced weights over prepared prices."""
    if not isinstance(prices, pd.DataFrame):
        raise TypeError("prices must be a pandas DataFrame")
    if len(prices.index) < 3:
        raise ValueError(
            "prices must contain at least three rows for historical simulation"
        )

    asset_returns = calculate_asset_returns(prices)
    portfolio_returns = calculate_portfolio_returns(asset_returns, weights)

    cumulative_return = _require_finite_result(
        calculate_cumulative_return(portfolio_returns),
        result_name="cumulative return",
    )
    annualized_volatility = _require_finite_result(
        calculate_annualized_volatility(portfolio_returns),
        result_name="annualized volatility",
    )
    sharpe_ratio = _calculate_nullable_sharpe(portfolio_returns)
    maximum_drawdown = calculate_max_drawdown_details(portfolio_returns)
    wealth_index = calculate_wealth_index(portfolio_returns)

    trajectory = (
        HistoricalTrajectoryPoint(
            date=prices.index[0],
            normalized_value=_NORMALIZED_STARTING_VALUE,
        ),
        *(
            HistoricalTrajectoryPoint(
                date=timestamp,
                normalized_value=_require_finite_result(
                    value,
                    result_name="normalized trajectory value",
                ),
            )
            for timestamp, value in wealth_index.items()
        ),
    )
    normalized_ending_value = trajectory[-1].normalized_value
    if not math.isclose(
        cumulative_return,
        normalized_ending_value - _NORMALIZED_STARTING_VALUE,
        rel_tol=1e-12,
        abs_tol=1e-12,
    ):
        raise ValueError(
            "calculated cumulative return and normalized ending value "
            "must be consistent"
        )

    return HistoricalSimulationResult(
        effective_start_date=prices.index[0],
        effective_end_date=prices.index[-1],
        price_observation_count=int(len(prices)),
        return_observation_count=int(len(portfolio_returns)),
        normalized_starting_value=_NORMALIZED_STARTING_VALUE,
        normalized_ending_value=normalized_ending_value,
        cumulative_return=cumulative_return,
        annualized_volatility=annualized_volatility,
        sharpe_ratio=sharpe_ratio,
        maximum_drawdown=maximum_drawdown,
        trajectory=trajectory,
    )


def simulate_allocation_change(
    prices: pd.DataFrame,
    original_weights: Mapping[str, float],
    modified_weights: Mapping[str, float],
) -> AllocationComparisonResult:
    """Compare two allocations over the same prepared historical prices."""
    original = simulate_historical_scenario(prices, original_weights)
    modified = simulate_historical_scenario(prices, modified_weights)

    sharpe_ratio_delta = None
    if original.sharpe_ratio is not None and modified.sharpe_ratio is not None:
        sharpe_ratio_delta = _require_finite_result(
            modified.sharpe_ratio - original.sharpe_ratio,
            result_name="Sharpe ratio delta",
        )

    return AllocationComparisonResult(
        original=original,
        modified=modified,
        normalized_ending_value_delta=_require_finite_result(
            modified.normalized_ending_value
            - original.normalized_ending_value,
            result_name="normalized ending value delta",
        ),
        cumulative_return_delta=_require_finite_result(
            modified.cumulative_return - original.cumulative_return,
            result_name="cumulative return delta",
        ),
        annualized_volatility_delta=_require_finite_result(
            modified.annualized_volatility - original.annualized_volatility,
            result_name="annualized volatility delta",
        ),
        sharpe_ratio_delta=sharpe_ratio_delta,
        maximum_drawdown_delta=_require_finite_result(
            modified.maximum_drawdown.max_drawdown
            - original.maximum_drawdown.max_drawdown,
            result_name="maximum drawdown delta",
        ),
    )


__all__ = [
    "HistoricalTrajectoryPoint",
    "HistoricalSimulationResult",
    "AllocationComparisonResult",
    "simulate_historical_scenario",
    "simulate_allocation_change",
]
