from collections import OrderedDict
from dataclasses import FrozenInstanceError
import inspect
import math
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

import backend.app.scenarios.simulator as simulator_module
from backend.app.analytics.drawdown import calculate_max_drawdown_details
from backend.app.analytics.returns import (
    calculate_asset_returns,
    calculate_cumulative_return,
    calculate_portfolio_returns,
)
from backend.app.analytics.sharpe import calculate_sharpe_ratio
from backend.app.analytics.volatility import calculate_annualized_volatility
from backend.app.scenarios.simulator import (
    AllocationComparisonResult,
    HistoricalSimulationResult,
    HistoricalTrajectoryPoint,
    simulate_allocation_change,
    simulate_historical_scenario,
)


def _prices() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ALPHA": [100.0, 110.0, 99.0, 108.9],
            "BETA": [100.0, 100.0, 110.0, 110.0],
        },
        index=pd.DatetimeIndex(
            ["2020-02-03", "2020-02-04", "2020-02-05", "2020-02-06"]
        ),
    )


def _weights() -> OrderedDict[str, float]:
    return OrderedDict((("ALPHA", 0.6), ("BETA", 0.4)))


def _modified_weights() -> OrderedDict[str, float]:
    return OrderedDict((("ALPHA", 0.2), ("BETA", 0.8)))


def _mixed_sharpe_prices() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ALPHA": [100.0, 200.0, 400.0, 800.0],
            "BETA": [100.0, 100.0, 200.0, 200.0],
        },
        index=pd.date_range("2020-01-01", periods=4),
    )


def _portfolio_returns(
    prices: pd.DataFrame | None = None,
    weights: OrderedDict[str, float] | None = None,
) -> pd.Series:
    selected_prices = _prices() if prices is None else prices
    selected_weights = _weights() if weights is None else weights
    return calculate_portfolio_returns(
        calculate_asset_returns(selected_prices),
        selected_weights,
    )


def test_simple_multi_asset_simulation_has_hand_checkable_values() -> None:
    result = simulate_historical_scenario(_prices(), _weights())

    assert isinstance(result, HistoricalSimulationResult)
    assert result.normalized_starting_value == 1.0
    assert result.normalized_ending_value == pytest.approx(1.101128)
    assert result.cumulative_return == pytest.approx(0.101128)
    assert [point.normalized_value for point in result.trajectory] == pytest.approx(
        [1.0, 1.06, 1.0388, 1.101128]
    )


def test_effective_dates_and_observation_counts_come_from_prepared_frame() -> None:
    result = simulate_historical_scenario(_prices(), _weights())

    assert result.effective_start_date == pd.Timestamp("2020-02-03")
    assert result.effective_end_date == pd.Timestamp("2020-02-06")
    assert result.price_observation_count == 4
    assert result.return_observation_count == 3
    assert result.return_observation_count == result.price_observation_count - 1


def test_trajectory_contains_one_point_per_price_with_initial_baseline() -> None:
    result = simulate_historical_scenario(_prices(), _weights())

    assert len(result.trajectory) == result.price_observation_count
    assert result.trajectory[0] == HistoricalTrajectoryPoint(
        date=pd.Timestamp("2020-02-03"),
        normalized_value=1.0,
    )
    assert result.trajectory[-1].date == result.effective_end_date
    assert (
        result.trajectory[-1].normalized_value
        == result.normalized_ending_value
    )


def test_cumulative_return_matches_existing_analytics_and_ending_value() -> None:
    portfolio_returns = _portfolio_returns()
    result = simulate_historical_scenario(_prices(), _weights())

    assert result.cumulative_return == pytest.approx(
        calculate_cumulative_return(portfolio_returns)
    )
    assert result.cumulative_return == pytest.approx(
        result.normalized_ending_value - 1.0
    )


