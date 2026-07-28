import numpy as np
import pandas as pd
import pytest

from backend.app.analytics.sharpe import calculate_sharpe_ratio


def _return_series(values: list[object]) -> pd.Series:
    return pd.Series(
        values,
        index=pd.date_range("2025-01-01", periods=len(values), freq="D"),
        name="portfolio_return",
    )


def test_calculate_sharpe_ratio_with_zero_risk_free_rate() -> None:
    returns = _return_series([0.01, 0.02, 0.03])

    result = calculate_sharpe_ratio(
        returns,
        annual_risk_free_rate=0.0,
        periods_per_year=4,
    )

    assert result == pytest.approx(4.0)


def test_calculate_sharpe_ratio_uses_sample_volatility() -> None:
    returns = _return_series([0.01, 0.02, 0.03])

    result = calculate_sharpe_ratio(returns, periods_per_year=4)

    population_volatility_result = 0.02 / np.std([0.01, 0.02, 0.03]) * 2
    assert result == pytest.approx(4.0)
    assert result != pytest.approx(population_volatility_result)


def test_calculate_sharpe_ratio_applies_small_annualization_factor() -> None:
    returns = _return_series([0.01, 0.02, 0.03])

    result = calculate_sharpe_ratio(returns, periods_per_year=1)

    assert result == pytest.approx(2.0)


def test_calculate_sharpe_ratio_uses_default_periods_per_year() -> None:
    returns = _return_series([0.01, 0.02, 0.03])

    result = calculate_sharpe_ratio(returns)

    assert result == pytest.approx(2.0 * np.sqrt(252))


def test_calculate_sharpe_ratio_converts_nonzero_risk_free_rate_geometrically() -> None:
    returns = _return_series([0.01, 0.02, 0.03])

    result = calculate_sharpe_ratio(
        returns,
        annual_risk_free_rate=0.04060401,
        periods_per_year=4,
    )

    assert result == pytest.approx(2.0)


def test_calculate_sharpe_ratio_accepts_negative_risk_free_rate() -> None:
    returns = _return_series([0.01, 0.02, 0.03])

    result = calculate_sharpe_ratio(
        returns,
        annual_risk_free_rate=-0.03940399,
        periods_per_year=4,
    )

    assert result == pytest.approx(6.0)


def test_calculate_sharpe_ratio_returns_python_float() -> None:
    result = calculate_sharpe_ratio(
        _return_series([0.01, 0.02, 0.03]),
        annual_risk_free_rate=np.float64(0.0),
        periods_per_year=np.int64(4),
    )

    assert type(result) is float


def test_calculate_sharpe_ratio_does_not_mutate_input() -> None:
    returns = _return_series([0.01, 0.02, 0.03])
    original = returns.copy(deep=True)

    calculate_sharpe_ratio(returns, periods_per_year=4)

    pd.testing.assert_series_equal(returns, original)


@pytest.mark.parametrize(
    "values",
    [
        [0.02, 0.02, 0.02],
        [0.0, 0.0, 0.0],
        [-0.02, -0.02, -0.02],
    ],
)
def test_calculate_sharpe_ratio_rejects_zero_volatility(
    values: list[float],
) -> None:
    with pytest.raises(ValueError, match="undefined.*volatility.*zero"):
        calculate_sharpe_ratio(_return_series(values))


def test_calculate_sharpe_ratio_rejects_wrong_returns_type() -> None:
    with pytest.raises(TypeError, match="pandas Series"):
        calculate_sharpe_ratio([0.01, 0.02])  # type: ignore[arg-type]


@pytest.mark.parametrize("values", [[], [0.01]])
def test_calculate_sharpe_ratio_rejects_too_few_observations(
    values: list[float],
) -> None:
    with pytest.raises(ValueError, match="at least two"):
        calculate_sharpe_ratio(_return_series(values))


def test_calculate_sharpe_ratio_rejects_non_datetime_index() -> None:
    returns = pd.Series([0.01, 0.02], index=[0, 1])

    with pytest.raises(TypeError, match="DatetimeIndex"):
        calculate_sharpe_ratio(returns)


def test_calculate_sharpe_ratio_rejects_duplicate_dates() -> None:
    date = pd.Timestamp("2025-01-01")
    returns = pd.Series([0.01, 0.02], index=pd.DatetimeIndex([date, date]))

    with pytest.raises(ValueError, match="duplicate"):
        calculate_sharpe_ratio(returns)


