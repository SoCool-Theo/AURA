from dataclasses import replace
from datetime import date

import pytest

from backend.app.forecasting.evaluation import (
    ForecastEvaluationResult,
    ForecastTargetType,
)
from backend.app.forecasting.models import (
    ARIMA_FIT_CONVERGENCE_WARNING,
    VOLATILITY_ARIMA_CANDIDATE_ID,
    VOLATILITY_LINEAR_REGRESSION_CANDIDATE_ID,
    VOLATILITY_RANDOM_FOREST_CANDIDATE_ID,
)
from backend.app.forecasting.selection import (
    HISTORICAL_AVERAGE_CANDIDATE_ID,
    MOVING_AVERAGE_CANDIDATE_ID,
    VOLATILITY_CANDIDATE_SIMPLICITY_ORDER,
    summarize_volatility_selection,
)
from backend.app.forecasting.splits import FoldPurpose


FOLDS = tuple(f"selection-{index:02d}" for index in range(1, 6))


def _result(candidate_id: str, fold_id: str, mae: float):
    return ForecastEvaluationResult(
        symbol="AAPL",
        target_type=ForecastTargetType.VOLATILITY,
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
        directional_accuracy=None,
        directional_evaluated_count=None,
        return_mape=None,
        warning=None,
        negative_prediction_clipped_count=0,
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
        *_candidate_results(VOLATILITY_LINEAR_REGRESSION_CANDIDATE_ID, linear),
        *_candidate_results(VOLATILITY_ARIMA_CANDIDATE_ID, arima),
        *_candidate_results(VOLATILITY_RANDOM_FOREST_CANDIDATE_ID, forest),
    )


def test_volatility_selection_applies_five_percent_and_practical_ties() -> None:
    summary = summarize_volatility_selection(
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
    assert tuple(stats) == VOLATILITY_CANDIDATE_SIMPLICITY_ORDER
    assert summary.best_baseline_id == HISTORICAL_AVERAGE_CANDIDATE_ID
    assert summary.best_baseline_mean_selection_mae == pytest.approx(0.1)
    assert (
        stats[VOLATILITY_LINEAR_REGRESSION_CANDIDATE_ID]
        .improvement_vs_best_baseline_percent
        == pytest.approx(6.0)
    )
    assert stats[VOLATILITY_LINEAR_REGRESSION_CANDIDATE_ID].clears_minimum_improvement
    assert stats[VOLATILITY_ARIMA_CANDIDATE_ID].clears_minimum_improvement
    assert not stats[VOLATILITY_RANDOM_FOREST_CANDIDATE_ID].clears_minimum_improvement
    assert (
        summary.leading_selection_candidate_id
        == VOLATILITY_LINEAR_REGRESSION_CANDIDATE_ID
    )
    assert not summary.baseline_remains_leading


def test_volatility_baseline_remains_when_no_complex_model_clears_threshold() -> None:
    summary = summarize_volatility_selection(
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
    assert summary.baseline_remains_leading


def test_volatility_summary_rejects_non_selection_or_return_results() -> None:
    calibration = replace(
        _result(HISTORICAL_AVERAGE_CANDIDATE_ID, "calibration-01", 0.1),
        fold_purpose=FoldPurpose.CALIBRATION,
    )
    with pytest.raises(ValueError, match="selection results"):
        summarize_volatility_selection(
            symbol="AAPL",
            results=(calibration,),
            expected_selection_fold_ids=FOLDS,
        )

    return_result = replace(
        _result(HISTORICAL_AVERAGE_CANDIDATE_ID, FOLDS[0], 0.1),
        target_type=ForecastTargetType.RETURN,
        negative_prediction_clipped_count=None,
    )
    with pytest.raises(ValueError, match="selection results"):
        summarize_volatility_selection(
            symbol="AAPL",
            results=(return_result,),
            expected_selection_fold_ids=FOLDS,
        )


def test_volatility_warning_is_reported_without_changing_selection_math() -> None:
    clean_results = _all_results(
        historical=0.1,
        moving=0.2,
        linear=0.11,
        arima=0.09,
        forest=0.12,
    )
    warned_results = tuple(
        replace(result, warning=ARIMA_FIT_CONVERGENCE_WARNING)
        if result.candidate_id == VOLATILITY_ARIMA_CANDIDATE_ID
        else result
        for result in clean_results
    )

    clean = summarize_volatility_selection(
        symbol="AAPL",
        results=clean_results,
        expected_selection_fold_ids=FOLDS,
    )
    warned = summarize_volatility_selection(
        symbol="AAPL",
        results=warned_results,
        expected_selection_fold_ids=FOLDS,
    )
    clean_stats = {item.candidate_id: item for item in clean.candidate_statistics}
    warned_stats = {
        item.candidate_id: item for item in warned.candidate_statistics
    }

    assert warned.best_baseline_id == clean.best_baseline_id
    assert (
        warned.leading_selection_candidate_id
        == clean.leading_selection_candidate_id
    )
    assert (
        warned_stats[VOLATILITY_ARIMA_CANDIDATE_ID].mean_selection_mae
        == clean_stats[VOLATILITY_ARIMA_CANDIDATE_ID].mean_selection_mae
    )
    assert (
        warned_stats[VOLATILITY_ARIMA_CANDIDATE_ID].warning
        == ARIMA_FIT_CONVERGENCE_WARNING
    )


def test_volatility_selection_does_not_mutate_caller_results() -> None:
    results = _all_results(
        historical=0.1,
        moving=0.2,
        linear=0.09,
        arima=0.11,
        forest=0.12,
    )
    before = tuple(results)

    first = summarize_volatility_selection(
        symbol="AAPL",
        results=results,
        expected_selection_fold_ids=FOLDS,
    )
    second = summarize_volatility_selection(
        symbol="AAPL",
        results=results,
        expected_selection_fold_ids=FOLDS,
    )

    assert first == second
    assert results == before
