"""Offline horizon-specific labels and selection, isolated from frozen V1.

This module is not imported by API inference. V1 candidate adapters retain their
legacy target-slot names; _candidate_dataset bridges those slots privately.
Their values are freshly constructed horizon labels, never scaled 30-day values.
External evidence must use the explicit horizon-specific names, not those slots.
"""

from __future__ import annotations

from bisect import bisect_left
from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import date, timedelta
import math
from numbers import Real

from .baselines import HistoricalMeanBaseline, MovingAverageBaseline
from .data import (
    AssetPriceHistory, ForecastDataset, ForecastDatasetRow,
    MIN_LABEL_COMPLETE_TRAINING_ORIGINS,
)
from .evaluation import (
    ForecastCandidate, ForecastEvaluationResult, ForecastTargetType,
    evaluate_candidate,
)
from .features import (
    FEATURE_SET_VERSION, MAX_FEATURE_LOOKBACK, ForecastFeatureRow,
    build_feature_rows,
)
from .models import (
    ArimaCandidate, LinearRegressionCandidate, RandomForestCandidate,
    VolatilityArimaCandidate, VolatilityLinearRegressionCandidate,
    VolatilityRandomForestCandidate,
)
from .selection import (
    SymbolSelectionSummary, summarize_symbol_selection,
    summarize_volatility_selection,
)
from .splits import ChronologicalEvaluationPlan, FoldPurpose
from .targets import MAX_ENDPOINT_SLIPPAGE_DAYS, ForecastTargetRow


SUPPORTED_HORIZONS = (7, 14, 21, 30)
NEW_HORIZONS = (7, 14, 21)


def validate_horizon(horizon_days: int) -> None:
    if type(horizon_days) is not int or horizon_days not in SUPPORTED_HORIZONS:
        raise ValueError("forecast horizon must be 7, 14, 21 or 30 calendar days")


def target_version(horizon_days: int) -> str:
    validate_horizon(horizon_days)
    return f"forecast-targets-{horizon_days}d-v1"


def target_name(target_type: ForecastTargetType, horizon_days: int) -> str:
    validate_horizon(horizon_days)
    if target_type is ForecastTargetType.RETURN:
        return f"return_{horizon_days}d"
    if target_type is ForecastTargetType.VOLATILITY:
        return f"realized_volatility_{horizon_days}d"
    raise ValueError("unsupported forecast target kind")


@dataclass(frozen=True, slots=True)
class HorizonTargetRow:
    symbol: str
    horizon_days: int
    origin_date: date
    requested_target_date: date
    endpoint_date: date
    endpoint_slippage_days: int
    return_value: float
    realized_volatility: float

    def __post_init__(self) -> None:
        validate_horizon(self.horizon_days)
        if any(type(value) is not date for value in (
            self.origin_date, self.requested_target_date, self.endpoint_date,
        )):
            raise ValueError("target dates must be dates")
        if (self.requested_target_date != self.origin_date + timedelta(days=self.horizon_days)
            or type(self.endpoint_slippage_days) is not int
            or not 0 <= self.endpoint_slippage_days <= MAX_ENDPOINT_SLIPPAGE_DAYS
            or self.endpoint_date != self.requested_target_date + timedelta(days=self.endpoint_slippage_days)):
            raise ValueError("target endpoint does not match its horizon")
        if (any(isinstance(value, bool) or not isinstance(value, Real)
                or not math.isfinite(value) for value in (self.return_value, self.realized_volatility))
            or self.realized_volatility < 0):
            raise ValueError("target values must be finite and volatility non-negative")


@dataclass(frozen=True, slots=True)
class HorizonDatasetRow:
    features: ForecastFeatureRow
    target: HorizonTargetRow


@dataclass(frozen=True, slots=True)
class HorizonDataset:
    symbol: str
    horizon_days: int
    price_observation_count: int
    feature_origin_count: int
    target_origin_count: int
    rows: tuple[HorizonDatasetRow, ...]

    def __post_init__(self) -> None:
        validate_horizon(self.horizon_days)
        if any(row.target.horizon_days != self.horizon_days
               or row.target.symbol != self.symbol or row.features.symbol != self.symbol
               or row.features.origin_date != row.target.origin_date for row in self.rows):
            raise ValueError("dataset cannot mix horizons, symbols or origins")
        origins = tuple(row.features.origin_date for row in self.rows)
        if any(right <= left for left, right in zip(origins, origins[1:])):
            raise ValueError("dataset origins must be strictly chronological")


def build_horizon_targets(
    history: AssetPriceHistory, *, horizon_days: int,
) -> tuple[HorizonTargetRow, ...]:
    """Use first stored price at/after the calendar horizon, at most +4 days.

    Volatility is sqrt(sum(consecutive future log returns squared)), exactly
    the non-annualized V1 definition. Missing dates are never filled.
    """
    validate_horizon(horizon_days)
    observations = history.observations
    dates = tuple(item.date for item in observations)
    prices = tuple(item.adjusted_close for item in observations)
    rows = []
    for origin_index, origin in enumerate(dates):
        requested = origin + timedelta(days=horizon_days)
        endpoint_index = bisect_left(dates, requested, lo=origin_index + 1)
        if endpoint_index == len(dates):
            continue
        endpoint = dates[endpoint_index]
        slippage = (endpoint - requested).days
        if slippage > MAX_ENDPOINT_SLIPPAGE_DAYS:
            continue
        future_returns = tuple(math.log(prices[index] / prices[index - 1])
                               for index in range(origin_index + 1, endpoint_index + 1))
        rows.append(HorizonTargetRow(
            history.symbol, horizon_days, origin, requested, endpoint, slippage,
            prices[endpoint_index] / prices[origin_index] - 1.0,
            math.sqrt(math.fsum(value * value for value in future_returns)),
        ))
    return tuple(rows)


