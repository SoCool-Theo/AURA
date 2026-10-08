from dataclasses import dataclass, replace
from datetime import date, timedelta
import math

import pytest

from backend.app.forecasting.baselines import (
    HistoricalMeanBaseline,
    MovingAverageBaseline,
)
from backend.app.forecasting.data import ForecastDataset, ForecastDatasetRow
from backend.app.forecasting.evaluation import (
    CandidatePrediction,
    ForecastTargetType,
    evaluate_candidate,
)
from backend.app.forecasting.features import ForecastFeatureRow
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
    volatility_value: float,
) -> ForecastDatasetRow:
    return ForecastDatasetRow(
        features=ForecastFeatureRow(
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
        ),
        target=ForecastTargetRow(
            symbol="AAPL",
            origin_date=origin,
            requested_target_date=origin + timedelta(days=30),
            endpoint_date=endpoint,
            endpoint_slippage_days=0,
            return_30d=return_value,
            realized_volatility_30d=volatility_value,
        ),
    )


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


def _plan(*, minimum_training_origins: int = 2) -> ChronologicalEvaluationPlan:
    fold = EvaluationFold(
        fold_id="selection-01",
        purpose=FoldPurpose.SELECTION,
        origin_start=date(2025, 6, 1),
        origin_end=date(2025, 7, 1),
    )
    config = EvaluationPlanConfig(
        evaluation_end_exclusive=date(2025, 7, 1),
        minimum_training_origins=minimum_training_origins,
    )
    return ChronologicalEvaluationPlan(config=config, folds=(fold,))


def _evaluation_dataset() -> ForecastDataset:
    return _dataset(
        (
            _row(
                origin=date(2025, 1, 1),
                endpoint=date(2025, 2, 1),
                return_value=0.1,
                volatility_value=0.2,
            ),
            _row(
                origin=date(2025, 2, 1),
                endpoint=date(2025, 3, 1),
                return_value=0.3,
                volatility_value=0.4,
            ),
            _row(
                origin=date(2025, 5, 20),
                endpoint=date(2025, 6, 20),
                return_value=99.0,
                volatility_value=99.0,
            ),
            _row(
                origin=date(2025, 6, 1),
                endpoint=date(2025, 7, 1),
                return_value=0.2,
                volatility_value=0.5,
            ),
            _row(
                origin=date(2025, 6, 15),
                endpoint=date(2025, 7, 15),
                return_value=-0.2,
                volatility_value=0.3,
            ),
        )
    )


def test_evaluator_preserves_contract_and_purges_future_label() -> None:
    results = evaluate_candidate(
        dataset=_evaluation_dataset(),
        plan=_plan(),
        target_type=ForecastTargetType.RETURN,
        candidate=HistoricalMeanBaseline(),
    )

    assert len(results) == 1
    result = results[0]
    assert result.symbol == "AAPL"
    assert result.target_type is ForecastTargetType.RETURN
    assert result.candidate_id == "historical_average"
    assert result.fold_id == "selection-01"
    assert result.fold_purpose is FoldPurpose.SELECTION
    assert result.training_cutoff == date(2025, 6, 1)
    assert result.training_observation_count == 2
    assert result.candidate_training_value_count == 2
    assert result.evaluated_observation_count == 2
    assert result.prediction_available is True
    assert result.mae == pytest.approx(0.2)
    assert result.rmse == pytest.approx(math.sqrt(0.08))
    assert result.directional_accuracy == 0.5
    assert result.directional_evaluated_count == 2
    assert result.return_mape is not None
    assert result.return_mape.included_count == 2
    assert result.warning is None


def test_volatility_evaluation_omits_direction_and_mape() -> None:
    result = evaluate_candidate(
        dataset=_evaluation_dataset(),
        plan=_plan(),
        target_type=ForecastTargetType.VOLATILITY,
        candidate=HistoricalMeanBaseline(),
    )[0]

    assert result.prediction_available is True
    assert result.mae == pytest.approx(0.1)
    assert result.rmse == pytest.approx(math.sqrt(0.02))
    assert result.directional_accuracy is None
    assert result.directional_evaluated_count is None
    assert result.return_mape is None


