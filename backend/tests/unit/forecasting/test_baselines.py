from datetime import date, timedelta

import pytest

from backend.app.forecasting.baselines import (
    HistoricalMeanBaseline,
    MovingAverageBaseline,
)
from backend.app.forecasting.data import ForecastDatasetRow
from backend.app.forecasting.evaluation import ForecastTargetType
from backend.app.forecasting.features import ForecastFeatureRow
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


def _evaluation_row() -> ForecastDatasetRow:
    return _row(
        origin=date(2026, 4, 1),
        endpoint=date(2026, 5, 1),
        return_value=0.0,
        volatility_value=0.0,
    )


def test_historical_mean_uses_only_labels_completed_before_cutoff() -> None:
    cutoff = date(2026, 4, 1)
    completed = (
        _row(
            origin=date(2026, 1, 1),
            endpoint=date(2026, 2, 1),
            return_value=0.1,
            volatility_value=0.2,
        ),
        _row(
            origin=date(2026, 2, 1),
            endpoint=date(2026, 3, 1),
            return_value=0.3,
            volatility_value=0.4,
        ),
    )
    future = _row(
        origin=date(2026, 3, 20),
        endpoint=cutoff,
        return_value=99.0,
        volatility_value=99.0,
    )

    prediction = HistoricalMeanBaseline().predict(
        training_rows=(*completed, future),
        evaluation_rows=(_evaluation_row(),),
        target_type=ForecastTargetType.RETURN,
        information_cutoff=cutoff,
    )

    assert prediction.values == pytest.approx((0.2,))
    assert prediction.training_value_count == 2


def test_historical_mean_keeps_return_and_volatility_targets_separate() -> None:
    rows = (
        _row(
            origin=date(2026, 1, 1),
            endpoint=date(2026, 2, 1),
            return_value=1.0,
            volatility_value=10.0,
        ),
        _row(
            origin=date(2026, 2, 1),
            endpoint=date(2026, 3, 1),
            return_value=3.0,
            volatility_value=14.0,
        ),
    )
    baseline = HistoricalMeanBaseline()
    common = {
        "training_rows": rows,
        "evaluation_rows": (_evaluation_row(),),
        "information_cutoff": date(2026, 4, 1),
    }

    return_prediction = baseline.predict(
        **common,
        target_type=ForecastTargetType.RETURN,
    )
    volatility_prediction = baseline.predict(
        **common,
        target_type=ForecastTargetType.VOLATILITY,
    )

    assert return_prediction.values == pytest.approx((2.0,))
    assert volatility_prediction.values == pytest.approx((12.0,))


def test_moving_average_uses_90_calendar_days_not_last_90_rows() -> None:
    cutoff = date(2026, 4, 1)
    old_rows = tuple(
        _row(
            origin=date(2025, 1, 1) + timedelta(days=index),
            endpoint=date(2025, 2, 1) + timedelta(days=index),
            return_value=100.0,
            volatility_value=100.0,
        )
        for index in range(100)
    )
    recent_rows = tuple(
        _row(
            origin=date(2025, 12, 1) + timedelta(days=index),
            endpoint=date(2026, 1, 1) + timedelta(days=index),
            return_value=float(index),
            volatility_value=float(index + 1),
        )
        for index in range(20)
    )

    prediction = MovingAverageBaseline().predict(
        training_rows=(*old_rows, *recent_rows),
        evaluation_rows=(_evaluation_row(),),
        target_type=ForecastTargetType.RETURN,
        information_cutoff=cutoff,
    )

    assert prediction.training_value_count == 20
    assert prediction.values == pytest.approx((9.5,))


def test_moving_average_is_unavailable_below_20_completed_labels() -> None:
    cutoff = date(2026, 4, 1)
    rows = tuple(
        _row(
            origin=date(2025, 12, 1) + timedelta(days=index),
            endpoint=date(2026, 1, 1) + timedelta(days=index),
            return_value=0.1,
            volatility_value=0.2,
        )
        for index in range(19)
    )

    prediction = MovingAverageBaseline().predict(
        training_rows=rows,
        evaluation_rows=(_evaluation_row(),),
        target_type=ForecastTargetType.RETURN,
        information_cutoff=cutoff,
    )

    assert prediction.available is False
    assert prediction.values is None
    assert prediction.training_value_count == 19
    assert prediction.warning is not None
    assert "at least 20" in prediction.warning


def test_moving_average_does_not_fall_back_to_old_history() -> None:
    cutoff = date(2026, 4, 1)
    old_rows = tuple(
        _row(
            origin=date(2024, 1, 1) + timedelta(days=index),
            endpoint=date(2024, 2, 1) + timedelta(days=index),
            return_value=0.1,
            volatility_value=0.2,
        )
        for index in range(100)
    )

    prediction = MovingAverageBaseline().predict(
        training_rows=old_rows,
        evaluation_rows=(_evaluation_row(),),
        target_type=ForecastTargetType.RETURN,
        information_cutoff=cutoff,
    )

    assert prediction.available is False
    assert prediction.training_value_count == 0


def test_baselines_do_not_mutate_input_rows() -> None:
    rows = [
        _row(
            origin=date(2026, 1, 1) + timedelta(days=index),
            endpoint=date(2026, 2, 1) + timedelta(days=index),
            return_value=float(index),
            volatility_value=float(index),
        )
        for index in range(20)
    ]
    rows_before = list(rows)
    evaluation_rows = [_evaluation_row()]
    evaluation_before = list(evaluation_rows)

    for baseline in (HistoricalMeanBaseline(), MovingAverageBaseline()):
        baseline.predict(
            training_rows=rows,
            evaluation_rows=evaluation_rows,
            target_type=ForecastTargetType.RETURN,
            information_cutoff=date(2026, 4, 1),
        )

    assert rows == rows_before
    assert evaluation_rows == evaluation_before
