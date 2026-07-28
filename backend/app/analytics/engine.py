"""Coordination layer for Aura's completed portfolio analytics."""

from collections.abc import Mapping
from dataclasses import dataclass

import pandas as pd

from .concentration import ConcentrationResult, analyze_concentration
from .correlation import (
    calculate_correlation_matrix,
    extract_correlation_pairs,
)
from .diversification import DiversificationResult, analyze_diversification
from .drawdown import MaxDrawdownResult, calculate_max_drawdown_details
from .returns import (
    calculate_annualized_return,
    calculate_asset_returns,
    calculate_cumulative_return,
    calculate_portfolio_returns,
)
from .risk_classifier import (
    RiskClassificationResult,
    analyze_risk_classification,
)
from .risk_driver import RiskDriverResult, analyze_risk_drivers
from .sharpe import calculate_sharpe_ratio
from .volatility import calculate_annualized_volatility


@dataclass(frozen=True, slots=True)
class PortfolioAnalyticsResult:
    """Contain coordinated portfolio analytics and supporting structures."""

    analysis_start: pd.Timestamp
    analysis_end: pd.Timestamp
    price_observation_count: int
    return_observation_count: int
    asset_count: int

    cumulative_return: float
    annualized_return: float
    annualized_volatility: float
    sharpe_ratio: float

    max_drawdown: MaxDrawdownResult
    concentration: ConcentrationResult
    diversification: DiversificationResult
    risk_drivers: RiskDriverResult
    risk_classification: RiskClassificationResult

    asset_returns: pd.DataFrame
    portfolio_returns: pd.Series
    correlation_matrix: pd.DataFrame
    correlation_pairs: pd.DataFrame


def _confirm_result_consistency(
    price_symbols: pd.Index,
    asset_returns: pd.DataFrame,
    portfolio_returns: pd.Series,
    correlation_matrix: pd.DataFrame,
    risk_drivers: RiskDriverResult,
) -> None:
    if asset_returns.empty:
        raise ValueError("calculated asset returns cannot be empty")
    if not asset_returns.columns.equals(price_symbols):
        raise ValueError(
            "calculated asset-return columns must match price columns"
        )
    if not portfolio_returns.index.equals(asset_returns.index):
        raise ValueError(
            "calculated portfolio-return index must match asset-return index"
        )
    if not (
        correlation_matrix.index.equals(price_symbols)
        and correlation_matrix.columns.equals(price_symbols)
    ):
        raise ValueError(
            "calculated correlation symbols must match portfolio symbols"
        )
    if (
        risk_drivers.top_driver not in price_symbols
        or risk_drivers.top_driver
        not in risk_drivers.ranked_contributions.index
    ):
        raise ValueError(
            "calculated top risk driver must exist in the portfolio"
        )


def analyze_portfolio(
    prices: pd.DataFrame,
    weights: Mapping[str, float],
    annual_risk_free_rate: float = 0.0,
    periods_per_year: int = 252,
    concentration_top_n: int = 3,
) -> PortfolioAnalyticsResult:
    """Coordinate all completed analytics for validated portfolio inputs."""
    asset_returns = calculate_asset_returns(prices)
    portfolio_returns = calculate_portfolio_returns(asset_returns, weights)
    cumulative_return = calculate_cumulative_return(portfolio_returns)
    annualized_return = calculate_annualized_return(
        portfolio_returns,
        periods_per_year=periods_per_year,
    )
    annualized_volatility = calculate_annualized_volatility(
        portfolio_returns,
        periods_per_year=periods_per_year,
    )
    max_drawdown = calculate_max_drawdown_details(portfolio_returns)
    sharpe_ratio = calculate_sharpe_ratio(
        portfolio_returns,
        annual_risk_free_rate=annual_risk_free_rate,
        periods_per_year=periods_per_year,
    )
    correlation_matrix = calculate_correlation_matrix(asset_returns)
    correlation_pairs = extract_correlation_pairs(correlation_matrix)
    concentration = analyze_concentration(
        weights,
        top_n=concentration_top_n,
    )
    diversification = analyze_diversification(
        weights,
        correlation_matrix,
    )
    risk_drivers = analyze_risk_drivers(
        asset_returns,
        weights,
        periods_per_year=periods_per_year,
    )
    risk_classification = analyze_risk_classification(
        annualized_volatility,
        max_drawdown.max_drawdown,
        concentration.largest_weight,
        diversification.overall_score,
    )

    _confirm_result_consistency(
        prices.columns,
        asset_returns,
        portfolio_returns,
        correlation_matrix,
        risk_drivers,
    )
    return PortfolioAnalyticsResult(
        analysis_start=prices.index[0],
        analysis_end=prices.index[-1],
        price_observation_count=int(len(prices)),
        return_observation_count=int(len(asset_returns)),
        asset_count=int(len(prices.columns)),
        cumulative_return=cumulative_return,
        annualized_return=annualized_return,
        annualized_volatility=annualized_volatility,
        sharpe_ratio=sharpe_ratio,
        max_drawdown=max_drawdown,
        concentration=concentration,
        diversification=diversification,
        risk_drivers=risk_drivers,
        risk_classification=risk_classification,
        asset_returns=asset_returns,
        portfolio_returns=portfolio_returns,
        correlation_matrix=correlation_matrix,
        correlation_pairs=correlation_pairs,
    )
