from collections.abc import Mapping
from dataclasses import FrozenInstanceError

import numpy as np
import pandas as pd
import pytest

from backend.app.analytics.risk_driver import (
    RiskDriverResult,
    analyze_risk_drivers,
    calculate_risk_contributions,
    rank_risk_drivers,
)


CONTRIBUTION_COLUMNS = [
    "weight",
    "annualized_asset_volatility",
    "marginal_volatility_contribution",
    "component_volatility_contribution",
    "percentage_volatility_contribution",
]


def _asset_returns() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ALPHA": [0.10, 0.20, 0.30],
            "BETA": [0.05, 0.10, 0.15],
        },
        index=pd.date_range("2026-01-01", periods=3),
    )


def _contributions() -> pd.DataFrame:
    return pd.DataFrame(
        [
            [0.60, 0.20, 0.20, 0.12, 0.75],
            [0.40, 0.10, 0.10, 0.04, 0.25],
        ],
        index=pd.Index(["ALPHA", "BETA"], name="asset"),
        columns=CONTRIBUTION_COLUMNS,
    )


def _negative_contribution_returns() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "GROWTH": [-0.10, 0.0, 0.10],
            "HEDGE": [0.20, 0.0, -0.20],
        },
        index=pd.date_range("2026-01-01", periods=3),
    )


def test_risk_contributions_use_annualized_sample_covariance() -> None:
    result = calculate_risk_contributions(
        _asset_returns(),
        {"ALPHA": 0.60, "BETA": 0.40},
        periods_per_year=4,
    )

    expected = _contributions()
    pd.testing.assert_frame_equal(
        result,
        expected,
        check_exact=False,
        rtol=1e-12,
        atol=1e-12,
    )


def test_risk_contributions_have_expected_structure() -> None:
    result = calculate_risk_contributions(
        _asset_returns(),
        {"ALPHA": 0.60, "BETA": 0.40},
        periods_per_year=4,
    )

    assert isinstance(result, pd.DataFrame)
    assert list(result.columns) == CONTRIBUTION_COLUMNS
    assert list(result.index) == ["ALPHA", "BETA"]
    assert result.index.name == "asset"
    assert all(pd.api.types.is_float_dtype(dtype) for dtype in result.dtypes)


def test_contributions_sum_to_portfolio_volatility_and_one() -> None:
    result = calculate_risk_contributions(
        _asset_returns(),
        {"ALPHA": 0.60, "BETA": 0.40},
        periods_per_year=4,
    )

    assert result["component_volatility_contribution"].sum() == pytest.approx(
        0.16
    )
    assert result[
        "percentage_volatility_contribution"
    ].sum() == pytest.approx(1.0)


def test_risk_contributions_align_weights_by_symbol() -> None:
    result = calculate_risk_contributions(
        _asset_returns(),
        {"BETA": 0.40, "ALPHA": 0.60},
        periods_per_year=4,
    )

    assert result["weight"].to_dict() == {"ALPHA": 0.60, "BETA": 0.40}
    assert result.loc["ALPHA", "component_volatility_contribution"] == (
        pytest.approx(0.12)
    )
    assert result.loc["BETA", "component_volatility_contribution"] == (
        pytest.approx(0.04)
    )


def test_risk_contributions_do_not_mutate_inputs() -> None:
    asset_returns = _asset_returns()
    original_returns = asset_returns.copy(deep=True)
    weights = {"BETA": 0.40, "ALPHA": 0.60}
    original_weights = weights.copy()

    calculate_risk_contributions(
        asset_returns,
        weights,
        periods_per_year=4,
    )

    pd.testing.assert_frame_equal(asset_returns, original_returns)
    assert weights == original_weights
    assert list(weights) == list(original_weights)


def test_zero_weight_asset_remains_with_zero_contribution() -> None:
    asset_returns = _asset_returns().assign(
        ZERO=[0.30, -0.20, 0.10]
    )

    result = calculate_risk_contributions(
        asset_returns,
        {"ALPHA": 0.60, "BETA": 0.40, "ZERO": 0.0},
        periods_per_year=4,
    )

    assert list(result.index) == ["ALPHA", "BETA", "ZERO"]
    assert result.loc["ZERO", "weight"] == pytest.approx(0.0)
    assert result.loc[
        "ZERO", "component_volatility_contribution"
    ] == pytest.approx(0.0)
    assert result.loc[
        "ZERO", "percentage_volatility_contribution"
    ] == pytest.approx(0.0)


