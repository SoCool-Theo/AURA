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
from .splits import (
    ChronologicalEvaluationPlan,
    EvaluationFold,
    EvaluationPlanConfig,
    FoldDatasetSlice,
    FoldPurpose,
    build_chronological_plan,
    slice_dataset_for_fold,
)
from .metrics import (
    RETURN_MAPE_MINIMUM_ABSOLUTE_ACTUAL,
    DirectionalAccuracyResult,
    SafeMapeResult,
    directional_accuracy,
    mean_absolute_error,
    root_mean_squared_error,
    safe_return_mape,
)
from .evaluation import (
    CandidatePrediction,
    ForecastCandidate,
    ForecastEvaluationResult,
    ForecastTargetType,
    evaluate_candidate,
)
from .baselines import HistoricalMeanBaseline, MovingAverageBaseline
from .models import (
    ARIMA_CANDIDATE_ID,
    ARIMA_FIT_CONVERGENCE_WARNING,
    ARIMA_ORDER,
    LINEAR_REGRESSION_CANDIDATE_ID,
    RANDOM_FOREST_CANDIDATE_ID,
    RANDOM_FOREST_PARAMETERS,
    ArimaCandidate,
    ForecastModelInputError,
    LinearRegressionCandidate,
    RandomForestCandidate,
)
from .selection import (
    CANDIDATE_SIMPLICITY_ORDER,
    MINIMUM_COMPLEX_MODEL_IMPROVEMENT_PERCENT,
    PRACTICAL_TIE_PERCENT,
    CandidateSelectionStatistics,
    SymbolSelectionSummary,
    summarize_symbol_selection,
)

__all__ = [
    "FEATURE_NAMES",
    "FEATURE_SET_VERSION",
    "FORECAST_HORIZON_DAYS",
    "ARIMA_CANDIDATE_ID",
    "ARIMA_FIT_CONVERGENCE_WARNING",
    "ARIMA_ORDER",
    "CANDIDATE_SIMPLICITY_ORDER",
    "LINEAR_REGRESSION_CANDIDATE_ID",
    "MAX_ENDPOINT_SLIPPAGE_DAYS",
    "MAX_FEATURE_LOOKBACK",
    "MIN_LABEL_COMPLETE_TRAINING_ORIGINS",
    "MINIMUM_COMPLEX_MODEL_IMPROVEMENT_PERCENT",
    "PRACTICAL_TIE_PERCENT",
    "RANDOM_FOREST_CANDIDATE_ID",
    "RANDOM_FOREST_PARAMETERS",
    "TARGET_SET_VERSION",
    "RETURN_MAPE_MINIMUM_ABSOLUTE_ACTUAL",
    "AssetPriceHistory",
    "ArimaCandidate",
    "CandidatePrediction",
    "CandidateSelectionStatistics",
    "ChronologicalEvaluationPlan",
    "DirectionalAccuracyResult",
    "EvaluationFold",
    "EvaluationPlanConfig",
    "FoldDatasetSlice",
    "FoldPurpose",
    "ForecastCandidate",
    "ForecastDataset",
    "ForecastDatasetRow",
    "ForecastEvaluationResult",
    "ForecastFeatureRow",
    "ForecastModelInputError",
    "ForecastPriceObservation",
    "ForecastTargetType",
    "ForecastTargetRow",
    "HistoricalMeanBaseline",
    "LinearRegressionCandidate",
    "MovingAverageBaseline",
    "RandomForestCandidate",
    "SafeMapeResult",
    "SymbolSelectionSummary",
    "build_chronological_plan",
    "build_feature_rows",
    "build_forecast_dataset",
    "build_price_histories",
    "build_target_rows",
    "directional_accuracy",
    "evaluate_candidate",
    "mean_absolute_error",
    "root_mean_squared_error",
    "safe_return_mape",
    "slice_dataset_for_fold",
    "summarize_symbol_selection",
]
