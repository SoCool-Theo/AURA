import numpy as np
import pandas as pd
import pytest

from backend.app.analytics.returns import (
    calculate_annualized_return,
    calculate_asset_returns,
    calculate_cumulative_return,
    calculate_portfolio_returns,
)


def _prices() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "BETA": [100.0, 110.0, 99.0],
            "ALPHA": [200.0, 180.0, 189.0],
        },
        index=pd.date_range("2026-01-01", periods=3, freq="D"),
    )


def _asset_returns() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "BETA": [0.10, -0.10],
            "ALPHA": [-0.05, 0.20],
        },
        index=pd.date_range("2026-01-02", periods=2, freq="D"),
    )


def test_calculate_asset_returns_uses_simple_returns_and_preserves_labels() -> None:
    prices = _prices()
    expected = pd.DataFrame(
        {
            "BETA": [0.10, -0.10],
            "ALPHA": [-0.10, 0.05],
        },
        index=prices.index[1:],
    )

    result = calculate_asset_returns(prices)

    pd.testing.assert_frame_equal(result, expected)
    assert list(result.columns) == ["BETA", "ALPHA"]
    assert result.index.equals(prices.index[1:])
    assert prices.index[0] not in result.index
    assert not result.isna().any().any()


def test_two_prices_produce_exactly_one_return_row() -> None:
    prices = pd.DataFrame(
        {"AAPL": [50.0, 55.0]},
        index=pd.to_datetime(["2026-01-01", "2026-01-02"]),
    )

    result = calculate_asset_returns(prices)

    assert len(result) == 1
    assert result.index.equals(prices.index[1:])
    assert result.iloc[0, 0] == pytest.approx(0.10)


def test_calculate_asset_returns_does_not_mutate_prices() -> None:
    prices = _prices()
    original = prices.copy(deep=True)

    calculate_asset_returns(prices)

    pd.testing.assert_frame_equal(prices, original)


def test_calculate_portfolio_returns_aligns_weights_by_symbol() -> None:
    asset_returns = _asset_returns()
    weights = {"ALPHA": 0.25, "BETA": 0.75}
    expected = pd.Series(
        [0.0625, -0.025],
        index=asset_returns.index,
        name="portfolio_return",
    )

    result = calculate_portfolio_returns(asset_returns, weights)

    pd.testing.assert_series_equal(result, expected)
    assert result.index.equals(asset_returns.index)
    assert result.name == "portfolio_return"


def test_calculate_portfolio_returns_allows_zero_weight_assets() -> None:
    asset_returns = _asset_returns()
    weights = {"ALPHA": 0.0, "BETA": 1.0}
    expected = pd.Series(
        [0.10, -0.10],
        index=asset_returns.index,
        name="portfolio_return",
    )

    result = calculate_portfolio_returns(asset_returns, weights)

    pd.testing.assert_series_equal(result, expected)


def test_calculate_portfolio_returns_does_not_mutate_inputs() -> None:
    asset_returns = _asset_returns()
    original_returns = asset_returns.copy(deep=True)
    weights = {"ALPHA": 0.25, "BETA": 0.75}
    original_weights = weights.copy()

    calculate_portfolio_returns(asset_returns, weights)

    pd.testing.assert_frame_equal(asset_returns, original_returns)
    assert weights == original_weights


def test_calculate_cumulative_return_compounds_periodic_returns() -> None:
    portfolio_returns = pd.Series([0.10, -0.05, 0.02])

    result = calculate_cumulative_return(portfolio_returns)

    assert isinstance(result, float)
    assert result == pytest.approx(0.0659)


def test_calculate_annualized_return_uses_requested_periods_per_year() -> None:
    portfolio_returns = pd.Series([0.10, 0.10])

    result = calculate_annualized_return(portfolio_returns, periods_per_year=4)

    assert isinstance(result, float)
    assert result == pytest.approx(0.4641)


def test_zero_returns_produce_zero_cumulative_and_annualized_returns() -> None:
    portfolio_returns = pd.Series([0.0, 0.0, 0.0])

    assert calculate_cumulative_return(portfolio_returns) == pytest.approx(0.0)
    assert calculate_annualized_return(
        portfolio_returns, periods_per_year=12
    ) == pytest.approx(0.0)


