"""Selection-fold-only comparison policy for Phase 4 return candidates."""

from __future__ import annotations

from dataclasses import dataclass
import math

from .baselines import HistoricalMeanBaseline, MovingAverageBaseline
from .evaluation import ForecastEvaluationResult, ForecastTargetType
from .models import (
    ARIMA_CANDIDATE_ID,
    LINEAR_REGRESSION_CANDIDATE_ID,
    RANDOM_FOREST_CANDIDATE_ID,
)
from .splits import FoldPurpose


MINIMUM_COMPLEX_MODEL_IMPROVEMENT_PERCENT = 5.0
PRACTICAL_TIE_PERCENT = 1.0
HISTORICAL_AVERAGE_CANDIDATE_ID = HistoricalMeanBaseline().candidate_id
MOVING_AVERAGE_CANDIDATE_ID = MovingAverageBaseline().candidate_id
CANDIDATE_SIMPLICITY_ORDER: tuple[str, ...] = (
    HISTORICAL_AVERAGE_CANDIDATE_ID,
    MOVING_AVERAGE_CANDIDATE_ID,
    LINEAR_REGRESSION_CANDIDATE_ID,
    ARIMA_CANDIDATE_ID,
    RANDOM_FOREST_CANDIDATE_ID,
)
BASELINE_CANDIDATE_IDS = frozenset(CANDIDATE_SIMPLICITY_ORDER[:2])
COMPLEX_CANDIDATE_IDS = frozenset(CANDIDATE_SIMPLICITY_ORDER[2:])


@dataclass(frozen=True, slots=True)
class CandidateSelectionStatistics:
    """Selection-fold aggregate for one candidate and symbol."""

    candidate_id: str
    available_fold_count: int
    required_fold_count: int
    mean_selection_mae: float | None
    improvement_vs_best_baseline_percent: float | None
    clears_minimum_improvement: bool
    practical_tie_with_best_baseline: bool | None
    warning: str | None


@dataclass(frozen=True, slots=True)
class SymbolSelectionSummary:
    """Policy result without claiming a final production model."""

    symbol: str
    best_baseline_id: str | None
    best_baseline_mean_selection_mae: float | None
    leading_selection_candidate_id: str | None
    baseline_remains_leading: bool
    candidate_statistics: tuple[CandidateSelectionStatistics, ...]
    warning: str | None


def _is_practical_tie(left: float, right: float) -> bool:
    if not (math.isfinite(left) and math.isfinite(right)):
        raise ValueError("tie inputs must be finite")
    if left == right:
        return True
    reference = min(abs(left), abs(right))
    if reference == 0.0:
        return False
    return abs(left - right) / reference * 100.0 <= PRACTICAL_TIE_PERCENT


def _available_mean(
    results: tuple[ForecastEvaluationResult, ...],
    *,
    expected_fold_ids: tuple[str, ...],
) -> tuple[float | None, int, str | None]:
    by_fold: dict[str, ForecastEvaluationResult] = {}
    for result in results:
        if result.fold_id in by_fold:
            raise ValueError(
                f"duplicate selection result for fold {result.fold_id}"
            )
        by_fold[result.fold_id] = result
    available = tuple(
        result
        for result in results
        if result.prediction_available and result.mae is not None
    )
    missing = tuple(
        fold_id for fold_id in expected_fold_ids if fold_id not in by_fold
    )
    unavailable = tuple(
        fold_id
        for fold_id in expected_fold_ids
        if fold_id in by_fold and not by_fold[fold_id].prediction_available
    )
    if missing or unavailable or len(results) != len(expected_fold_ids):
        details: list[str] = []
        if missing:
            details.append(f"missing folds: {', '.join(missing)}")
        if unavailable:
            details.append(f"unavailable folds: {', '.join(unavailable)}")
        unexpected = tuple(
            result.fold_id
            for result in results
            if result.fold_id not in expected_fold_ids
        )
        if unexpected:
            details.append(f"unexpected folds: {', '.join(unexpected)}")
        return None, len(available), "; ".join(details)
    values = tuple(result.mae for result in available)
    if len(values) != len(expected_fold_ids) or any(
        value is None or not math.isfinite(value) for value in values
    ):
        return None, len(available), "selection MAE is unavailable or non-finite"
    mean = math.fsum(value for value in values if value is not None) / len(values)
    if not math.isfinite(mean):
        raise ValueError("mean selection MAE must be finite")
    return mean, len(available), None


def _simpler_or_lower(
    candidates: tuple[tuple[str, float], ...],
) -> tuple[str, float]:
    if not candidates:
        raise ValueError("at least one candidate is required")
    simplicity = {
        candidate_id: index
        for index, candidate_id in enumerate(CANDIDATE_SIMPLICITY_ORDER)
    }
    selected = candidates[0]
    for candidate in candidates[1:]:
        if _is_practical_tie(selected[1], candidate[1]):
            if simplicity[candidate[0]] < simplicity[selected[0]]:
                selected = candidate
        elif candidate[1] < selected[1]:
            selected = candidate
    return selected


