"""Read-only portfolio composition; no fitting or historical analytics changes."""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
import math
from numbers import Real
from uuid import UUID

import numpy as np
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..core.instruments import USER_ASSET_SYMBOLS
from ..database.models import MarketData, Portfolio
from ..services.market_data_service import MarketDataService
from ..services.portfolio_baseline_resolver import (
    PortfolioBaselineResolutionService, ResolvedPortfolioWeight,
)
from .data import ForecastDataError, build_price_histories
from .inference import AssetForecast, ForecastInferenceService
from .inference_errors import (
    ForecastHistoryInsufficientError,
    ForecastMarketDataUnavailableError, ForecastPredictionError,
)


# Absolute tolerances: allocation sum and matrix validity in decimal ratios;
# variance epsilon in squared 30-day volatility units, never annualized.
WEIGHT_SUM_TOLERANCE = 1e-10
MATRIX_TOLERANCE = 1e-12
VARIANCE_EPSILON = 1e-14
MIN_CORRELATION_OBSERVATIONS = 60
MAX_CORRELATION_OBSERVATIONS = 252


class InvalidForecastPortfolioError(ValueError):
    """Saved portfolio cannot supply a valid complete forecast allocation."""


@dataclass(frozen=True, slots=True)
class PortfolioForecastComponent:
    forecast: AssetForecast
    current_weight: float
    forecast_volatility_contribution: float
    forecast_volatility_contribution_share: float


@dataclass(frozen=True, slots=True)
class PortfolioForecast:
    portfolio_id: UUID
    portfolio_name: str
    baseline_kind: str
    expected_return_30d: float
    forecast_realized_volatility_30d: float
    correlation_as_of_date: date
    correlation_observation_count: int
    market_data_as_of: date
    artifact_version: str
    components: tuple[PortfolioForecastComponent, ...]


def validated_weights(
    resolved_weights: Sequence[ResolvedPortfolioWeight],
) -> tuple[tuple[str, ...], np.ndarray]:
    """Copy the authoritative allocation; normalize only rounding-size drift."""
    rows = tuple(resolved_weights)
    symbols = tuple(row.symbol for row in rows)
    if not rows or len(set(symbols)) != len(symbols):
        raise InvalidForecastPortfolioError("empty or duplicate portfolio allocation")
    if any(symbol not in USER_ASSET_SYMBOLS for symbol in symbols):
        raise InvalidForecastPortfolioError("unsupported portfolio asset")
    try:
        if any(isinstance(row.weight, bool) for row in rows):
            raise ValueError()
        weights = np.array([float(row.weight) for row in rows], dtype=float)
    except (TypeError, ValueError, OverflowError):
        raise InvalidForecastPortfolioError("invalid portfolio weights") from None
    if not np.isfinite(weights).all() or (weights < 0).any() or (weights > 1).any():
        raise InvalidForecastPortfolioError("invalid portfolio weights")
    total = math.fsum(weights)
    if abs(total - 1.0) > WEIGHT_SUM_TOLERANCE:
        raise InvalidForecastPortfolioError("portfolio weights must sum to one")
    return symbols, weights / total


def aligned_log_returns(
    records: Iterable[MarketData], symbols: tuple[str, ...], as_of: date,
) -> np.ndarray:
    """Log each asset's consecutive stored prices, then intersect return dates.

    Missing dates remain missing. No price/return filling or pairwise windows.
    Filtering also enforces the cutoff if an adapter returns extra observations.
    """
    try:
        histories = build_price_histories(
            row for row in records if row.symbol in symbols and row.date <= as_of
        )
    except ForecastDataError:
        raise ForecastHistoryInsufficientError("invalid correlation history") from None
    by_symbol = {}
    for history in histories:
        observations = history.observations
        by_symbol[history.symbol] = {
            current.date: math.log(current.adjusted_close) - math.log(previous.adjusted_close)
            for previous, current in zip(observations, observations[1:])
        }
    if any(symbol not in by_symbol for symbol in symbols):
        raise ForecastHistoryInsufficientError("missing correlation history")
    dates = sorted(set.intersection(*(set(by_symbol[symbol]) for symbol in symbols)))
    dates = dates[-MAX_CORRELATION_OBSERVATIONS:]
    if len(dates) < MIN_CORRELATION_OBSERVATIONS:
        raise ForecastHistoryInsufficientError("insufficient common correlation history")
    values = np.array([[by_symbol[symbol][day] for symbol in symbols] for day in dates])
    if not np.isfinite(values).all():
        raise ForecastPredictionError("non-finite correlation returns")
    return values