def test_weight_total_just_inside_tolerance_is_accepted() -> None:
    asset_returns = pd.DataFrame(
        {"A": [0.10], "B": [0.20]},
        index=pd.to_datetime(["2026-01-02"]),
    )

    result = calculate_portfolio_returns(
        asset_returns, {"A": 0.5, "B": 0.5000005}
    )

    assert result.iloc[0] == pytest.approx(0.1500001)


def test_weight_total_outside_tolerance_is_rejected() -> None:
    with pytest.raises(ValueError, match="total weight"):
        calculate_portfolio_returns(
            _asset_returns(), {"BETA": 0.5, "ALPHA": 0.5000011}
        )


def test_asset_returns_rejects_wrong_input_type() -> None:
    with pytest.raises(TypeError, match="pandas DataFrame"):
        calculate_asset_returns([100.0, 110.0])  # type: ignore[arg-type]


def test_asset_returns_requires_at_least_two_price_rows() -> None:
    prices = pd.DataFrame(
        {"AAPL": [100.0]},
        index=pd.to_datetime(["2026-01-01"]),
    )

    with pytest.raises(ValueError, match="at least two rows"):
        calculate_asset_returns(prices)


def test_asset_returns_requires_at_least_one_asset_column() -> None:
    prices = pd.DataFrame(index=pd.date_range("2026-01-01", periods=2))

    with pytest.raises(ValueError, match="asset column"):
        calculate_asset_returns(prices)


def test_asset_returns_requires_datetime_index() -> None:
    prices = pd.DataFrame({"AAPL": [100.0, 110.0]})

    with pytest.raises(TypeError, match="DatetimeIndex"):
        calculate_asset_returns(prices)


@pytest.mark.parametrize(
    ("invalid_value", "exception_type", "message"),
    [
        (np.nan, ValueError, "missing"),
        (np.inf, ValueError, "finite"),
        (-np.inf, ValueError, "finite"),
        (True, TypeError, "Boolean"),
        (100.0 + 0.0j, TypeError, "complex"),
        (0.0, ValueError, "greater than zero"),
        (-1.0, ValueError, "greater than zero"),
    ],
)
def test_asset_returns_rejects_invalid_price_values(
    invalid_value: object,
    exception_type: type[Exception],
    message: str,
) -> None:
    prices = pd.DataFrame(
        {"AAPL": [100.0, invalid_value]},
        index=pd.date_range("2026-01-01", periods=2),
    )

    with pytest.raises(exception_type, match=message):
        calculate_asset_returns(prices)


def test_asset_returns_rejects_duplicate_dates() -> None:
    prices = pd.DataFrame(
        {"AAPL": [100.0, 110.0]},
        index=pd.to_datetime(["2026-01-01", "2026-01-01"]),
    )

    with pytest.raises(ValueError, match="duplicate"):
        calculate_asset_returns(prices)


def test_asset_returns_rejects_unsorted_dates() -> None:
    prices = pd.DataFrame(
        {"AAPL": [110.0, 100.0]},
        index=pd.to_datetime(["2026-01-02", "2026-01-01"]),
    )

    with pytest.raises(ValueError, match="strictly increasing"):
        calculate_asset_returns(prices)


def test_asset_returns_rejects_nat() -> None:
    prices = pd.DataFrame(
        {"AAPL": [100.0, 110.0]},
        index=pd.DatetimeIndex(["2026-01-01", pd.NaT]),
    )

    with pytest.raises(ValueError, match="NaT"):
        calculate_asset_returns(prices)


def test_asset_returns_rejects_timezone_aware_dates() -> None:
    prices = pd.DataFrame(
        {"AAPL": [100.0, 110.0]},
        index=pd.date_range("2026-01-01", periods=2, tz="UTC"),
    )

    with pytest.raises(ValueError, match="timezone-naive"):
        calculate_asset_returns(prices)


def test_asset_returns_rejects_duplicate_symbols() -> None:
    prices = pd.DataFrame(
        [[100.0, 200.0], [110.0, 220.0]],
        index=pd.date_range("2026-01-01", periods=2),
        columns=["AAPL", "AAPL"],
    )

    with pytest.raises(ValueError, match="unique"):
        calculate_asset_returns(prices)


