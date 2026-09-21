"""Shared validation and feature extraction for return-model candidates."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
import math

import numpy as np

from ..data import ForecastDatasetRow
from ..evaluation import ForecastTargetType
from ..features import FEATURE_NAMES


class ForecastModelInputError(ValueError):
    """Raised when a model adapter receives unsafe fold input."""


def require_return_target(target_type: ForecastTargetType) -> None:
    """Reject target types unsupported by the Phase 4 candidates."""
    if target_type is not ForecastTargetType.RETURN:
        raise ForecastModelInputError(
            "Phase 4 model candidates support only return_30d"
        )


def _feature_vector(row: ForecastDatasetRow) -> tuple[float, ...]:
    values = tuple(float(getattr(row.features, name)) for name in FEATURE_NAMES)
    if len(values) != len(FEATURE_NAMES) or not all(
        math.isfinite(value) for value in values
    ):
        raise ForecastModelInputError(
            "model feature values must be complete and finite"
        )
    return values


def supervised_fold_arrays(
    *,
    training_rows: Sequence[ForecastDatasetRow],
    evaluation_rows: Sequence[ForecastDatasetRow],
    information_cutoff: date,
) -> tuple[
    tuple[tuple[float, ...], ...],
    tuple[float, ...],
    tuple[tuple[float, ...], ...],
]:
    """Build ordered training features/labels and evaluation features only."""
    if type(information_cutoff) is not date:
        raise ForecastModelInputError("information_cutoff must be a date")
    if not training_rows:
        raise ForecastModelInputError("model training rows cannot be empty")
    if not evaluation_rows:
        raise ForecastModelInputError("model evaluation rows cannot be empty")
    if any(
        row.target.endpoint_date >= information_cutoff for row in training_rows
    ):
        raise ForecastModelInputError(
            "training target endpoints must be before the information cutoff"
        )

    training_origins = tuple(
        row.features.origin_date for row in training_rows
    )
    evaluation_origins = tuple(
        row.features.origin_date for row in evaluation_rows
    )
    if any(
        current <= previous
        for previous, current in zip(training_origins, training_origins[1:])
    ):
        raise ForecastModelInputError(
            "model training rows must be strictly chronological"
        )
    if any(
        current <= previous
        for previous, current in zip(evaluation_origins, evaluation_origins[1:])
    ):
        raise ForecastModelInputError(
            "model evaluation rows must be strictly chronological"
        )

    training_features = tuple(_feature_vector(row) for row in training_rows)
    training_targets = tuple(
        float(row.target.return_30d) for row in training_rows
    )
    if not all(math.isfinite(value) for value in training_targets):
        raise ForecastModelInputError("model training targets must be finite")
    evaluation_features = tuple(
        _feature_vector(row) for row in evaluation_rows
    )
    return training_features, training_targets, evaluation_features


def chronological_return_targets(
    *,
    training_rows: Sequence[ForecastDatasetRow],
    information_cutoff: date,
) -> tuple[float, ...]:
    """Return endpoint-purged targets ordered by endpoint then origin date."""
    if type(information_cutoff) is not date:
        raise ForecastModelInputError("information_cutoff must be a date")
    if not training_rows:
        raise ForecastModelInputError("ARIMA training rows cannot be empty")
    if any(
        row.target.endpoint_date >= information_cutoff for row in training_rows
    ):
        raise ForecastModelInputError(
            "training target endpoints must be before the information cutoff"
        )
    ordered = tuple(
        sorted(
            training_rows,
            key=lambda row: (
                row.target.endpoint_date,
                row.features.origin_date,
            ),
        )
    )
    values = tuple(float(row.target.return_30d) for row in ordered)
    if not all(math.isfinite(value) for value in values):
        raise ForecastModelInputError("ARIMA training targets must be finite")
    return values


def validated_predictions(
    values: object,
    *,
    expected_count: int,
) -> tuple[float, ...]:
    """Normalize estimator output while rejecting shape and finite failures."""
    try:
        array = np.asarray(values, dtype=float)
    except (TypeError, ValueError, OverflowError) as error:
        raise ForecastModelInputError(
            "model predictions must be a one-dimensional numeric sequence"
        ) from error
    if array.ndim != 1:
        raise ForecastModelInputError(
            "model predictions must be a one-dimensional numeric sequence"
        )
    predictions = tuple(float(value) for value in array)
    if len(predictions) != expected_count:
        raise ForecastModelInputError(
            "model prediction count does not match evaluation rows"
        )
    if not all(math.isfinite(value) for value in predictions):
        raise ForecastModelInputError("model predictions must be finite")
    return predictions