def historical_correlation(returns: np.ndarray) -> np.ndarray:
    """Pearson correlation from one complete common return matrix."""
    if returns.ndim != 2 or not np.isfinite(returns).all():
        raise ForecastPredictionError("invalid common return matrix")
    if returns.shape[0] < MIN_CORRELATION_OBSERVATIONS or returns.shape[1] < 1:
        raise ForecastHistoryInsufficientError("insufficient correlation observations")
    # A constant series has undefined correlation, including for one asset.
    if (np.std(returns, axis=0) == 0).any():
        raise ForecastPredictionError("undefined correlation")
    with np.errstate(divide="ignore", invalid="ignore"):
        correlation = np.atleast_2d(np.corrcoef(returns, rowvar=False))
    return validate_correlation(correlation, returns.shape[1])


def validate_correlation(correlation: np.ndarray, size: int) -> np.ndarray:
    """Reject unsafe matrices without repairing or overwriting caller inputs."""
    try:
        matrix = np.asarray(correlation, dtype=float)
    except (TypeError, ValueError, OverflowError):
        raise ForecastPredictionError("invalid correlation matrix") from None
    if (
        matrix.shape != (size, size) or not np.isfinite(matrix).all()
        or (np.abs(matrix) > 1 + MATRIX_TOLERANCE).any()
        or not np.allclose(matrix, matrix.T, rtol=0, atol=MATRIX_TOLERANCE)
        or not np.allclose(np.diag(matrix), 1, rtol=0, atol=MATRIX_TOLERANCE)
    ):
        raise ForecastPredictionError("invalid correlation matrix")
    try:
        if np.linalg.eigvalsh(matrix).min() < -MATRIX_TOLERANCE:
            raise ForecastPredictionError("correlation matrix is not positive semidefinite")
    except np.linalg.LinAlgError:
        raise ForecastPredictionError("invalid correlation matrix") from None
    return matrix


def variance_to_volatility(variance: float) -> float:
    """Floor only negative floating-point roundoff within VARIANCE_EPSILON."""
    if not math.isfinite(variance) or variance < -VARIANCE_EPSILON:
        raise ForecastPredictionError("invalid portfolio forecast variance")
    return math.sqrt(max(variance, 0.0))


def compose_volatility(
    weights: Sequence[float] | np.ndarray,
    volatilities: Sequence[float] | np.ndarray,
    correlation: Sequence[Sequence[float]] | np.ndarray,
) -> tuple[float, np.ndarray, np.ndarray]:
    """D R D covariance and signed Euler contributions; zero sigma -> zeros."""
    weights = np.asarray(weights, dtype=float)
    volatilities = np.asarray(volatilities, dtype=float)
    if (
        weights.ndim != 1 or volatilities.shape != weights.shape
        or not np.isfinite(weights).all() or not np.isfinite(volatilities).all()
        or (volatilities < 0).any()
    ):
        raise ForecastPredictionError("invalid covariance inputs")
    matrix = validate_correlation(correlation, len(weights))
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        covariance = volatilities[:, None] * matrix * volatilities[None, :]
        marginal = covariance @ weights
        sigma = variance_to_volatility(float(weights @ marginal))
        contributions = weights * marginal / sigma if sigma else np.zeros_like(weights)
        shares = contributions / sigma if sigma else np.zeros_like(weights)
    if not all(np.isfinite(values).all() for values in (covariance, contributions, shares)):
        raise ForecastPredictionError("invalid forecast covariance result")
    if sigma and (
        not math.isclose(math.fsum(contributions), sigma, rel_tol=1e-9, abs_tol=1e-12)
        or not math.isclose(math.fsum(shares), 1.0, rel_tol=1e-9, abs_tol=1e-12)
    ):
        raise ForecastPredictionError("inconsistent forecast contributions")
    return sigma, contributions, shares


