from dataclasses import replace
from datetime import date, timedelta
import math
from types import SimpleNamespace
from unittest.mock import patch
import warnings

import pytest
from statsmodels.tools.sm_exceptions import ConvergenceWarning

from backend.app.forecasting.data import ForecastDataset, ForecastDatasetRow
from backend.app.forecasting.evaluation import (
    CandidatePrediction,
    ForecastTargetType,
    evaluate_candidate,
)
from backend.app.forecasting.features import FEATURE_NAMES, ForecastFeatureRow
from backend.app.forecasting.models import (
    ARIMA_FIT_CONVERGENCE_WARNING,
    ARIMA_ORDER,
    RANDOM_FOREST_PARAMETERS,
    VOLATILITY_ARIMA_CANDIDATE_ID,
    VOLATILITY_LINEAR_REGRESSION_CANDIDATE_ID,
    VOLATILITY_RANDOM_FOREST_CANDIDATE_ID,
    ForecastModelInputError,
    VolatilityArimaCandidate,
    VolatilityLinearRegressionCandidate,
    VolatilityRandomForestCandidate,
)
from backend.app.forecasting.splits import (
    ChronologicalEvaluationPlan,
    EvaluationFold,
    EvaluationPlanConfig,
    FoldPurpose,
)
from backend.app.forecasting.targets import ForecastTargetRow


def _row(
    *,
    origin: date,
    endpoint: date,
    volatility: float,
    feature_start: float,
    return_value: float = 99.0,
) -> ForecastDatasetRow:
    return ForecastDatasetRow(
        features=ForecastFeatureRow(
            symbol="AAPL",
            origin_date=origin,
            **{
                name: feature_start + index
                for index, name in enumerate(FEATURE_NAMES)
            },
        ),
        target=ForecastTargetRow(
            symbol="AAPL",
            origin_date=origin,
            requested_target_date=origin + timedelta(days=30),
            endpoint_date=endpoint,
            endpoint_slippage_days=(endpoint - (origin + timedelta(days=30))).days,
            return_30d=return_value,
            realized_volatility_30d=volatility,
        ),
    )


def _rows() -> tuple[ForecastDatasetRow, ...]:
    return (
        _row(
            origin=date(2024, 1, 1),
            endpoint=date(2024, 2, 1),
            volatility=0.1,
            feature_start=1.0,
        ),
        _row(
            origin=date(2024, 2, 1),
            endpoint=date(2024, 3, 3),
            volatility=0.2,
            feature_start=2.0,
        ),
        _row(
            origin=date(2025, 1, 1),
            endpoint=date(2025, 2, 1),
            volatility=0.3,
            feature_start=3.0,
        ),
        _row(
            origin=date(2025, 1, 2),
            endpoint=date(2025, 2, 2),
            volatility=0.4,
            feature_start=4.0,
        ),
    )


def _dataset(rows: tuple[ForecastDatasetRow, ...]) -> ForecastDataset:
    return ForecastDataset(
        symbol="AAPL",
        feature_set_version="forecast-features-v1",
        target_set_version="forecast-targets-v1",
        max_feature_lookback=252,
        minimum_label_complete_training_origins=2,
        price_observation_count=1000,
        feature_origin_count=len(rows),
        target_origin_count=len(rows),
        rows=rows,
    )


def _plan() -> ChronologicalEvaluationPlan:
    return ChronologicalEvaluationPlan(
        config=EvaluationPlanConfig(
            evaluation_end_exclusive=date(2025, 2, 1),
            minimum_training_origins=2,
        ),
        folds=(
            EvaluationFold(
                fold_id="selection-01",
                purpose=FoldPurpose.SELECTION,
                origin_start=date(2025, 1, 1),
                origin_end=date(2025, 2, 1),
            ),
        ),
    )


def test_volatility_candidate_ids_and_fixed_configurations_are_stable() -> None:
    assert (
        VolatilityLinearRegressionCandidate().candidate_id
        == VOLATILITY_LINEAR_REGRESSION_CANDIDATE_ID
    )
    assert (
        VolatilityArimaCandidate().candidate_id
        == VOLATILITY_ARIMA_CANDIDATE_ID
    )
    assert (
        VolatilityRandomForestCandidate().candidate_id
        == VOLATILITY_RANDOM_FOREST_CANDIDATE_ID
    )
    assert VolatilityArimaCandidate().order == ARIMA_ORDER == (1, 0, 1)
    assert RANDOM_FOREST_PARAMETERS == {
        "n_estimators": 200,
        "max_depth": 8,
        "min_samples_leaf": 5,
        "random_state": 42,
        "n_jobs": 1,
    }


