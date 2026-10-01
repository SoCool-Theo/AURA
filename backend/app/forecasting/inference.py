"""Internal inference using immutable deployed artifacts and persisted prices."""

from dataclasses import dataclass
from datetime import UTC, date, datetime
from functools import lru_cache
import math

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from ..core.config import settings
from ..core.instruments import USER_ASSET_SYMBOLS
from ..services.market_data_service import MarketDataService
from .data import AssetPriceHistory, ForecastDataError, build_price_histories
from .evaluation import ForecastTargetType
from .features import FEATURE_NAMES, FEATURE_SET_VERSION, build_feature_rows
from .finalization import prediction_interval
from .registry import ForecastArtifactRegistry
from .inference_errors import (
    ForecastHistoryInsufficientError, ForecastDataStaleError,
    ForecastPredictionError, ForecastSymbolUnsupportedError,
    ForecastMarketDataUnavailableError,
)
from .targets import FORECAST_HORIZON_DAYS, TARGET_SET_VERSION


MAX_FORECAST_DATA_AGE_DAYS = 4


@dataclass(frozen=True, slots=True)
class AssetForecast:
    symbol: str
    origin_date: date
    horizon_days: int
    expected_return_30d: float
    return_interval_lower: float
    return_interval_upper: float
    forecast_realized_volatility_30d: float
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


def arima_step_index(history: AssetPriceHistory, cutoff: date, origin: date) -> int:
    """Count only stored observations from deployment cutoff through origin."""
    eligible = tuple(row.date for row in history.observations if row.date >= cutoff)
    if not eligible or origin < eligible[0] or origin not in eligible:
        raise ForecastHistoryInsufficientError("no deployed observation at the forecast origin")
    return sum(observed <= origin for observed in eligible)


@lru_cache(maxsize=4)
def _configured_registry(version: str) -> ForecastArtifactRegistry:
    return ForecastArtifactRegistry(artifact_version=version)


class ForecastInferenceService:
    """Caller supplies the current application's session; no database URL loading."""

    def __init__(self, session: Session, *, registry: ForecastArtifactRegistry | None = None):
        self._market_data = MarketDataService(session)
        self._registry = registry or _configured_registry(settings.forecasting_artifact_version)

    def predict(self, symbol: str, *, reference_date: date | None = None) -> AssetForecast:
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
            feature_rows = build_feature_rows(history)
        except ValueError:
            raise ForecastHistoryInsufficientError("unable to construct finite forecast features") from None
        if not feature_rows or feature_rows[-1].origin_date != origin:
            raise ForecastHistoryInsufficientError("insufficient feature warm-up history")
        features = (tuple(getattr(feature_rows[-1], name) for name in FEATURE_NAMES),)
        points = []
        intervals = []
        ids = []
        for target in (ForecastTargetType.RETURN, ForecastTargetType.VOLATILITY):
            artifact = self._registry.get(symbol, target)
            steps = arima_step_index(history, artifact.evaluation_cutoff, origin) if artifact.model.model_family == "arima" else 1
            try:
                values = artifact.model.predict(steps=steps, feature_matrix=features)
                if len(values) != steps or not all(math.isfinite(value) for value in values):
                    raise ValueError("invalid prediction sequence")
                point = float(values[-1])
                if target is ForecastTargetType.VOLATILITY:
                    point = max(point, 0.0)
                interval = prediction_interval(
                    point_prediction=point, residual_q10=artifact.residual_q10,
                    residual_q90=artifact.residual_q90, target_type=target,
                )
                if interval[0] > interval[1]:
                    raise ValueError("invalid interval bounds")
            except Exception:
                raise ForecastPredictionError("selected artifact produced an invalid prediction") from None
            points.append(point)
            intervals.append(interval)
            ids.append(artifact.model.candidate_id)
        return AssetForecast(
            symbol, origin, FORECAST_HORIZON_DAYS, points[0], *intervals[0],
            points[1], *intervals[1], 0.80, ids[0], ids[1],
            self._registry.artifact_version, FEATURE_SET_VERSION, TARGET_SET_VERSION,
            origin, age,
        )
