from collections.abc import Callable
from dataclasses import FrozenInstanceError

import numpy as np
import pandas as pd
import pytest

from backend.app.analytics.drawdown import (
    MaxDrawdownResult,
    calculate_drawdown_series,
    calculate_max_drawdown,
    calculate_max_drawdown_details,
    calculate_wealth_index,
)


def _returns(values: list[object]) -> pd.Series:
    return pd.Series(
        values,
        index=pd.date_range("2026-01-01", periods=len(values), freq="D"),
        name="portfolio_return",
    )


def test_wealth_index_compounds_from_initial_value_and_preserves_index() -> None:
    portfolio_returns = _returns([0.10, -0.20, 0.25])
    expected = pd.Series(
        [1.10, 0.88, 1.10],
        index=portfolio_returns.index,
        name="wealth_index",
    )

    result = calculate_wealth_index(portfolio_returns)

    assert isinstance(result, pd.Series)
    pd.testing.assert_series_equal(
        result, expected, check_exact=False, rtol=1e-12, atol=1e-12
    )
    assert result.index.equals(portfolio_returns.index)
    assert result.name == "wealth_index"
    assert len(result) == len(portfolio_returns)


def test_wealth_index_zero_returns_remain_at_one() -> None:
    portfolio_returns = _returns([0.0, 0.0, 0.0])

    result = calculate_wealth_index(portfolio_returns)

    np.testing.assert_allclose(result.to_numpy(), [1.0, 1.0, 1.0])


def test_wealth_index_does_not_mutate_input() -> None:
    portfolio_returns = _returns([0.10, -0.20])
    original = portfolio_returns.copy(deep=True)

    calculate_wealth_index(portfolio_returns)

    pd.testing.assert_series_equal(portfolio_returns, original)


def test_drawdown_series_uses_running_peaks_and_resets_at_new_highs() -> None:
    portfolio_returns = _returns([0.10, -0.20, 0.25, -0.10])
    expected = pd.Series(
        [0.0, -0.20, 0.0, -0.10],
        index=portfolio_returns.index,
        name="drawdown",
    )

    result = calculate_drawdown_series(portfolio_returns)

    pd.testing.assert_series_equal(
        result, expected, check_exact=False, rtol=1e-12, atol=1e-12
    )
    assert result.index.equals(portfolio_returns.index)
    assert result.name == "drawdown"
    assert np.all(result.to_numpy() <= 1e-15)


def test_drawdown_series_anchors_negative_first_return_at_initial_wealth() -> None:
    portfolio_returns = _returns([-0.10, 0.20])
    expected = pd.Series(
        [-0.10, 0.0],
        index=portfolio_returns.index,
        name="drawdown",
    )

    result = calculate_drawdown_series(portfolio_returns)

    pd.testing.assert_series_equal(
        result, expected, check_exact=False, rtol=1e-12, atol=1e-12
    )


def test_drawdown_series_is_zero_for_continuously_increasing_wealth() -> None:
    portfolio_returns = _returns([0.01, 0.02, 0.03])

    result = calculate_drawdown_series(portfolio_returns)

    np.testing.assert_allclose(result.to_numpy(), [0.0, 0.0, 0.0])


def test_drawdown_series_does_not_mutate_input() -> None:
    portfolio_returns = _returns([0.10, -0.20, 0.25])
    original = portfolio_returns.copy(deep=True)

    calculate_drawdown_series(portfolio_returns)

    pd.testing.assert_series_equal(portfolio_returns, original)


def test_max_drawdown_returns_negative_python_float() -> None:
    result = calculate_max_drawdown(_returns([0.10, -0.20, 0.25, -0.10]))

    assert isinstance(result, float)
    assert result == pytest.approx(-0.20)
    assert result < 0.0


def test_max_drawdown_is_zero_when_wealth_never_declines() -> None:
    result = calculate_max_drawdown(_returns([0.0, 0.05, 0.10]))

    assert result == pytest.approx(0.0)


def test_max_drawdown_handles_immediate_first_period_decline() -> None:
    result = calculate_max_drawdown(_returns([-0.15, 0.05]))

    assert result == pytest.approx(-0.15)


def test_max_drawdown_repeated_minimum_keeps_expected_value() -> None:
    result = calculate_max_drawdown(_returns([0.10, -0.20, 0.0]))

    assert result == pytest.approx(-0.20)


def test_max_drawdown_details_returns_peak_and_first_trough_dates() -> None:
    portfolio_returns = _returns([0.10, -0.20, 0.0])

    result = calculate_max_drawdown_details(portfolio_returns)

    assert result == MaxDrawdownResult(
        max_drawdown=pytest.approx(-0.20),
        peak_date=portfolio_returns.index[0],
        trough_date=portfolio_returns.index[1],
    )


