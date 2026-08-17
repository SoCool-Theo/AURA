from dataclasses import replace
from datetime import date
from decimal import Decimal
import json

import numpy as np
import pandas as pd
import pytest
from pydantic import ValidationError

from backend.app.analytics.concentration import ConcentrationResult
from backend.app.analytics.diversification import DiversificationResult
from backend.app.analytics.drawdown import MaxDrawdownResult
from backend.app.analytics.engine import PortfolioAnalyticsResult
from backend.app.analytics.risk_classifier import RiskClassificationResult
from backend.app.analytics.risk_driver import RiskDriverResult
from backend.app.database.models import MarketData
from backend.app.schemas import (
    PortfolioAnalysisRequest,
    PortfolioAnalysisResponse,
)
from backend.app.services.analysis_service import (
    _build_price_frame,
    _map_analysis_response,
)


def _record(
    symbol: str,
    observation_date: str,
    adjusted_close: str,
    *,
    volume: int | None = None,
    source: str = "test-provider",
) -> MarketData:
    return MarketData(
        symbol=symbol,
        date=date.fromisoformat(observation_date),
        adjusted_close=Decimal(adjusted_close),
        volume=volume,
        source=source,
    )


def _analysis_request() -> PortfolioAnalysisRequest:
    return PortfolioAnalysisRequest.model_validate(
        {
            "portfolio_name": "Core Portfolio",
            "holdings": [
                {"symbol": "MSFT", "weight": 0.5},
                {"symbol": "AAPL", "weight": 0.3},
                {"symbol": "BND", "weight": 0.2},
            ],
            "start_date": "2026-01-01",
            "end_date": "2026-01-31",
        }
    )


def _analytics_result() -> PortfolioAnalyticsResult:
    symbols = pd.Index(["MSFT", "AAPL", "BND"], name="asset")
    return_dates = pd.DatetimeIndex(
        ["2026-01-03", "2026-01-04", "2026-01-05"]
    )
    asset_metrics = pd.DataFrame(
        [
            [0.5, 0.10, 2.0, 0.20, -0.08, 1.2],
            [0.3, -0.05, -0.9, 0.25, -0.18, -0.4],
            [0.2, 0.02, 0.5, 0.04, -0.03, 0.1],
        ],
        index=symbols,
        columns=[
            "weight",
            "cumulative_return",
            "annualized_return",
            "annualized_volatility",
            "max_drawdown",
            "sharpe_ratio",
        ],
    )
    asset_returns = pd.DataFrame(
        [
            [0.01, -0.02, 0.001],
            [-0.03, 0.01, 0.002],
            [0.04, 0.02, -0.001],
        ],
        index=return_dates,
        columns=symbols,
    )
    ranked_contributions = pd.DataFrame(
        [
            [1, 0.2, 0.04, 0.60, 0.12, 0.60],
            [2, 0.5, 0.20, 0.40, 0.10, 0.50],
            [3, 0.3, 0.25, -0.08, -0.02, -0.10],
        ],
        index=pd.Index(["BND", "MSFT", "AAPL"], name="asset"),
        columns=[
            "rank",
            "weight",
            "annualized_asset_volatility",
            "marginal_volatility_contribution",
            "component_volatility_contribution",
            "percentage_volatility_contribution",
        ],
    )
    correlation_matrix = pd.DataFrame(
        [
            [1.0, -0.2, 0.1],
            [-0.2, 1.0, 0.4],
            [0.1, 0.4, 1.0],
        ],
        index=symbols,
        columns=symbols,
    )
    correlation_pairs = pd.DataFrame(
        [
            ["MSFT", "AAPL", -0.2],
            ["MSFT", "BND", 0.1],
            ["AAPL", "BND", 0.4],
        ],
        columns=["asset_1", "asset_2", "correlation"],
    )

    return PortfolioAnalyticsResult(
        analysis_start=pd.Timestamp("2026-01-02"),
        analysis_end=pd.Timestamp("2026-01-05"),
        price_observation_count=np.int64(4),  # type: ignore[arg-type]
        return_observation_count=np.int64(3),  # type: ignore[arg-type]
        asset_count=np.int64(3),  # type: ignore[arg-type]
        cumulative_return=np.float64(0.032),
        annualized_return=np.float64(1.25),
        annualized_volatility=np.float64(0.18),
        sharpe_ratio=np.float64(0.75),
        max_drawdown=MaxDrawdownResult(
            max_drawdown=np.float64(-0.12),
            peak_date=pd.Timestamp("2026-01-03"),
            trough_date=pd.Timestamp("2026-01-04"),
        ),
        concentration=ConcentrationResult(
            largest_weight=np.float64(0.5),
            top_n_weight=np.float64(0.8),
            hhi=np.float64(0.38),
            effective_number_of_assets=np.float64(1.0 / 0.38),
            top_n=np.int64(2),  # type: ignore[arg-type]
        ),
        diversification=DiversificationResult(
            active_asset_count=np.int64(3),  # type: ignore[arg-type]
            effective_number_of_assets=np.float64(1.0 / 0.38),
            weight_score=np.float64(81.5),
            average_pairwise_correlation=np.float64(0.1),
            correlation_score=np.float64(90.0),
            overall_score=np.float64(73.35),
            level="Strong",
            defined_pair_count=np.int64(3),  # type: ignore[arg-type]
            total_pair_count=np.int64(3),  # type: ignore[arg-type]
        ),
        risk_drivers=RiskDriverResult(
            portfolio_volatility=np.float64(0.2),
            top_driver="BND",
            ranked_contributions=ranked_contributions,
        ),
        risk_classification=RiskClassificationResult(
            risk_score=np.float64(40.0),
            risk_level="Moderate",
            volatility_points=np.int64(2),  # type: ignore[arg-type]
            drawdown_points=np.int64(1),  # type: ignore[arg-type]
            concentration_points=np.int64(2),  # type: ignore[arg-type]
            diversification_points=np.int64(0),  # type: ignore[arg-type]
            metrics_used=(
                "volatility",
                "maximum_drawdown",
                "concentration",
                "diversification",
            ),
            reasons=(
                "Elevated historical volatility",
                "Large single-asset concentration",
            ),
        ),
        asset_metrics=asset_metrics,
        asset_returns=asset_returns,
        portfolio_returns=pd.Series(
            np.array([0.005, -0.01, 0.02], dtype=np.float64),
            index=return_dates,
            name="portfolio_return",
        ),
        correlation_matrix=correlation_matrix,
        correlation_pairs=correlation_pairs,
    )


