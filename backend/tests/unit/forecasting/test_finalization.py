from dataclasses import replace
from datetime import date, timedelta
import math
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from backend.app.forecasting.data import ForecastDataset, ForecastDatasetRow
from backend.app.forecasting.evaluation import (
    CandidatePrediction,
    ForecastTargetType,
)
from backend.app.forecasting.features import FEATURE_NAMES, ForecastFeatureRow
from backend.app.forecasting.finalization import (
    CALIBRATION_MINIMUM_OBSERVATIONS,
    ForecastArtifactModel,
    ForecastFinalizationError,
    calibrate_frozen_selection,
    evaluate_frozen_final_test,
    prediction_interval,
    train_deployment_artifact,
)
from backend.app.forecasting.models import (
    ARIMA_FIT_CONVERGENCE_WARNING,
    ARIMA_ORDER,
)
from backend.app.forecasting.selection_manifest import FrozenSelectionRecord
from backend.app.forecasting.splits import (
    ChronologicalEvaluationPlan,
    EvaluationFold,
    EvaluationPlanConfig,
    FoldPurpose,
)
from backend.app.forecasting.targets import ForecastTargetRow


def _row(origin: date, endpoint: date, value: float) -> ForecastDatasetRow:
    return ForecastDatasetRow(
        features=ForecastFeatureRow(
            symbol="AAPL",
            origin_date=origin,
            **{
                name: float(index + 1)
                for index, name in enumerate(FEATURE_NAMES)
            },
        ),
        target=ForecastTargetRow(
            symbol="AAPL",
            origin_date=origin,
            requested_target_date=origin + timedelta(days=30),
            endpoint_date=endpoint,
            endpoint_slippage_days=(endpoint - origin).days - 30,
            return_30d=value,
            realized_volatility_30d=max(value, 0.0),
        ),
    )


def _dataset(calibration_count: int = 60) -> ForecastDataset:
    training = tuple(
        _row(
            date(2023, 1, 1) + timedelta(days=index),
            date(2023, 1, 31) + timedelta(days=index),
            0.1,
        )
        for index in range(100)
    )
    calibration = tuple(
        _row(
            date(2024, 1, 1) + timedelta(days=index),
            date(2024, 1, 31) + timedelta(days=index),
            index / 100,
        )
        for index in range(calibration_count)
    )
    final_test = tuple(
        _row(
            date(2024, 3, 15) + timedelta(days=index),
            date(2024, 4, 14) + timedelta(days=index),
            0.2,
        )
        for index in range(60)
    )
    rows = (*training, *calibration, *final_test)
    return ForecastDataset(
        symbol="AAPL",
        feature_set_version="forecast-features-v1",
        target_set_version="forecast-targets-v1",
        max_feature_lookback=252,
        minimum_label_complete_training_origins=50,
        price_observation_count=500,
        feature_origin_count=len(rows),
        target_origin_count=len(rows),
        rows=rows,
    )


def _plan() -> ChronologicalEvaluationPlan:
    return ChronologicalEvaluationPlan(
        config=EvaluationPlanConfig(
            evaluation_end_exclusive=date(2024, 6, 1),
            minimum_training_origins=50,
        ),
        folds=(
            EvaluationFold(
                "calibration-01",
                FoldPurpose.CALIBRATION,
                date(2024, 1, 1),
                date(2024, 3, 15),
            ),
            EvaluationFold(
                "final-test-01",
                FoldPurpose.FINAL_TEST,
                date(2024, 3, 15),
                date(2024, 6, 1),
            ),
        ),
    )


def _selection(
    target_type: ForecastTargetType = ForecastTargetType.RETURN,
) -> FrozenSelectionRecord:
    return FrozenSelectionRecord(
        symbol="AAPL",
        target_type=target_type,
        selected_candidate_id="historical_average",
        selected_candidate_kind="baseline",
        best_baseline_id="historical_average",
        best_baseline_mean_selection_mae=0.1,
        selected_candidate_mean_selection_mae=0.1,
        improvement_vs_best_baseline_percent=None,
        practical_tie_with_best_baseline=True,
        selection_warning=None,
        source_selection_report_sha256="a" * 64,
        evaluation_cutoff=date(2026, 9, 17),
    )


class _ConstantCandidate:
    candidate_id = "historical_average"

    def __init__(self, value: float):
        self.value = value
        self.seen_purposes: list[int] = []

    def predict(self, *, training_rows, evaluation_rows, **kwargs):
        self.seen_purposes.append(len(evaluation_rows))
        return CandidatePrediction(
            candidate_id=self.candidate_id,
            values=tuple(self.value for _ in evaluation_rows),
            training_value_count=len(training_rows),
        )


def test_calibration_requires_60_residuals_and_uses_calibration_only() -> None:
    with pytest.raises(ForecastFinalizationError, match="at least 60"):
        calibrate_frozen_selection(
            dataset=_dataset(59),
            plan=_plan(),
            selection=_selection(),
            candidate=_ConstantCandidate(0.1),
        )

    candidate = _ConstantCandidate(0.1)
    result = calibrate_frozen_selection(
        dataset=_dataset(60),
        plan=_plan(),
        selection=_selection(),
        candidate=candidate,
    )

    assert result.fold_id == "calibration-01"
    assert result.observation_count == CALIBRATION_MINIMUM_OBSERVATIONS
    assert candidate.seen_purposes == [60]
    assert result.residual_q10 == pytest.approx(-0.041)
    assert result.residual_q90 == pytest.approx(0.431)
    assert result.mae == pytest.approx(
        sum(abs(index / 100 - 0.1) for index in range(60)) / 60
    )


