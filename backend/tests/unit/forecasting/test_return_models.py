from datetime import date, timedelta
import math
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler

from backend.app.forecasting.data import ForecastDataset, ForecastDatasetRow
from backend.app.forecasting.evaluation import (
    CandidatePrediction,
    ForecastTargetType,
    evaluate_candidate,
)
from backend.app.forecasting.features import FEATURE_NAMES, ForecastFeatureRow
from backend.app.forecasting.models import (
    ARIMA_CANDIDATE_ID,
    ARIMA_ORDER,
    LINEAR_REGRESSION_CANDIDATE_ID,
    RANDOM_FOREST_CANDIDATE_ID,
    RANDOM_FOREST_PARAMETERS,
    ArimaCandidate,
    ForecastModelInputError,
    LinearRegressionCandidate,
    RandomForestCandidate,
    build_linear_regression_pipeline,
    build_random_forest_regressor,
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
    return_value: float,
    feature_start: float = 1.0,
) -> ForecastDatasetRow:
    feature_values = {
        name: feature_start + index
        for index, name in enumerate(FEATURE_NAMES)
    }
    return ForecastDatasetRow(
        features=ForecastFeatureRow(
            symbol="AAPL",
            origin_date=origin,
            **feature_values,
        ),
        target=ForecastTargetRow(
            symbol="AAPL",
            origin_date=origin,
            requested_target_date=origin + timedelta(days=30),
            endpoint_date=endpoint,
            endpoint_slippage_days=(endpoint - (origin + timedelta(days=30))).days,
            return_30d=return_value,
            realized_volatility_30d=0.2,
        ),
    )


def _rows():
    return (
        _row(
            origin=date(2024, 1, 1),
            endpoint=date(2024, 2, 1),
            return_value=0.1,
            feature_start=1.0,
        ),
        _row(
            origin=date(2024, 2, 1),
            endpoint=date(2024, 3, 3),
            return_value=-0.2,
            feature_start=2.0,
        ),
        _row(
            origin=date(2025, 1, 1),
            endpoint=date(2025, 2, 1),
            return_value=0.3,
            feature_start=3.0,
        ),
        _row(
            origin=date(2025, 1, 2),
            endpoint=date(2025, 2, 2),
            return_value=-0.4,
            feature_start=4.0,
        ),
    )


def test_candidate_ids_and_fixed_model_configurations_are_stable() -> None:
    assert LinearRegressionCandidate().candidate_id == LINEAR_REGRESSION_CANDIDATE_ID
    assert ArimaCandidate().candidate_id == ARIMA_CANDIDATE_ID
    assert RandomForestCandidate().candidate_id == RANDOM_FOREST_CANDIDATE_ID
    assert ARIMA_ORDER == (1, 0, 1)
    assert RANDOM_FOREST_PARAMETERS == {
        "n_estimators": 200,
        "max_depth": 8,
        "min_samples_leaf": 5,
        "random_state": 42,
        "n_jobs": 1,
    }
    with pytest.raises(TypeError):
        ArimaCandidate(order=(2, 0, 0))
    with pytest.raises(TypeError):
        LinearRegressionCandidate(candidate_id="changed")


def test_linear_pipeline_contains_fold_local_scaler_then_regression() -> None:
    pipeline = build_linear_regression_pipeline()

    assert tuple(pipeline.named_steps) == ("scaler", "regressor")
    assert isinstance(pipeline.named_steps["scaler"], StandardScaler)
    assert isinstance(pipeline.named_steps["regressor"], LinearRegression)


def test_random_forest_builder_uses_only_approved_parameters() -> None:
    regressor = build_random_forest_regressor()
    parameters = regressor.get_params()

    for name, value in RANDOM_FOREST_PARAMETERS.items():
        assert parameters[name] == value


@pytest.mark.parametrize(
    "candidate",
    (
        LinearRegressionCandidate(),
        ArimaCandidate(),
        RandomForestCandidate(),
    ),
)
def test_phase4_candidates_reject_volatility_without_fitting(candidate) -> None:
    rows = _rows()

    with pytest.raises(ForecastModelInputError, match="only return_30d"):
        candidate.predict(
            training_rows=rows[:2],
            evaluation_rows=rows[2:],
            target_type=ForecastTargetType.VOLATILITY,
            information_cutoff=date(2025, 1, 1),
        )


