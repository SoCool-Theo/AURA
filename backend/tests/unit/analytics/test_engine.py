from dataclasses import FrozenInstanceError

import numpy as np
import pandas as pd
import pytest

import backend.app.analytics as analytics_package
from backend.app.analytics import (
    PortfolioAnalyticsResult as PublicPortfolioAnalyticsResult,
)
from backend.app.analytics import analyze_portfolio as public_analyze_portfolio
from backend.app.analytics.concentration import (
    ConcentrationResult,
    analyze_concentration,
)
from backend.app.analytics.correlation import (
    calculate_correlation_matrix,
    extract_correlation_pairs,
)
from backend.app.analytics.diversification import (
    DiversificationResult,
    analyze_diversification,
)
from backend.app.analytics.drawdown import (
    MaxDrawdownResult,
    calculate_max_drawdown,
    calculate_max_drawdown_details,
)
from backend.app.analytics.engine import (
    PortfolioAnalyticsResult,
    analyze_portfolio,
)
from backend.app.analytics.returns import (
    calculate_annualized_return,
    calculate_asset_returns,
    calculate_cumulative_return,
    calculate_portfolio_returns,
)
from backend.app.analytics.risk_classifier import (
    AssetRiskClassificationResult,
    RiskClassificationResult,
    analyze_asset_risk_classification,
    analyze_risk_classification,
)
from backend.app.analytics.risk_driver import (
    RiskDriverResult,
    analyze_risk_drivers,
)
from backend.app.analytics.sharpe import calculate_sharpe_ratio
from backend.app.analytics.volatility import (
    calculate_annualized_volatility,
    calculate_asset_volatilities,
)
from backend.scripts.run_engine_check import main as run_engine_check


def _prices() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "BETA": [100.0, 110.0, 99.0, 118.8],
            "ALPHA": [100.0, 100.0, 110.0, 104.5],
        },
        index=pd.date_range("2026-01-01", periods=4),
    )


def _weights() -> dict[str, float]:
    return {"ALPHA": 0.40, "BETA": 0.60}


def _analyze() -> PortfolioAnalyticsResult:
    return analyze_portfolio(
        _prices(),
        _weights(),
        annual_risk_free_rate=0.03,
        periods_per_year=3,
        concentration_top_n=1,
    )


def test_public_analytics_package_exports_stable_engine_interface() -> None:
    assert PublicPortfolioAnalyticsResult is PortfolioAnalyticsResult
    assert public_analyze_portfolio is analyze_portfolio
    assert analytics_package.__all__ == [
        "PortfolioAnalyticsResult",
        "analyze_portfolio",
    ]


def test_public_analyze_portfolio_runs_end_to_end() -> None:
    prices = _prices()
    result = public_analyze_portfolio(
        prices,
        _weights(),
        annual_risk_free_rate=0.03,
        periods_per_year=3,
        concentration_top_n=1,
    )

    assert isinstance(result, PublicPortfolioAnalyticsResult)
    assert isinstance(result.max_drawdown, MaxDrawdownResult)
    assert isinstance(result.concentration, ConcentrationResult)
    assert isinstance(result.diversification, DiversificationResult)
    assert isinstance(result.risk_drivers, RiskDriverResult)
    assert isinstance(result.risk_classification, RiskClassificationResult)
    assert result.risk_drivers.top_driver in prices.columns
    assert result.risk_classification.risk_level in {
        "Low",
        "Moderate",
        "High",
        "Very High",
    }