def test_volatility_calibration_clips_before_residuals() -> None:
    result = calibrate_frozen_selection(
        dataset=_dataset(),
        plan=_plan(),
        selection=_selection(ForecastTargetType.VOLATILITY),
        candidate=_ConstantCandidate(-0.2),
    )

    assert result.negative_prediction_clipped_count == 60
    assert result.residual_q10 == pytest.approx(0.059)
    assert result.residual_q90 == pytest.approx(0.531)


def test_final_test_uses_only_frozen_candidate_and_bad_finite_result_is_recorded() -> None:
    candidate = _ConstantCandidate(999.0)
    result = evaluate_frozen_final_test(
        dataset=_dataset(),
        plan=_plan(),
        selection=_selection(),
        candidate=candidate,
    )

    assert result.fold_id == "final-test-01"
    assert result.selected_candidate_id == "historical_average"
    assert result.mae == pytest.approx(998.8)
    assert result.rmse == pytest.approx(998.8)
    assert candidate.seen_purposes == [60]

    changed = _ConstantCandidate(0.0)
    changed.candidate_id = "moving_average_90_calendar_days"
    with pytest.raises(ForecastFinalizationError, match="frozen selection"):
        evaluate_frozen_final_test(
            dataset=_dataset(),
            plan=_plan(),
            selection=_selection(),
            candidate=changed,
        )


def test_non_finite_final_test_prediction_blocks_finalization() -> None:
    class NonFiniteCandidate(_ConstantCandidate):
        def predict(self, *, training_rows, evaluation_rows, **kwargs):
            return SimpleNamespace(
                available=True,
                values=(math.nan,) * len(evaluation_rows),
                training_value_count=len(training_rows),
                warning=None,
            )

    with pytest.raises(ForecastFinalizationError, match="finite"):
        evaluate_frozen_final_test(
            dataset=_dataset(),
            plan=_plan(),
            selection=_selection(),
            candidate=NonFiniteCandidate(0.0),
        )


def test_interval_floor_applies_only_to_volatility() -> None:
    assert prediction_interval(
        point_prediction=0.02,
        residual_q10=-0.05,
        residual_q90=0.1,
        target_type=ForecastTargetType.RETURN,
    ) == pytest.approx((-0.03, 0.12))
    assert prediction_interval(
        point_prediction=0.02,
        residual_q10=-0.05,
        residual_q90=0.1,
        target_type=ForecastTargetType.VOLATILITY,
    ) == pytest.approx((0.0, 0.12))


def test_deployment_training_uses_all_labels_complete_through_cutoff() -> None:
    cutoff = date(2024, 4, 1)
    rows = (
        _row(date(2024, 1, 1), date(2024, 2, 1), 0.1),
        _row(date(2024, 2, 1), cutoff, 0.2),
        _row(date(2024, 3, 1), cutoff + timedelta(days=1), 99.0),
    )
    dataset = replace(_dataset(), rows=rows)
    selection = replace(_selection(), evaluation_cutoff=cutoff)

    result = train_deployment_artifact(
        dataset=dataset,
        selection=selection,
        evaluation_cutoff=cutoff,
    )

    assert result.training_row_count == 2
    assert result.training_origin_min == date(2024, 1, 1)
    assert result.training_origin_max == date(2024, 2, 1)
    assert result.artifact_model.predict(steps=2) == pytest.approx((0.15, 0.15))


def test_artifact_wrapper_preserves_return_and_clips_volatility() -> None:
    return_model = ForecastArtifactModel(
        candidate_id="historical_average",
        target_type=ForecastTargetType.RETURN,
        model_family="historical_average",
        constant_prediction=-0.2,
    )
    volatility_model = replace(
        return_model,
        target_type=ForecastTargetType.VOLATILITY,
    )

    assert return_model.predict(steps=1) == (-0.2,)
    assert volatility_model.predict(steps=1) == (0.0,)


def test_deployment_arima_preserves_order_and_convergence_warning() -> None:
    captured = {}

    class FakeFitted:
        def forecast(self, *, steps):
            return (0.1,) * steps

    def fake_fit(targets):
        captured["targets"] = targets
        return FakeFitted(), True

    selection = replace(
        _selection(),
        selected_candidate_id="arima_1_0_1_v1",
        selected_candidate_kind="complex",
    )
    with patch(
        "backend.app.forecasting.finalization."
        "_fit_arima_with_warning_metadata",
        side_effect=fake_fit,
    ):
        result = train_deployment_artifact(
            dataset=_dataset(),
            selection=selection,
            evaluation_cutoff=selection.evaluation_cutoff,
        )

    assert result.model_parameters == {"order": list(ARIMA_ORDER)}
    assert result.warning == ARIMA_FIT_CONVERGENCE_WARNING
    assert len(captured["targets"]) == len(_dataset().rows)


def test_deployment_arima_non_finite_forecast_blocks_artifact() -> None:
    class NonFiniteFitted:
        def forecast(self, *, steps):
            return (float("nan"),) * steps

    selection = replace(
        _selection(),
        selected_candidate_id="arima_1_0_1_v1",
        selected_candidate_kind="complex",
    )
    with patch(
        "backend.app.forecasting.finalization."
        "_fit_arima_with_warning_metadata",
        return_value=(NonFiniteFitted(), False),
    ), pytest.raises(ValueError, match="finite"):
        train_deployment_artifact(
            dataset=_dataset(),
            selection=selection,
            evaluation_cutoff=selection.evaluation_cutoff,
        )
