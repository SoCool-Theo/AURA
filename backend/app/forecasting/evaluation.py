"""Candidate-agnostic chronological forecast evaluation."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
import math
from numbers import Real
from typing import Protocol

from .data import ForecastDataset, ForecastDatasetRow
from .metrics import (
    SafeMapeResult,
    directional_accuracy,
    mean_absolute_error,
    root_mean_squared_error,
    safe_return_mape,
)
from .splits import (
    ChronologicalEvaluationPlan,
    FoldPurpose,
    slice_dataset_for_fold,
)


class ForecastTargetType(StrEnum):
    """Phase 2 target columns supported by the common evaluator."""

    RETURN = "return_30d"
    VOLATILITY = "realized_volatility_30d"


@dataclass(frozen=True, slots=True)
class CandidatePrediction:
    """One candidate's fold predictions or explicit unavailability."""

    candidate_id: str
    values: tuple[float, ...] | None
    training_value_count: int
    warning: str | None = None

    def __post_init__(self) -> None:
        if not self.candidate_id:
            raise ValueError("candidate_id cannot be empty")
        if type(self.training_value_count) is not int or self.training_value_count < 0:
            raise ValueError("training_value_count must be a non-negative integer")
        if self.values is not None and not all(
            isinstance(value, Real)
            and not isinstance(value, bool)
            and math.isfinite(float(value))
            for value in self.values
        ):
            raise ValueError("candidate predictions must be finite real numbers")

    @property
    def available(self) -> bool:
        return self.values is not None


class ForecastCandidate(Protocol):
    """Small internal boundary shared by baselines and future model adapters."""

    candidate_id: str

    def predict(
        self,
        *,
        training_rows: Sequence[ForecastDatasetRow],
        evaluation_rows: Sequence[ForecastDatasetRow],
        target_type: ForecastTargetType,
        information_cutoff: date,
    ) -> CandidatePrediction:
        """Return predictions frozen at the explicit information cutoff."""


@dataclass(frozen=True, slots=True)
class ForecastEvaluationResult:
    """Internal finite metrics and provenance for one candidate/fold/target."""

    symbol: str
    target_type: ForecastTargetType
    candidate_id: str
    fold_id: str
    fold_purpose: FoldPurpose
    training_cutoff: date
    evaluation_origin_start: date
    evaluation_origin_end: date
    training_observation_count: int
    candidate_training_value_count: int
    evaluated_observation_count: int
    prediction_available: bool
    mae: float | None
    rmse: float | None
    directional_accuracy: float | None
    directional_evaluated_count: int | None
    return_mape: SafeMapeResult | None
    warning: str | None

    def __post_init__(self) -> None:
        for value in (self.mae, self.rmse, self.directional_accuracy):
            if value is not None and not math.isfinite(value):
                raise ValueError("evaluation metrics must be finite when available")
        for count in (
            self.training_observation_count,
            self.candidate_training_value_count,
            self.evaluated_observation_count,
        ):
            if type(count) is not int or count < 0:
                raise ValueError("evaluation counts must be non-negative integers")


def target_value(
    row: ForecastDatasetRow,
    target_type: ForecastTargetType,
) -> float:
    """Return one target without mixing return and volatility values."""
    if target_type is ForecastTargetType.RETURN:
        return row.target.return_30d
    if target_type is ForecastTargetType.VOLATILITY:
        return row.target.realized_volatility_30d
    raise ValueError(f"unsupported forecast target type: {target_type}")


def _unavailable_result(
    *,
    dataset: ForecastDataset,
    target_type: ForecastTargetType,
    candidate_id: str,
    fold_id: str,
    fold_purpose: FoldPurpose,
    training_cutoff: date,
    evaluation_origin_start: date,
    evaluation_origin_end: date,
    training_count: int,
    candidate_training_count: int,
    evaluation_count: int,
    warning: str,
) -> ForecastEvaluationResult:
    return ForecastEvaluationResult(
        symbol=dataset.symbol,
        target_type=target_type,
        candidate_id=candidate_id,
        fold_id=fold_id,
        fold_purpose=fold_purpose,
        training_cutoff=training_cutoff,
        evaluation_origin_start=evaluation_origin_start,
        evaluation_origin_end=evaluation_origin_end,
        training_observation_count=training_count,
        candidate_training_value_count=candidate_training_count,
        evaluated_observation_count=evaluation_count,
        prediction_available=False,
        mae=None,
        rmse=None,
        directional_accuracy=None,
        directional_evaluated_count=None,
        return_mape=None,
        warning=warning,
    )