def test_map_analysis_response_constructs_complete_strict_response() -> None:
    request = _analysis_request()
    result = _analytics_result()

    response = _map_analysis_response(request, result)

    assert isinstance(response, PortfolioAnalysisResponse)
    assert response.portfolio_name == "Core Portfolio"
    assert response.start_date == date(2026, 1, 1)
    assert response.end_date == date(2026, 1, 31)
    assert response.metadata.model_dump() == {
        "analysis_start": date(2026, 1, 2),
        "analysis_end": date(2026, 1, 5),
        "price_observation_count": 4,
        "return_observation_count": 3,
        "asset_count": 3,
    }
    assert response.portfolio_metrics.model_dump() == {
        "cumulative_return": 0.032,
        "annualized_return": 1.25,
        "annualized_volatility": 0.18,
        "sharpe_ratio": 0.75,
    }
    assert response.max_drawdown.model_dump() == {
        "max_drawdown": -0.12,
        "peak_date": date(2026, 1, 3),
        "trough_date": date(2026, 1, 4),
    }
    assert response.concentration.model_dump() == {
        "largest_weight": 0.5,
        "top_n_weight": 0.8,
        "hhi": 0.38,
        "effective_number_of_assets": pytest.approx(1.0 / 0.38),
        "top_n": 2,
    }
    assert response.diversification.model_dump() == {
        "active_asset_count": 3,
        "effective_number_of_assets": pytest.approx(1.0 / 0.38),
        "weight_score": 81.5,
        "average_pairwise_correlation": 0.1,
        "correlation_score": 90.0,
        "overall_score": 73.35,
        "level": "Strong",
        "defined_pair_count": 3,
        "total_pair_count": 3,
    }
    assert response.risk_classification.model_dump() == {
        "risk_score": 40.0,
        "risk_level": "Moderate",
        "volatility_points": 2,
        "drawdown_points": 1,
        "concentration_points": 2,
        "diversification_points": 0,
        "metrics_used": [
            "volatility",
            "maximum_drawdown",
            "concentration",
            "diversification",
        ],
        "reasons": [
            "Elevated historical volatility",
            "Large single-asset concentration",
        ],
    }
    assert type(response.metadata.price_observation_count) is int
    assert type(response.portfolio_metrics.cumulative_return) is float
    assert type(response.max_drawdown.peak_date) is date
    validated = PortfolioAnalysisResponse.model_validate(
        response.model_dump()
    )
    assert validated == response
    json.dumps(response.model_dump(mode="json"), allow_nan=False)