@pytest.mark.parametrize(
    "candidate",
    (
        VolatilityLinearRegressionCandidate(),
        VolatilityArimaCandidate(),
        VolatilityRandomForestCandidate(),
    ),
)
def test_volatility_candidates_reject_return_target_without_fitting(candidate) -> None:
    rows = _rows()

    with pytest.raises(ForecastModelInputError, match="only realized_volatility_30d"):
        candidate.predict(
            training_rows=rows[:2],
            evaluation_rows=rows[2:],
            target_type=ForecastTargetType.RETURN,
            information_cutoff=date(2025, 1, 1),
        )


def test_linear_volatility_adapter_uses_fold_local_training_only() -> None:
    rows = _rows()
    calls: dict[str, object] = {}

    class FakePipeline:
        def fit(self, features, targets):
            calls["fit_features"] = features
            calls["fit_targets"] = targets
            return self

        def predict(self, features):
            calls["prediction_features"] = features
            return (-0.03, 0.08)

    with patch(
        "backend.app.forecasting.models.linear_regression."
        "build_linear_regression_pipeline",
        return_value=FakePipeline(),
    ):
        prediction = VolatilityLinearRegressionCandidate().predict(
            training_rows=rows[:2],
            evaluation_rows=rows[2:],
            target_type=ForecastTargetType.VOLATILITY,
            information_cutoff=date(2025, 1, 1),
        )

    assert calls["fit_targets"] == (0.1, 0.2)
    assert len(calls["fit_features"]) == 2
    assert len(calls["prediction_features"]) == 2
    assert calls["fit_features"] != calls["prediction_features"]
    assert prediction.values == (-0.03, 0.08)


def test_random_forest_volatility_adapter_reuses_fixed_builder_without_mutation() -> None:
    rows = list(_rows())
    before = list(rows)

    class FakeRegressor:
        def fit(self, features, targets):
            assert targets == (0.1, 0.2)
            return self

        def predict(self, features):
            return (0.04, 0.05)

    with patch(
        "backend.app.forecasting.models.random_forest."
        "build_random_forest_regressor",
        return_value=FakeRegressor(),
    ):
        prediction = VolatilityRandomForestCandidate().predict(
            training_rows=rows[:2],
            evaluation_rows=rows[2:],
            target_type=ForecastTargetType.VOLATILITY,
            information_cutoff=date(2025, 1, 1),
        )

    assert prediction.values == (0.04, 0.05)
    assert rows == before


def test_arima_uses_chronological_volatility_labels_not_evaluation_actuals() -> None:
    rows = _rows()
    captured: dict[str, object] = {}

    class EvaluationTargetTrap:
        def __getattribute__(self, name):
            raise AssertionError(f"evaluation target accessed: {name}")

    evaluation_rows = tuple(
        SimpleNamespace(features=row.features, target=EvaluationTargetTrap())
        for row in rows[2:]
    )

    class FakeFitted:
        def forecast(self, *, steps):
            captured["steps"] = steps
            return (-0.02, 0.06)

    class FakeArima:
        def __init__(self, targets, *, order):
            captured["targets"] = targets
            captured["order"] = order

        def fit(self):
            return FakeFitted()

    with patch("backend.app.forecasting.models.arima.ARIMA", FakeArima):
        prediction = VolatilityArimaCandidate().predict(
            training_rows=(rows[1], rows[0]),
            evaluation_rows=evaluation_rows,
            target_type=ForecastTargetType.VOLATILITY,
            information_cutoff=date(2025, 1, 1),
        )

    assert captured == {
        "targets": (0.1, 0.2),
        "order": (1, 0, 1),
        "steps": 2,
    }
    assert prediction.values == (-0.02, 0.06)


