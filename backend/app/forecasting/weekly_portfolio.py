"""Same-horizon portfolio composition using the established V1 risk formulas."""

from dataclasses import dataclass
from datetime import UTC, date, datetime
import math
from numbers import Real
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..database.models import Portfolio
from ..services.market_data_service import MarketDataService
from ..services.portfolio_baseline_resolver import PortfolioBaselineResolutionService
from .inference_errors import ForecastMarketDataUnavailableError, ForecastPredictionError
from .monetary_projection import (
    PortfolioMonetaryProjection, build_monetary_projection, build_component_monetary_projections,
)
from .portfolio import validated_weights, aligned_log_returns, historical_correlation, compose_volatility
from .weekly_inference import WeeklyAssetForecast, WeeklyForecastInferenceService
from .weekly_registry import WEEKLY_VERSION, validate_weekly_horizon
from .features import FEATURE_SET_VERSION


@dataclass(frozen=True, slots=True)
class WeeklyPortfolioComponent:
    forecast: WeeklyAssetForecast
    current_weight: float
    forecast_volatility_contribution: float
    forecast_volatility_contribution_share: float
    monetary_projection: PortfolioMonetaryProjection | None = None


@dataclass(frozen=True, slots=True)
class WeeklyPortfolioForecast:
    portfolio_id: UUID
    portfolio_name: str
    baseline_kind: str
    horizon_days: int
    expected_return: float
    forecast_realized_volatility: float
    correlation_as_of_date: date
    correlation_observation_count: int
    market_data_as_of: date
    artifact_version: str
    components: tuple[WeeklyPortfolioComponent, ...]
    monetary_projection: PortfolioMonetaryProjection | None = None


def _validate_component(forecast: WeeklyAssetForecast, symbol: str, horizon: int, today: date):
    values = (forecast.expected_return, forecast.forecast_realized_volatility,
              forecast.return_interval_lower, forecast.return_interval_upper,
              forecast.volatility_interval_lower, forecast.volatility_interval_upper)
    if (any(not isinstance(value, Real) or isinstance(value, bool) or not math.isfinite(value) for value in values)
            or type(forecast.origin_date) is not date or type(forecast.market_data_as_of) is not date):
        raise ForecastPredictionError("invalid weekly component values")
    if (forecast.symbol != symbol or type(forecast.horizon_days) is not int or forecast.horizon_days != horizon
            or forecast.artifact_version != WEEKLY_VERSION or forecast.feature_version != FEATURE_SET_VERSION
            or forecast.target_version != f"forecast-targets-{horizon}d-v1"
            or forecast.forecast_realized_volatility < 0 or forecast.volatility_interval_lower < 0
            or forecast.return_interval_lower > forecast.return_interval_upper
            or forecast.volatility_interval_lower > forecast.volatility_interval_upper
            or forecast.interval_coverage != .8 or forecast.market_data_as_of != forecast.origin_date
            or not 0 <= (today - forecast.origin_date).days <= 4
            or type(forecast.market_data_age_days) is not int
            or forecast.market_data_age_days != (today - forecast.origin_date).days):
        raise ForecastPredictionError("invalid weekly component context")


class WeeklyPortfolioForecastService:
    """Caller ownership-checks the portfolio; every component must succeed."""

    def __init__(self, session: Session):
        self._session = session
        self._baseline = PortfolioBaselineResolutionService(session)
        self._market_data = MarketDataService(session)

    def predict(self, portfolio: Portfolio, *, horizon_days: int) -> WeeklyPortfolioForecast:
        validate_weekly_horizon(horizon_days)
        today = datetime.now(UTC).date()
        baseline = self._baseline.resolve(portfolio=portfolio, valuation_date=today)
        symbols, weights = validated_weights(baseline.resolved_weights)
        inference = WeeklyForecastInferenceService(self._session)
        forecasts = tuple(inference.predict(symbol, horizon_days=horizon_days, reference_date=today) for symbol in symbols)
        for symbol, forecast in zip(symbols, forecasts):
            _validate_component(forecast, symbol, horizon_days, today)
        as_of = min(f.origin_date for f in forecasts)
        try:
            records = self._market_data.get_range(symbols, date.min, as_of)
        except SQLAlchemyError:
            raise ForecastMarketDataUnavailableError("correlation market data unavailable") from None
        returns = aligned_log_returns(records, symbols, as_of)
        correlation = historical_correlation(returns)
        sigma, contributions, shares = compose_volatility(
            weights, [f.forecast_realized_volatility for f in forecasts], correlation,
        )
        try:
            expected_return = math.fsum(w * f.expected_return for w, f in zip(weights, forecasts))
        except (OverflowError, ValueError):
            raise ForecastPredictionError("invalid weekly portfolio return") from None
        if not math.isfinite(expected_return):
            raise ForecastPredictionError("invalid weekly portfolio return")
        monetary_projection = build_monetary_projection(baseline, expected_return)
        component_money = build_component_monetary_projections(
            baseline, tuple((f.symbol, f.expected_return) for f in forecasts), monetary_projection,
        )
        return WeeklyPortfolioForecast(
            portfolio.id, portfolio.name, baseline.baseline_kind.value, horizon_days,
            expected_return, sigma, as_of, len(returns), min(f.market_data_as_of for f in forecasts),
            WEEKLY_VERSION, tuple(WeeklyPortfolioComponent(f, float(w), float(rc), float(share), component_money[f.symbol])
                for f, w, rc, share in zip(forecasts, weights, contributions, shares)),
            monetary_projection=monetary_projection,
        )