@pytest.mark.parametrize("symbol", ["", " ", " AAPL", "AAPL "])
def test_asset_returns_rejects_invalid_symbols(symbol: str) -> None:
    prices = pd.DataFrame(
        {symbol: [100.0, 110.0]},
        index=pd.date_range("2026-01-01", periods=2),
    )

    with pytest.raises(ValueError, match="symbol"):
        calculate_asset_returns(prices)


def test_asset_returns_rejects_non_string_symbols() -> None:
    prices = pd.DataFrame(
        {123: [100.0, 110.0]},
        index=pd.date_range("2026-01-01", periods=2),
    )

    with pytest.raises(TypeError, match="strings"):
        calculate_asset_returns(prices)


def test_portfolio_returns_rejects_wrong_asset_returns_type() -> None:
    with pytest.raises(TypeError, match="pandas DataFrame"):
        calculate_portfolio_returns(  # type: ignore[arg-type]
            [0.10, 0.20], {"A": 1.0}
        )


def test_portfolio_returns_rejects_empty_asset_return_rows() -> None:
    asset_returns = pd.DataFrame(
        {"A": pd.Series(dtype=float)},
        index=pd.DatetimeIndex([]),
    )

    with pytest.raises(ValueError, match="at least one row"):
        calculate_portfolio_returns(asset_returns, {"A": 1.0})


def test_portfolio_returns_rejects_empty_asset_columns() -> None:
    asset_returns = pd.DataFrame(index=pd.to_datetime(["2026-01-01"]))

    with pytest.raises(ValueError, match="asset column"):
        calculate_portfolio_returns(asset_returns, {})


@pytest.mark.parametrize(
    ("invalid_value", "exception_type", "message"),
    [
        (np.nan, ValueError, "missing"),
        (np.inf, ValueError, "finite"),
        (True, TypeError, "Boolean"),
        (0.10 + 0.0j, TypeError, "complex"),
    ],
)
def test_portfolio_returns_rejects_invalid_asset_return_values(
    invalid_value: object,
    exception_type: type[Exception],
    message: str,
) -> None:
    asset_returns = pd.DataFrame(
        {"A": [invalid_value]},
        index=pd.to_datetime(["2026-01-02"]),
    )

    with pytest.raises(exception_type, match=message):
        calculate_portfolio_returns(asset_returns, {"A": 1.0})


@pytest.mark.parametrize(
    "index",
    [
        pd.Index([0, 1]),
        pd.DatetimeIndex(["2026-01-01", pd.NaT]),
        pd.to_datetime(["2026-01-01", "2026-01-01"]),
        pd.to_datetime(["2026-01-02", "2026-01-01"]),
        pd.date_range("2026-01-01", periods=2, tz="UTC"),
    ],
)
def test_portfolio_returns_rejects_invalid_asset_return_index(
    index: pd.Index,
) -> None:
    asset_returns = pd.DataFrame({"A": [0.10, 0.20]}, index=index)

    with pytest.raises((TypeError, ValueError)):
        calculate_portfolio_returns(asset_returns, {"A": 1.0})


@pytest.mark.parametrize(
    "columns",
    [
        ["A", "A"],
        ["", "B"],
        [" ", "B"],
        [" A", "B"],
        ["A ", "B"],
    ],
)
def test_portfolio_returns_rejects_invalid_asset_return_symbols(
    columns: list[str],
) -> None:
    asset_returns = pd.DataFrame(
        [[0.10, 0.20]],
        index=pd.to_datetime(["2026-01-02"]),
        columns=columns,
    )

    with pytest.raises(ValueError, match="symbol"):
        calculate_portfolio_returns(asset_returns, {"A": 0.5, "B": 0.5})


def test_portfolio_returns_rejects_non_string_asset_return_symbols() -> None:
    asset_returns = pd.DataFrame(
        [[0.10]],
        index=pd.to_datetime(["2026-01-02"]),
        columns=[1],
    )

    with pytest.raises(TypeError, match="strings"):
        calculate_portfolio_returns(asset_returns, {"1": 1.0})


def test_portfolio_returns_rejects_wrong_weights_type() -> None:
    with pytest.raises(TypeError, match="Mapping"):
        calculate_portfolio_returns(  # type: ignore[arg-type]
            _asset_returns(), [0.75, 0.25]
        )