def test_negative_risk_contribution_is_preserved() -> None:
    result = calculate_risk_contributions(
        _negative_contribution_returns(),
        {"GROWTH": 0.80, "HEDGE": 0.20},
        periods_per_year=1,
    )

    assert result.loc[
        "GROWTH", "component_volatility_contribution"
    ] == pytest.approx(0.08)
    assert result.loc[
        "HEDGE", "component_volatility_contribution"
    ] == pytest.approx(-0.04)
    assert result.loc[
        "HEDGE", "percentage_volatility_contribution"
    ] == pytest.approx(-1.0)
    assert result[
        "percentage_volatility_contribution"
    ].sum() == pytest.approx(1.0)


def test_constant_asset_is_allowed_when_portfolio_has_volatility() -> None:
    asset_returns = pd.DataFrame(
        {
            "VARIABLE": [-0.10, 0.0, 0.10],
            "CONSTANT": [0.02, 0.02, 0.02],
        },
        index=pd.date_range("2026-01-01", periods=3),
    )

    result = calculate_risk_contributions(
        asset_returns,
        {"VARIABLE": 0.50, "CONSTANT": 0.50},
        periods_per_year=1,
    )

    assert result.loc[
        "CONSTANT", "annualized_asset_volatility"
    ] == pytest.approx(0.0, abs=1e-15)
    assert result.loc[
        "CONSTANT", "component_volatility_contribution"
    ] == pytest.approx(0.0, abs=1e-15)
    assert result["component_volatility_contribution"].sum() == pytest.approx(
        0.05
    )


def test_rank_risk_drivers_sorts_by_signed_component_contribution() -> None:
    contributions = calculate_risk_contributions(
        _negative_contribution_returns(),
        {"GROWTH": 0.80, "HEDGE": 0.20},
        periods_per_year=1,
    )

    result = rank_risk_drivers(contributions)

    assert list(result.index) == ["GROWTH", "HEDGE"]
    assert result["rank"].tolist() == [1, 2]
    assert list(result.columns) == ["rank", *CONTRIBUTION_COLUMNS]
    assert result.loc[
        "HEDGE", "component_volatility_contribution"
    ] < 0.0


def test_rank_risk_drivers_preserves_original_order_for_ties() -> None:
    contributions = pd.DataFrame(
        [
            [0.50, 0.20, 0.10, 0.05, 0.50],
            [0.50, 0.20, 0.10, 0.05, 0.50],
        ],
        index=pd.Index(["BETA", "ALPHA"], name="asset"),
        columns=CONTRIBUTION_COLUMNS,
    )

    result = rank_risk_drivers(contributions)

    assert list(result.index) == ["BETA", "ALPHA"]
    assert result["rank"].tolist() == [1, 2]


def test_rank_risk_drivers_does_not_mutate_input() -> None:
    contributions = _contributions()
    original = contributions.copy(deep=True)

    result = rank_risk_drivers(contributions)

    pd.testing.assert_frame_equal(contributions, original)
    assert "rank" not in contributions.columns
    assert result is not contributions


def test_analyze_risk_drivers_returns_consistent_result() -> None:
    result = analyze_risk_drivers(
        _asset_returns(),
        {"BETA": 0.40, "ALPHA": 0.60},
        periods_per_year=4,
    )

    assert isinstance(result, RiskDriverResult)
    assert result.portfolio_volatility == pytest.approx(0.16)
    assert result.top_driver == "ALPHA"
    assert list(result.ranked_contributions.index) == ["ALPHA", "BETA"]
    assert result.ranked_contributions[
        "component_volatility_contribution"
    ].sum() == pytest.approx(result.portfolio_volatility)
    assert result.ranked_contributions[
        "percentage_volatility_contribution"
    ].sum() == pytest.approx(1.0)


def test_risk_driver_result_is_immutable() -> None:
    result = analyze_risk_drivers(
        _asset_returns(),
        {"ALPHA": 0.60, "BETA": 0.40},
        periods_per_year=4,
    )

    with pytest.raises(FrozenInstanceError):
        result.top_driver = "BETA"  # type: ignore[misc]


def test_analyze_risk_drivers_does_not_mutate_inputs() -> None:
    asset_returns = _asset_returns()
    original_returns = asset_returns.copy(deep=True)
    weights = {"BETA": 0.40, "ALPHA": 0.60}
    original_weights = weights.copy()

    analyze_risk_drivers(asset_returns, weights, periods_per_year=4)

    pd.testing.assert_frame_equal(asset_returns, original_returns)
    assert weights == original_weights
    assert list(weights) == list(original_weights)


