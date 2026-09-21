"""Leakage-separated 30-calendar-day target construction.

Targets consume Aura's canonical persisted ``adjusted_close`` values. That
field can represent the data pipeline's documented raw-close fallback when a
provider does not supply an adjusted value; this layer preserves the stored
value and does not claim stronger price provenance.
"""

from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass
from datetime import date, timedelta
import math

from .data import AssetPriceHistory


TARGET_SET_VERSION = "forecast-targets-v1"
FORECAST_HORIZON_DAYS = 30
MAX_ENDPOINT_SLIPPAGE_DAYS = 4


class ForecastTargetError(ValueError):
    """Raised when a finite approved target cannot be produced."""


@dataclass(frozen=True, slots=True)
class ForecastTargetRow:
    """One completed future label with its exact calendar provenance."""

    symbol: str
    origin_date: date
    requested_target_date: date
    endpoint_date: date
    endpoint_slippage_days: int
    return_30d: float
    realized_volatility_30d: float

    @property
    def label_completion_date(self) -> date:
        """Return the date by which every value in this label is observable."""
        return self.endpoint_date


def build_target_rows(
    history: AssetPriceHistory,
) -> tuple[ForecastTargetRow, ...]:
    """Return labels using the first stored observation at/after day 30.

    The endpoint may slip by at most four calendar days. Realized volatility
    is ``sqrt(sum(r_i**2))`` where each ``r_i`` is a consecutive observed-price
    log return whose ending observation is strictly after the origin and no
    later than the endpoint. The result is not annualized.
    """
    observations = history.observations
    dates = tuple(observation.date for observation in observations)
    prices = tuple(observation.adjusted_close for observation in observations)
    rows: list[ForecastTargetRow] = []

    for origin_index, origin_date in enumerate(dates):
        requested_target_date = origin_date + timedelta(
            days=FORECAST_HORIZON_DAYS
        )
        endpoint_index = bisect_left(
            dates,
            requested_target_date,
            lo=origin_index + 1,
        )
        if endpoint_index == len(dates):
            continue
        endpoint_date = dates[endpoint_index]
        slippage_days = (endpoint_date - requested_target_date).days
        if slippage_days > MAX_ENDPOINT_SLIPPAGE_DAYS:
            continue

        origin_price = prices[origin_index]
        endpoint_price = prices[endpoint_index]
        return_30d = endpoint_price / origin_price - 1.0
        future_log_returns = tuple(
            math.log(prices[index] / prices[index - 1])
            for index in range(origin_index + 1, endpoint_index + 1)
        )
        realized_volatility_30d = math.sqrt(
            math.fsum(value * value for value in future_log_returns)
        )
        if not (
            math.isfinite(return_30d)
            and math.isfinite(realized_volatility_30d)
        ):
            raise ForecastTargetError("forecast targets must be finite")

        rows.append(
            ForecastTargetRow(
                symbol=history.symbol,
                origin_date=origin_date,
                requested_target_date=requested_target_date,
                endpoint_date=endpoint_date,
                endpoint_slippage_days=slippage_days,
                return_30d=return_30d,
                realized_volatility_30d=realized_volatility_30d,
            )
        )
    return tuple(rows)
