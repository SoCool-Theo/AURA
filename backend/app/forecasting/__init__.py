"""Internal foundation for Aura's future asset forecasting capability.

This package is deliberately separate from Aura's deterministic analytics.
It does not train models, perform inference, or define public API contracts.
"""

from .data import (
    MIN_LABEL_COMPLETE_TRAINING_ORIGINS,
    AssetPriceHistory,
    ForecastDataset,
    ForecastDatasetRow,
    ForecastPriceObservation,
    build_forecast_dataset,
    build_price_histories,
)
from .features import (
    FEATURE_NAMES,
    FEATURE_SET_VERSION,
    MAX_FEATURE_LOOKBACK,
    ForecastFeatureRow,
    build_feature_rows,
)
from .targets import (
    FORECAST_HORIZON_DAYS,
    MAX_ENDPOINT_SLIPPAGE_DAYS,
    TARGET_SET_VERSION,
    ForecastTargetRow,
    build_target_rows,
)

__all__ = [
    "FEATURE_NAMES",
    "FEATURE_SET_VERSION",
    "FORECAST_HORIZON_DAYS",
    "MAX_ENDPOINT_SLIPPAGE_DAYS",
    "MAX_FEATURE_LOOKBACK",
    "MIN_LABEL_COMPLETE_TRAINING_ORIGINS",
    "TARGET_SET_VERSION",
    "AssetPriceHistory",
    "ForecastDataset",
    "ForecastDatasetRow",
    "ForecastFeatureRow",
    "ForecastPriceObservation",
    "ForecastTargetRow",
    "build_feature_rows",
    "build_forecast_dataset",
    "build_price_histories",
    "build_target_rows",
]