@pytest.mark.parametrize(
    "weights",
    [
        {"BETA": 1.0},
        {"BETA": 0.75, "ALPHA": 0.25, "GAMMA": 0.0},
        {"BETA": 1.0, "alpha": 0.0},
    ],
)
def test_portfolio_returns_requires_exact_weight_symbols(
    weights: dict[str, float],
) -> None:
    with pytest.raises(ValueError, match="exactly match"):
        calculate_portfolio_returns(_asset_returns(), weights)


@pytest.mark.parametrize(
    ("weights", "exception_type", "message"),
    [
        ({"BETA": 1.0, "ALPHA": -0.1}, ValueError, "between"),
        ({"BETA": 1.1, "ALPHA": 0.0}, ValueError, "between"),
        ({"BETA": 0.0, "ALPHA": 0.0}, ValueError, "greater than zero"),
        ({"BETA": np.nan, "ALPHA": 0.0}, ValueError, "finite"),
        ({"BETA": np.inf, "ALPHA": 0.0}, ValueError, "finite"),
        ({"BETA": True, "ALPHA": 0.0}, TypeError, "Boolean"),
        ({"BETA": 1.0 + 0.0j, "ALPHA": 0.0}, TypeError, "complex"),
        ({"BETA": 40.0, "ALPHA": 0.0}, ValueError, "between"),
    ],
)
def test_portfolio_returns_rejects_invalid_weight_values(
    weights: dict[str, object],
    exception_type: type[Exception],
    message: str,
) -> None:
    with pytest.raises(exception_type, match=message):
        calculate_portfolio_returns(_asset_returns(), weights)  # type: ignore[arg-type]


@pytest.mark.parametrize("invalid_key", ["", " ", " BETA", "BETA "])
def test_portfolio_returns_rejects_invalid_weight_symbols(
    invalid_key: str,
) -> None:
    weights = {invalid_key: 0.75, "ALPHA": 0.25}

    with pytest.raises(ValueError, match="weight symbols"):
        calculate_portfolio_returns(_asset_returns(), weights)


def test_portfolio_returns_rejects_non_string_weight_symbols() -> None:
    weights = {1: 0.75, "ALPHA": 0.25}

    with pytest.raises(TypeError, match="strings"):
        calculate_portfolio_returns(_asset_returns(), weights)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "calculator",
    [calculate_cumulative_return, calculate_annualized_return],
)
def test_return_aggregations_reject_wrong_input_type(calculator: object) -> None:
    with pytest.raises(TypeError, match="pandas Series"):
        calculator([0.10, 0.20])  # type: ignore[operator]


@pytest.mark.parametrize(
    "calculator",
    [calculate_cumulative_return, calculate_annualized_return],
)
def test_return_aggregations_reject_empty_series(calculator: object) -> None:
    with pytest.raises(ValueError, match="empty"):
        calculator(pd.Series(dtype=float))  # type: ignore[operator]


@pytest.mark.parametrize(
    ("invalid_value", "exception_type", "message"),
    [
        (np.nan, ValueError, "missing"),
        (np.inf, ValueError, "finite"),
        (-np.inf, ValueError, "finite"),
        (True, TypeError, "Boolean"),
        (0.10 + 0.0j, TypeError, "complex"),
        (-1.0, ValueError, "greater than -1.0"),
        (-1.01, ValueError, "greater than -1.0"),
    ],
)
@pytest.mark.parametrize(
    "calculator",
    [calculate_cumulative_return, calculate_annualized_return],
)
def test_return_aggregations_reject_invalid_values(
    calculator: object,
    invalid_value: object,
    exception_type: type[Exception],
    message: str,
) -> None:
    with pytest.raises(exception_type, match=message):
        calculator(pd.Series([invalid_value]))  # type: ignore[operator]


@pytest.mark.parametrize(
    ("periods_per_year", "exception_type"),
    [
        (True, TypeError),
        (252.0, TypeError),
        ("252", TypeError),
        (0, ValueError),
        (-1, ValueError),
    ],
)
def test_annualized_return_rejects_invalid_periods_per_year(
    periods_per_year: object,
    exception_type: type[Exception],
) -> None:
    with pytest.raises(exception_type, match="periods_per_year"):
        calculate_annualized_return(  # type: ignore[arg-type]
            pd.Series([0.10]), periods_per_year=periods_per_year
        )