def test_evaluator_preserves_756_origin_minimum() -> None:
    base = date(2020, 1, 1)
    training = tuple(
        _row(
            origin=base + timedelta(days=index),
            endpoint=base + timedelta(days=index + 30),
            return_value=0.1,
            volatility_value=0.2,
        )
        for index in range(755)
    )
    evaluation = _row(
        origin=date(2025, 6, 1),
        endpoint=date(2025, 7, 1),
        return_value=0.1,
        volatility_value=0.2,
    )

    result = evaluate_candidate(
        dataset=_dataset((*training, evaluation)),
        plan=_plan(minimum_training_origins=756),
        target_type=ForecastTargetType.RETURN,
        candidate=HistoricalMeanBaseline(),
    )[0]

    assert result.prediction_available is False
    assert result.training_observation_count == 755
    assert result.mae is None
    assert result.warning is not None
    assert "755 < 756" in result.warning


def test_evaluator_represents_moving_average_unavailability() -> None:
    result = evaluate_candidate(
        dataset=_evaluation_dataset(),
        plan=_plan(),
        target_type=ForecastTargetType.RETURN,
        candidate=MovingAverageBaseline(),
    )[0]

    assert result.prediction_available is False
    assert result.candidate_training_value_count == 0
    assert result.mae is None
    assert result.warning is not None
    assert "at least 20" in result.warning


@dataclass(frozen=True)
class _ConstantCandidate:
    candidate_id: str = "future-candidate-adapter"
    value: float = 0.0

    def predict(self, *, training_rows, evaluation_rows, target_type, information_cutoff):
        return CandidatePrediction(
            candidate_id=self.candidate_id,
            values=tuple(self.value for _ in evaluation_rows),
            training_value_count=len(training_rows),
        )


def test_candidate_agnostic_boundary_accepts_future_adapter_shape() -> None:
    result = evaluate_candidate(
        dataset=_evaluation_dataset(),
        plan=_plan(),
        target_type=ForecastTargetType.RETURN,
        candidate=_ConstantCandidate(),
    )[0]

    assert result.candidate_id == "future-candidate-adapter"
    assert result.prediction_available is True
    assert result.evaluated_observation_count == 2


def test_evaluator_rejects_non_finite_candidate_predictions() -> None:
    with pytest.raises(ValueError, match="finite"):
        evaluate_candidate(
            dataset=_evaluation_dataset(),
            plan=_plan(),
            target_type=ForecastTargetType.RETURN,
            candidate=_ConstantCandidate(value=math.nan),
        )


def test_future_label_change_cannot_affect_earlier_fold_result() -> None:
    dataset = _evaluation_dataset()
    future_row = dataset.rows[2]
    changed_future = replace(
        future_row,
        target=replace(
            future_row.target,
            return_30d=-9999.0,
            realized_volatility_30d=9999.0,
        ),
    )
    changed_dataset = replace(
        dataset,
        rows=(*dataset.rows[:2], changed_future, *dataset.rows[3:]),
    )

    original = evaluate_candidate(
        dataset=dataset,
        plan=_plan(),
        target_type=ForecastTargetType.RETURN,
        candidate=HistoricalMeanBaseline(),
    )
    changed = evaluate_candidate(
        dataset=changed_dataset,
        plan=_plan(),
        target_type=ForecastTargetType.RETURN,
        candidate=HistoricalMeanBaseline(),
    )

    assert changed == original


def test_evaluation_is_deterministic_and_does_not_mutate_dataset() -> None:
    dataset = _evaluation_dataset()
    rows_before = dataset.rows

    first = evaluate_candidate(
        dataset=dataset,
        plan=_plan(),
        target_type=ForecastTargetType.RETURN,
        candidate=HistoricalMeanBaseline(),
    )
    second = evaluate_candidate(
        dataset=dataset,
        plan=_plan(),
        target_type=ForecastTargetType.RETURN,
        candidate=HistoricalMeanBaseline(),
    )

    assert first == second
    assert dataset.rows is rows_before
