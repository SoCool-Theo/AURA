"""Internal Phase 4 candidate adapters for ``return_30d``."""

from .arima import (
    ARIMA_CANDIDATE_ID,
    ARIMA_FIT_CONVERGENCE_WARNING,
    ARIMA_ORDER,
    ArimaCandidate,
)
from .base import ForecastModelInputError
from .linear_regression import (
    LINEAR_REGRESSION_CANDIDATE_ID,
    LinearRegressionCandidate,
    build_linear_regression_pipeline,
)
from .random_forest import (
    RANDOM_FOREST_CANDIDATE_ID,
    RANDOM_FOREST_PARAMETERS,
    RandomForestCandidate,
    build_random_forest_regressor,
)

__all__ = [
    "ARIMA_CANDIDATE_ID",
    "ARIMA_FIT_CONVERGENCE_WARNING",
    "ARIMA_ORDER",
    "LINEAR_REGRESSION_CANDIDATE_ID",
    "RANDOM_FOREST_CANDIDATE_ID",
    "RANDOM_FOREST_PARAMETERS",
    "ArimaCandidate",
    "ForecastModelInputError",
    "LinearRegressionCandidate",
    "RandomForestCandidate",
    "build_linear_regression_pipeline",
    "build_random_forest_regressor",
]