def test_max_drawdown_details_uses_initial_baseline_peak() -> None:
    portfolio_returns = _returns([-0.10, 0.0])

    result = calculate_max_drawdown_details(portfolio_returns)

    assert result.max_drawdown == pytest.approx(-0.10)
    assert result.peak_date is None
    assert result.trough_date == portfolio_returns.index[0]


def test_max_drawdown_details_has_no_dates_when_there_is_no_drawdown() -> None:
    result = calculate_max_drawdown_details(_returns([0.0, 0.05, 0.10]))

    assert result == MaxDrawdownResult(0.0, None, None)


def test_max_drawdown_details_uses_most_recent_repeated_peak() -> None:
    portfolio_returns = _returns([0.10, 0.0, -0.20])

    result = calculate_max_drawdown_details(portfolio_returns)

    assert result.peak_date == portfolio_returns.index[1]
    assert result.trough_date == portfolio_returns.index[2]
    assert result.max_drawdown == pytest.approx(-0.20)


def test_max_drawdown_details_uses_first_repeated_minimum() -> None:
    portfolio_returns = _returns([0.10, 0.0, -0.20, 0.0])

    result = calculate_max_drawdown_details(portfolio_returns)

    assert result.trough_date == portfolio_returns.index[2]


def test_max_drawdown_result_is_immutable() -> None:
    result = MaxDrawdownResult(-0.20, pd.Timestamp("2026-01-01"), None)

    with pytest.raises(FrozenInstanceError):
        result.max_drawdown = -0.30  # type: ignore[misc]


def test_small_drawdown_is_preserved_without_rounding() -> None:
    portfolio_returns = _returns([0.0000001, -0.0000002])

    result = calculate_max_drawdown(portfolio_returns)

    assert result == pytest.approx(-0.0000002)
    assert result != 0.0


PUBLIC_FUNCTIONS: list[Callable[[pd.Series], object]] = [
    calculate_wealth_index,
    calculate_drawdown_series,
    calculate_max_drawdown,
    calculate_max_drawdown_details,
]


@pytest.mark.parametrize("calculator", PUBLIC_FUNCTIONS)
def test_drawdown_functions_reject_wrong_input_type(
    calculator: Callable[[pd.Series], object],
) -> None:
    with pytest.raises(TypeError, match="pandas Series"):
        calculator([0.10, -0.10])  # type: ignore[arg-type]


@pytest.mark.parametrize("calculator", PUBLIC_FUNCTIONS)
def test_drawdown_functions_reject_empty_series(
    calculator: Callable[[pd.Series], object],
) -> None:
    portfolio_returns = pd.Series(dtype=float, index=pd.DatetimeIndex([]))

    with pytest.raises(ValueError, match="empty"):
        calculator(portfolio_returns)


@pytest.mark.parametrize(
    ("index", "exception_type", "message"),
    [
        (pd.Index([0, 1]), TypeError, "DatetimeIndex"),
        (
            pd.to_datetime(["2026-01-01", "2026-01-01"]),
            ValueError,
            "duplicate",
        ),
        (
            pd.to_datetime(["2026-01-02", "2026-01-01"]),
            ValueError,
            "strictly increasing",
        ),
        (
            pd.DatetimeIndex(["2026-01-01", pd.NaT]),
            ValueError,
            "NaT",
        ),
        (
            pd.date_range("2026-01-01", periods=2, tz="UTC"),
            ValueError,
            "timezone-naive",
        ),
    ],
)
@pytest.mark.parametrize("calculator", PUBLIC_FUNCTIONS)
def test_drawdown_functions_reject_invalid_index(
    calculator: Callable[[pd.Series], object],
    index: pd.Index,
    exception_type: type[Exception],
    message: str,
) -> None:
    portfolio_returns = pd.Series([0.10, -0.10], index=index)

    with pytest.raises(exception_type, match=message):
        calculator(portfolio_returns)


@pytest.mark.parametrize(
    ("invalid_value", "exception_type", "message"),
    [
        (np.nan, ValueError, "missing"),
        (np.inf, ValueError, "finite"),
        (-np.inf, ValueError, "finite"),
        (True, TypeError, "Boolean"),
        (0.10 + 0.0j, TypeError, "complex"),
        ("0.10", TypeError, "real numeric"),
        (-1.0, ValueError, "greater than -1.0"),
        (-1.01, ValueError, "greater than -1.0"),
    ],
)
@pytest.mark.parametrize("calculator", PUBLIC_FUNCTIONS)
def test_drawdown_functions_reject_invalid_values(
    calculator: Callable[[pd.Series], object],
    invalid_value: object,
    exception_type: type[Exception],
    message: str,
) -> None:
    portfolio_returns = _returns([0.10, invalid_value])

    with pytest.raises(exception_type, match=message):
        calculator(portfolio_returns)
