"""Historical-average forecast baseline."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
import math

from ..data import ForecastDatasetRow
from ..evaluation import (
    CandidatePrediction,
    ForecastTargetType,
    target_value,
)


@dataclass(frozen=True, slots=True)
class HistoricalMeanBaseline:
    """Predict the mean of all target labels completed before the cutoff."""

    candidate_id: str = "historical_average"

    def predict(
        self,
        *,
        training_rows: Sequence[ForecastDatasetRow],
        evaluation_rows: Sequence[ForecastDatasetRow],
        target_type: ForecastTargetType,
        information_cutoff: date,
    ) -> CandidatePrediction:
        completed_values = tuple(
            target_value(row, target_type)
            for row in training_rows
            if row.target.endpoint_date < information_cutoff
        )
        if not completed_values:
            return CandidatePrediction(
                candidate_id=self.candidate_id,
                values=None,
                training_value_count=0,
                warning="historical average has no completed target labels",
            )
        prediction = math.fsum(completed_values) / len(completed_values)
        if not math.isfinite(prediction):
            raise ValueError("historical average prediction must be finite")
        return CandidatePrediction(
            candidate_id=self.candidate_id,
            values=tuple(prediction for _ in evaluation_rows),
            training_value_count=len(completed_values),
        )