def test_simulator_preserves_periodically_rebalanced_weighting_semantics() -> None:
    portfolio_returns = _portfolio_returns()

    assert portfolio_returns.to_numpy() == pytest.approx([0.06, -0.02, 0.06])

    result = simulate_historical_scenario(_prices(), _weights())

    assert [point.normalized_value for point in result.trajectory] == pytest.approx(
        [1.0, 1.06, 1.0388, 1.101128]
    )


def test_annualized_volatility_reuses_existing_default_behavior() -> None:
    portfolio_returns = _portfolio_returns()
    result = simulate_historical_scenario(_prices(), _weights())

    assert result.annualized_volatility == pytest.approx(
        calculate_annualized_volatility(portfolio_returns)
    )


def test_defined_sharpe_reuses_existing_defaults() -> None:
    portfolio_returns = _portfolio_returns()
    result = simulate_historical_scenario(_prices(), _weights())

    assert result.sharpe_ratio == pytest.approx(
        calculate_sharpe_ratio(portfolio_returns)
    )


def test_undefined_sharpe_becomes_none_without_failing_simulation() -> None:
    prices = pd.DataFrame(
        {"CONSTANT": [100.0, 110.0, 121.0]},
        index=pd.DatetimeIndex(["2020-01-01", "2020-01-02", "2020-01-03"]),
    )

    result = simulate_historical_scenario(prices, {"CONSTANT": 1.0})

    assert result.sharpe_ratio is None
    assert result.annualized_volatility == pytest.approx(0.0)
    assert result.normalized_ending_value == pytest.approx(1.21)
    assert result.cumulative_return == pytest.approx(0.21)


def test_unexpected_sharpe_error_is_not_silently_rewritten() -> None:
    failure = ValueError("unexpected Sharpe failure")

    with patch.object(
        simulator_module,
        "calculate_sharpe_ratio",
        side_effect=failure,
    ):
        with pytest.raises(ValueError) as raised:
            simulate_historical_scenario(_prices(), _weights())

    assert raised.value is failure


def test_maximum_drawdown_preserves_existing_negative_value_and_dates() -> None:
    portfolio_returns = _portfolio_returns()
    expected = calculate_max_drawdown_details(portfolio_returns)

    result = simulate_historical_scenario(_prices(), _weights())

    assert result.maximum_drawdown == expected
    assert result.maximum_drawdown.max_drawdown == pytest.approx(-0.02)
    assert result.maximum_drawdown.peak_date == pd.Timestamp("2020-02-04")
    assert result.maximum_drawdown.trough_date == pd.Timestamp("2020-02-05")


def test_trajectory_order_is_deterministic_and_matches_price_order() -> None:
    first = simulate_historical_scenario(_prices(), _weights())
    second = simulate_historical_scenario(_prices(), _weights())

    expected_dates = tuple(_prices().index)
    assert tuple(point.date for point in first.trajectory) == expected_dates
    assert first.trajectory == second.trajectory


@pytest.mark.parametrize("price_count", [0, 1, 2])
def test_fewer_than_three_prices_are_rejected(price_count: int) -> None:
    prices = _prices().iloc[:price_count]

    with pytest.raises(ValueError, match="at least three rows"):
        simulate_historical_scenario(prices, _weights())


def test_simulator_does_not_mutate_prices_or_their_axes() -> None:
    prices = _prices()
    snapshot = prices.copy(deep=True)
    index_identity = id(prices.index)
    columns_identity = id(prices.columns)

    simulate_historical_scenario(prices, _weights())

    pd.testing.assert_frame_equal(prices, snapshot)
    assert id(prices.index) == index_identity
    assert id(prices.columns) == columns_identity
    assert list(prices.columns) == ["ALPHA", "BETA"]


def test_simulator_does_not_mutate_weight_mapping_or_order() -> None:
    weights = _weights()
    snapshot = list(weights.items())
    identity = id(weights)

    simulate_historical_scenario(_prices(), weights)

    assert id(weights) == identity
    assert list(weights.items()) == snapshot


