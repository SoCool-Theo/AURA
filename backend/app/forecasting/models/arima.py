"""Fixed-order ARIMA candidate over the completed 30-day return series."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from typing import ClassVar
import warnings

from statsmodels.tools.sm_exceptions import ConvergenceWarning
from statsmodels.tsa.arima.model import ARIMA

from ..data import ForecastDatasetRow
from ..evaluation import CandidatePrediction, ForecastTargetType
from .base import (
    ForecastModelInputError,
    chronological_return_targets,
    chronological_volatility_targets,
    require_return_target,
    require_volatility_target,
    validated_predictions,
)


ARIMA_CANDIDATE_ID = "arima_1_0_1_v1"
VOLATILITY_ARIMA_CANDIDATE_ID = "volatility_arima_1_0_1_v1"
ARIMA_ORDER = (1, 0, 1)
ARIMA_FIT_CONVERGENCE_WARNING = "arima_fit_convergence_warning"


def _fit_arima_with_warning_metadata(
    training_targets: tuple[float, ...],
) -> tuple[object, bool]:
    """Fit once while capturing only deterministic convergence metadata."""
    captured: list[warnings.WarningMessage] = []
    try:
        with warnings.catch_warnings(record=True) as fit_warnings:
            captured = fit_warnings
            warnings.simplefilter("always", ConvergenceWarning)
            fitted = ARIMA(training_targets, order=ARIMA_ORDER).fit()
    finally:
        for fit_warning in captured:
            if not issubclass(fit_warning.category, ConvergenceWarning):
                warnings.warn_explicit(
                    fit_warning.message,
                    fit_warning.category,
                    fit_warning.filename,
                    fit_warning.lineno,
                )
    convergence_warning = any(
        issubclass(fit_warning.category, ConvergenceWarning)
        for fit_warning in captured
    )
    return fitted, convergence_warning


@dataclass(frozen=True, slots=True)
class ArimaCandidate:
    """Model the chronological ``return_30d`` target series directly."""

    candidate_id: ClassVar[str] = ARIMA_CANDIDATE_ID
    target_type: ClassVar[ForecastTargetType] = ForecastTargetType.RETURN
    order: ClassVar[tuple[int, int, int]] = ARIMA_ORDER

    def predict(
        self,
        *,
        training_rows: Sequence[ForecastDatasetRow],
        evaluation_rows: Sequence[ForecastDatasetRow],
        target_type: ForecastTargetType,
        information_cutoff: date,
    ) -> CandidatePrediction:
        require_return_target(target_type)
        if not evaluation_rows:
            raise ForecastModelInputError("ARIMA evaluation rows cannot be empty")
        evaluation_origins = tuple(
            row.features.origin_date for row in evaluation_rows
        )
        if any(
            current <= previous
            for previous, current in zip(
                evaluation_origins,
                evaluation_origins[1:],
            )
        ):
            raise ForecastModelInputError(
                "ARIMA evaluation rows must be strictly chronological"
            )
        training_targets = chronological_return_targets(
            training_rows=training_rows,
            information_cutoff=information_cutoff,
        )
        try:
            fitted, convergence_warning = _fit_arima_with_warning_metadata(
                training_targets
            )
            values = validated_predictions(
                fitted.forecast(steps=len(evaluation_rows)),
                expected_count=len(evaluation_rows),
            )
        except ForecastModelInputError:
            raise
        except Exception as error:
            return CandidatePrediction(
                candidate_id=self.candidate_id,
                values=None,
                training_value_count=len(training_targets),
                warning=(
                    "ARIMA unavailable for this fold: "
                    f"{type(error).__name__}: {error}"
                ),
            )
        return CandidatePrediction(
            candidate_id=self.candidate_id,
            values=values,
            training_value_count=len(training_targets),
            warning=(
                ARIMA_FIT_CONVERGENCE_WARNING
                if convergence_warning
                else None
            ),
        )


@dataclass(frozen=True, slots=True)
class VolatilityArimaCandidate:
    """Model the chronological realized-volatility target series directly."""

    candidate_id: ClassVar[str] = VOLATILITY_ARIMA_CANDIDATE_ID
    target_type: ClassVar[ForecastTargetType] = ForecastTargetType.VOLATILITY
    order: ClassVar[tuple[int, int, int]] = ARIMA_ORDER

    def predict(
        self,
        *,
        training_rows: Sequence[ForecastDatasetRow],
        evaluation_rows: Sequence[ForecastDatasetRow],
        target_type: ForecastTargetType,
        information_cutoff: date,
    ) -> CandidatePrediction:
        require_volatility_target(target_type)
        if not evaluation_rows:
            raise ForecastModelInputError("ARIMA evaluation rows cannot be empty")
        evaluation_origins = tuple(
            row.features.origin_date for row in evaluation_rows
        )
        if any(
            current <= previous
            for previous, current in zip(
                evaluation_origins,
                evaluation_origins[1:],
            )
        ):
            raise ForecastModelInputError(
                "ARIMA evaluation rows must be strictly chronological"
            )
        training_targets = chronological_volatility_targets(
            training_rows=training_rows,
            information_cutoff=information_cutoff,
        )
        try:
            fitted, convergence_warning = _fit_arima_with_warning_metadata(
                training_targets
            )
            values = validated_predictions(
                fitted.forecast(steps=len(evaluation_rows)),
                expected_count=len(evaluation_rows),
            )
        except ForecastModelInputError:
            raise
        except Exception as error:
            return CandidatePrediction(
                candidate_id=self.candidate_id,
                values=None,
                training_value_count=len(training_targets),
                warning=(
                    "volatility ARIMA unavailable for this fold: "
                    f"{type(error).__name__}: {error}"
                ),
            )
        return CandidatePrediction(
            candidate_id=self.candidate_id,
            values=values,
            training_value_count=len(training_targets),
            warning=(
                ARIMA_FIT_CONVERGENCE_WARNING
                if convergence_warning
                else None
            ),
        )
