"""Pure adapters for Aura's future portfolio-analysis service."""

from collections.abc import Sequence
from datetime import date
import math

import pandas as pd

from ..analytics import PortfolioAnalyticsResult
from ..database.models import MarketData
from ..schemas import PortfolioAnalysisRequest, PortfolioAnalysisResponse


_MISSING_MARKET_DATA_PREFIX = (
    "market data is unavailable for requested symbols: "
)


def _optional_float(value: float | None) -> float | None:
    return None if value is None else float(value)


def _optional_nan_float(value: object) -> float | None:
    numeric_value = float(value)
    return None if math.isnan(numeric_value) else numeric_value


def _optional_timestamp_date(value: pd.Timestamp | None) -> date | None:
    return None if value is None else value.date()


def _build_price_frame(
    records: Sequence[MarketData],
    symbols: Sequence[str],
) -> pd.DataFrame:
    """Return exact-date-aligned adjusted closes in requested symbol order."""
    requested_symbols = tuple(symbols)
    prices_by_symbol = {symbol: {} for symbol in requested_symbols}

    for record in records:
        if record.symbol in prices_by_symbol:
            prices_by_symbol[record.symbol][record.date] = float(
                record.adjusted_close
            )

    missing_symbols = [
        symbol
        for symbol in requested_symbols
        if not prices_by_symbol[symbol]
    ]
    if missing_symbols:
        raise ValueError(
            _MISSING_MARKET_DATA_PREFIX + ", ".join(missing_symbols)
        )

    if not requested_symbols:
        return pd.DataFrame(index=pd.DatetimeIndex([]))

    common_dates = set.intersection(
        *(set(prices_by_symbol[symbol]) for symbol in requested_symbols)
    )
    ordered_dates = sorted(common_dates)
    values = [
        [
            prices_by_symbol[symbol][observation_date]
            for symbol in requested_symbols
        ]
        for observation_date in ordered_dates
    ]

    return pd.DataFrame(
        values,
        index=pd.DatetimeIndex(ordered_dates),
        columns=requested_symbols,
        dtype=float,
    )


def _map_analysis_response(
    request: PortfolioAnalysisRequest,
    result: PortfolioAnalyticsResult,
) -> PortfolioAnalysisResponse:
    """Map completed analytics into Aura's validated JSON-safe response."""
    risk_driver_entries = [
        {
            "rank": int(row["rank"]),
            "symbol": str(symbol),
            "weight": float(row["weight"]),
            "annualized_asset_volatility": float(
                row["annualized_asset_volatility"]
            ),
            "marginal_volatility_contribution": float(
                row["marginal_volatility_contribution"]
            ),
            "component_volatility_contribution": float(
                row["component_volatility_contribution"]
            ),
            "percentage_volatility_contribution": float(
                row["percentage_volatility_contribution"]
            ),
        }
        for symbol, row in result.risk_drivers.ranked_contributions.iterrows()
    ]
    asset_metrics = [
        {
            "symbol": str(symbol),
            "weight": float(row["weight"]),
            "cumulative_return": float(row["cumulative_return"]),
            "annualized_return": float(row["annualized_return"]),
            "annualized_volatility": float(
                row["annualized_volatility"]
            ),
            "max_drawdown": float(row["max_drawdown"]),
            "sharpe_ratio": _optional_nan_float(row["sharpe_ratio"]),
        }
        for symbol, row in result.asset_metrics.iterrows()
    ]
    correlation_values = [
        [_optional_nan_float(value) for value in row]
        for row in result.correlation_matrix.to_numpy(dtype=object)
    ]
    correlation_pairs = [
        {
            "asset_a": str(row["asset_1"]),
            "asset_b": str(row["asset_2"]),
            "correlation": _optional_nan_float(row["correlation"]),
        }
        for _, row in result.correlation_pairs.iterrows()
    ]
    portfolio_returns = [
        {
            "date": timestamp.date(),
            "portfolio_return": float(value),
        }
        for timestamp, value in result.portfolio_returns.items()
    ]

    return PortfolioAnalysisResponse.model_validate(
        {
            "portfolio_name": request.portfolio_name,
            "start_date": request.start_date,
            "end_date": request.end_date,
            "metadata": {
                "analysis_start": result.analysis_start.date(),
                "analysis_end": result.analysis_end.date(),
                "price_observation_count": int(
                    result.price_observation_count
                ),
                "return_observation_count": int(
                    result.return_observation_count
                ),
                "asset_count": int(result.asset_count),
            },
            "portfolio_metrics": {
                "cumulative_return": float(result.cumulative_return),
                "annualized_return": float(result.annualized_return),
                "annualized_volatility": float(
                    result.annualized_volatility
                ),
                "sharpe_ratio": float(result.sharpe_ratio),
            },
            "max_drawdown": {
                "max_drawdown": float(result.max_drawdown.max_drawdown),
                "peak_date": _optional_timestamp_date(
                    result.max_drawdown.peak_date
                ),
                "trough_date": _optional_timestamp_date(
                    result.max_drawdown.trough_date
                ),
            },
            "concentration": {
                "largest_weight": float(
                    result.concentration.largest_weight
                ),
                "top_n_weight": float(result.concentration.top_n_weight),
                "hhi": float(result.concentration.hhi),
                "effective_number_of_assets": float(
                    result.concentration.effective_number_of_assets
                ),
                "top_n": int(result.concentration.top_n),
            },
            "diversification": {
                "active_asset_count": int(
                    result.diversification.active_asset_count
                ),
                "effective_number_of_assets": float(
                    result.diversification.effective_number_of_assets
                ),
                "weight_score": float(result.diversification.weight_score),
                "average_pairwise_correlation": _optional_float(
                    result.diversification.average_pairwise_correlation
                ),
                "correlation_score": _optional_float(
                    result.diversification.correlation_score
                ),
                "overall_score": _optional_float(
                    result.diversification.overall_score
                ),
                "level": result.diversification.level,
                "defined_pair_count": int(
                    result.diversification.defined_pair_count
                ),
                "total_pair_count": int(
                    result.diversification.total_pair_count
                ),
            },
            "risk_classification": {
                "risk_score": float(
                    result.risk_classification.risk_score
                ),
                "risk_level": result.risk_classification.risk_level,
                "volatility_points": int(
                    result.risk_classification.volatility_points
                ),
                "drawdown_points": int(
                    result.risk_classification.drawdown_points
                ),
                "concentration_points": int(
                    result.risk_classification.concentration_points
                ),
                "diversification_points": (
                    None
                    if result.risk_classification.diversification_points
                    is None
                    else int(
                        result.risk_classification.diversification_points
                    )
                ),
                "metrics_used": list(
                    result.risk_classification.metrics_used
                ),
                "reasons": list(result.risk_classification.reasons),
            },
            "risk_drivers": {
                "portfolio_volatility": float(
                    result.risk_drivers.portfolio_volatility
                ),
                "top_driver": result.risk_drivers.top_driver,
                "entries": risk_driver_entries,
            },
            "asset_metrics": asset_metrics,
            "correlation_matrix": {
                "symbols": [
                    str(symbol)
                    for symbol in result.correlation_matrix.columns
                ],
                "values": correlation_values,
            },
            "correlation_pairs": correlation_pairs,
            "portfolio_returns": portfolio_returns,
        }
    )
