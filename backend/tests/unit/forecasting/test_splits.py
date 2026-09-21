from datetime import date, timedelta

from backend.app.forecasting.data import (
    ForecastDataset,
    ForecastDatasetRow,
)
from backend.app.forecasting.features import ForecastFeatureRow
from backend.app.forecasting.splits import (
    EvaluationFold,
    EvaluationPlanConfig,
    FoldPurpose,
    build_chronological_plan,
    slice_dataset_for_fold,
)
from backend.app.forecasting.targets import ForecastTargetRow


def _row(
    *,
    origin: date,
    endpoint: date,
    value: float = 0.1,
) -> ForecastDatasetRow:
    features = ForecastFeatureRow(
        symbol="AAPL",
        origin_date=origin,
        log_return_1=0.0,
        cumulative_return_5=0.0,
        cumulative_return_21=0.0,
        cumulative_return_63=0.0,
        cumulative_return_126=0.0,
        cumulative_return_252=0.0,
        rolling_mean_log_return_5=0.0,
        rolling_mean_log_return_21=0.0,
        rolling_mean_log_return_63=0.0,
        rolling_volatility_log_return_5=0.0,
        rolling_volatility_log_return_21=0.0,
        rolling_volatility_log_return_63=0.0,
        rolling_volatility_log_return_126=0.0,
        rolling_volatility_log_return_252=0.0,
    )
    target = ForecastTargetRow(
        symbol="AAPL",
        origin_date=origin,
        requested_target_date=origin + timedelta(days=30),
        endpoint_date=endpoint,
        endpoint_slippage_days=max(
            0,
            (endpoint - (origin + timedelta(days=30))).days,
        ),
        return_30d=value,
        realized_volatility_30d=abs(value),
    )
    return ForecastDatasetRow(features=features, target=target)


def _dataset(rows: tuple[ForecastDatasetRow, ...]) -> ForecastDataset:
    return ForecastDataset(
        symbol="AAPL",
        feature_set_version="forecast-features-v1",
        target_set_version="forecast-targets-v1",
        max_feature_lookback=252,
        minimum_label_complete_training_origins=756,
        price_observation_count=len(rows) + 282,
        feature_origin_count=len(rows),
        target_origin_count=len(rows),
        rows=rows,
    )


def test_default_plan_has_ordered_non_overlapping_purposes() -> None:
    plan = build_chronological_plan(
        EvaluationPlanConfig(
            evaluation_end_exclusive=date(2026, 9, 18),
        )
    )

    assert [fold.fold_id for fold in plan.folds] == [
        "selection-01",
        "selection-02",
        "selection-03",
        "selection-04",
        "selection-05",
        "calibration-01",
        "final-test-01",
    ]
    assert [fold.purpose for fold in plan.folds] == [
        FoldPurpose.SELECTION,
        FoldPurpose.SELECTION,
        FoldPurpose.SELECTION,
        FoldPurpose.SELECTION,
        FoldPurpose.SELECTION,
        FoldPurpose.CALIBRATION,
        FoldPurpose.FINAL_TEST,
    ]
    assert plan.folds[0].origin_start == date(2022, 9, 18)
    assert plan.folds[-1].origin_start == date(2025, 9, 18)
    assert plan.folds[-1].origin_end == date(2026, 9, 18)
    assert all(
        previous.origin_end == current.origin_start
        for previous, current in zip(plan.folds, plan.folds[1:])
    )


def test_plan_dates_are_parameterized_and_month_end_safe() -> None:
    january_plan = build_chronological_plan(
        EvaluationPlanConfig(
            evaluation_end_exclusive=date(2031, 1, 31),
        )
    )
    september_plan = build_chronological_plan(
        EvaluationPlanConfig(
            evaluation_end_exclusive=date(2031, 9, 30),
        )
    )

    assert january_plan.folds[-1].origin_end == date(2031, 1, 31)
    assert january_plan.folds[-1].origin_start == date(2030, 1, 31)
    assert september_plan.folds[-1].origin_end == date(2031, 9, 30)
    assert september_plan.folds[-1].origin_start == date(2030, 9, 30)
    assert january_plan.folds != september_plan.folds


def test_training_is_purged_by_endpoint_not_origin_date() -> None:
    fold = EvaluationFold(
        fold_id="selection-01",
        purpose=FoldPurpose.SELECTION,
        origin_start=date(2025, 6, 1),
        origin_end=date(2025, 7, 1),
    )
    completed = _row(
        origin=date(2025, 4, 20),
        endpoint=date(2025, 5, 31),
    )
    overlapping = _row(
        origin=date(2025, 5, 20),
        endpoint=date(2025, 6, 20),
    )
    fold_start = _row(
        origin=date(2025, 6, 1),
        endpoint=date(2025, 7, 1),
    )
    fold_end = _row(
        origin=date(2025, 7, 1),
        endpoint=date(2025, 7, 31),
    )

    sliced = slice_dataset_for_fold(
        _dataset((completed, overlapping, fold_start, fold_end)),
        fold,
        minimum_training_origins=1,
    )

    assert sliced.training_rows == (completed,)
    assert overlapping not in sliced.training_rows
    assert sliced.evaluation_rows == (fold_start,)


def test_exact_756_training_origins_are_eligible() -> None:
    fold_start = date(2026, 1, 1)
    rows = tuple(
        _row(
            origin=date(2020, 1, 1) + timedelta(days=index),
            endpoint=date(2020, 2, 1) + timedelta(days=index),
        )
        for index in range(756)
    )
    fold = EvaluationFold(
        fold_id="selection-01",
        purpose=FoldPurpose.SELECTION,
        origin_start=fold_start,
        origin_end=date(2026, 7, 1),
    )

    sliced = slice_dataset_for_fold(_dataset(rows), fold)

    assert len(sliced.training_rows) == 756
    assert sliced.training_eligible is True


def test_later_starting_assets_become_eligible_independently() -> None:
    fold = EvaluationFold(
        fold_id="selection-01",
        purpose=FoldPurpose.SELECTION,
        origin_start=date(2026, 1, 1),
        origin_end=date(2026, 7, 1),
    )
    base = date(2020, 1, 1)
    eligible_rows = tuple(
        _row(
            origin=base + timedelta(days=index),
            endpoint=base + timedelta(days=index + 30),
        )
        for index in range(756)
    )
    later_rows = eligible_rows[:-1]

    eligible = slice_dataset_for_fold(_dataset(eligible_rows), fold)
    later = slice_dataset_for_fold(_dataset(later_rows), fold)

    assert eligible.training_eligible is True
    assert later.training_eligible is False
    assert len(later.training_rows) == 755


def test_split_does_not_mutate_dataset_rows() -> None:
    rows = (
        _row(origin=date(2025, 1, 1), endpoint=date(2025, 2, 1)),
    )
    dataset = _dataset(rows)
    original_rows = dataset.rows
    fold = EvaluationFold(
        fold_id="selection-01",
        purpose=FoldPurpose.SELECTION,
        origin_start=date(2025, 6, 1),
        origin_end=date(2025, 12, 1),
    )

    slice_dataset_for_fold(dataset, fold, minimum_training_origins=1)

    assert dataset.rows is original_rows
    assert dataset.rows == rows