def evaluate_candidate(
    *,
    dataset: ForecastDataset,
    plan: ChronologicalEvaluationPlan,
    target_type: ForecastTargetType,
    candidate: ForecastCandidate,
) -> tuple[ForecastEvaluationResult, ...]:
    """Evaluate one candidate under identical purged chronological folds."""
    results: list[ForecastEvaluationResult] = []
    for fold in plan.folds:
        fold_slice = slice_dataset_for_fold(
            dataset,
            fold,
            minimum_training_origins=plan.config.minimum_training_origins,
        )
        training_count = len(fold_slice.training_rows)
        evaluation_count = len(fold_slice.evaluation_rows)
        common = {
            "dataset": dataset,
            "target_type": target_type,
            "candidate_id": candidate.candidate_id,
            "fold_id": fold.fold_id,
            "fold_purpose": fold.purpose,
            "training_cutoff": fold.training_cutoff,
            "evaluation_origin_start": fold.origin_start,
            "evaluation_origin_end": fold.origin_end,
            "training_count": training_count,
            "evaluation_count": evaluation_count,
        }
        if not fold_slice.training_eligible:
            results.append(
                _unavailable_result(
                    **common,
                    candidate_training_count=training_count,
                    warning=(
                        "minimum training history not met: "
                        f"{training_count} < {plan.config.minimum_training_origins}"
                    ),
                )
            )
            continue
        if not fold_slice.evaluation_rows:
            results.append(
                _unavailable_result(
                    **common,
                    candidate_training_count=0,
                    warning="fold contains no label-complete evaluation origins",
                )
            )
            continue

        prediction = candidate.predict(
            training_rows=fold_slice.training_rows,
            evaluation_rows=fold_slice.evaluation_rows,
            target_type=target_type,
            information_cutoff=fold.training_cutoff,
        )
        if prediction.candidate_id != candidate.candidate_id:
            raise ValueError("candidate prediction identifier mismatch")
        if not prediction.available:
            results.append(
                _unavailable_result(
                    **common,
                    candidate_training_count=prediction.training_value_count,
                    warning=prediction.warning or "candidate prediction unavailable",
                )
            )
            continue
        assert prediction.values is not None
        if len(prediction.values) != evaluation_count:
            raise ValueError("candidate prediction count does not match fold rows")
        if not all(math.isfinite(value) for value in prediction.values):
            raise ValueError("candidate predictions must be finite")

        actual = tuple(
            target_value(row, target_type)
            for row in fold_slice.evaluation_rows
        )
        directional_result = (
            directional_accuracy(actual, prediction.values)
            if target_type is ForecastTargetType.RETURN
            else None
        )
        mape_result = (
            safe_return_mape(actual, prediction.values)
            if target_type is ForecastTargetType.RETURN
            else None
        )
        results.append(
            ForecastEvaluationResult(
                symbol=dataset.symbol,
                target_type=target_type,
                candidate_id=candidate.candidate_id,
                fold_id=fold.fold_id,
                fold_purpose=fold.purpose,
                training_cutoff=fold.training_cutoff,
                evaluation_origin_start=fold.origin_start,
                evaluation_origin_end=fold.origin_end,
                training_observation_count=training_count,
                candidate_training_value_count=prediction.training_value_count,
                evaluated_observation_count=evaluation_count,
                prediction_available=True,
                mae=mean_absolute_error(actual, prediction.values),
                rmse=root_mean_squared_error(actual, prediction.values),
                directional_accuracy=(
                    None if directional_result is None else directional_result.value
                ),
                directional_evaluated_count=(
                    None
                    if directional_result is None
                    else directional_result.evaluated_count
                ),
                return_mape=mape_result,
                warning=prediction.warning,
            )
        )
    return tuple(results)
