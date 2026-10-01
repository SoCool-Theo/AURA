"""Coordination layer for Aura's completed portfolio analytics."""

from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .concentration import ConcentrationResult, analyze_concentration
from .correlation import (
    calculate_correlation_matrix,
    extract_correlation_pairs,
)
from .diversification import DiversificationResult, analyze_diversification
from .drawdown import (
    MaxDrawdownResult,
    calculate_max_drawdown,
    calculate_max_drawdown_details,
)
from .returns import (
    calculate_annualized_return,
    calculate_asset_returns,
    calculate_cumulative_return,
    calculate_fixed_share_portfolio_values,
    calculate_portfolio_returns,
)
from .risk_classifier import (
    AssetRiskClassificationResult,
    RiskClassificationResult,
    analyze_asset_risk_classification,
    analyze_risk_classification,
)
from .risk_driver import RiskDriverResult, analyze_risk_drivers
from .sharpe import calculate_sharpe_ratio
from .volatility import (
    calculate_annualized_volatility,
    calculate_asset_volatilities,
)


_ASSET_METRIC_COLUMNS = (
    "weight",
    "cumulative_return",
    "annualized_return",
    "annualized_volatility",
    "max_drawdown",
    "sharpe_ratio",
)
_ZERO_VOLATILITY_SHARPE_ERROR = (
    "Sharpe ratio is undefined when return volatility is zero"
)


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

    asset_metrics: pd.DataFrame
    asset_risk_classifications: Mapping[
        str, AssetRiskClassificationResult
    ]
    asset_returns: pd.DataFrame
    portfolio_returns: pd.Series
    correlation_matrix: pd.DataFrame
    correlation_pairs: pd.DataFrame
    historical_portfolio_values: pd.Series | None = None


def _calculate_asset_sharpe_ratio(
    asset_returns: pd.Series,
    annual_risk_free_rate: float,
    periods_per_year: int,
) -> float:
    try:
        return calculate_sharpe_ratio(
            asset_returns,
            annual_risk_free_rate=annual_risk_free_rate,
            periods_per_year=periods_per_year,
        )
    except ValueError as error:
        if str(error) != _ZERO_VOLATILITY_SHARPE_ERROR:
            raise
        return np.nan


def _calculate_asset_metrics(
    asset_returns: pd.DataFrame,
    weights: Mapping[str, float],
    annual_risk_free_rate: float,
    periods_per_year: int,
) -> pd.DataFrame:
    annualized_volatilities = calculate_asset_volatilities(
        asset_returns,
        periods_per_year=periods_per_year,
    )
    rows: list[tuple[float, float, float, float, float, float]] = []

    for symbol in asset_returns.columns:
        returns = asset_returns[symbol]
        rows.append(
            (
                float(weights[symbol]),
                calculate_cumulative_return(returns),
                calculate_annualized_return(
                    returns,
                    periods_per_year=periods_per_year,
                ),
                float(annualized_volatilities[symbol]),
                calculate_max_drawdown(returns),
                _calculate_asset_sharpe_ratio(
                    returns,
                    annual_risk_free_rate,
                    periods_per_year,
                ),
            )
        )

    return pd.DataFrame(
        rows,
        index=pd.Index(asset_returns.columns, name="asset"),
        columns=_ASSET_METRIC_COLUMNS,
    )


def _calculate_asset_risk_classifications(
    asset_metrics: pd.DataFrame,
) -> dict[str, AssetRiskClassificationResult]:
    return {
        str(symbol): analyze_asset_risk_classification(
            float(row["annualized_volatility"]),
            float(row["max_drawdown"]),
        )
        for symbol, row in asset_metrics.iterrows()
    }


def _confirm_result_consistency(
    price_symbols: pd.Index,
    asset_metrics: pd.DataFrame,
    asset_risk_classifications: Mapping[
        str, AssetRiskClassificationResult
    ],
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
    if (
        not asset_metrics.index.equals(price_symbols)
        or asset_metrics.index.name != "asset"
    ):
        raise ValueError(
            "calculated asset-metric index must match price columns"
        )
    if tuple(asset_metrics.columns) != _ASSET_METRIC_COLUMNS:
        raise ValueError(
            "calculated asset-metric columns must match the engine contract"
        )
    if list(asset_risk_classifications) != list(price_symbols):
        raise ValueError(
            "calculated asset-risk symbols must match price columns"
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
    *,
    share_quantities: Mapping[str, float] | None = None,
) -> PortfolioAnalyticsResult:
    """Coordinate all completed analytics for validated portfolio inputs."""
    asset_returns = calculate_asset_returns(prices)
    historical_portfolio_values = None
    if share_quantities is None:
        portfolio_returns = calculate_portfolio_returns(asset_returns, weights)
    else:
        historical_portfolio_values = calculate_fixed_share_portfolio_values(
            prices,
            share_quantities,
        )
        portfolio_returns = calculate_asset_returns(
            historical_portfolio_values.to_frame()
        )["portfolio_value"].rename("portfolio_return")
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
    asset_metrics = _calculate_asset_metrics(
        asset_returns,
        weights,
        annual_risk_free_rate,
        periods_per_year,
    )
    asset_risk_classifications = _calculate_asset_risk_classifications(
        asset_metrics
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
        asset_metrics,
        asset_risk_classifications,
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
        asset_metrics=asset_metrics,
        asset_risk_classifications=asset_risk_classifications,
        asset_returns=asset_returns,
        portfolio_returns=portfolio_returns,
        correlation_matrix=correlation_matrix,
        correlation_pairs=correlation_pairs,
        historical_portfolio_values=historical_portfolio_values,
    )