def _validate_component(forecast: AssetForecast, symbol: str, today: date) -> None:
    values = (
        forecast.expected_return_30d, forecast.forecast_realized_volatility_30d,
        forecast.return_interval_lower, forecast.return_interval_upper,
        forecast.volatility_interval_lower, forecast.volatility_interval_upper,
    )
    if (
        not all(isinstance(value, Real) and not isinstance(value, bool) for value in values)
        or type(forecast.origin_date) is not date
        or type(forecast.market_data_as_of) is not date
    ):
        raise ForecastPredictionError("invalid component forecast values")
    if (
        forecast.symbol != symbol or forecast.horizon_days != 30
        or not all(math.isfinite(value) for value in values)
        or forecast.forecast_realized_volatility_30d < 0
        or forecast.volatility_interval_lower < 0
        or forecast.return_interval_lower > forecast.return_interval_upper
        or forecast.volatility_interval_lower > forecast.volatility_interval_upper
        or forecast.interval_coverage != 0.80
        or forecast.market_data_as_of != forecast.origin_date
        or not 0 <= (today - forecast.origin_date).days <= 4
        or forecast.market_data_age_days != (today - forecast.origin_date).days
    ):
        raise ForecastPredictionError("invalid component forecast")


class PortfolioForecastService:
    """Compose an already ownership-checked portfolio using one caller session."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._baseline = PortfolioBaselineResolutionService(session)
        self._market_data = MarketDataService(session)

    def predict(self, portfolio: Portfolio) -> PortfolioForecast:
        today = datetime.now(UTC).date()
        baseline = self._baseline.resolve(portfolio=portfolio, valuation_date=today)
        symbols, weights = validated_weights(baseline.resolved_weights)
        inference = ForecastInferenceService(self._session)
        forecasts = tuple(inference.predict(symbol, reference_date=today) for symbol in symbols)
        for symbol, forecast in zip(symbols, forecasts):
            _validate_component(forecast, symbol, today)
        if len({(f.artifact_version, f.feature_version, f.target_version) for f in forecasts}) != 1:
            raise ForecastPredictionError("inconsistent component artifact provenance")
        as_of = min(f.origin_date for f in forecasts)
        try:
            records = self._market_data.get_range(symbols, date.min, as_of)
        except SQLAlchemyError:
            raise ForecastMarketDataUnavailableError("correlation market data unavailable") from None
        returns = aligned_log_returns(records, symbols, as_of)
        correlation = historical_correlation(returns)
        sigma, contributions, shares = compose_volatility(
            weights, [f.forecast_realized_volatility_30d for f in forecasts], correlation,
        )
        try:
            expected_return = math.fsum(w * f.expected_return_30d for w, f in zip(weights, forecasts))
        except (OverflowError, ValueError):
            raise ForecastPredictionError("invalid portfolio forecast return") from None
        if not math.isfinite(expected_return):
            raise ForecastPredictionError("invalid portfolio forecast return")
        return PortfolioForecast(
            portfolio.id, portfolio.name, baseline.baseline_kind.value, expected_return,
            sigma, as_of, len(returns), min(f.market_data_as_of for f in forecasts),
            forecasts[0].artifact_version,
            tuple(PortfolioForecastComponent(f, float(w), float(rc), float(share))
                  for f, w, rc, share in zip(forecasts, weights, contributions, shares)),
        )
