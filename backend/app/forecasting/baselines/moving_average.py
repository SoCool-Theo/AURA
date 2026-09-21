"""Trailing-calendar-window forecast baseline."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
import math

from ..data import ForecastDatasetRow
from ..evaluation import (
    CandidatePrediction,
    ForecastTargetType,
    target_value,
)


MOVING_AVERAGE_WINDOW_DAYS = 90
MOVING_AVERAGE_MINIMUM_LABELS = 20


@dataclass(frozen=True, slots=True)
class MovingAverageBaseline:
    """Predict from labels completed in the trailing 90 calendar days."""

    candidate_id: str = "moving_average_90_calendar_days"
    window_days: int = MOVING_AVERAGE_WINDOW_DAYS
    minimum_labels: int = MOVING_AVERAGE_MINIMUM_LABELS

    def __post_init__(self) -> None:
        if type(self.window_days) is not int or self.window_days <= 0:
            raise ValueError("window_days must be a positive integer")
        if type(self.minimum_labels) is not int or self.minimum_labels <= 0:
            raise ValueError("minimum_labels must be a positive integer")

    def predict(
        self,
        *,
        training_rows: Sequence[ForecastDatasetRow],
        evaluation_rows: Sequence[ForecastDatasetRow],
        target_type: ForecastTargetType,
        information_cutoff: date,
    ) -> CandidatePrediction:
        window_start = information_cutoff - timedelta(days=self.window_days)
        completed_rows = tuple(
            row
            for row in training_rows
            if window_start <= row.target.endpoint_date < information_cutoff
        )
        if len(completed_rows) < self.minimum_labels:
            return CandidatePrediction(
                candidate_id=self.candidate_id,
                values=None,
                training_value_count=len(completed_rows),
                warning=(
                    "moving average requires at least "
                    f"{self.minimum_labels} completed labels in the trailing "
                    f"{self.window_days} calendar days"
                ),
            )
        completed_values = tuple(
            target_value(row, target_type) for row in completed_rows
        )
        prediction = math.fsum(completed_values) / len(completed_values)
        if not math.isfinite(prediction):
            raise ValueError("moving average prediction must be finite")
        return CandidatePrediction(
            candidate_id=self.candidate_id,
            values=tuple(prediction for _ in evaluation_rows),
            training_value_count=len(completed_values),
        )
