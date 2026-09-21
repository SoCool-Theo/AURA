"""Deterministic Random Forest return candidate."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from typing import ClassVar

from sklearn.ensemble import RandomForestRegressor

from ..data import ForecastDatasetRow
from ..evaluation import CandidatePrediction, ForecastTargetType
from .base import (
    ForecastModelInputError,
    require_return_target,
    supervised_fold_arrays,
    validated_predictions,
)


RANDOM_FOREST_CANDIDATE_ID = "random_forest_v1"
RANDOM_FOREST_PARAMETERS: dict[str, int] = {
    "n_estimators": 200,
    "max_depth": 8,
    "min_samples_leaf": 5,
    "random_state": 42,
    "n_jobs": 1,
}


def build_random_forest_regressor() -> RandomForestRegressor:
    """Return the immutable V1 comparison configuration without fitting it."""
    return RandomForestRegressor(**RANDOM_FOREST_PARAMETERS)


@dataclass(frozen=True, slots=True)
class RandomForestCandidate:
    """Predict ``return_30d`` with Aura's fixed V1 forest configuration."""

    candidate_id: ClassVar[str] = RANDOM_FOREST_CANDIDATE_ID
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
            regressor = build_random_forest_regressor()
            regressor.fit(training_features, training_targets)
            values = validated_predictions(
                regressor.predict(evaluation_features),
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
                    "random forest unavailable for this fold: "
                    f"{type(error).__name__}: {error}"
                ),
            )
        return CandidatePrediction(
            candidate_id=self.candidate_id,
            values=values,
            training_value_count=len(training_rows),
        )
