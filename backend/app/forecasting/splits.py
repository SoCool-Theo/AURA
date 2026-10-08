"""Date-driven chronological folds with endpoint-based training purging."""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from .data import (
    MIN_LABEL_COMPLETE_TRAINING_ORIGINS,
    ForecastDataset,
    ForecastDatasetRow,
)


class FoldPurpose(StrEnum):
    """Approved uses for chronological forecast-evaluation periods."""

    SELECTION = "selection"
    CALIBRATION = "calibration"
    FINAL_TEST = "final_test"


@dataclass(frozen=True, slots=True)
class EvaluationPlanConfig:
    """Calendar configuration for one deterministic evaluation plan."""

    evaluation_end_exclusive: date
    selection_fold_count: int = 5
    selection_fold_months: int = 6
    calibration_months: int = 6
    final_test_months: int = 12
    minimum_training_origins: int = MIN_LABEL_COMPLETE_TRAINING_ORIGINS

    def __post_init__(self) -> None:
        if type(self.evaluation_end_exclusive) is not date:
            raise TypeError("evaluation_end_exclusive must be a date")
        for name in (
            "selection_fold_count",
            "selection_fold_months",
            "calibration_months",
            "final_test_months",
            "minimum_training_origins",
        ):
            value = getattr(self, name)
            if type(value) is not int or value <= 0:
                raise ValueError(f"{name} must be a positive integer")


@dataclass(frozen=True, slots=True)
class EvaluationFold:
    """One non-overlapping half-open forecast-origin interval."""

    fold_id: str
    purpose: FoldPurpose
    origin_start: date
    origin_end: date

    def __post_init__(self) -> None:
        if not self.fold_id:
            raise ValueError("fold_id cannot be empty")
        if self.origin_start >= self.origin_end:
            raise ValueError("fold origin_start must be before origin_end")

    @property
    def training_cutoff(self) -> date:
        """Return the exclusive information boundary for training labels."""
        return self.origin_start


@dataclass(frozen=True, slots=True)
class ChronologicalEvaluationPlan:
    """Ordered folds generated from explicit calendar configuration."""

    config: EvaluationPlanConfig
    folds: tuple[EvaluationFold, ...]


@dataclass(frozen=True, slots=True)
class FoldDatasetSlice:
    """Purged training rows and evaluation rows for one symbol/fold."""

    symbol: str
    fold: EvaluationFold
    training_rows: tuple[ForecastDatasetRow, ...]
    evaluation_rows: tuple[ForecastDatasetRow, ...]
    minimum_training_origins: int
    training_eligible: bool


def _shift_months(anchor: date, months: int) -> date:
    """Shift from one common anchor, clamping only invalid month-end days."""
    month_index = anchor.year * 12 + (anchor.month - 1) + months
    year, zero_based_month = divmod(month_index, 12)
    month = zero_based_month + 1
    day = min(anchor.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def build_chronological_plan(
    config: EvaluationPlanConfig,
) -> ChronologicalEvaluationPlan:
    """Build selection, calibration, and final-test half-open folds."""
    selection_total_months = (
        config.selection_fold_count * config.selection_fold_months
    )
    after_selection_months = (
        config.calibration_months + config.final_test_months
    )
    total_months = selection_total_months + after_selection_months
    folds: list[EvaluationFold] = []

    for index in range(config.selection_fold_count):
        start_offset = -total_months + index * config.selection_fold_months
        end_offset = start_offset + config.selection_fold_months
        folds.append(
            EvaluationFold(
                fold_id=f"selection-{index + 1:02d}",
                purpose=FoldPurpose.SELECTION,
                origin_start=_shift_months(
                    config.evaluation_end_exclusive,
                    start_offset,
                ),
                origin_end=_shift_months(
                    config.evaluation_end_exclusive,
                    end_offset,
                ),
            )
        )

    calibration_start = _shift_months(
        config.evaluation_end_exclusive,
        -after_selection_months,
    )
    final_test_start = _shift_months(
        config.evaluation_end_exclusive,
        -config.final_test_months,
    )
    folds.extend(
        (
            EvaluationFold(
                fold_id="calibration-01",
                purpose=FoldPurpose.CALIBRATION,
                origin_start=calibration_start,
                origin_end=final_test_start,
            ),
            EvaluationFold(
                fold_id="final-test-01",
                purpose=FoldPurpose.FINAL_TEST,
                origin_start=final_test_start,
                origin_end=config.evaluation_end_exclusive,
            ),
        )
    )

    for previous, current in zip(folds, folds[1:]):
        if previous.origin_end != current.origin_start:
            raise RuntimeError("chronological evaluation folds are not contiguous")
    return ChronologicalEvaluationPlan(config=config, folds=tuple(folds))


def slice_dataset_for_fold(
    dataset: ForecastDataset,
    fold: EvaluationFold,
    *,
    minimum_training_origins: int = MIN_LABEL_COMPLETE_TRAINING_ORIGINS,
) -> FoldDatasetSlice:
    """Return endpoint-purged training rows and half-open evaluation rows.

    A training label is usable only when its endpoint is strictly before the
    fold start. An origin before the fold start is therefore still excluded
    when its target completes on or after that boundary.
    """
    if type(minimum_training_origins) is not int or minimum_training_origins <= 0:
        raise ValueError("minimum_training_origins must be a positive integer")

    training_rows = tuple(
        row
        for row in dataset.rows
        if row.target.endpoint_date < fold.origin_start
    )
    evaluation_rows = tuple(
        row
        for row in dataset.rows
        if fold.origin_start <= row.features.origin_date < fold.origin_end
    )
    return FoldDatasetSlice(
        symbol=dataset.symbol,
        fold=fold,
        training_rows=training_rows,
        evaluation_rows=evaluation_rows,
        minimum_training_origins=minimum_training_origins,
        training_eligible=len(training_rows) >= minimum_training_origins,
    )