def test_map_analysis_response_preserves_all_engine_collection_order() -> None:
    response = _map_analysis_response(
        _analysis_request(),
        _analytics_result(),
    )

    assert [entry.symbol for entry in response.risk_drivers.entries] == [
        "BND",
        "MSFT",
        "AAPL",
    ]
    assert [entry.rank for entry in response.risk_drivers.entries] == [1, 2, 3]
    negative_entry = response.risk_drivers.entries[2]
    assert negative_entry.marginal_volatility_contribution == -0.08
    assert negative_entry.component_volatility_contribution == -0.02
    assert negative_entry.percentage_volatility_contribution == -0.1
    assert [metric.symbol for metric in response.asset_metrics] == [
        "MSFT",
        "AAPL",
        "BND",
    ]
    assert response.asset_metrics[1].model_dump() == {
        "symbol": "AAPL",
        "weight": 0.3,
        "cumulative_return": -0.05,
        "annualized_return": -0.9,
        "annualized_volatility": 0.25,
        "max_drawdown": -0.18,
        "sharpe_ratio": -0.4,
    }
    assert response.correlation_matrix.symbols == ["MSFT", "AAPL", "BND"]
    assert response.correlation_matrix.values == [
        [1.0, -0.2, 0.1],
        [-0.2, 1.0, 0.4],
        [0.1, 0.4, 1.0],
    ]
    assert [
        (pair.asset_a, pair.asset_b)
        for pair in response.correlation_pairs
    ] == [
        ("MSFT", "AAPL"),
        ("MSFT", "BND"),
        ("AAPL", "BND"),
    ]
    assert [point.date for point in response.portfolio_returns] == [
        date(2026, 1, 3),
        date(2026, 1, 4),
        date(2026, 1, 5),
    ]
    assert [point.portfolio_return for point in response.portfolio_returns] == [
        0.005,
        -0.01,
        0.02,
    ]


def test_map_analysis_response_preserves_nullable_drawdown_dates() -> None:
    result = replace(
        _analytics_result(),
        max_drawdown=MaxDrawdownResult(0.0, None, None),
    )

    response = _map_analysis_response(_analysis_request(), result)

    assert response.max_drawdown.max_drawdown == 0.0
    assert response.max_drawdown.peak_date is None
    assert response.max_drawdown.trough_date is None


def test_map_analysis_response_preserves_unavailable_analytics_as_null() -> None:
    result = _analytics_result()
    unavailable_asset_metrics = result.asset_metrics.copy(deep=True)
    unavailable_asset_metrics.loc["AAPL", "sharpe_ratio"] = np.nan
    unavailable_matrix = pd.DataFrame(
        [
            [1.0, np.nan, np.nan],
            [np.nan, np.nan, np.nan],
            [np.nan, np.nan, np.nan],
        ],
        index=result.correlation_matrix.index.copy(),
        columns=result.correlation_matrix.columns.copy(),
    )
    unavailable_pairs = result.correlation_pairs.copy(deep=True)
    unavailable_pairs["correlation"] = np.nan
    unavailable_result = replace(
        result,
        diversification=DiversificationResult(
            active_asset_count=3,
            effective_number_of_assets=1.0 / 0.38,
            weight_score=81.5,
            average_pairwise_correlation=None,
            correlation_score=None,
            overall_score=None,
            level="Unavailable",
            defined_pair_count=0,
            total_pair_count=3,
        ),
        risk_classification=RiskClassificationResult(
            risk_score=45.0,
            risk_level="Moderate",
            volatility_points=1,
            drawdown_points=1,
            concentration_points=2,
            diversification_points=None,
            metrics_used=(
                "volatility",
                "maximum_drawdown",
                "concentration",
            ),
            reasons=(
                "Large single-asset concentration",
                "Diversification score unavailable",
            ),
        ),
        asset_metrics=unavailable_asset_metrics,
        correlation_matrix=unavailable_matrix,
        correlation_pairs=unavailable_pairs,
    )

    response = _map_analysis_response(
        _analysis_request(),
        unavailable_result,
    )

    assert response.diversification.average_pairwise_correlation is None
    assert response.diversification.correlation_score is None
    assert response.diversification.overall_score is None
    assert response.diversification.level == "Unavailable"
    assert response.risk_classification.diversification_points is None
    assert response.risk_classification.metrics_used == [
        "volatility",
        "maximum_drawdown",
        "concentration",
    ]
    assert response.risk_classification.reasons == [
        "Large single-asset concentration",
        "Diversification score unavailable",
    ]
    assert response.asset_metrics[1].sharpe_ratio is None
    assert response.correlation_matrix.values == [
        [1.0, None, None],
        [None, None, None],
        [None, None, None],
    ]
    assert [pair.correlation for pair in response.correlation_pairs] == [
        None,
        None,
        None,
    ]
    json.dumps(response.model_dump(mode="json"), allow_nan=False)