def test_linear_adapter_uses_approved_feature_order_and_training_only_fit() -> None:
    rows = _rows()
    calls: dict[str, object] = {}

    class FakePipeline:
        def fit(self, features, targets):
            calls["fit_features"] = features
            calls["fit_targets"] = targets
            return self

        def predict(self, features):
            calls["prediction_features"] = features
            return (0.05, -0.05)

    with patch(
        "backend.app.forecasting.models.linear_regression."
        "build_linear_regression_pipeline",
        return_value=FakePipeline(),
    ):
        prediction = LinearRegressionCandidate().predict(
            training_rows=rows[:2],
            evaluation_rows=rows[2:],
            target_type=ForecastTargetType.RETURN,
            information_cutoff=date(2025, 1, 1),
        )

    assert calls["fit_features"] == (
        tuple(float(index + 1) for index in range(len(FEATURE_NAMES))),
        tuple(float(index + 2) for index in range(len(FEATURE_NAMES))),
    )
    assert calls["fit_targets"] == (0.1, -0.2)
    assert calls["prediction_features"] == (
        tuple(float(index + 3) for index in range(len(FEATURE_NAMES))),
        tuple(float(index + 4) for index in range(len(FEATURE_NAMES))),
    )
    assert prediction.values == (0.05, -0.05)
    assert prediction.training_value_count == 2


def test_random_forest_adapter_uses_mocked_estimator_without_mutation() -> None:
    rows = list(_rows())
    before = tuple(rows)

    class FakeRegressor:
        def fit(self, features, targets):
            assert targets == (0.1, -0.2)
            return self

        def predict(self, features):
            assert len(features) == 2
            return (0.01, 0.02)

    with patch(
        "backend.app.forecasting.models.random_forest."
        "build_random_forest_regressor",
        return_value=FakeRegressor(),
    ):
        prediction = RandomForestCandidate().predict(
            training_rows=rows[:2],
            evaluation_rows=rows[2:],
            target_type=ForecastTargetType.RETURN,
            information_cutoff=date(2025, 1, 1),
        )

    assert prediction.values == (0.01, 0.02)
    assert tuple(rows) == before


def test_arima_sorts_targets_and_does_not_read_evaluation_actuals() -> None:
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
            return (0.04, -0.03)

    class FakeArima:
        def __init__(self, targets, *, order):
            captured["targets"] = targets
            captured["order"] = order

        def fit(self):
            return FakeFitted()

    with patch("backend.app.forecasting.models.arima.ARIMA", FakeArima):
        prediction = ArimaCandidate().predict(
            training_rows=(rows[1], rows[0]),
            evaluation_rows=evaluation_rows,
            target_type=ForecastTargetType.RETURN,
            information_cutoff=date(2025, 1, 1),
        )

    assert captured == {
        "targets": (0.1, -0.2),
        "order": (1, 0, 1),
        "steps": 2,
    }
    assert prediction.values == (0.04, -0.03)


def test_model_adapter_rejects_non_finite_mock_prediction() -> None:
    rows = _rows()

    class FakePipeline:
        def fit(self, features, targets):
            return self

        def predict(self, features):
            return (math.nan, 0.0)

    with (
        patch(
            "backend.app.forecasting.models.linear_regression."
            "build_linear_regression_pipeline",
            return_value=FakePipeline(),
        ),
        pytest.raises(ForecastModelInputError, match="finite"),
    ):
        LinearRegressionCandidate().predict(
            training_rows=rows[:2],
            evaluation_rows=rows[2:],
            target_type=ForecastTargetType.RETURN,
            information_cutoff=date(2025, 1, 1),
        )


def test_model_adapter_rejects_wrong_mock_prediction_count() -> None:
    rows = _rows()

    class FakePipeline:
        def fit(self, features, targets):
            return self

        def predict(self, features):
            return (0.0,)

    with (
        patch(
            "backend.app.forecasting.models.linear_regression."
            "build_linear_regression_pipeline",
            return_value=FakePipeline(),
        ),
        pytest.raises(ForecastModelInputError, match="count"),
    ):
        LinearRegressionCandidate().predict(
            training_rows=rows[:2],
            evaluation_rows=rows[2:],
            target_type=ForecastTargetType.RETURN,
            information_cutoff=date(2025, 1, 1),
        )