@pytest.mark.parametrize(
    ("prices", "weights", "exception_type", "message"),
    [
        (
            pd.DataFrame(
                {"ALPHA": [100.0, 101.0, 102.0]},
                index=pd.DatetimeIndex(
                    ["2020-01-03", "2020-01-02", "2020-01-01"]
                ),
            ),
            {"ALPHA": 1.0},
            ValueError,
            "strictly increasing",
        ),
        (
            pd.DataFrame(
                {"ALPHA": [100.0, np.nan, 102.0]},
                index=pd.date_range("2020-01-01", periods=3),
            ),
            {"ALPHA": 1.0},
            ValueError,
            "missing",
        ),
        (_prices(), {"ALPHA": 1.0}, ValueError, "exactly match"),
        (_prices(), {"ALPHA": 0.5, "BETA": 0.4}, ValueError, "total weight"),
    ],
)
def test_existing_analytics_validation_remains_effective(
    prices: pd.DataFrame,
    weights: dict[str, float],
    exception_type: type[Exception],
    message: str,
) -> None:
    with pytest.raises(exception_type, match=message):
        simulate_historical_scenario(prices, weights)


def test_non_dataframe_prices_preserve_existing_type_error() -> None:
    with pytest.raises(TypeError, match="prices must be a pandas DataFrame"):
        simulate_historical_scenario(  # type: ignore[arg-type]
            [[100.0], [101.0], [102.0]],
            {"ALPHA": 1.0},
        )


def test_result_and_trajectory_are_immutable() -> None:
    result = simulate_historical_scenario(_prices(), _weights())

    assert isinstance(result.trajectory, tuple)
    with pytest.raises(FrozenInstanceError):
        result.normalized_ending_value = 1.0  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        result.trajectory[0].normalized_value = 2.0  # type: ignore[misc]


def test_unexpected_nonfinite_metric_is_rejected_not_rewritten() -> None:
    with patch.object(
        simulator_module,
        "calculate_annualized_volatility",
        return_value=math.inf,
    ):
        with pytest.raises(ValueError, match="annualized volatility.*finite"):
            simulate_historical_scenario(_prices(), _weights())


def test_valid_allocation_change_returns_both_results_and_deltas() -> None:
    result = simulate_allocation_change(
        _prices(),
        _weights(),
        _modified_weights(),
    )

    assert isinstance(result, AllocationComparisonResult)
    assert isinstance(result.original, HistoricalSimulationResult)
    assert isinstance(result.modified, HistoricalSimulationResult)
    assert result.normalized_ending_value_delta > 0.0
    assert result.annualized_volatility_delta < 0.0


def test_allocation_original_matches_direct_historical_simulation() -> None:
    prices = _prices()
    original_weights = _weights()

    result = simulate_allocation_change(
        prices,
        original_weights,
        _modified_weights(),
    )

    assert result.original == simulate_historical_scenario(
        prices,
        original_weights,
    )


def test_allocation_modified_matches_direct_historical_simulation() -> None:
    prices = _prices()
    modified_weights = _modified_weights()

    result = simulate_allocation_change(
        prices,
        _weights(),
        modified_weights,
    )

    assert result.modified == simulate_historical_scenario(
        prices,
        modified_weights,
    )


def test_allocation_change_passes_same_price_frame_to_both_simulations() -> None:
    prices = _prices()

    with patch.object(
        simulator_module,
        "simulate_historical_scenario",
        wraps=simulate_historical_scenario,
    ) as simulator:
        simulate_allocation_change(prices, _weights(), _modified_weights())

    assert simulator.call_count == 2
    assert simulator.call_args_list[0].args[0] is prices
    assert simulator.call_args_list[1].args[0] is prices


def test_allocation_change_has_positive_comparison_deltas() -> None:
    result = simulate_allocation_change(
        _prices(),
        _weights(),
        _modified_weights(),
    )

    assert result.normalized_ending_value_delta > 0.0
    assert result.cumulative_return_delta > 0.0
    assert result.sharpe_ratio_delta is not None
    assert result.sharpe_ratio_delta > 0.0
    assert result.maximum_drawdown_delta > 0.0


