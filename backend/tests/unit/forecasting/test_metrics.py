import math

import pytest

from backend.app.forecasting.metrics import (
    ForecastMetricError,
    directional_accuracy,
    mean_absolute_error,
    root_mean_squared_error,
    safe_return_mape,
)


def test_mae_and_rmse_are_deterministic() -> None:
    actual = (1.0, 2.0, 4.0)
    predicted = (2.0, 2.0, 1.0)

    assert mean_absolute_error(actual, predicted) == pytest.approx(4.0 / 3.0)
    assert root_mean_squared_error(actual, predicted) == pytest.approx(
        math.sqrt(10.0 / 3.0)
    )


def test_directional_accuracy_uses_three_state_signs_including_zero() -> None:
    result = directional_accuracy(
        actual=(-0.1, 0.0, 0.2, 0.0),
        predicted=(-0.3, 0.0, -0.1, 0.01),
    )

    assert result.value == 0.5
    assert result.evaluated_count == 4


def test_safe_mape_excludes_returns_below_one_percent() -> None:
    result = safe_return_mape(
        actual=(0.005, -0.009, 0.02, -0.04),
        predicted=(0.5, 0.5, 0.01, -0.02),
    )

    assert result.value == pytest.approx(50.0)
    assert result.included_count == 2
    assert result.excluded_count == 2
    assert result.minimum_absolute_actual == 0.01
    assert result.available is True


def test_safe_mape_includes_actual_at_exact_one_percent_boundary() -> None:
    result = safe_return_mape(actual=(0.01,), predicted=(0.0,))

    assert result.value == pytest.approx(100.0)
    assert result.included_count == 1
    assert result.excluded_count == 0


def test_safe_mape_is_explicitly_unavailable_when_all_actuals_are_small() -> None:
    result = safe_return_mape(
        actual=(0.0, 0.005, -0.009999),
        predicted=(0.1, 0.1, 0.1),
    )

    assert result.value is None
    assert result.included_count == 0
    assert result.excluded_count == 3
    assert result.available is False


@pytest.mark.parametrize("invalid", [math.nan, math.inf, -math.inf])
def test_metrics_reject_nan_and_infinity(invalid: float) -> None:
    with pytest.raises(ForecastMetricError, match="finite"):
        mean_absolute_error((0.1, invalid), (0.1, 0.2))
    with pytest.raises(ForecastMetricError, match="finite"):
        root_mean_squared_error((0.1, 0.2), (0.1, invalid))
    with pytest.raises(ForecastMetricError, match="finite"):
        directional_accuracy((invalid,), (0.1,))
    with pytest.raises(ForecastMetricError, match="finite"):
        safe_return_mape((0.1,), (invalid,))


def test_metrics_reject_non_finite_results_from_finite_extremes() -> None:
    with pytest.raises(ForecastMetricError, match="result must be finite"):
        mean_absolute_error((1e308,), (-1e308,))
    with pytest.raises(ForecastMetricError, match="result must be finite"):
        root_mean_squared_error((1e308,), (-1e308,))
    with pytest.raises(ForecastMetricError, match="result must be finite"):
        safe_return_mape((0.01,), (1e308,))


def test_metrics_reject_empty_or_misaligned_inputs() -> None:
    with pytest.raises(ForecastMetricError, match="empty"):
        mean_absolute_error((), ())
    with pytest.raises(ForecastMetricError, match="lengths"):
        root_mean_squared_error((1.0,), (1.0, 2.0))


def test_metrics_do_not_mutate_caller_sequences() -> None:
    actual = [0.02, -0.03]
    predicted = [0.01, -0.01]
    actual_before = list(actual)
    predicted_before = list(predicted)

    mean_absolute_error(actual, predicted)
    root_mean_squared_error(actual, predicted)
    directional_accuracy(actual, predicted)
    safe_return_mape(actual, predicted)

    assert actual == actual_before
    assert predicted == predicted_before