def test_model_adapter_rejects_two_dimensional_mock_predictions() -> None:
    rows = _rows()

    class FakePipeline:
        def fit(self, features, targets):
            return self

        def predict(self, features):
            return ((0.0,), (0.0,))

    with (
        patch(
            "backend.app.forecasting.models.linear_regression."
            "build_linear_regression_pipeline",
            return_value=FakePipeline(),
        ),
        pytest.raises(ForecastModelInputError, match="one-dimensional"),
    ):
        LinearRegressionCandidate().predict(
            training_rows=rows[:2],
            evaluation_rows=rows[2:],
            target_type=ForecastTargetType.RETURN,
            information_cutoff=date(2025, 1, 1),
        )


def test_supervised_adapter_defensively_rejects_unpurged_training_target() -> None:
    rows = _rows()
    unpurged = _row(
        origin=date(2024, 12, 1),
        endpoint=date(2025, 1, 1),
        return_value=10.0,
    )

    with pytest.raises(ForecastModelInputError, match="before"):
        LinearRegressionCandidate().predict(
            training_rows=(*rows[:2], unpurged),
            evaluation_rows=rows[2:],
            target_type=ForecastTargetType.RETURN,
            information_cutoff=date(2025, 1, 1),
        )


def test_estimator_failure_is_explicitly_unavailable() -> None:
    rows = _rows()

    class FailingRegressor:
        def fit(self, features, targets):
            raise RuntimeError("synthetic fit failure")

    with patch(
        "backend.app.forecasting.models.random_forest."
        "build_random_forest_regressor",
        return_value=FailingRegressor(),
    ):
        prediction = RandomForestCandidate().predict(
            training_rows=rows[:2],
            evaluation_rows=rows[2:],
            target_type=ForecastTargetType.RETURN,
            information_cutoff=date(2025, 1, 1),
        )

    assert prediction.available is False
    assert prediction.warning is not None
    assert "synthetic fit failure" in prediction.warning


def test_selection_only_evaluation_preserves_endpoint_purge() -> None:
    cutoff = date(2025, 1, 1)
    rows = _rows()
    leaking = _row(
        origin=date(2024, 12, 15),
        endpoint=date(2025, 1, 15),
        return_value=99.0,
    )
    dataset = ForecastDataset(
        symbol="AAPL",
        feature_set_version="forecast-features-v1",
        target_set_version="forecast-targets-v1",
        max_feature_lookback=252,
        minimum_label_complete_training_origins=2,
        price_observation_count=1000,
        feature_origin_count=5,
        target_origin_count=5,
        rows=(*rows[:2], leaking, *rows[2:]),
    )
    plan = ChronologicalEvaluationPlan(
        config=EvaluationPlanConfig(
            evaluation_end_exclusive=date(2026, 1, 1),
            minimum_training_origins=2,
        ),
        folds=(
            EvaluationFold(
                "selection-01",
                FoldPurpose.SELECTION,
                cutoff,
                date(2025, 2, 1),
            ),
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
                date(2026, 1, 1),
            ),
        ),
    )

    class SpyCandidate:
        candidate_id = "spy"

        def predict(
            self,
            *,
            training_rows,
            evaluation_rows,
            target_type,
            information_cutoff,
        ):
            assert tuple(row.target.return_30d for row in training_rows) == (
                0.1,
                -0.2,
            )
            assert information_cutoff == cutoff
            return CandidatePrediction(
                candidate_id=self.candidate_id,
                values=tuple(0.0 for _ in evaluation_rows),
                training_value_count=len(training_rows),
            )

    results = evaluate_candidate(
        dataset=dataset,
        plan=plan,
        target_type=ForecastTargetType.RETURN,
        candidate=SpyCandidate(),
        fold_purposes=(FoldPurpose.SELECTION,),
    )

    assert tuple(result.fold_id for result in results) == ("selection-01",)
    assert results[0].mae == pytest.approx(0.35)
    assert results[0].rmse == pytest.approx(math.sqrt(0.125))
    assert results[0].directional_accuracy == 0.0