def test_allocation_change_has_negative_comparison_delta() -> None:
    result = simulate_allocation_change(
        _prices(),
        _weights(),
        _modified_weights(),
    )

    assert result.annualized_volatility_delta < 0.0


def test_identical_allocations_have_zero_defined_deltas() -> None:
    result = simulate_allocation_change(_prices(), _weights(), _weights())

    assert result.normalized_ending_value_delta == pytest.approx(0.0)
    assert result.cumulative_return_delta == pytest.approx(0.0)
    assert result.annualized_volatility_delta == pytest.approx(0.0)
    assert result.sharpe_ratio_delta == pytest.approx(0.0)
    assert result.maximum_drawdown_delta == pytest.approx(0.0)


def test_normalized_ending_value_delta_is_modified_minus_original() -> None:
    result = simulate_allocation_change(
        _prices(),
        _weights(),
        _modified_weights(),
    )

    assert result.normalized_ending_value_delta == pytest.approx(
        result.modified.normalized_ending_value
        - result.original.normalized_ending_value
    )


def test_cumulative_return_delta_is_modified_minus_original() -> None:
    result = simulate_allocation_change(
        _prices(),
        _weights(),
        _modified_weights(),
    )

    assert result.cumulative_return_delta == pytest.approx(
        result.modified.cumulative_return - result.original.cumulative_return
    )


def test_annualized_volatility_delta_is_modified_minus_original() -> None:
    result = simulate_allocation_change(
        _prices(),
        _weights(),
        _modified_weights(),
    )

    assert result.annualized_volatility_delta == pytest.approx(
        result.modified.annualized_volatility
        - result.original.annualized_volatility
    )


def test_defined_sharpe_delta_is_modified_minus_original() -> None:
    result = simulate_allocation_change(
        _prices(),
        _weights(),
        _modified_weights(),
    )

    assert result.original.sharpe_ratio is not None
    assert result.modified.sharpe_ratio is not None
    assert result.sharpe_ratio_delta == pytest.approx(
        result.modified.sharpe_ratio - result.original.sharpe_ratio
    )


def test_sharpe_delta_is_none_when_original_sharpe_is_undefined() -> None:
    result = simulate_allocation_change(
        _mixed_sharpe_prices(),
        OrderedDict((("ALPHA", 1.0), ("BETA", 0.0))),
        OrderedDict((("ALPHA", 0.0), ("BETA", 1.0))),
    )

    assert result.original.sharpe_ratio is None
    assert result.modified.sharpe_ratio is not None
    assert result.sharpe_ratio_delta is None


def test_sharpe_delta_is_none_when_modified_sharpe_is_undefined() -> None:
    result = simulate_allocation_change(
        _mixed_sharpe_prices(),
        OrderedDict((("ALPHA", 0.0), ("BETA", 1.0))),
        OrderedDict((("ALPHA", 1.0), ("BETA", 0.0))),
    )

    assert result.original.sharpe_ratio is not None
    assert result.modified.sharpe_ratio is None
    assert result.sharpe_ratio_delta is None


def test_maximum_drawdown_delta_preserves_signed_values_and_direction() -> None:
    result = simulate_allocation_change(
        _prices(),
        _weights(),
        _modified_weights(),
    )

    assert result.original.maximum_drawdown.max_drawdown == pytest.approx(-0.02)
    assert result.modified.maximum_drawdown.max_drawdown == pytest.approx(0.0)
    assert result.maximum_drawdown_delta == pytest.approx(0.02)
    assert result.maximum_drawdown_delta == pytest.approx(
        result.modified.maximum_drawdown.max_drawdown
        - result.original.maximum_drawdown.max_drawdown
    )


