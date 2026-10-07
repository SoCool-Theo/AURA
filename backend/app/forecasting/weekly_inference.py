"""Actual weekly targets from immutable models and current persisted prices."""

from dataclasses import dataclass
from datetime import UTC, date, datetime
from functools import lru_cache
import math

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..core.instruments import USER_ASSET_SYMBOLS
from ..services.market_data_service import MarketDataService
from .data import ForecastDataError, build_price_histories
from .evaluation import ForecastTargetType
from .features import FEATURE_NAMES, FEATURE_SET_VERSION, build_feature_rows
from .finalization import prediction_interval
from .inference import MAX_FORECAST_DATA_AGE_DAYS, arima_step_index
from .inference_errors import (
    ForecastDataStaleError, ForecastHistoryInsufficientError,
    ForecastMarketDataUnavailableError, ForecastPredictionError, ForecastSymbolUnsupportedError,
)
from .weekly_registry import WeeklyArtifactRegistry, validate_weekly_horizon


@dataclass(frozen=True, slots=True)
class WeeklyAssetForecast:
    symbol: str
    origin_date: date
    horizon_days: int
    expected_return: float
    return_interval_lower: float
    return_interval_upper: float
    forecast_realized_volatility: float
    volatility_interval_lower: float
    volatility_interval_upper: float
    interval_coverage: float
    return_model_id: str
    volatility_model_id: str
    artifact_version: str
    feature_version: str
    target_version: str
    market_data_as_of: date
    market_data_age_days: int
    return_warning_codes: tuple[str, ...]
    volatility_warning_codes: tuple[str, ...]


@lru_cache(maxsize=1)
def _configured_weekly_registry() -> WeeklyArtifactRegistry:
    return WeeklyArtifactRegistry()


class WeeklyForecastInferenceService:
    """No provider requests, fitting, scaling of 30-day results or DB writes."""

    def __init__(self, session: Session, *, registry: WeeklyArtifactRegistry | None = None):
        self._market_data = MarketDataService(session)
        self._registry = registry or _configured_weekly_registry()

    def predict(self, symbol: str, *, horizon_days: int,
                reference_date: date | None = None) -> WeeklyAssetForecast:
        validate_weekly_horizon(horizon_days)
        if not isinstance(symbol, str) or symbol not in USER_ASSET_SYMBOLS:
            raise ForecastSymbolUnsupportedError("unsupported forecast symbol")
        today = reference_date if reference_date is not None else datetime.now(UTC).date()
        if type(today) is not date:
            raise ForecastPredictionError("reference date must be a date")
        try:
            histories = build_price_histories(self._market_data.get_range((symbol,), date.min, today))
        except ForecastDataError:
            raise ForecastHistoryInsufficientError("invalid persisted forecast history") from None
        except SQLAlchemyError:
            raise ForecastMarketDataUnavailableError("persisted forecast market data is unavailable") from None
        if len(histories) != 1 or histories[0].symbol != symbol:
            raise ForecastHistoryInsufficientError("no persisted history for requested symbol")
        history = histories[0]
        origin = history.observations[-1].date
        age = (today - origin).days
        if age < 0:
            raise ForecastPredictionError("forecast origin cannot be in the future")
        if age > MAX_FORECAST_DATA_AGE_DAYS:
            raise ForecastDataStaleError("latest market observation is more than 4 calendar days old")
        try:
            rows = build_feature_rows(history)
        except ValueError:
            raise ForecastHistoryInsufficientError("unable to construct finite forecast features") from None
        if not rows or rows[-1].origin_date != origin:
            raise ForecastHistoryInsufficientError("insufficient feature warm-up history")
        features = (tuple(getattr(rows[-1], name) for name in FEATURE_NAMES),)
        points, intervals, ids, warnings = [], [], [], []
        for target in (ForecastTargetType.RETURN, ForecastTargetType.VOLATILITY):
            artifact = self._registry.get(symbol, target, horizon_days)
            steps = (arima_step_index(history, artifact.evaluation_cutoff, origin)
                     if artifact.model.model_family == "arima" else 1)
            try:
                values = artifact.model.predict(steps=steps, feature_matrix=features)
                if len(values) != steps or not all(math.isfinite(value) for value in values):
                    raise ValueError()
                point = float(values[-1])
                if target is ForecastTargetType.VOLATILITY:
                    point = max(point, 0.)
                interval = prediction_interval(point_prediction=point,
                    residual_q10=artifact.residual_q10, residual_q90=artifact.residual_q90, target_type=target)
                if not all(math.isfinite(value) for value in interval) or interval[0] > interval[1]:
                    raise ValueError()
            except Exception:
                raise ForecastPredictionError("selected weekly artifact produced an invalid prediction") from None
            points.append(point)
            intervals.append(interval)
            ids.append(artifact.model.candidate_id)
            warnings.append(artifact.warning_codes)
        return WeeklyAssetForecast(
            symbol, origin, horizon_days, points[0], *intervals[0], points[1], *intervals[1], .8,
            ids[0], ids[1], self._registry.artifact_version, FEATURE_SET_VERSION,
            f"forecast-targets-{horizon_days}d-v1", origin, age, warnings[0], warnings[1],
        )