def test_calculate_sharpe_ratio_rejects_unsorted_dates() -> None:
    returns = pd.Series(
        [0.01, 0.02],
        index=pd.DatetimeIndex(["2025-01-02", "2025-01-01"]),
    )

    with pytest.raises(ValueError, match="strictly increasing"):
        calculate_sharpe_ratio(returns)


def test_calculate_sharpe_ratio_rejects_nat_index() -> None:
    returns = pd.Series(
        [0.01, 0.02],
        index=pd.DatetimeIndex(["2025-01-01", pd.NaT]),
    )

    with pytest.raises(ValueError, match="NaT"):
        calculate_sharpe_ratio(returns)


def test_calculate_sharpe_ratio_rejects_timezone_aware_index() -> None:
    returns = pd.Series(
        [0.01, 0.02],
        index=pd.date_range("2025-01-01", periods=2, tz="UTC"),
    )

    with pytest.raises(ValueError, match="timezone-naive"):
        calculate_sharpe_ratio(returns)


@pytest.mark.parametrize("bad_value", [np.nan, np.inf, -np.inf])
def test_calculate_sharpe_ratio_rejects_nonfinite_return(
    bad_value: float,
) -> None:
    with pytest.raises(ValueError, match="missing|finite"):
        calculate_sharpe_ratio(_return_series([0.01, bad_value]))


def test_calculate_sharpe_ratio_rejects_boolean_return() -> None:
    with pytest.raises(TypeError, match="Boolean"):
        calculate_sharpe_ratio(_return_series([0.01, True]))


def test_calculate_sharpe_ratio_rejects_complex_return() -> None:
    with pytest.raises(TypeError, match="complex"):
        calculate_sharpe_ratio(_return_series([0.01, 0.02 + 0.01j]))


@pytest.mark.parametrize("bad_value", [-1.0, -1.01])
def test_calculate_sharpe_ratio_rejects_total_loss_or_below(
    bad_value: float,
) -> None:
    with pytest.raises(ValueError, match="greater than -1.0"):
        calculate_sharpe_ratio(_return_series([0.01, bad_value]))


@pytest.mark.parametrize("bad_rate", [True, 0.01 + 0.01j, "0.01"])
def test_calculate_sharpe_ratio_rejects_invalid_risk_free_rate_type(
    bad_rate: object,
) -> None:
    with pytest.raises(TypeError, match="annual_risk_free_rate"):
        calculate_sharpe_ratio(
            _return_series([0.01, 0.02]),
            annual_risk_free_rate=bad_rate,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize("bad_rate", [np.nan, np.inf, -np.inf])
def test_calculate_sharpe_ratio_rejects_nonfinite_risk_free_rate(
    bad_rate: float,
) -> None:
    with pytest.raises(ValueError, match="finite"):
        calculate_sharpe_ratio(
            _return_series([0.01, 0.02]),
            annual_risk_free_rate=bad_rate,
        )


@pytest.mark.parametrize("bad_rate", [-1.0, -1.01])
def test_calculate_sharpe_ratio_rejects_risk_free_rate_at_or_below_minus_one(
    bad_rate: float,
) -> None:
    with pytest.raises(ValueError, match="greater than -1.0"):
        calculate_sharpe_ratio(
            _return_series([0.01, 0.02]),
            annual_risk_free_rate=bad_rate,
        )


@pytest.mark.parametrize("bad_periods", [0, -1])
def test_calculate_sharpe_ratio_rejects_nonpositive_periods(
    bad_periods: int,
) -> None:
    with pytest.raises(ValueError, match="greater than zero"):
        calculate_sharpe_ratio(
            _return_series([0.01, 0.02]),
            periods_per_year=bad_periods,
        )


@pytest.mark.parametrize("bad_periods", [4.0, "4", True])
def test_calculate_sharpe_ratio_rejects_invalid_periods_type(
    bad_periods: object,
) -> None:
    with pytest.raises(TypeError, match="integer"):
        calculate_sharpe_ratio(
            _return_series([0.01, 0.02]),
            periods_per_year=bad_periods,  # type: ignore[arg-type]
        )
