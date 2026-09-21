"""Fold-local scaled Linear Regression return candidate."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from typing import ClassVar

from sklearn.linear_model import LinearRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from ..data import ForecastDatasetRow
from ..evaluation import CandidatePrediction, ForecastTargetType
from .base import (
    ForecastModelInputError,
    require_return_target,
    require_volatility_target,
    supervised_fold_arrays,
    supervised_volatility_fold_arrays,
    validated_predictions,
)


LINEAR_REGRESSION_CANDIDATE_ID = "linear_regression_v1"
VOLATILITY_LINEAR_REGRESSION_CANDIDATE_ID = (
    "volatility_linear_regression_v1"
)


def build_linear_regression_pipeline() -> Pipeline:
    """Return the fixed V1 pipeline; fitting remains caller-triggered."""
    return Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            ("regressor", LinearRegression()),
        ]
    )


@dataclass(frozen=True, slots=True)
class LinearRegressionCandidate:
    """Predict ``return_30d`` using fold-local feature scaling and OLS."""

    candidate_id: ClassVar[str] = LINEAR_REGRESSION_CANDIDATE_ID
    target_type: ClassVar[ForecastTargetType] = ForecastTargetType.RETURN

    def predict(
        self,
        *,
        training_rows: Sequence[ForecastDatasetRow],
        evaluation_rows: Sequence[ForecastDatasetRow],
        target_type: ForecastTargetType,
        information_cutoff: date,
    ) -> CandidatePrediction:
        require_return_target(target_type)
        training_features, training_targets, evaluation_features = (
            supervised_fold_arrays(
                training_rows=training_rows,
                evaluation_rows=evaluation_rows,
                information_cutoff=information_cutoff,
            )
        )
        try:
            pipeline = build_linear_regression_pipeline()
            pipeline.fit(training_features, training_targets)
            values = validated_predictions(
                pipeline.predict(evaluation_features),
                expected_count=len(evaluation_rows),
            )
        except ForecastModelInputError:
            raise
        except Exception as error:
            return CandidatePrediction(
                candidate_id=self.candidate_id,
                values=None,
                training_value_count=len(training_rows),
                warning=(
                    "linear regression unavailable for this fold: "
                    f"{type(error).__name__}: {error}"
                ),
            )
        return CandidatePrediction(
            candidate_id=self.candidate_id,
            values=values,
            training_value_count=len(training_rows),
        )


@dataclass(frozen=True, slots=True)
class VolatilityLinearRegressionCandidate:
    """Predict realized volatility with fold-local scaling and OLS."""

    candidate_id: ClassVar[str] = VOLATILITY_LINEAR_REGRESSION_CANDIDATE_ID
    target_type: ClassVar[ForecastTargetType] = ForecastTargetType.VOLATILITY

    def predict(
        self,
        *,
        training_rows: Sequence[ForecastDatasetRow],
        evaluation_rows: Sequence[ForecastDatasetRow],
        target_type: ForecastTargetType,
        information_cutoff: date,
    ) -> CandidatePrediction:
        require_volatility_target(target_type)
        training_features, training_targets, evaluation_features = (
            supervised_volatility_fold_arrays(
                training_rows=training_rows,
                evaluation_rows=evaluation_rows,
                information_cutoff=information_cutoff,
            )
        )
        try:
            pipeline = build_linear_regression_pipeline()
            pipeline.fit(training_features, training_targets)
            values = validated_predictions(
                pipeline.predict(evaluation_features),
                expected_count=len(evaluation_rows),
            )
        except ForecastModelInputError:
            raise
        except Exception as error:
            return CandidatePrediction(
                candidate_id=self.candidate_id,
                values=None,
                training_value_count=len(training_rows),
                warning=(
                    "volatility linear regression unavailable for this fold: "
                    f"{type(error).__name__}: {error}"
                ),
            )
        return CandidatePrediction(
            candidate_id=self.candidate_id,
            values=values,
            training_value_count=len(training_rows),
        )