@pytest.mark.parametrize("invalid_value", [np.nan, np.inf, -np.inf])
def test_map_analysis_response_rejects_unexpected_non_finite_required_value(
    invalid_value: float,
) -> None:
    result = replace(
        _analytics_result(),
        cumulative_return=np.float64(invalid_value),
    )

    with pytest.raises(ValidationError):
        _map_analysis_response(_analysis_request(), result)


def test_map_analysis_response_does_not_mutate_request_or_result() -> None:
    request = _analysis_request()
    result = _analytics_result()
    request_snapshot = request.model_dump()
    asset_metrics_snapshot = result.asset_metrics.copy(deep=True)
    asset_returns_snapshot = result.asset_returns.copy(deep=True)
    portfolio_returns_snapshot = result.portfolio_returns.copy(deep=True)
    matrix_snapshot = result.correlation_matrix.copy(deep=True)
    pairs_snapshot = result.correlation_pairs.copy(deep=True)
    drivers_snapshot = result.risk_drivers.ranked_contributions.copy(
        deep=True
    )
    contained_identities = (
        id(result.asset_metrics),
        id(result.asset_returns),
        id(result.portfolio_returns),
        id(result.correlation_matrix),
        id(result.correlation_pairs),
        id(result.risk_drivers.ranked_contributions),
    )

    _map_analysis_response(request, result)

    assert request.model_dump() == request_snapshot
    assert contained_identities == (
        id(result.asset_metrics),
        id(result.asset_returns),
        id(result.portfolio_returns),
        id(result.correlation_matrix),
        id(result.correlation_pairs),
        id(result.risk_drivers.ranked_contributions),
    )
    pd.testing.assert_frame_equal(result.asset_metrics, asset_metrics_snapshot)
    pd.testing.assert_frame_equal(result.asset_returns, asset_returns_snapshot)
    pd.testing.assert_series_equal(
        result.portfolio_returns,
        portfolio_returns_snapshot,
    )
    pd.testing.assert_frame_equal(result.correlation_matrix, matrix_snapshot)
    pd.testing.assert_frame_equal(result.correlation_pairs, pairs_snapshot)
    pd.testing.assert_frame_equal(
        result.risk_drivers.ranked_contributions,
        drivers_snapshot,
    )


def test_build_price_frame_converts_one_symbol_and_sorts_dates() -> None:
    records = [
        _record("AAPL", "2026-01-03", "103.125000000000"),
        _record("AAPL", "2026-01-01", "101.500000000000"),
        _record("AAPL", "2026-01-02", "102.250000000000"),
    ]

    result = _build_price_frame(records, ["AAPL"])

    expected = pd.DataFrame(
        {"AAPL": [101.5, 102.25, 103.125]},
        index=pd.DatetimeIndex(
            [
                date(2026, 1, 1),
                date(2026, 1, 2),
                date(2026, 1, 3),
            ]
        ),
        dtype=float,
    )
    pd.testing.assert_frame_equal(result, expected)
    assert result.index.is_monotonic_increasing
    assert result.index.is_unique


def test_build_price_frame_uses_request_order_not_repository_order() -> None:
    records = [
        _record("AAPL", "2026-01-01", "100.000000000000"),
        _record("AAPL", "2026-01-02", "101.000000000000"),
        _record("BND", "2026-01-01", "70.000000000000"),
        _record("BND", "2026-01-02", "71.000000000000"),
        _record("MSFT", "2026-01-01", "400.000000000000"),
        _record("MSFT", "2026-01-02", "404.000000000000"),
    ]

    result = _build_price_frame(records, ["MSFT", "AAPL", "BND"])

    assert list(result.columns) == ["MSFT", "AAPL", "BND"]
    assert result.to_dict(orient="list") == {
        "MSFT": [400.0, 404.0],
        "AAPL": [100.0, 101.0],
        "BND": [70.0, 71.0],
    }


def test_build_price_frame_is_independent_of_arbitrary_record_order() -> None:
    records = [
        _record("MSFT", "2026-01-03", "403.000000000000"),
        _record("AAPL", "2026-01-01", "101.000000000000"),
        _record("MSFT", "2026-01-01", "401.000000000000"),
        _record("AAPL", "2026-01-03", "103.000000000000"),
    ]

    result = _build_price_frame(records, ("AAPL", "MSFT"))

    assert list(result.index) == [
        pd.Timestamp("2026-01-01"),
        pd.Timestamp("2026-01-03"),
    ]
    assert result.to_dict(orient="list") == {
        "AAPL": [101.0, 103.0],
        "MSFT": [401.0, 403.0],
    }