def test_negative_contributor_ranks_below_positive_contributor() -> None:
    result = analyze_risk_drivers(
        _negative_contribution_returns(),
        {"GROWTH": 0.80, "HEDGE": 0.20},
        periods_per_year=1,
    )

    assert result.top_driver == "GROWTH"
    assert result.ranked_contributions.loc["GROWTH", "rank"] == 1
    assert result.ranked_contributions.loc["HEDGE", "rank"] == 2
    assert result.portfolio_volatility == pytest.approx(0.04)


@pytest.mark.parametrize(
    "asset_returns",
    [
        pd.DataFrame(index=pd.DatetimeIndex([])),
        pd.DataFrame(
            {"A": [0.10]},
            index=pd.to_datetime(["2026-01-01"]),
        ),
    ],
)
def test_risk_contributions_require_two_rows(
    asset_returns: pd.DataFrame,
) -> None:
    with pytest.raises(ValueError, match="at least two rows"):
        calculate_risk_contributions(asset_returns, {"A": 1.0})


def test_risk_contributions_reject_wrong_return_type() -> None:
    with pytest.raises(TypeError, match="pandas DataFrame"):
        calculate_risk_contributions(  # type: ignore[arg-type]
            [[0.10], [0.20]], {"A": 1.0}
        )


def test_risk_contributions_require_asset_column() -> None:
    asset_returns = pd.DataFrame(
        index=pd.date_range("2026-01-01", periods=2)
    )

    with pytest.raises(ValueError, match="asset column"):
        calculate_risk_contributions(asset_returns, {})


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
def test_risk_contributions_reject_invalid_index(
    index: pd.Index,
    exception_type: type[Exception],
    message: str,
) -> None:
    asset_returns = pd.DataFrame({"A": [0.10, 0.20]}, index=index)

    with pytest.raises(exception_type, match=message):
        calculate_risk_contributions(asset_returns, {"A": 1.0})


def test_risk_contributions_reject_duplicate_symbols() -> None:
    asset_returns = pd.DataFrame(
        [[0.10, 0.20], [0.20, 0.30]],
        index=pd.date_range("2026-01-01", periods=2),
        columns=["A", "A"],
    )

    with pytest.raises(ValueError, match="unique"):
        calculate_risk_contributions(asset_returns, {"A": 1.0})


@pytest.mark.parametrize("symbol", ["", " ", " A", "A "])
def test_risk_contributions_reject_invalid_return_symbol(
    symbol: str,
) -> None:
    asset_returns = pd.DataFrame(
        {symbol: [0.10, 0.20]},
        index=pd.date_range("2026-01-01", periods=2),
    )

    with pytest.raises(ValueError, match="asset symbols"):
        calculate_risk_contributions(asset_returns, {symbol: 1.0})


def test_risk_contributions_reject_non_string_return_symbol() -> None:
    asset_returns = pd.DataFrame(
        {1: [0.10, 0.20]},
        index=pd.date_range("2026-01-01", periods=2),
    )

    with pytest.raises(TypeError, match="strings"):
        calculate_risk_contributions(  # type: ignore[arg-type]
            asset_returns, {1: 1.0}
        )


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
def test_risk_contributions_reject_invalid_return_value(
    invalid_value: object,
    exception_type: type[Exception],
    message: str,
) -> None:
    asset_returns = pd.DataFrame(
        {"A": [0.10, invalid_value]},
        index=pd.date_range("2026-01-01", periods=2),
    )

    with pytest.raises(exception_type, match=message):
        calculate_risk_contributions(asset_returns, {"A": 1.0})


def test_risk_contributions_reject_wrong_weight_type() -> None:
    with pytest.raises(TypeError, match="Mapping"):
        calculate_risk_contributions(  # type: ignore[arg-type]
            _asset_returns(), [0.60, 0.40]
        )


def test_risk_contributions_reject_empty_weights() -> None:
    with pytest.raises(ValueError, match="at least one asset"):
        calculate_risk_contributions(_asset_returns(), {})


@pytest.mark.parametrize("symbol", ["", " ", " ALPHA", "ALPHA "])
def test_risk_contributions_reject_invalid_weight_symbol(
    symbol: str,
) -> None:
    with pytest.raises(ValueError, match="asset symbols"):
        calculate_risk_contributions(
            _asset_returns(),
            {symbol: 0.60, "BETA": 0.40},
        )


