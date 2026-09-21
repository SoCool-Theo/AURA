"""Internal return and realized-volatility candidate adapters."""

from .arima import (
    ARIMA_CANDIDATE_ID,
    ARIMA_FIT_CONVERGENCE_WARNING,
    ARIMA_ORDER,
    VOLATILITY_ARIMA_CANDIDATE_ID,
    ArimaCandidate,
    VolatilityArimaCandidate,
)
from .base import ForecastModelInputError
from .linear_regression import (
    LINEAR_REGRESSION_CANDIDATE_ID,
    VOLATILITY_LINEAR_REGRESSION_CANDIDATE_ID,
    LinearRegressionCandidate,
    VolatilityLinearRegressionCandidate,
    build_linear_regression_pipeline,
)
from .random_forest import (
    RANDOM_FOREST_CANDIDATE_ID,
    RANDOM_FOREST_PARAMETERS,
    VOLATILITY_RANDOM_FOREST_CANDIDATE_ID,
    RandomForestCandidate,
    VolatilityRandomForestCandidate,
    build_random_forest_regressor,
)

__all__ = [
    "ARIMA_CANDIDATE_ID",
    "ARIMA_FIT_CONVERGENCE_WARNING",
    "ARIMA_ORDER",
    "LINEAR_REGRESSION_CANDIDATE_ID",
    "RANDOM_FOREST_CANDIDATE_ID",
    "RANDOM_FOREST_PARAMETERS",
    "VOLATILITY_ARIMA_CANDIDATE_ID",
    "VOLATILITY_LINEAR_REGRESSION_CANDIDATE_ID",
    "VOLATILITY_RANDOM_FOREST_CANDIDATE_ID",
    "ArimaCandidate",
    "ForecastModelInputError",
    "LinearRegressionCandidate",
    "RandomForestCandidate",
    "VolatilityArimaCandidate",
    "VolatilityLinearRegressionCandidate",
    "VolatilityRandomForestCandidate",
    "build_linear_regression_pipeline",
    "build_random_forest_regressor",
]
