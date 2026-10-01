"""Frozen-candidate calibration, final testing, and deployment fitting."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
import math

from .baselines import HistoricalMeanBaseline, MovingAverageBaseline
from .baselines.moving_average import (
    MOVING_AVERAGE_MINIMUM_LABELS,
    MOVING_AVERAGE_WINDOW_DAYS,
)
from .data import ForecastDataset, ForecastDatasetRow
from .evaluation import (
    CandidatePrediction,
    ForecastCandidate,
    ForecastTargetType,
    target_value,
)
from .features import FEATURE_NAMES
from .metrics import (
    directional_accuracy,
    mean_absolute_error,
    root_mean_squared_error,
)
from .models import (
    ARIMA_CANDIDATE_ID,
    ARIMA_FIT_CONVERGENCE_WARNING,
    ARIMA_ORDER,
    LINEAR_REGRESSION_CANDIDATE_ID,
    RANDOM_FOREST_CANDIDATE_ID,
    RANDOM_FOREST_PARAMETERS,
    VOLATILITY_ARIMA_CANDIDATE_ID,
    VOLATILITY_LINEAR_REGRESSION_CANDIDATE_ID,
    VOLATILITY_RANDOM_FOREST_CANDIDATE_ID,
    ArimaCandidate,
    LinearRegressionCandidate,
    RandomForestCandidate,
    VolatilityArimaCandidate,
    VolatilityLinearRegressionCandidate,
    VolatilityRandomForestCandidate,
    build_linear_regression_pipeline,
    build_random_forest_regressor,
)
from .models.arima import _fit_arima_with_warning_metadata
from .models.base import validated_predictions
from .selection import (
    HISTORICAL_AVERAGE_CANDIDATE_ID,
    MOVING_AVERAGE_CANDIDATE_ID,
)
from .selection_manifest import FrozenSelectionRecord
from .splits import (
    ChronologicalEvaluationPlan,
    EvaluationFold,
    FoldPurpose,
    slice_dataset_for_fold,
)


CALIBRATION_MINIMUM_OBSERVATIONS = 60
NOMINAL_INTERVAL_COVERAGE = 0.80
LOWER_RESIDUAL_QUANTILE = 0.10
UPPER_RESIDUAL_QUANTILE = 0.90


class ForecastFinalizationError(ValueError):
    """Raised when a frozen selection cannot be finalized safely."""


@dataclass(frozen=True, slots=True)
class FoldPredictionEvaluation:
    symbol: str
    target_type: ForecastTargetType
    candidate_id: str
    fold_id: str
    fold_purpose: FoldPurpose
    training_observation_count: int
    candidate_training_value_count: int
    evaluated_observation_count: int
    actual_values: tuple[float, ...]
    prediction_values: tuple[float, ...]
    mae: float
    rmse: float
    directional_accuracy: float | None
    negative_prediction_clipped_count: int | None
    warning: str | None


@dataclass(frozen=True, slots=True)
class CalibrationResult:
    symbol: str
    target_type: ForecastTargetType
    selected_candidate_id: str
    fold_id: str
    observation_count: int
    residual_q10: float
    residual_q90: float
    mae: float
    rmse: float
    negative_prediction_clipped_count: int | None
    warning: str | None


@dataclass(frozen=True, slots=True)
class FinalTestResult:
    symbol: str
    target_type: ForecastTargetType
    selected_candidate_id: str
    fold_id: str
    observation_count: int
    mae: float
    rmse: float
    directional_accuracy: float | None
    negative_prediction_clipped_count: int | None
    warning: str | None


@dataclass(slots=True)
class ForecastArtifactModel:
    """Serializable common wrapper for baseline and complex fitted models."""

    candidate_id: str
    target_type: ForecastTargetType
    model_family: str
    fitted_model: object | None = None
    constant_prediction: float | None = None

    def predict(
        self,
        *,
        steps: int,
        feature_matrix: Sequence[Sequence[float]] | None = None,
    ) -> tuple[float, ...]:
        if type(steps) is not int or steps <= 0:
            raise ForecastFinalizationError("prediction steps must be positive")
        if self.model_family in {"historical_average", "moving_average"}:
            if self.constant_prediction is None:
                raise ForecastFinalizationError(
                    "baseline artifact is missing its prediction value"
                )
            raw = tuple(self.constant_prediction for _ in range(steps))
        elif self.model_family == "arima":
            if self.fitted_model is None:
                raise ForecastFinalizationError("ARIMA artifact is not fitted")
            raw = validated_predictions(
                self.fitted_model.forecast(steps=steps),
                expected_count=steps,
            )
        else:
            if self.fitted_model is None or feature_matrix is None:
                raise ForecastFinalizationError(
                    "feature-model artifact requires fitted state and features"
                )
            if len(feature_matrix) != steps:
                raise ForecastFinalizationError(
                    "feature rows must match prediction steps"
                )
            raw = validated_predictions(
                self.fitted_model.predict(feature_matrix),
                expected_count=steps,
            )
        if self.target_type is ForecastTargetType.VOLATILITY:
            return tuple(max(value, 0.0) for value in raw)
        return raw


@dataclass(frozen=True, slots=True)
class DeploymentTrainingResult:
    symbol: str
    target_type: ForecastTargetType
    selected_candidate_id: str
    model_family: str
    model_parameters: dict[str, object]
    artifact_model: ForecastArtifactModel
    training_row_count: int
    training_origin_min: date
    training_origin_max: date
    warning: str | None


def candidate_for_selection(record: FrozenSelectionRecord) -> ForecastCandidate:
    mapping: dict[str, ForecastCandidate] = {
        HISTORICAL_AVERAGE_CANDIDATE_ID: HistoricalMeanBaseline(),
        MOVING_AVERAGE_CANDIDATE_ID: MovingAverageBaseline(),
        LINEAR_REGRESSION_CANDIDATE_ID: LinearRegressionCandidate(),
        ARIMA_CANDIDATE_ID: ArimaCandidate(),
        RANDOM_FOREST_CANDIDATE_ID: RandomForestCandidate(),
        VOLATILITY_LINEAR_REGRESSION_CANDIDATE_ID: (
            VolatilityLinearRegressionCandidate()
        ),
        VOLATILITY_ARIMA_CANDIDATE_ID: VolatilityArimaCandidate(),
        VOLATILITY_RANDOM_FOREST_CANDIDATE_ID: (
            VolatilityRandomForestCandidate()
        ),
    }
    try:
        candidate = mapping[record.selected_candidate_id]
    except KeyError as error:
        raise ForecastFinalizationError(
            f"unsupported frozen candidate: {record.selected_candidate_id}"
        ) from error
    candidate_target = getattr(candidate, "target_type", None)
    if (
        candidate_target is not None
        and candidate_target is not record.target_type
    ):
        raise ForecastFinalizationError(
            "frozen candidate is incompatible with its target"
        )
    return candidate


def _fold_for_purpose(
    plan: ChronologicalEvaluationPlan,
    purpose: FoldPurpose,
) -> EvaluationFold:
    matches = tuple(fold for fold in plan.folds if fold.purpose is purpose)
    if len(matches) != 1:
        raise ForecastFinalizationError(
            f"evaluation plan must contain exactly one {purpose.value} fold"
        )
    return matches[0]


def evaluate_frozen_selection_fold(
    *,
    dataset: ForecastDataset,
    plan: ChronologicalEvaluationPlan,
    selection: FrozenSelectionRecord,
    purpose: FoldPurpose,
    candidate: ForecastCandidate | None = None,
) -> FoldPredictionEvaluation:
    """Predict first, then access actual targets strictly for scoring."""
    if purpose not in {FoldPurpose.CALIBRATION, FoldPurpose.FINAL_TEST}:
        raise ForecastFinalizationError(
            "finalization accepts only calibration or final-test folds"
        )
    if dataset.symbol != selection.symbol:
        raise ForecastFinalizationError("dataset and selection symbol mismatch")
    fold = _fold_for_purpose(plan, purpose)
    fold_slice = slice_dataset_for_fold(
        dataset,
        fold,
        minimum_training_origins=plan.config.minimum_training_origins,
    )
    if not fold_slice.training_eligible:
        raise ForecastFinalizationError(
            "minimum label-complete training history is not met"
        )
    if not fold_slice.evaluation_rows:
        raise ForecastFinalizationError("evaluation fold contains no usable rows")
    approved_candidate = (
        candidate_for_selection(selection) if candidate is None else candidate
    )
    if approved_candidate.candidate_id != selection.selected_candidate_id:
        raise ForecastFinalizationError("candidate differs from frozen selection")
    prediction: CandidatePrediction = approved_candidate.predict(
        training_rows=fold_slice.training_rows,
        evaluation_rows=fold_slice.evaluation_rows,
        target_type=selection.target_type,
        information_cutoff=fold.training_cutoff,
    )
    if not prediction.available or prediction.values is None:
        raise ForecastFinalizationError(
            prediction.warning or "frozen candidate prediction is unavailable"
        )
    raw_predictions = prediction.values
    if len(raw_predictions) != len(fold_slice.evaluation_rows):
        raise ForecastFinalizationError("prediction count mismatch")
    if not all(math.isfinite(value) for value in raw_predictions):
        raise ForecastFinalizationError("predictions must be finite")
    clipped_count: int | None = None
    final_predictions = raw_predictions
    if selection.target_type is ForecastTargetType.VOLATILITY:
        clipped_count = sum(value < 0.0 for value in raw_predictions)
        final_predictions = tuple(max(value, 0.0) for value in raw_predictions)

    actual_values = tuple(
        target_value(row, selection.target_type)
        for row in fold_slice.evaluation_rows
    )
    if not all(math.isfinite(value) for value in actual_values):
        raise ForecastFinalizationError("actual targets must be finite")
    if (
        selection.target_type is ForecastTargetType.VOLATILITY
        and any(value < 0.0 for value in actual_values)
    ):
        raise ForecastFinalizationError(
            "realized-volatility targets must be non-negative"
        )
    directional = (
        directional_accuracy(actual_values, final_predictions).value
        if selection.target_type is ForecastTargetType.RETURN
        else None
    )
    return FoldPredictionEvaluation(
        symbol=dataset.symbol,
        target_type=selection.target_type,
        candidate_id=selection.selected_candidate_id,
        fold_id=fold.fold_id,
        fold_purpose=fold.purpose,
        training_observation_count=len(fold_slice.training_rows),
        candidate_training_value_count=prediction.training_value_count,
        evaluated_observation_count=len(fold_slice.evaluation_rows),
        actual_values=actual_values,
        prediction_values=final_predictions,
        mae=mean_absolute_error(actual_values, final_predictions),
        rmse=root_mean_squared_error(actual_values, final_predictions),
        directional_accuracy=directional,
        negative_prediction_clipped_count=clipped_count,
        warning=prediction.warning,
    )


def _linear_quantile(values: Sequence[float], quantile: float) -> float:
    if not values:
        raise ForecastFinalizationError("quantile values cannot be empty")
    if not 0.0 <= quantile <= 1.0:
        raise ForecastFinalizationError("quantile must be between zero and one")
    ordered = tuple(sorted(float(value) for value in values))
    if not all(math.isfinite(value) for value in ordered):
        raise ForecastFinalizationError("quantile values must be finite")
    position = (len(ordered) - 1) * quantile
    lower_index = math.floor(position)
    upper_index = math.ceil(position)
    if lower_index == upper_index:
        return ordered[lower_index]
    weight = position - lower_index
    return ordered[lower_index] * (1.0 - weight) + ordered[upper_index] * weight


def calibrate_frozen_selection(
    *,
    dataset: ForecastDataset,
    plan: ChronologicalEvaluationPlan,
    selection: FrozenSelectionRecord,
    candidate: ForecastCandidate | None = None,
) -> CalibrationResult:
    evaluated = evaluate_frozen_selection_fold(
        dataset=dataset,
        plan=plan,
        selection=selection,
        purpose=FoldPurpose.CALIBRATION,
        candidate=candidate,
    )
    if evaluated.evaluated_observation_count < CALIBRATION_MINIMUM_OBSERVATIONS:
        raise ForecastFinalizationError(
            "calibration requires at least "
            f"{CALIBRATION_MINIMUM_OBSERVATIONS} usable residuals"
        )
    residuals = tuple(
        actual - predicted
        for actual, predicted in zip(
            evaluated.actual_values,
            evaluated.prediction_values,
            strict=True,
        )
    )
    return CalibrationResult(
        symbol=evaluated.symbol,
        target_type=evaluated.target_type,
        selected_candidate_id=evaluated.candidate_id,
        fold_id=evaluated.fold_id,
        observation_count=len(residuals),
        residual_q10=_linear_quantile(residuals, LOWER_RESIDUAL_QUANTILE),
        residual_q90=_linear_quantile(residuals, UPPER_RESIDUAL_QUANTILE),
        mae=evaluated.mae,
        rmse=evaluated.rmse,
        negative_prediction_clipped_count=(
            evaluated.negative_prediction_clipped_count
        ),
        warning=evaluated.warning,
    )


def evaluate_frozen_final_test(
    *,
    dataset: ForecastDataset,
    plan: ChronologicalEvaluationPlan,
    selection: FrozenSelectionRecord,
    candidate: ForecastCandidate | None = None,
) -> FinalTestResult:
    evaluated = evaluate_frozen_selection_fold(
        dataset=dataset,
        plan=plan,
        selection=selection,
        purpose=FoldPurpose.FINAL_TEST,
        candidate=candidate,
    )
    return FinalTestResult(
        symbol=evaluated.symbol,
        target_type=evaluated.target_type,
        selected_candidate_id=evaluated.candidate_id,
        fold_id=evaluated.fold_id,
        observation_count=evaluated.evaluated_observation_count,
        mae=evaluated.mae,
        rmse=evaluated.rmse,
        directional_accuracy=evaluated.directional_accuracy,
        negative_prediction_clipped_count=(
            evaluated.negative_prediction_clipped_count
        ),
        warning=evaluated.warning,
    )


def prediction_interval(
    *,
    point_prediction: float,
    residual_q10: float,
    residual_q90: float,
    target_type: ForecastTargetType,
) -> tuple[float, float]:
    values = (point_prediction, residual_q10, residual_q90)
    if not all(math.isfinite(value) for value in values):
        raise ForecastFinalizationError("interval inputs must be finite")
    if residual_q10 > residual_q90:
        raise ForecastFinalizationError("residual quantiles are reversed")
    lower = point_prediction + residual_q10
    upper = point_prediction + residual_q90
    if target_type is ForecastTargetType.VOLATILITY:
        lower = max(lower, 0.0)
    if not (math.isfinite(lower) and math.isfinite(upper)):
        raise ForecastFinalizationError("interval bounds must be finite")
    return lower, upper


def _model_family_and_parameters(
    candidate_id: str,
) -> tuple[str, dict[str, object]]:
    if candidate_id == HISTORICAL_AVERAGE_CANDIDATE_ID:
        return "historical_average", {"aggregation": "all_completed_labels"}
    if candidate_id == MOVING_AVERAGE_CANDIDATE_ID:
        return "moving_average", {
            "window_days": MOVING_AVERAGE_WINDOW_DAYS,
            "minimum_labels": MOVING_AVERAGE_MINIMUM_LABELS,
        }
    if candidate_id in {
        LINEAR_REGRESSION_CANDIDATE_ID,
        VOLATILITY_LINEAR_REGRESSION_CANDIDATE_ID,
    }:
        return "linear_regression", {
            "pipeline": ["StandardScaler", "LinearRegression"]
        }
    if candidate_id in {ARIMA_CANDIDATE_ID, VOLATILITY_ARIMA_CANDIDATE_ID}:
        return "arima", {"order": list(ARIMA_ORDER)}
    if candidate_id in {
        RANDOM_FOREST_CANDIDATE_ID,
        VOLATILITY_RANDOM_FOREST_CANDIDATE_ID,
    }:
        return "random_forest", dict(RANDOM_FOREST_PARAMETERS)
    raise ForecastFinalizationError(f"unsupported candidate: {candidate_id}")


def _feature_matrix(
    rows: Sequence[ForecastDatasetRow],
) -> tuple[tuple[float, ...], ...]:
    matrix = tuple(
        tuple(float(getattr(row.features, name)) for name in FEATURE_NAMES)
        for row in rows
    )
    if not all(math.isfinite(value) for row in matrix for value in row):
        raise ForecastFinalizationError("deployment features must be finite")
    return matrix


def train_deployment_artifact(
    *,
    dataset: ForecastDataset,
    selection: FrozenSelectionRecord,
    evaluation_cutoff: date,
) -> DeploymentTrainingResult:
    """Fit a frozen candidate on all labels complete through the cutoff."""
    if dataset.symbol != selection.symbol:
        raise ForecastFinalizationError("dataset and selection symbol mismatch")
    if evaluation_cutoff != selection.evaluation_cutoff:
        raise ForecastFinalizationError("deployment cutoff is not frozen")
    information_cutoff = evaluation_cutoff + timedelta(days=1)
    eligible_rows = tuple(
        row
        for row in dataset.rows
        if row.target.endpoint_date < information_cutoff
    )
    if not eligible_rows:
        raise ForecastFinalizationError(
            "deployment training has no label-complete rows"
        )
    targets = tuple(
        float(target_value(row, selection.target_type)) for row in eligible_rows
    )
    if not all(math.isfinite(value) for value in targets):
        raise ForecastFinalizationError("deployment targets must be finite")
    if (
        selection.target_type is ForecastTargetType.VOLATILITY
        and any(value < 0.0 for value in targets)
    ):
        raise ForecastFinalizationError(
            "deployment volatility targets must be non-negative"
        )

    family, parameters = _model_family_and_parameters(
        selection.selected_candidate_id
    )
    fitted_model: object | None = None
    constant_prediction: float | None = None
    training_rows = eligible_rows
    warning: str | None = None
    if family == "historical_average":
        constant_prediction = math.fsum(targets) / len(targets)
    elif family == "moving_average":
        window_start = information_cutoff - timedelta(
            days=MOVING_AVERAGE_WINDOW_DAYS
        )
        window_rows = tuple(
            row
            for row in eligible_rows
            if window_start <= row.target.endpoint_date < information_cutoff
        )
        if len(window_rows) < MOVING_AVERAGE_MINIMUM_LABELS:
            raise ForecastFinalizationError(
                "deployment moving average has insufficient completed labels"
            )
        training_rows = window_rows
        window_targets = tuple(
            float(target_value(row, selection.target_type))
            for row in window_rows
        )
        constant_prediction = math.fsum(window_targets) / len(window_targets)
    elif family == "linear_regression":
        fitted_model = build_linear_regression_pipeline()
        fitted_model.fit(_feature_matrix(eligible_rows), targets)
    elif family == "random_forest":
        fitted_model = build_random_forest_regressor()
        fitted_model.fit(_feature_matrix(eligible_rows), targets)
    elif family == "arima":
        ordered = tuple(
            sorted(
                eligible_rows,
                key=lambda row: (
                    row.target.endpoint_date,
                    row.features.origin_date,
                ),
            )
        )
        training_rows = ordered
        ordered_targets = tuple(
            float(target_value(row, selection.target_type)) for row in ordered
        )
        fitted_model, convergence_warning = _fit_arima_with_warning_metadata(
            ordered_targets
        )
        warning = (
            ARIMA_FIT_CONVERGENCE_WARNING if convergence_warning else None
        )
    if constant_prediction is not None and not math.isfinite(constant_prediction):
        raise ForecastFinalizationError(
            "deployment baseline prediction must be finite"
        )
    origins = tuple(row.features.origin_date for row in training_rows)
    artifact_model = ForecastArtifactModel(
        candidate_id=selection.selected_candidate_id,
        target_type=selection.target_type,
        model_family=family,
        fitted_model=fitted_model,
        constant_prediction=constant_prediction,
    )
    validation_features = (
        _feature_matrix((eligible_rows[-1],))
        if family in {"linear_regression", "random_forest"}
        else None
    )
    artifact_model.predict(
        steps=1,
        feature_matrix=validation_features,
    )
    return DeploymentTrainingResult(
        symbol=dataset.symbol,
        target_type=selection.target_type,
        selected_candidate_id=selection.selected_candidate_id,
        model_family=family,
        model_parameters=parameters,
        artifact_model=artifact_model,
        training_row_count=len(training_rows),
        training_origin_min=min(origins),
        training_origin_max=max(origins),
        warning=warning,
    )
