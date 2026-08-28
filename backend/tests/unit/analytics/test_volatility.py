from collections.abc import Callable

import numpy as np
import pandas as pd
import pytest

from backend.app.analytics.volatility import (
    calculate_annualized_volatility,
    calculate_asset_volatilities,
    calculate_periodic_volatility,
)


def _returns() -> pd.Series:
    return pd.Series(
        [-0.10, 0.0, 0.10],
        index=pd.date_range("2026-01-01", periods=3, freq="D"),
        name="portfolio_return",
    )


def _asset_returns() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "BETA": [-0.10, 0.0, 0.10],
            "ALPHA": [0.05, 0.05, 0.05],
        },
        index=pd.date_range("2026-01-01", periods=3, freq="D"),
    )


def test_periodic_volatility_uses_sample_standard_deviation() -> None:
    returns = _returns()

    result = calculate_periodic_volatility(returns)

    assert result == pytest.approx(0.10)
    assert result != pytest.approx(np.std(returns.to_numpy(), ddof=0))


def test_periodic_volatility_returns_python_float_for_constant_returns() -> None:
    returns = pd.Series(
        [0.02, 0.02, 0.02],
        index=pd.date_range("2026-01-01", periods=3),
    )

    result = calculate_periodic_volatility(returns)

    assert isinstance(result, float)
    assert result == pytest.approx(0.0)


def test_periodic_volatility_does_not_mutate_input() -> None:
    returns = _returns()
    original = returns.copy(deep=True)

    calculate_periodic_volatility(returns)

    pd.testing.assert_series_equal(returns, original)


def test_annualized_volatility_uses_requested_periods_per_year() -> None:
    result = calculate_annualized_volatility(_returns(), periods_per_year=4)

    assert isinstance(result, float)
    assert result == pytest.approx(0.20)


def test_annualized_volatility_defaults_to_252_periods() -> None:
    result = calculate_annualized_volatility(_returns())

    assert result == pytest.approx(0.10 * np.sqrt(252))


def test_annualized_volatility_is_zero_for_constant_returns() -> None:
    returns = pd.Series(
        [0.03, 0.03],
        index=pd.date_range("2026-01-01", periods=2),
    )

    result = calculate_annualized_volatility(returns, periods_per_year=12)

    assert isinstance(result, float)
    assert result == pytest.approx(0.0)


def test_annualized_volatility_does_not_mutate_input() -> None:
    returns = _returns()
    original = returns.copy(deep=True)

    calculate_annualized_volatility(returns, periods_per_year=4)

    pd.testing.assert_series_equal(returns, original)


def test_asset_volatilities_calculates_each_asset_and_preserves_order() -> None:
    asset_returns = _asset_returns()
    expected = pd.Series(
        [0.20, 0.0],
        index=pd.Index(["BETA", "ALPHA"]),
        name="annualized_volatility",
    )

    result = calculate_asset_volatilities(
        asset_returns, periods_per_year=4
    )

    assert isinstance(result, pd.Series)
    pd.testing.assert_series_equal(result, expected)
    assert list(result.index) == ["BETA", "ALPHA"]
    assert result.name == "annualized_volatility"


def test_asset_volatilities_does_not_mutate_input() -> None:
    asset_returns = _asset_returns()
    original = asset_returns.copy(deep=True)

    calculate_asset_volatilities(asset_returns, periods_per_year=4)

    pd.testing.assert_frame_equal(asset_returns, original)


def test_periodic_volatility_rejects_wrong_input_type() -> None:
    with pytest.raises(TypeError, match="pandas Series"):
        calculate_periodic_volatility([-0.10, 0.10])  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "returns",
    [
        pd.Series(dtype=float, index=pd.DatetimeIndex([])),
        pd.Series([0.10], index=pd.to_datetime(["2026-01-01"])),
    ],
)
def test_periodic_volatility_requires_two_observations(
    returns: pd.Series,
) -> None:
    with pytest.raises(ValueError, match="at least two observations"):
        calculate_periodic_volatility(returns)


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
def test_periodic_volatility_rejects_invalid_values(
    invalid_value: object,
    exception_type: type[Exception],
    message: str,
) -> None:
    returns = pd.Series(
        [0.10, invalid_value],
        index=pd.date_range("2026-01-01", periods=2),
    )

    with pytest.raises(exception_type, match=message):
        calculate_periodic_volatility(returns)


@pytest.mark.parametrize(
    ("index", "exception_type", "message"),
    [
        (pd.Index([0, 1]), TypeError, "DatetimeIndex"),
        (
            pd.DatetimeIndex(["2026-01-01", pd.NaT]),
            ValueError,
            "NaT",
        ),
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
            pd.date_range("2026-01-01", periods=2, tz="UTC"),
            ValueError,
            "timezone-naive",
        ),
    ],
)
def test_periodic_volatility_rejects_invalid_index(
    index: pd.Index,
    exception_type: type[Exception],
    message: str,
) -> None:
    returns = pd.Series([0.10, 0.20], index=index)

    with pytest.raises(exception_type, match=message):
        calculate_periodic_volatility(returns)


