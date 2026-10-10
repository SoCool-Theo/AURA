"""Deterministic past-only feature construction for asset forecasting."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import math

from .data import AssetPriceHistory


FEATURE_SET_VERSION = "forecast-features-v1"
MAX_FEATURE_LOOKBACK = 252
_CUMULATIVE_WINDOWS = (5, 21, 63, 126, 252)
_MEAN_WINDOWS = (5, 21, 63)
_VOLATILITY_WINDOWS = (5, 21, 63, 126, 252)
FEATURE_NAMES: tuple[str, ...] = (
    "log_return_1",
    "cumulative_return_5",
    "cumulative_return_21",
    "cumulative_return_63",
    "cumulative_return_126",
    "cumulative_return_252",
    "rolling_mean_log_return_5",
    "rolling_mean_log_return_21",
    "rolling_mean_log_return_63",
    "rolling_volatility_log_return_5",
    "rolling_volatility_log_return_21",
    "rolling_volatility_log_return_63",
    "rolling_volatility_log_return_126",
    "rolling_volatility_log_return_252",
)


class ForecastFeatureError(ValueError):
    """Raised when a finite past-only feature row cannot be produced."""


@dataclass(frozen=True, slots=True)
class ForecastFeatureRow:
    """V1 features calculated only from observations at or before origin.

    ``cumulative_return_N`` is ``P[t] / P[t-N] - 1`` using observed-row
    positions. Rolling means use the trailing N observed log returns ending at
    the origin. Rolling volatilities are the unannualized sample standard
    deviation (``ddof=1``) of those same trailing log returns.
    """

    symbol: str
    origin_date: date
    log_return_1: float
    cumulative_return_5: float
    cumulative_return_21: float
    cumulative_return_63: float
    cumulative_return_126: float
    cumulative_return_252: float
    rolling_mean_log_return_5: float
    rolling_mean_log_return_21: float
    rolling_mean_log_return_63: float
    rolling_volatility_log_return_5: float
    rolling_volatility_log_return_21: float
    rolling_volatility_log_return_63: float
    rolling_volatility_log_return_126: float
    rolling_volatility_log_return_252: float


def _sample_volatility(values: tuple[float, ...]) -> float:
    mean = math.fsum(values) / len(values)
    squared_deviations = math.fsum((value - mean) ** 2 for value in values)
    return math.sqrt(squared_deviations / (len(values) - 1))


def _require_finite(values: tuple[float, ...]) -> None:
    if not all(math.isfinite(value) for value in values):
        raise ForecastFeatureError("forecast features must be finite")


def build_feature_rows(
    history: AssetPriceHistory,
) -> tuple[ForecastFeatureRow, ...]:
    """Return warmed-up V1 rows in origin-date order without future access."""
    prices = tuple(
        observation.adjusted_close for observation in history.observations
    )
    dates = tuple(observation.date for observation in history.observations)
    if len(prices) <= MAX_FEATURE_LOOKBACK:
        return ()

    log_returns = tuple(
        math.log(current / previous)
        for previous, current in zip(prices, prices[1:])
    )
    rows: list[ForecastFeatureRow] = []
    for index in range(MAX_FEATURE_LOOKBACK, len(prices)):
        cumulative = {
            window: prices[index] / prices[index - window] - 1.0
            for window in _CUMULATIVE_WINDOWS
        }
        rolling_returns = {
            window: log_returns[index - window : index]
            for window in _VOLATILITY_WINDOWS
        }
        rolling_means = {
            window: math.fsum(rolling_returns[window]) / window
            for window in _MEAN_WINDOWS
        }
        rolling_volatilities = {
            window: _sample_volatility(rolling_returns[window])
            for window in _VOLATILITY_WINDOWS
        }
        feature_values = (
            log_returns[index - 1],
            *(cumulative[window] for window in _CUMULATIVE_WINDOWS),
            *(rolling_means[window] for window in _MEAN_WINDOWS),
            *(rolling_volatilities[window] for window in _VOLATILITY_WINDOWS),
        )
        _require_finite(feature_values)
        rows.append(
            ForecastFeatureRow(
                symbol=history.symbol,
                origin_date=dates[index],
                log_return_1=log_returns[index - 1],
                cumulative_return_5=cumulative[5],
                cumulative_return_21=cumulative[21],
                cumulative_return_63=cumulative[63],
                cumulative_return_126=cumulative[126],
                cumulative_return_252=cumulative[252],
                rolling_mean_log_return_5=rolling_means[5],
                rolling_mean_log_return_21=rolling_means[21],
                rolling_mean_log_return_63=rolling_means[63],
                rolling_volatility_log_return_5=rolling_volatilities[5],
                rolling_volatility_log_return_21=rolling_volatilities[21],
                rolling_volatility_log_return_63=rolling_volatilities[63],
                rolling_volatility_log_return_126=rolling_volatilities[126],
                rolling_volatility_log_return_252=rolling_volatilities[252],
            )
        )
    return tuple(rows)