def test_arima_convergence_warning_remains_available_and_stable() -> None:
    rows = _rows()

    class FakeFitted:
        def forecast(self, *, steps):
            return (0.01,) * steps

    class WarningArima:
        def __init__(self, targets, *, order):
            assert order == (1, 0, 1)

        def fit(self):
            warnings.warn("synthetic convergence", ConvergenceWarning)
            return FakeFitted()

    with patch("backend.app.forecasting.models.arima.ARIMA", WarningArima):
        prediction = VolatilityArimaCandidate().predict(
            training_rows=rows[:2],
            evaluation_rows=rows[2:],
            target_type=ForecastTargetType.VOLATILITY,
            information_cutoff=date(2025, 1, 1),
        )

    assert prediction.available
    assert prediction.warning == ARIMA_FIT_CONVERGENCE_WARNING


def test_volatility_fit_failure_remains_unavailable() -> None:
    rows = _rows()

    class FailingRegressor:
        def fit(self, features, targets):
            raise RuntimeError("synthetic fit failure")

    with patch(
        "backend.app.forecasting.models.random_forest."
        "build_random_forest_regressor",
        return_value=FailingRegressor(),
    ):
        prediction = VolatilityRandomForestCandidate().predict(
            training_rows=rows[:2],
            evaluation_rows=rows[2:],
            target_type=ForecastTargetType.VOLATILITY,
            information_cutoff=date(2025, 1, 1),
        )

    assert not prediction.available
    assert "synthetic fit failure" in (prediction.warning or "")


def test_negative_predictions_are_clipped_before_metrics_without_mutation() -> None:
    raw_values = [-0.03, 0.08]
    before = list(raw_values)

    class RawCandidate:
        candidate_id = "raw-volatility"

        def predict(self, **kwargs):
            return CandidatePrediction(
                candidate_id=self.candidate_id,
                values=tuple(raw_values),
                training_value_count=len(kwargs["training_rows"]),
            )

    result = evaluate_candidate(
        dataset=_dataset(_rows()),
        plan=_plan(),
        target_type=ForecastTargetType.VOLATILITY,
        candidate=RawCandidate(),
    )[0]

    assert raw_values == before
    assert result.negative_prediction_clipped_count == 1
    assert result.mae == pytest.approx((0.3 + 0.32) / 2)
    assert result.rmse == pytest.approx(math.sqrt((0.3**2 + 0.32**2) / 2))
    assert result.directional_accuracy is None
    assert result.directional_evaluated_count is None
    assert result.return_mape is None


def test_negative_linear_prediction_is_clipped_by_common_evaluator() -> None:
    class FakePipeline:
        def fit(self, features, targets):
            return self

        def predict(self, features):
            return (-0.03, 0.08)

    with patch(
        "backend.app.forecasting.models.linear_regression."
        "build_linear_regression_pipeline",
        return_value=FakePipeline(),
    ):
        result = evaluate_candidate(
            dataset=_dataset(_rows()),
            plan=_plan(),
            target_type=ForecastTargetType.VOLATILITY,
            candidate=VolatilityLinearRegressionCandidate(),
        )[0]

    assert result.prediction_available
    assert result.negative_prediction_clipped_count == 1
    assert result.mae == pytest.approx((0.3 + 0.32) / 2)


def test_negative_arima_prediction_is_clipped_by_common_evaluator() -> None:
    class FakeFitted:
        def forecast(self, *, steps):
            assert steps == 2
            return (-0.03, 0.08)

    class FakeArima:
        def __init__(self, targets, *, order):
            assert order == (1, 0, 1)

        def fit(self):
            return FakeFitted()

    with patch("backend.app.forecasting.models.arima.ARIMA", FakeArima):
        result = evaluate_candidate(
            dataset=_dataset(_rows()),
            plan=_plan(),
            target_type=ForecastTargetType.VOLATILITY,
            candidate=VolatilityArimaCandidate(),
        )[0]

    assert result.prediction_available
    assert result.negative_prediction_clipped_count == 1
    assert result.mae == pytest.approx((0.3 + 0.32) / 2)