def build_horizon_dataset(
    history: AssetPriceHistory, *, horizon_days: int,
    features: Sequence[ForecastFeatureRow] | None = None,
) -> HorizonDataset:
    """Reuse past-only V1 features and join freshly computed horizon labels."""
    validate_horizon(horizon_days)
    feature_rows = tuple(build_feature_rows(history) if features is None else features)
    target_rows = build_horizon_targets(history, horizon_days=horizon_days)
    by_origin = {row.origin_date: row for row in target_rows}
    return HorizonDataset(
        history.symbol, horizon_days, len(history.observations), len(feature_rows), len(target_rows),
        tuple(HorizonDatasetRow(feature, by_origin[feature.origin_date])
              for feature in feature_rows if feature.origin_date in by_origin),
    )


def _candidate_dataset(dataset: HorizonDataset, *, endpoint_before: date) -> ForecastDataset:
    """Private offline bridge to unchanged V1 algorithms, not a V1 artifact.

    Remove evaluation labels reaching the next fold as well as preserving the
    existing training endpoint purge. Selection never scores calibration/test
    outcomes. Legacy *_30d slots carry this dataset's actual horizon values only.
    """
    rows = tuple(ForecastDatasetRow(
        features=row.features,
        target=ForecastTargetRow(
            symbol=dataset.symbol, origin_date=row.target.origin_date,
            requested_target_date=row.target.requested_target_date,
            endpoint_date=row.target.endpoint_date,
            endpoint_slippage_days=row.target.endpoint_slippage_days,
            return_30d=row.target.return_value,
            realized_volatility_30d=row.target.realized_volatility,
        ),
    ) for row in dataset.rows if row.target.endpoint_date < endpoint_before)
    return ForecastDataset(
        symbol=dataset.symbol, feature_set_version=FEATURE_SET_VERSION,
        target_set_version=target_version(dataset.horizon_days),
        max_feature_lookback=MAX_FEATURE_LOOKBACK,
        minimum_label_complete_training_origins=MIN_LABEL_COMPLETE_TRAINING_ORIGINS,
        price_observation_count=dataset.price_observation_count,
        feature_origin_count=dataset.feature_origin_count,
        target_origin_count=dataset.target_origin_count, rows=rows,
    )


def horizon_candidates(target_type: ForecastTargetType) -> tuple[ForecastCandidate, ...]:
    if target_type is ForecastTargetType.RETURN:
        models = (LinearRegressionCandidate(), ArimaCandidate(), RandomForestCandidate())
    elif target_type is ForecastTargetType.VOLATILITY:
        models = (VolatilityLinearRegressionCandidate(), VolatilityArimaCandidate(), VolatilityRandomForestCandidate())
    else:
        raise ValueError("unsupported forecast target kind")
    return (HistoricalMeanBaseline(), MovingAverageBaseline(), *models)


def evaluate_horizon_selection(
    *, dataset: HorizonDataset, plan: ChronologicalEvaluationPlan,
    target_type: ForecastTargetType, candidates: Sequence[ForecastCandidate] | None = None,
) -> tuple[tuple[ForecastEvaluationResult, ...], SymbolSelectionSummary]:
    """Evaluate only selection folds, with no fitting on later labels."""
    approved = tuple(horizon_candidates(target_type) if candidates is None else candidates)
    target_name(target_type, dataset.horizon_days)
    ids = tuple(item.candidate_id for item in approved)
    if len(set(ids)) != len(ids):
        raise ValueError("candidate identifiers must be unique")
    selection_folds = tuple(fold for fold in plan.folds if fold.purpose is FoldPurpose.SELECTION)
    if not selection_folds:
        raise ValueError("selection folds are required")
    results = []
    # Reuse the same finite, purged label slice for every candidate in each fold.
    for fold in selection_folds:
        candidate_dataset = _candidate_dataset(dataset, endpoint_before=fold.origin_end)
        fold_plan = replace(plan, folds=(fold,))
        for candidate in approved:
            results.extend(evaluate_candidate(
                dataset=candidate_dataset, plan=fold_plan,
                target_type=target_type, candidate=candidate,
                fold_purposes=(FoldPurpose.SELECTION,),
            ))
    summarize = summarize_symbol_selection if target_type is ForecastTargetType.RETURN else summarize_volatility_selection
    ordered = tuple(results)
    summary = summarize(
        symbol=dataset.symbol, results=ordered,
        expected_selection_fold_ids=tuple(fold.fold_id for fold in selection_folds),
    )
    return ordered, summary