def test_allocation_change_preserves_supplied_weight_mapping_order() -> None:
    original_weights = OrderedDict((("BETA", 0.4), ("ALPHA", 0.6)))
    modified_weights = OrderedDict((("BETA", 0.8), ("ALPHA", 0.2)))

    with patch.object(
        simulator_module,
        "simulate_historical_scenario",
        wraps=simulate_historical_scenario,
    ) as simulator:
        simulate_allocation_change(
            _prices(),
            original_weights,
            modified_weights,
        )

    passed_original = simulator.call_args_list[0].args[1]
    passed_modified = simulator.call_args_list[1].args[1]
    assert passed_original is original_weights
    assert passed_modified is modified_weights
    assert list(passed_original) == ["BETA", "ALPHA"]
    assert list(passed_modified) == ["BETA", "ALPHA"]


def test_allocation_change_supports_and_retains_zero_weight_holdings() -> None:
    prices = _mixed_sharpe_prices()
    original_weights = OrderedDict((("ALPHA", 1.0), ("BETA", 0.0)))
    modified_weights = OrderedDict((("ALPHA", 0.0), ("BETA", 1.0)))

    with patch.object(
        simulator_module,
        "simulate_historical_scenario",
        wraps=simulate_historical_scenario,
    ) as simulator:
        result = simulate_allocation_change(
            prices,
            original_weights,
            modified_weights,
        )

    assert isinstance(result, AllocationComparisonResult)
    assert list(simulator.call_args_list[0].args[1].items()) == [
        ("ALPHA", 1.0),
        ("BETA", 0.0),
    ]
    assert list(simulator.call_args_list[1].args[1].items()) == [
        ("ALPHA", 0.0),
        ("BETA", 1.0),
    ]


def test_allocation_change_does_not_mutate_price_frame() -> None:
    prices = _prices()
    snapshot = prices.copy(deep=True)
    index_identity = id(prices.index)
    columns_identity = id(prices.columns)

    simulate_allocation_change(prices, _weights(), _modified_weights())

    pd.testing.assert_frame_equal(prices, snapshot)
    assert id(prices.index) == index_identity
    assert id(prices.columns) == columns_identity


def test_allocation_change_does_not_mutate_original_weights() -> None:
    original_weights = _weights()
    snapshot = list(original_weights.items())
    identity = id(original_weights)

    simulate_allocation_change(
        _prices(),
        original_weights,
        _modified_weights(),
    )

    assert id(original_weights) == identity
    assert list(original_weights.items()) == snapshot


def test_allocation_change_does_not_mutate_modified_weights() -> None:
    modified_weights = _modified_weights()
    snapshot = list(modified_weights.items())
    identity = id(modified_weights)

    simulate_allocation_change(_prices(), _weights(), modified_weights)

    assert id(modified_weights) == identity
    assert list(modified_weights.items()) == snapshot


@pytest.mark.parametrize("invalid_side", ["original", "modified"])
def test_allocation_change_propagates_existing_validation_errors(
    invalid_side: str,
) -> None:
    valid_weights = _weights()
    invalid_weights = {"ALPHA": 1.0}
    original_weights = (
        invalid_weights if invalid_side == "original" else valid_weights
    )
    modified_weights = (
        invalid_weights if invalid_side == "modified" else valid_weights
    )

    with pytest.raises(ValueError) as raised:
        simulate_allocation_change(
            _prices(),
            original_weights,
            modified_weights,
        )

    assert str(raised.value) == (
        "weight symbols must exactly match the asset-return columns"
    )


def test_simulator_module_has_no_orchestration_or_external_dependencies() -> None:
    source = inspect.getsource(simulator_module)

    for forbidden_reference in (
        "fastapi",
        "sqlalchemy",
        "MarketDataService",
        "PortfolioService",
        "_build_price_frame",
        "yfinance",
        "read_csv",
        "requests",
    ):
        assert forbidden_reference not in source


def test_direct_simulator_exports_are_importable() -> None:
    assert simulator_module.__all__ == [
        "HistoricalTrajectoryPoint",
        "HistoricalSimulationResult",
        "AllocationComparisonResult",
        "simulate_historical_scenario",
        "simulate_allocation_change",
    ]