def summarize_symbol_selection(
    *,
    symbol: str,
    results: tuple[ForecastEvaluationResult, ...],
    expected_selection_fold_ids: tuple[str, ...],
) -> SymbolSelectionSummary:
    """Apply the approved 5% improvement and 1% practical-tie policy."""
    if not symbol:
        raise ValueError("symbol cannot be empty")
    if not expected_selection_fold_ids:
        raise ValueError("expected_selection_fold_ids cannot be empty")
    if len(set(expected_selection_fold_ids)) != len(expected_selection_fold_ids):
        raise ValueError("expected selection fold identifiers must be unique")
    if any(
        result.symbol != symbol
        or result.target_type is not ForecastTargetType.RETURN
        or result.fold_purpose is not FoldPurpose.SELECTION
        for result in results
    ):
        raise ValueError(
            "selection summaries accept only matching return selection results"
        )

    grouped = {candidate_id: [] for candidate_id in CANDIDATE_SIMPLICITY_ORDER}
    for result in results:
        if result.candidate_id not in grouped:
            raise ValueError(
                f"unsupported selection candidate: {result.candidate_id}"
            )
        grouped[result.candidate_id].append(result)

    aggregates: dict[str, tuple[float | None, int, str | None]] = {}
    for candidate_id in CANDIDATE_SIMPLICITY_ORDER:
        aggregates[candidate_id] = _available_mean(
            tuple(grouped[candidate_id]),
            expected_fold_ids=expected_selection_fold_ids,
        )

    baseline_options = tuple(
        (candidate_id, aggregates[candidate_id][0])
        for candidate_id in CANDIDATE_SIMPLICITY_ORDER
        if candidate_id in BASELINE_CANDIDATE_IDS
        and aggregates[candidate_id][0] is not None
    )
    if not baseline_options:
        statistics = tuple(
            CandidateSelectionStatistics(
                candidate_id=candidate_id,
                available_fold_count=aggregates[candidate_id][1],
                required_fold_count=len(expected_selection_fold_ids),
                mean_selection_mae=aggregates[candidate_id][0],
                improvement_vs_best_baseline_percent=None,
                clears_minimum_improvement=False,
                practical_tie_with_best_baseline=None,
                warning=aggregates[candidate_id][2],
            )
            for candidate_id in CANDIDATE_SIMPLICITY_ORDER
        )
        return SymbolSelectionSummary(
            symbol=symbol,
            best_baseline_id=None,
            best_baseline_mean_selection_mae=None,
            leading_selection_candidate_id=None,
            baseline_remains_leading=False,
            candidate_statistics=statistics,
            warning="no baseline has all required selection-fold results",
        )

    best_baseline_id, best_baseline_mae = _simpler_or_lower(
        tuple(
            (candidate_id, mean)
            for candidate_id, mean in baseline_options
            if mean is not None
        )
    )
    statistics_list: list[CandidateSelectionStatistics] = []
    qualifying: list[tuple[str, float]] = []
    for candidate_id in CANDIDATE_SIMPLICITY_ORDER:
        mean, available_count, warning = aggregates[candidate_id]
        improvement: float | None = None
        clears = False
        tie: bool | None = None
        if mean is not None:
            tie = _is_practical_tie(mean, best_baseline_mae)
            if candidate_id in COMPLEX_CANDIDATE_IDS:
                improvement = (
                    None
                    if best_baseline_mae == 0.0
                    else (best_baseline_mae - mean)
                    / best_baseline_mae
                    * 100.0
                )
                clears = (
                    improvement is not None
                    and improvement
                    >= MINIMUM_COMPLEX_MODEL_IMPROVEMENT_PERCENT
                )
                if clears:
                    qualifying.append((candidate_id, mean))
        statistics_list.append(
            CandidateSelectionStatistics(
                candidate_id=candidate_id,
                available_fold_count=available_count,
                required_fold_count=len(expected_selection_fold_ids),
                mean_selection_mae=mean,
                improvement_vs_best_baseline_percent=improvement,
                clears_minimum_improvement=clears,
                practical_tie_with_best_baseline=tie,
                warning=warning,
            )
        )

    leading_id = best_baseline_id
    if qualifying:
        leading_id, _ = _simpler_or_lower(tuple(qualifying))
    return SymbolSelectionSummary(
        symbol=symbol,
        best_baseline_id=best_baseline_id,
        best_baseline_mean_selection_mae=best_baseline_mae,
        leading_selection_candidate_id=leading_id,
        baseline_remains_leading=leading_id in BASELINE_CANDIDATE_IDS,
        candidate_statistics=tuple(statistics_list),
        warning=None,
    )
