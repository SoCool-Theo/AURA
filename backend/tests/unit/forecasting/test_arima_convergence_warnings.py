from dataclasses import replace
from datetime import date, timedelta
import math
import warnings
from unittest.mock import patch

import pytest
from statsmodels.tools.sm_exceptions import ConvergenceWarning

from backend.app.forecasting.data import ForecastDataset, ForecastDatasetRow
from backend.app.forecasting.evaluation import (
    ForecastTargetType,
    evaluate_candidate,
)
from backend.app.forecasting.features import FEATURE_NAMES, ForecastFeatureRow
from backend.app.forecasting.models import (
    ARIMA_FIT_CONVERGENCE_WARNING,
    ARIMA_ORDER,
    ArimaCandidate,
    ForecastModelInputError,
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
) -> ForecastDatasetRow:
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
            endpoint_slippage_days=(endpoint - (origin + timedelta(days=30))).days,
            return_30d=return_value,
            realized_volatility_30d=0.2,
        ),
    )


def _rows() -> tuple[ForecastDatasetRow, ...]:
    return (
        _row(
            origin=date(2024, 1, 1),
            endpoint=date(2024, 2, 1),
            return_value=0.1,
        ),
        _row(
            origin=date(2024, 2, 1),
            endpoint=date(2024, 3, 3),
            return_value=-0.2,
        ),
        _row(
            origin=date(2025, 1, 1),
            endpoint=date(2025, 2, 1),
            return_value=0.3,
        ),
        _row(
            origin=date(2025, 1, 2),
            endpoint=date(2025, 2, 2),
            return_value=-0.4,
        ),
    )


class _FiniteFitted:
    def forecast(self, *, steps):
        return tuple(0.0 for _ in range(steps))


class _CleanArima:
    def __init__(self, targets, *, order):
        assert order == ARIMA_ORDER

    def fit(self):
        return _FiniteFitted()


class _WarningArima:
    def __init__(self, targets, *, order):
        assert order == ARIMA_ORDER

    def fit(self):
        warnings.warn("optimizer did not converge", ConvergenceWarning)
        return _FiniteFitted()


def _predict_with(arima_type):
    rows = _rows()
    with patch("backend.app.forecasting.models.arima.ARIMA", arima_type):
        prediction = ArimaCandidate().predict(
            training_rows=rows[:2],
            evaluation_rows=rows[2:],
            target_type=ForecastTargetType.RETURN,
            information_cutoff=date(2025, 1, 1),
        )
    return prediction


def test_successful_arima_fit_without_warning_has_null_metadata() -> None:
    prediction = _predict_with(_CleanArima)

    assert prediction.available
    assert prediction.warning is None


def test_convergence_warning_keeps_prediction_available_and_is_stable() -> None:
    training_rows = list(_rows()[:2])
    evaluation_rows = list(_rows()[2:])
    training_before = list(training_rows)
    evaluation_before = list(evaluation_rows)

    class WarningAndUnrelatedArima(_WarningArima):
        def fit(self):
            warnings.warn("unrelated diagnostic", UserWarning)
            return super().fit()

    with (
        pytest.warns(UserWarning, match="unrelated diagnostic"),
        patch(
            "backend.app.forecasting.models.arima.ARIMA",
            WarningAndUnrelatedArima,
        ),
    ):
        prediction = ArimaCandidate().predict(
            training_rows=training_rows,
            evaluation_rows=evaluation_rows,
            target_type=ForecastTargetType.RETURN,
            information_cutoff=date(2025, 1, 1),
        )

    assert prediction.available
    assert prediction.warning == ARIMA_FIT_CONVERGENCE_WARNING
    assert training_rows == training_before
    assert evaluation_rows == evaluation_before


def test_arima_fit_failure_retains_unavailable_behavior() -> None:
    class FailingArima(_CleanArima):
        def fit(self):
            raise RuntimeError("synthetic fit failure")

    prediction = _predict_with(FailingArima)

    assert prediction.available is False
    assert prediction.warning is not None
    assert "synthetic fit failure" in prediction.warning


def test_arima_non_finite_prediction_validation_is_unchanged() -> None:
    class NonFiniteFitted:
        def forecast(self, *, steps):
            return (math.nan,) * steps

    class NonFiniteArima(_WarningArima):
        def fit(self):
            warnings.warn("optimizer did not converge", ConvergenceWarning)
            return NonFiniteFitted()

    with pytest.raises(ForecastModelInputError, match="finite"):
        _predict_with(NonFiniteArima)


def test_warning_metadata_does_not_change_evaluation_metrics() -> None:
    rows = _rows()
    dataset = ForecastDataset(
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
    fold = EvaluationFold(
        fold_id="selection-01",
        purpose=FoldPurpose.SELECTION,
        origin_start=date(2025, 1, 1),
        origin_end=date(2025, 2, 1),
    )
    plan = ChronologicalEvaluationPlan(
        config=EvaluationPlanConfig(
            evaluation_end_exclusive=date(2025, 2, 1),
            minimum_training_origins=2,
        ),
        folds=(fold,),
    )

    with patch("backend.app.forecasting.models.arima.ARIMA", _CleanArima):
        clean = evaluate_candidate(
            dataset=dataset,
            plan=plan,
            target_type=ForecastTargetType.RETURN,
            candidate=ArimaCandidate(),
        )[0]
    with patch("backend.app.forecasting.models.arima.ARIMA", _WarningArima):
        warned = evaluate_candidate(
            dataset=dataset,
            plan=plan,
            target_type=ForecastTargetType.RETURN,
            candidate=ArimaCandidate(),
        )[0]

    assert warned.prediction_available
    assert warned.warning == ARIMA_FIT_CONVERGENCE_WARNING
    assert replace(warned, warning=None) == clean
