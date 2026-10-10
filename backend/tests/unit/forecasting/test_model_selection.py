from dataclasses import replace
from datetime import date

import pytest

from backend.app.forecasting.evaluation import (
    ForecastEvaluationResult,
    ForecastTargetType,
)
from backend.app.forecasting.models import (
    ARIMA_CANDIDATE_ID,
    ARIMA_FIT_CONVERGENCE_WARNING,
    LINEAR_REGRESSION_CANDIDATE_ID,
    RANDOM_FOREST_CANDIDATE_ID,
)
from backend.app.forecasting.selection import (
    HISTORICAL_AVERAGE_CANDIDATE_ID,
    MOVING_AVERAGE_CANDIDATE_ID,
    summarize_symbol_selection,
)
from backend.app.forecasting.splits import FoldPurpose


FOLDS = tuple(f"selection-{index:02d}" for index in range(1, 6))


def _result(candidate_id: str, fold_id: str, mae: float):
    return ForecastEvaluationResult(
        symbol="AAPL",
        target_type=ForecastTargetType.RETURN,
        candidate_id=candidate_id,
        fold_id=fold_id,
        fold_purpose=FoldPurpose.SELECTION,
        training_cutoff=date(2024, 1, 1),
        evaluation_origin_start=date(2024, 1, 1),
        evaluation_origin_end=date(2024, 7, 1),
        training_observation_count=756,
        candidate_training_value_count=756,
        evaluated_observation_count=100,
        prediction_available=True,
        mae=mae,
        rmse=mae,
        directional_accuracy=0.5,
        directional_evaluated_count=100,
        return_mape=None,
        warning=None,
    )


def _candidate_results(candidate_id: str, mae: float):
    return tuple(_result(candidate_id, fold_id, mae) for fold_id in FOLDS)


def _all_results(
    *,
    historical: float,
    moving: float,
    linear: float,
    arima: float,
    forest: float,
):
    return (
        *_candidate_results(HISTORICAL_AVERAGE_CANDIDATE_ID, historical),
        *_candidate_results(MOVING_AVERAGE_CANDIDATE_ID, moving),
        *_candidate_results(LINEAR_REGRESSION_CANDIDATE_ID, linear),
        *_candidate_results(ARIMA_CANDIDATE_ID, arima),
        *_candidate_results(RANDOM_FOREST_CANDIDATE_ID, forest),
    )


def test_selection_applies_five_percent_threshold_and_one_percent_ties() -> None:
    summary = summarize_symbol_selection(
        symbol="AAPL",
        results=_all_results(
            historical=0.1000,
            moving=0.0995,
            linear=0.0940,
            arima=0.0935,
            forest=0.0990,
        ),
        expected_selection_fold_ids=FOLDS,
    )

    stats = {item.candidate_id: item for item in summary.candidate_statistics}
    assert summary.best_baseline_id == HISTORICAL_AVERAGE_CANDIDATE_ID
    assert summary.best_baseline_mean_selection_mae == pytest.approx(0.1)
    assert stats[LINEAR_REGRESSION_CANDIDATE_ID].clears_minimum_improvement
    assert (
        stats[LINEAR_REGRESSION_CANDIDATE_ID]
        .improvement_vs_best_baseline_percent
        == pytest.approx(6.0)
    )
    assert stats[ARIMA_CANDIDATE_ID].clears_minimum_improvement
    assert (
        stats[ARIMA_CANDIDATE_ID].improvement_vs_best_baseline_percent
        == pytest.approx(6.5)
    )
    assert not stats[RANDOM_FOREST_CANDIDATE_ID].clears_minimum_improvement
    assert summary.leading_selection_candidate_id == LINEAR_REGRESSION_CANDIDATE_ID
    assert summary.baseline_remains_leading is False


def test_baseline_remains_when_no_complex_candidate_clears_threshold() -> None:
    summary = summarize_symbol_selection(
        symbol="AAPL",
        results=_all_results(
            historical=0.1,
            moving=0.12,
            linear=0.096,
            arima=0.11,
            forest=0.2,
        ),
        expected_selection_fold_ids=FOLDS,
    )

    assert summary.leading_selection_candidate_id == HISTORICAL_AVERAGE_CANDIDATE_ID
    assert summary.baseline_remains_leading is True


def test_exact_five_percent_improvement_qualifies() -> None:
    summary = summarize_symbol_selection(
        symbol="AAPL",
        results=_all_results(
            historical=0.1,
            moving=0.2,
            linear=0.095,
            arima=0.2,
            forest=0.2,
        ),
        expected_selection_fold_ids=FOLDS,
    )
    stats = {item.candidate_id: item for item in summary.candidate_statistics}

    assert stats[LINEAR_REGRESSION_CANDIDATE_ID].clears_minimum_improvement
    assert summary.leading_selection_candidate_id == LINEAR_REGRESSION_CANDIDATE_ID


def test_missing_candidate_fold_is_explicitly_unavailable() -> None:
    results = _all_results(
        historical=0.1,
        moving=0.2,
        linear=0.08,
        arima=0.2,
        forest=0.2,
    )
    results = tuple(
        result
        for result in results
        if not (
            result.candidate_id == LINEAR_REGRESSION_CANDIDATE_ID
            and result.fold_id == "selection-05"
        )
    )

    summary = summarize_symbol_selection(
        symbol="AAPL",
        results=results,
        expected_selection_fold_ids=FOLDS,
    )
    stats = {item.candidate_id: item for item in summary.candidate_statistics}

    assert stats[LINEAR_REGRESSION_CANDIDATE_ID].mean_selection_mae is None
    assert stats[LINEAR_REGRESSION_CANDIDATE_ID].warning is not None
    assert "selection-05" in stats[LINEAR_REGRESSION_CANDIDATE_ID].warning
    assert summary.baseline_remains_leading


def test_summary_rejects_calibration_or_final_test_results() -> None:
    calibration = _result(
        HISTORICAL_AVERAGE_CANDIDATE_ID,
        "calibration-01",
        0.001,
    )
    calibration = replace(
        calibration,
        fold_purpose=FoldPurpose.CALIBRATION,
    )

    with pytest.raises(ValueError, match="selection results"):
        summarize_symbol_selection(
            symbol="AAPL",
            results=(calibration,),
            expected_selection_fold_ids=FOLDS,
        )


def test_available_warning_does_not_change_model_selection_calculations() -> None:
    clean_results = _all_results(
        historical=0.1,
        moving=0.2,
        linear=0.11,
        arima=0.09,
        forest=0.12,
    )
    warned_results = tuple(
        replace(
            result,
            warning=ARIMA_FIT_CONVERGENCE_WARNING,
        )
        if result.candidate_id == ARIMA_CANDIDATE_ID
        else result
        for result in clean_results
    )

    clean = summarize_symbol_selection(
        symbol="AAPL",
        results=clean_results,
        expected_selection_fold_ids=FOLDS,
    )
    warned = summarize_symbol_selection(
        symbol="AAPL",
        results=warned_results,
        expected_selection_fold_ids=FOLDS,
    )

    assert warned == clean