def test_build_price_frame_uses_exact_stock_crypto_date_intersection() -> None:
    records = [
        _record("AAPL", "2026-01-02", "100.000000000000"),
        _record("AAPL", "2026-01-05", "102.000000000000"),
        _record("BTC-USD", "2026-01-02", "90000.000000000000"),
        _record("BTC-USD", "2026-01-03", "91000.000000000000"),
        _record("BTC-USD", "2026-01-04", "92000.000000000000"),
        _record("BTC-USD", "2026-01-05", "93000.000000000000"),
    ]

    result = _build_price_frame(records, ["BTC-USD", "AAPL"])

    assert list(result.index) == [
        pd.Timestamp("2026-01-02"),
        pd.Timestamp("2026-01-05"),
    ]
    assert result.to_dict(orient="list") == {
        "BTC-USD": [90000.0, 93000.0],
        "AAPL": [100.0, 102.0],
    }
    assert not result.isna().any().any()


@pytest.mark.parametrize(
    ("records", "symbols", "expected_message"),
    [
        (
            [],
            ["AAPL", "MSFT"],
            "market data is unavailable for requested symbols: AAPL, MSFT",
        ),
        (
            [_record("MSFT", "2026-01-01", "400.000000000000")],
            ["MSFT", "AAPL"],
            "market data is unavailable for requested symbols: AAPL",
        ),
        (
            [_record("AAPL", "2026-01-01", "100.000000000000")],
            ["MSFT", "AAPL", "BND"],
            "market data is unavailable for requested symbols: MSFT, BND",
        ),
    ],
)
def test_build_price_frame_reports_missing_symbols_in_request_order(
    records: list[MarketData],
    symbols: list[str],
    expected_message: str,
) -> None:
    with pytest.raises(ValueError) as raised:
        _build_price_frame(records, symbols)

    assert str(raised.value) == expected_message


@pytest.mark.parametrize("common_date_count", [0, 1, 2])
def test_build_price_frame_returns_insufficient_common_history(
    common_date_count: int,
) -> None:
    common_dates = ["2026-01-10", "2026-01-11"][:common_date_count]
    records = [
        *[
            _record("AAPL", observation_date, "100.000000000000")
            for observation_date in common_dates
        ],
        *[
            _record("MSFT", observation_date, "400.000000000000")
            for observation_date in common_dates
        ],
        _record("AAPL", "2026-01-01", "99.000000000000"),
        _record("MSFT", "2026-01-02", "399.000000000000"),
    ]

    result = _build_price_frame(records, ["AAPL", "MSFT"])

    assert result.shape == (common_date_count, 2)
    assert list(result.columns) == ["AAPL", "MSFT"]
    assert list(result.index) == [pd.Timestamp(value) for value in common_dates]
    assert not result.isna().any().any()


def test_build_price_frame_uses_only_adjusted_close_values() -> None:
    records = [
        _record(
            "AAPL",
            "2026-01-01",
            "101.125000000000",
            volume=123_456,
            source="ignored-source",
        )
    ]

    result = _build_price_frame(records, ["AAPL"])

    assert list(result.columns) == ["AAPL"]
    assert result.dtypes.to_dict() == {"AAPL": float}
    assert result.iloc[0, 0] == 101.125
    assert "volume" not in result.columns
    assert "source" not in result.columns


def test_build_price_frame_does_not_mutate_records_or_symbols() -> None:
    records = [
        _record(
            "MSFT",
            "2026-01-02",
            "402.500000000000",
            volume=2_000,
            source="provider-b",
        ),
        _record(
            "AAPL",
            "2026-01-02",
            "101.125000000000",
            source="provider-a",
        ),
    ]
    symbols = ["MSFT", "AAPL"]
    record_snapshot = [
        (
            record.symbol,
            record.date,
            record.adjusted_close,
            record.volume,
            record.source,
        )
        for record in records
    ]
    record_identities = [id(record) for record in records]
    symbols_snapshot = list(symbols)

    _build_price_frame(records, symbols)

    assert [id(record) for record in records] == record_identities
    assert [
        (
            record.symbol,
            record.date,
            record.adjusted_close,
            record.volume,
            record.source,
        )
        for record in records
    ] == record_snapshot
    assert symbols == symbols_snapshot