def test_asset_volatilities_rejects_wrong_input_type() -> None:
    with pytest.raises(TypeError, match="pandas DataFrame"):
        calculate_asset_volatilities(  # type: ignore[arg-type]
            [[0.10], [0.20]]
        )


@pytest.mark.parametrize(
    "asset_returns",
    [
        pd.DataFrame(
            {"A": pd.Series(dtype=float)},
            index=pd.DatetimeIndex([]),
        ),
        pd.DataFrame(
            {"A": [0.10]},
            index=pd.to_datetime(["2026-01-01"]),
        ),
    ],
)
def test_asset_volatilities_requires_two_rows(
    asset_returns: pd.DataFrame,
) -> None:
    with pytest.raises(ValueError, match="at least two rows"):
        calculate_asset_volatilities(asset_returns)


def test_asset_volatilities_requires_an_asset_column() -> None:
    asset_returns = pd.DataFrame(
        index=pd.date_range("2026-01-01", periods=2)
    )

    with pytest.raises(ValueError, match="asset column"):
        calculate_asset_volatilities(asset_returns)


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
def test_asset_volatilities_rejects_invalid_values(
    invalid_value: object,
    exception_type: type[Exception],
    message: str,
) -> None:
    asset_returns = pd.DataFrame(
        {"A": [0.10, invalid_value]},
        index=pd.date_range("2026-01-01", periods=2),
    )

    with pytest.raises(exception_type, match=message):
        calculate_asset_volatilities(asset_returns)


def test_asset_volatilities_rejects_duplicate_symbols() -> None:
    asset_returns = pd.DataFrame(
        [[0.10, 0.20], [0.20, 0.30]],
        index=pd.date_range("2026-01-01", periods=2),
        columns=["A", "A"],
    )

    with pytest.raises(ValueError, match="unique"):
        calculate_asset_volatilities(asset_returns)


@pytest.mark.parametrize("symbol", ["", " ", " A", "A "])
def test_asset_volatilities_rejects_invalid_symbols(symbol: str) -> None:
    asset_returns = pd.DataFrame(
        {symbol: [0.10, 0.20]},
        index=pd.date_range("2026-01-01", periods=2),
    )

    with pytest.raises(ValueError, match="symbol"):
        calculate_asset_volatilities(asset_returns)


def test_asset_volatilities_rejects_non_string_symbols() -> None:
    asset_returns = pd.DataFrame(
        {1: [0.10, 0.20]},
        index=pd.date_range("2026-01-01", periods=2),
    )

    with pytest.raises(TypeError, match="strings"):
        calculate_asset_volatilities(asset_returns)


@pytest.mark.parametrize(
    ("index", "exception_type", "message"),
    [
        (pd.Index([0, 1]), TypeError, "DatetimeIndex"),
        (
            pd.DatetimeIndex(["2026-01-01", pd.NaT]),
            ValueError,
            "NaT",
        ),
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
            pd.date_range("2026-01-01", periods=2, tz="UTC"),
            ValueError,
            "timezone-naive",
        ),
    ],
)
def test_asset_volatilities_rejects_invalid_index(
    index: pd.Index,
    exception_type: type[Exception],
    message: str,
) -> None:
    asset_returns = pd.DataFrame({"A": [0.10, 0.20]}, index=index)

    with pytest.raises(exception_type, match=message):
        calculate_asset_volatilities(asset_returns)


def _annualize_series(periods_per_year: object) -> float:
    return calculate_annualized_volatility(  # type: ignore[arg-type]
        _returns(), periods_per_year=periods_per_year
    )


def _annualize_assets(periods_per_year: object) -> pd.Series:
    return calculate_asset_volatilities(  # type: ignore[arg-type]
        _asset_returns(), periods_per_year=periods_per_year
    )


@pytest.mark.parametrize(
    "calculator",
    [_annualize_series, _annualize_assets],
)
@pytest.mark.parametrize(
    ("periods_per_year", "exception_type"),
    [
        (0, ValueError),
        (-1, ValueError),
        (252.0, TypeError),
        ("252", TypeError),
        (True, TypeError),
    ],
)
def test_annualized_volatility_rejects_invalid_periods_per_year(
    calculator: Callable[[object], object],
    periods_per_year: object,
    exception_type: type[Exception],
) -> None:
    with pytest.raises(exception_type, match="periods_per_year"):
        calculator(periods_per_year)