def test_risk_contributions_reject_non_string_weight_symbol() -> None:
    with pytest.raises(TypeError, match="strings"):
        calculate_risk_contributions(  # type: ignore[arg-type]
            _asset_returns(),
            {1: 0.60, "BETA": 0.40},
        )


@pytest.mark.parametrize(
    "weights",
    [
        {"ALPHA": 1.0},
        {"ALPHA": 0.60, "BETA": 0.30, "EXTRA": 0.10},
        {"alpha": 0.60, "BETA": 0.40},
    ],
)
def test_risk_contributions_require_exact_weight_symbols(
    weights: Mapping[str, float],
) -> None:
    with pytest.raises(ValueError, match="exactly match"):
        calculate_risk_contributions(_asset_returns(), weights)


@pytest.mark.parametrize(
    ("weights", "exception_type", "message"),
    [
        (
            {"ALPHA": -0.10, "BETA": 1.10},
            ValueError,
            "between",
        ),
        (
            {"ALPHA": 1.10, "BETA": -0.10},
            ValueError,
            "between",
        ),
        (
            {"ALPHA": 0.0, "BETA": 0.0},
            ValueError,
            "greater than zero",
        ),
        (
            {"ALPHA": 0.60, "BETA": 0.30},
            ValueError,
            "total weight",
        ),
        (
            {"ALPHA": np.nan, "BETA": 0.40},
            ValueError,
            "finite",
        ),
        (
            {"ALPHA": np.inf, "BETA": 0.40},
            ValueError,
            "finite",
        ),
        (
            {"ALPHA": True, "BETA": 0.0},
            TypeError,
            "Boolean",
        ),
        (
            {"ALPHA": 1.0 + 0.0j, "BETA": 0.0},
            TypeError,
            "complex",
        ),
        (
            {"ALPHA": 40, "BETA": 0.0},
            ValueError,
            "between",
        ),
    ],
)
def test_risk_contributions_reject_invalid_weight_values(
    weights: Mapping[str, object],
    exception_type: type[Exception],
    message: str,
) -> None:
    with pytest.raises(exception_type, match=message):
        calculate_risk_contributions(  # type: ignore[arg-type]
            _asset_returns(), weights
        )


def test_risk_contributions_accept_weight_tolerance_and_numpy_values() -> None:
    result = calculate_risk_contributions(
        _asset_returns(),
        {
            "ALPHA": np.float64(0.60),
            "BETA": np.float32(0.4000005),
        },
        periods_per_year=np.int64(4),
    )

    assert result.loc["ALPHA", "weight"] == pytest.approx(0.60)
    assert result.loc["BETA", "weight"] == pytest.approx(
        float(np.float32(0.4000005))
    )


@pytest.mark.parametrize(
    ("periods_per_year", "exception_type"),
    [
        (0, ValueError),
        (-1, ValueError),
        (4.0, TypeError),
        ("4", TypeError),
        (True, TypeError),
    ],
)
def test_risk_contributions_reject_invalid_periods_per_year(
    periods_per_year: object,
    exception_type: type[Exception],
) -> None:
    with pytest.raises(exception_type, match="periods_per_year"):
        calculate_risk_contributions(
            _asset_returns(),
            {"ALPHA": 0.60, "BETA": 0.40},
            periods_per_year=periods_per_year,  # type: ignore[arg-type]
        )


def test_all_constant_returns_have_undefined_risk_contribution() -> None:
    asset_returns = pd.DataFrame(
        {"A": [0.10, 0.10, 0.10], "B": [0.20, 0.20, 0.20]},
        index=pd.date_range("2026-01-01", periods=3),
    )

    with pytest.raises(
        ValueError,
        match="undefined.*zero-volatility",
    ):
        calculate_risk_contributions(
            asset_returns,
            {"A": 0.50, "B": 0.50},
        )


def test_perfectly_offsetting_portfolio_has_undefined_contributions() -> None:
    asset_returns = pd.DataFrame(
        {"A": [-0.10, 0.0, 0.10], "B": [0.10, 0.0, -0.10]},
        index=pd.date_range("2026-01-01", periods=3),
    )

    with pytest.raises(
        ValueError,
        match="undefined.*zero-volatility",
    ):
        calculate_risk_contributions(
            asset_returns,
            {"A": 0.50, "B": 0.50},
            periods_per_year=1,
        )