def test_positive_predictions_are_unchanged_and_clipped_count_is_zero() -> None:
    class PositiveCandidate:
        candidate_id = "positive-volatility"

        def predict(self, **kwargs):
            return CandidatePrediction(
                candidate_id=self.candidate_id,
                values=(0.3, 0.4),
                training_value_count=len(kwargs["training_rows"]),
            )

    result = evaluate_candidate(
        dataset=_dataset(_rows()),
        plan=_plan(),
        target_type=ForecastTargetType.VOLATILITY,
        candidate=PositiveCandidate(),
    )[0]

    assert result.negative_prediction_clipped_count == 0
    assert result.mae == 0.0
    assert result.rmse == 0.0


def test_non_finite_raw_prediction_remains_rejected() -> None:
    rows = _rows()

    class FakePipeline:
        def fit(self, features, targets):
            return self

        def predict(self, features):
            return (math.nan, math.inf)

    with (
        patch(
            "backend.app.forecasting.models.linear_regression."
            "build_linear_regression_pipeline",
            return_value=FakePipeline(),
        ),
        pytest.raises(ForecastModelInputError, match="finite"),
    ):
        VolatilityLinearRegressionCandidate().predict(
            training_rows=rows[:2],
            evaluation_rows=rows[2:],
            target_type=ForecastTargetType.VOLATILITY,
            information_cutoff=date(2025, 1, 1),
        )


def test_negative_volatility_targets_are_rejected() -> None:
    rows = _rows()
    invalid_training = replace(
        rows[0],
        target=replace(rows[0].target, realized_volatility_30d=-0.01),
    )

    with pytest.raises(ForecastModelInputError, match="non-negative"):
        VolatilityLinearRegressionCandidate().predict(
            training_rows=(invalid_training, rows[1]),
            evaluation_rows=rows[2:],
            target_type=ForecastTargetType.VOLATILITY,
            information_cutoff=date(2025, 1, 1),
        )

    invalid_evaluation = replace(
        rows[2],
        target=replace(rows[2].target, realized_volatility_30d=-0.01),
    )

    class ConstantCandidate:
        candidate_id = "constant-volatility"

        def predict(self, **kwargs):
            return CandidatePrediction(
                candidate_id=self.candidate_id,
                values=(0.0,) * len(kwargs["evaluation_rows"]),
                training_value_count=len(kwargs["training_rows"]),
            )

    with pytest.raises(ValueError, match="non-negative"):
        evaluate_candidate(
            dataset=_dataset((*rows[:2], invalid_evaluation, rows[3])),
            plan=_plan(),
            target_type=ForecastTargetType.VOLATILITY,
            candidate=ConstantCandidate(),
        )


def test_volatility_evaluation_preserves_endpoint_purge_and_selection_only() -> None:
    rows = _rows()
    leaking = _row(
        origin=date(2024, 12, 15),
        endpoint=date(2025, 1, 15),
        volatility=9.9,
        feature_start=9.0,
    )
    plan = ChronologicalEvaluationPlan(
        config=EvaluationPlanConfig(
            evaluation_end_exclusive=date(2025, 4, 1),
            minimum_training_origins=2,
        ),
        folds=(
            *_plan().folds,
            EvaluationFold(
                "calibration-01",
                FoldPurpose.CALIBRATION,
                date(2025, 2, 1),
                date(2025, 3, 1),
            ),
            EvaluationFold(
                "final-test-01",
                FoldPurpose.FINAL_TEST,
                date(2025, 3, 1),
                date(2025, 4, 1),
            ),
        ),
    )

    class SpyCandidate:
        candidate_id = "volatility-spy"

        def predict(self, **kwargs):
            assert tuple(
                row.target.realized_volatility_30d
                for row in kwargs["training_rows"]
            ) == (0.1, 0.2)
            return CandidatePrediction(
                candidate_id=self.candidate_id,
                values=(0.0,) * len(kwargs["evaluation_rows"]),
                training_value_count=len(kwargs["training_rows"]),
            )

    results = evaluate_candidate(
        dataset=_dataset((*rows[:2], leaking, *rows[2:])),
        plan=plan,
        target_type=ForecastTargetType.VOLATILITY,
        candidate=SpyCandidate(),
        fold_purposes=(FoldPurpose.SELECTION,),
    )

    assert tuple(result.fold_id for result in results) == ("selection-01",)
    assert results[0].negative_prediction_clipped_count == 0