def test_manual_engine_check_prints_finite_summary(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = run_engine_check()
    output = capsys.readouterr().out

    assert exit_code == 0
    for heading in (
        "Analysis start:",
        "Analysis end:",
        "Number of assets:",
        "Number of price observations:",
        "Cumulative portfolio return:",
        "Annualized portfolio return:",
        "Annualized volatility:",
        "Maximum drawdown:",
        "Sharpe ratio:",
        "Diversification level:",
        "Diversification score:",
        "Overall risk level:",
        "Overall risk score:",
        "Top risk driver:",
    ):
        assert heading in output

    normalized_output = output.lower()
    assert "buy" not in normalized_output
    assert "sell" not in normalized_output
    assert "nan" not in normalized_output
    assert "infinity" not in normalized_output


def test_analyze_portfolio_returns_complete_result() -> None:
    result = _analyze()

    assert isinstance(result, PortfolioAnalyticsResult)
    assert result.analysis_start == pd.Timestamp("2026-01-01")
    assert result.analysis_end == pd.Timestamp("2026-01-04")
    assert type(result.price_observation_count) is int
    assert result.price_observation_count == 4
    assert type(result.return_observation_count) is int
    assert result.return_observation_count == 3
    assert type(result.asset_count) is int
    assert result.asset_count == 2
    assert result.cumulative_return == pytest.approx(0.14268)
    assert result.annualized_return == pytest.approx(0.14268)


def test_analyze_portfolio_has_known_portfolio_returns_and_drawdown() -> None:
    result = _analyze()
    expected_returns = pd.Series(
        [0.06, -0.02, 0.10],
        index=_prices().index[1:],
        name="portfolio_return",
    )

    pd.testing.assert_series_equal(
        result.portfolio_returns,
        expected_returns,
        check_exact=False,
        rtol=1e-12,
        atol=1e-12,
    )
    assert result.max_drawdown == MaxDrawdownResult(
        max_drawdown=pytest.approx(-0.02),
        peak_date=_prices().index[1],
        trough_date=_prices().index[2],
    )


def test_analyze_portfolio_result_is_frozen() -> None:
    result = _analyze()

    with pytest.raises(FrozenInstanceError):
        result.asset_count = 3  # type: ignore[misc]


def test_engine_results_match_direct_public_module_calls() -> None:
    prices = _prices()
    weights = _weights()
    result = analyze_portfolio(
        prices,
        weights,
        annual_risk_free_rate=0.03,
        periods_per_year=3,
        concentration_top_n=1,
    )

    asset_returns = calculate_asset_returns(prices)
    portfolio_returns = calculate_portfolio_returns(asset_returns, weights)
    correlation_matrix = calculate_correlation_matrix(asset_returns)
    max_drawdown = calculate_max_drawdown_details(portfolio_returns)
    concentration = analyze_concentration(weights, top_n=1)
    diversification = analyze_diversification(weights, correlation_matrix)
    risk_drivers = analyze_risk_drivers(
        asset_returns,
        weights,
        periods_per_year=3,
    )
    risk_classification = analyze_risk_classification(
        calculate_annualized_volatility(
            portfolio_returns,
            periods_per_year=3,
        ),
        max_drawdown.max_drawdown,
        concentration.largest_weight,
        diversification.overall_score,
    )
    asset_volatilities = calculate_asset_volatilities(
        asset_returns,
        periods_per_year=3,
    )

    pd.testing.assert_frame_equal(result.asset_returns, asset_returns)
    pd.testing.assert_series_equal(result.portfolio_returns, portfolio_returns)
    assert result.cumulative_return == pytest.approx(
        calculate_cumulative_return(portfolio_returns)
    )
    assert result.annualized_return == pytest.approx(
        calculate_annualized_return(
            portfolio_returns,
            periods_per_year=3,
        )
    )
    assert result.annualized_volatility == pytest.approx(
        calculate_annualized_volatility(
            portfolio_returns,
            periods_per_year=3,
        )
    )
    assert result.sharpe_ratio == pytest.approx(
        calculate_sharpe_ratio(
            portfolio_returns,
            annual_risk_free_rate=0.03,
            periods_per_year=3,
        )
    )
    assert result.max_drawdown == max_drawdown
    assert result.concentration == concentration
    assert result.diversification == diversification
    pd.testing.assert_frame_equal(
        result.correlation_matrix,
        correlation_matrix,
    )
    pd.testing.assert_frame_equal(
        result.correlation_pairs,
        extract_correlation_pairs(correlation_matrix),
    )
    assert result.risk_drivers.portfolio_volatility == pytest.approx(
        risk_drivers.portfolio_volatility
    )
    assert result.risk_drivers.top_driver == risk_drivers.top_driver
    pd.testing.assert_frame_equal(
        result.risk_drivers.ranked_contributions,
        risk_drivers.ranked_contributions,
    )
    assert result.risk_classification == risk_classification
    for symbol in prices.columns:
        symbol_returns = asset_returns[symbol]
        assert result.asset_metrics.loc[
            symbol, "cumulative_return"
        ] == pytest.approx(calculate_cumulative_return(symbol_returns))
        assert result.asset_metrics.loc[
            symbol, "annualized_return"
        ] == pytest.approx(
            calculate_annualized_return(
                symbol_returns,
                periods_per_year=3,
            )
        )
        assert result.asset_metrics.loc[
            symbol, "annualized_volatility"
        ] == pytest.approx(asset_volatilities[symbol])
        assert result.asset_metrics.loc[
            symbol, "max_drawdown"
        ] == pytest.approx(calculate_max_drawdown(symbol_returns))
        assert result.asset_metrics.loc[
            symbol, "sharpe_ratio"
        ] == pytest.approx(
            calculate_sharpe_ratio(
                symbol_returns,
                annual_risk_free_rate=0.03,
                periods_per_year=3,
            )
        )
        assert result.asset_risk_classifications[symbol] == (
            analyze_asset_risk_classification(
                float(asset_volatilities[symbol]),
                calculate_max_drawdown(symbol_returns),
            )
        )


def test_asset_metrics_have_required_structure_and_alignment() -> None:
    result = _analyze()

    assert isinstance(result.asset_metrics, pd.DataFrame)
    assert list(result.asset_metrics.index) == ["BETA", "ALPHA"]
    assert result.asset_metrics.index.name == "asset"
    assert list(result.asset_metrics.columns) == [
        "weight",
        "cumulative_return",
        "annualized_return",
        "annualized_volatility",
        "max_drawdown",
        "sharpe_ratio",
    ]
    assert result.asset_metrics.loc["BETA", "weight"] == pytest.approx(0.60)
    assert result.asset_metrics.loc["ALPHA", "weight"] == pytest.approx(0.40)


def test_asset_metrics_preserve_full_numerical_precision() -> None:
    result = _analyze()
    beta_volatility = result.asset_metrics.loc[
        "BETA", "annualized_volatility"
    ]

    assert beta_volatility == pytest.approx(0.2645751311064591)
    assert beta_volatility != round(beta_volatility, 6)


def test_engine_forwards_nondefault_parameters() -> None:
    prices = _prices()
    weights = _weights()
    result = analyze_portfolio(
        prices,
        weights,
        annual_risk_free_rate=0.05,
        periods_per_year=6,
        concentration_top_n=1,
    )
    direct_returns = calculate_portfolio_returns(
        calculate_asset_returns(prices),
        weights,
    )

    assert result.annualized_return == pytest.approx(
        calculate_annualized_return(direct_returns, periods_per_year=6)
    )
    assert result.annualized_volatility == pytest.approx(
        calculate_annualized_volatility(
            direct_returns,
            periods_per_year=6,
        )
    )
    assert result.sharpe_ratio == pytest.approx(
        calculate_sharpe_ratio(
            direct_returns,
            annual_risk_free_rate=0.05,
            periods_per_year=6,
        )
    )
    assert result.risk_drivers.portfolio_volatility == pytest.approx(
        analyze_risk_drivers(
            result.asset_returns,
            weights,
            periods_per_year=6,
        ).portfolio_volatility
    )
    assert result.concentration.top_n == 1
    assert result.concentration.top_n_weight == pytest.approx(0.60)
    for symbol in prices.columns:
        symbol_returns = result.asset_returns[symbol]
        assert result.asset_metrics.loc[
            symbol, "annualized_return"
        ] == pytest.approx(
            calculate_annualized_return(
                symbol_returns,
                periods_per_year=6,
            )
        )
        assert result.asset_metrics.loc[
            symbol, "sharpe_ratio"
        ] == pytest.approx(
            calculate_sharpe_ratio(
                symbol_returns,
                annual_risk_free_rate=0.05,
                periods_per_year=6,
            )
        )


def test_engine_uses_covariance_aware_risk_drivers() -> None:
    result = _analyze()
    direct = analyze_risk_drivers(
        result.asset_returns,
        _weights(),
        periods_per_year=3,
    )

    pd.testing.assert_frame_equal(
        result.risk_drivers.ranked_contributions,
        direct.ranked_contributions,
    )
    assert result.risk_drivers.top_driver == "BETA"
    assert result.risk_drivers.ranked_contributions.loc[
        "ALPHA", "component_volatility_contribution"
    ] < 0.0


def test_engine_classification_uses_completed_metric_results() -> None:
    result = _analyze()
    direct = analyze_risk_classification(
        result.annualized_volatility,
        result.max_drawdown.max_drawdown,
        result.concentration.largest_weight,
        result.diversification.overall_score,
    )

    assert result.risk_classification == direct
    assert result.risk_classification.diversification_points is not None
    assert "diversification" in result.risk_classification.metrics_used


def test_weight_mapping_order_does_not_change_asset_alignment() -> None:
    prices = _prices()
    reordered_weights = {"BETA": 0.60, "ALPHA": 0.40}

    result = analyze_portfolio(
        prices,
        reordered_weights,
        periods_per_year=3,
    )

    assert list(result.asset_returns.columns) == ["BETA", "ALPHA"]
    assert list(result.correlation_matrix.index) == ["BETA", "ALPHA"]
    assert list(result.correlation_matrix.columns) == ["BETA", "ALPHA"]
    assert result.risk_drivers.top_driver in prices.columns
    assert set(result.risk_drivers.ranked_contributions.index) == {
        "BETA",
        "ALPHA",
    }
    assert result.asset_metrics["weight"].to_dict() == {
        "BETA": pytest.approx(0.60),
        "ALPHA": pytest.approx(0.40),
    }


def test_engine_preserves_inputs() -> None:
    prices = _prices()
    original_prices = prices.copy(deep=True)
    weights = _weights()
    original_weights = weights.copy()

    result = analyze_portfolio(
        prices,
        weights,
        periods_per_year=3,
    )

    pd.testing.assert_frame_equal(prices, original_prices)
    assert weights == original_weights
    assert list(weights) == list(original_weights)
    assert result.asset_returns is not prices


def test_engine_result_has_expected_pandas_and_nested_types() -> None:
    result = _analyze()

    assert isinstance(result.asset_metrics, pd.DataFrame)
    assert list(result.asset_risk_classifications) == ["BETA", "ALPHA"]
    assert all(
        isinstance(classification, AssetRiskClassificationResult)
        for classification in result.asset_risk_classifications.values()
    )
    assert isinstance(result.asset_returns, pd.DataFrame)
    assert isinstance(result.portfolio_returns, pd.Series)
    assert result.portfolio_returns.name == "portfolio_return"
    assert isinstance(result.correlation_matrix, pd.DataFrame)
    assert isinstance(result.correlation_pairs, pd.DataFrame)
    assert list(result.correlation_pairs.columns) == [
        "asset_1",
        "asset_2",
        "correlation",
    ]
    assert isinstance(result.max_drawdown, MaxDrawdownResult)
    assert isinstance(result.concentration, ConcentrationResult)
    assert isinstance(result.diversification, DiversificationResult)
    assert isinstance(result.risk_drivers, RiskDriverResult)
    assert isinstance(
        result.risk_classification,
        RiskClassificationResult,
    )
    assert (
        result.risk_drivers.top_driver
        in result.risk_drivers.ranked_contributions.index
    )


def test_engine_preserves_undefined_correlations() -> None:
    prices = pd.DataFrame(
        {
            "VARIABLE": [100.0, 110.0, 110.0, 121.0],
            "CONSTANT_RETURN": [10.0, 20.0, 40.0, 80.0],
        },
        index=pd.date_range("2026-01-01", periods=4),
    )

    result = analyze_portfolio(
        prices,
        {"VARIABLE": 0.60, "CONSTANT_RETURN": 0.40},
        periods_per_year=3,
    )

    assert result.correlation_matrix.loc[
        "CONSTANT_RETURN"
    ].isna().all()
    assert result.correlation_matrix[
        "CONSTANT_RETURN"
    ].isna().all()
    assert result.correlation_pairs["correlation"].isna().all()
    assert not (
        result.correlation_matrix.fillna(2.0).to_numpy() == 0.0
    ).all()
    assert result.diversification.overall_score is None
    assert result.diversification.level == "Unavailable"
    assert result.risk_classification.diversification_points is None
    assert "diversification" not in (
        result.risk_classification.metrics_used
    )
    assert result.risk_classification.reasons[-1] == (
        "Diversification score unavailable"
    )
    assert result.risk_drivers.portfolio_volatility > 0.0
    assert result.asset_metrics.loc[
        "CONSTANT_RETURN", "annualized_volatility"
    ] == pytest.approx(0.0)
    constant_sharpe = result.asset_metrics.loc[
        "CONSTANT_RETURN", "sharpe_ratio"
    ]
    assert np.isnan(constant_sharpe)
    assert constant_sharpe != 0.0
    assert not np.isinf(constant_sharpe)
    assert np.isfinite(
        result.asset_metrics.loc["VARIABLE", "sharpe_ratio"]
    )
    assert np.isfinite(result.sharpe_ratio)


def test_zero_volatility_portfolio_propagates_value_error() -> None:
    prices = pd.DataFrame(
        {"CONSTANT_RETURN": [1.0, 2.0, 4.0, 8.0]},
        index=pd.date_range("2026-01-01", periods=4),
    )

    with pytest.raises(ValueError, match="Sharpe ratio.*zero"):
        analyze_portfolio(
            prices,
            {"CONSTANT_RETURN": 1.0},
            periods_per_year=3,
        )


@pytest.mark.parametrize(
    "weights",
    [
        {"BETA": 1.0},
        {"BETA": 0.60, "ALPHA": 0.30, "EXTRA": 0.10},
        {"BETA": 0.60, "alpha": 0.40},
    ],
)
def test_engine_propagates_symbol_mismatch_errors(
    weights: dict[str, float],
) -> None:
    with pytest.raises(ValueError, match="exactly match"):
        analyze_portfolio(_prices(), weights, periods_per_year=3)


def test_engine_propagates_invalid_price_type() -> None:
    with pytest.raises(TypeError, match="prices.*DataFrame"):
        analyze_portfolio(  # type: ignore[arg-type]
            [[100.0], [110.0], [120.0]],
            {"A": 1.0},
        )


def test_engine_propagates_unsorted_dates() -> None:
    prices = _prices().iloc[[0, 2, 1, 3]]

    with pytest.raises(ValueError, match="strictly increasing"):
        analyze_portfolio(prices, _weights(), periods_per_year=3)


def test_engine_propagates_missing_price() -> None:
    prices = _prices()
    prices.iloc[1, 0] = np.nan

    with pytest.raises(ValueError, match="missing"):
        analyze_portfolio(prices, _weights(), periods_per_year=3)


def test_engine_propagates_invalid_weight_total() -> None:
    with pytest.raises(ValueError, match="total weight"):
        analyze_portfolio(
            _prices(),
            {"BETA": 0.50, "ALPHA": 0.40},
            periods_per_year=3,
        )


def test_engine_propagates_invalid_risk_free_rate() -> None:
    with pytest.raises(TypeError, match="annual_risk_free_rate"):
        analyze_portfolio(
            _prices(),
            _weights(),
            annual_risk_free_rate="0.03",  # type: ignore[arg-type]
            periods_per_year=3,
        )


@pytest.mark.parametrize(
    ("periods_per_year", "exception_type"),
    [
        (0, ValueError),
        (-1, ValueError),
        (3.0, TypeError),
        ("3", TypeError),
        (True, TypeError),
    ],
)
def test_engine_propagates_invalid_periods_per_year(
    periods_per_year: object,
    exception_type: type[Exception],
) -> None:
    with pytest.raises(exception_type, match="periods_per_year"):
        analyze_portfolio(
            _prices(),
            _weights(),
            periods_per_year=periods_per_year,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    ("concentration_top_n", "exception_type"),
    [
        (0, ValueError),
        (-1, ValueError),
        (1.0, TypeError),
        ("1", TypeError),
        (True, TypeError),
    ],
)
def test_engine_propagates_invalid_concentration_top_n(
    concentration_top_n: object,
    exception_type: type[Exception],
) -> None:
    with pytest.raises(exception_type, match="top_n"):
        analyze_portfolio(
            _prices(),
            _weights(),
            periods_per_year=3,
            concentration_top_n=concentration_top_n,  # type: ignore[arg-type]
        )