def test_materially_negative_portfolio_variance_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def invalid_covariance(
        frame: pd.DataFrame,
        ddof: int = 1,
    ) -> pd.DataFrame:
        del ddof
        return pd.DataFrame(
            [[1.0, -2.0], [-2.0, 1.0]],
            index=frame.columns,
            columns=frame.columns,
        )

    monkeypatch.setattr(pd.DataFrame, "cov", invalid_covariance)

    with pytest.raises(ValueError, match="materially negative"):
        calculate_risk_contributions(
            _asset_returns(),
            {"ALPHA": 0.50, "BETA": 0.50},
            periods_per_year=1,
        )


def test_rank_risk_drivers_rejects_wrong_type() -> None:
    with pytest.raises(TypeError, match="pandas DataFrame"):
        rank_risk_drivers([])  # type: ignore[arg-type]


def test_rank_risk_drivers_rejects_empty_dataframe() -> None:
    contributions = pd.DataFrame(columns=CONTRIBUTION_COLUMNS)
    contributions.index.name = "asset"

    with pytest.raises(ValueError, match="at least one asset"):
        rank_risk_drivers(contributions)


def test_rank_risk_drivers_requires_exact_columns() -> None:
    missing = _contributions().drop(
        columns="marginal_volatility_contribution"
    )
    extra = _contributions().assign(extra=0.0)

    with pytest.raises(ValueError, match="exactly"):
        rank_risk_drivers(missing)
    with pytest.raises(ValueError, match="exactly"):
        rank_risk_drivers(extra)


def test_rank_risk_drivers_requires_asset_index_name() -> None:
    contributions = _contributions().rename_axis(None)

    with pytest.raises(ValueError, match="index name.*asset"):
        rank_risk_drivers(contributions)


def test_rank_risk_drivers_rejects_duplicate_symbols() -> None:
    contributions = _contributions()
    contributions.index = pd.Index(["ALPHA", "ALPHA"], name="asset")

    with pytest.raises(ValueError, match="unique"):
        rank_risk_drivers(contributions)


@pytest.mark.parametrize("symbol", ["", " ", " ALPHA", "ALPHA "])
def test_rank_risk_drivers_rejects_invalid_symbol(symbol: str) -> None:
    contributions = _contributions()
    contributions.index = pd.Index([symbol, "BETA"], name="asset")

    with pytest.raises(ValueError, match="asset symbols"):
        rank_risk_drivers(contributions)


def test_rank_risk_drivers_rejects_non_string_symbol() -> None:
    contributions = _contributions()
    contributions.index = pd.Index([1, "BETA"], name="asset")

    with pytest.raises(TypeError, match="strings"):
        rank_risk_drivers(contributions)


@pytest.mark.parametrize(
    ("invalid_value", "exception_type", "message"),
    [
        (np.nan, ValueError, "missing"),
        (np.inf, ValueError, "finite"),
        (-np.inf, ValueError, "finite"),
        (True, TypeError, "Boolean"),
        (0.10 + 0.0j, TypeError, "complex"),
        ("0.10", TypeError, "real numeric"),
    ],
)
def test_rank_risk_drivers_rejects_invalid_value(
    invalid_value: object,
    exception_type: type[Exception],
    message: str,
) -> None:
    contributions = _contributions().astype(object)
    contributions.iloc[0, 2] = invalid_value

    with pytest.raises(exception_type, match=message):
        rank_risk_drivers(contributions)


@pytest.mark.parametrize("invalid_weight", [-0.01, 1.01])
def test_rank_risk_drivers_rejects_invalid_weight(
    invalid_weight: float,
) -> None:
    contributions = _contributions()
    contributions.loc["ALPHA", "weight"] = invalid_weight

    with pytest.raises(ValueError, match="weights.*between"):
        rank_risk_drivers(contributions)


def test_rank_risk_drivers_rejects_negative_asset_volatility() -> None:
    contributions = _contributions()
    contributions.loc["ALPHA", "annualized_asset_volatility"] = -0.01

    with pytest.raises(ValueError, match="volatility.*negative"):
        rank_risk_drivers(contributions)


def test_rank_risk_drivers_requires_positive_component_total() -> None:
    contributions = _contributions()
    contributions["component_volatility_contribution"] = [0.01, -0.01]

    with pytest.raises(ValueError, match="sum to a positive"):
        rank_risk_drivers(contributions)


def test_rank_risk_drivers_requires_percentage_total_of_one() -> None:
    contributions = _contributions()
    contributions["percentage_volatility_contribution"] = [0.60, 0.30]

    with pytest.raises(ValueError, match="sum to 1.0"):
        rank_risk_drivers(contributions)
