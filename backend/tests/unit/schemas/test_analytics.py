from copy import deepcopy
from datetime import date
from decimal import Decimal
import json

import pytest
from pydantic import ValidationError

from backend.app.schemas.analytics import (
    AnalysisMetadata,
    AssetMetrics,
    AssetReturnPoint,
    AssetReturnSeries,
    AssetRiskClassification,
    ConcentrationMetrics,
    CorrelationMatrix,
    CorrelationPair,
    DiversificationMetrics,
    MaximumDrawdownMetrics,
    PortfolioAnalysisResponse,
    PortfolioMetrics,
    PortfolioReturnPoint,
    RiskClassification,
    RiskDriverAnalysis,
    RiskDriverEntry,
)


def _maximum_drawdown_data() -> dict[str, object]:
    return {
        "max_drawdown": -0.25,
        "peak_date": "2026-01-10",
        "trough_date": "2026-01-20",
    }


def _concentration_data() -> dict[str, object]:
    return {
        "largest_weight": 0.50,
        "top_n_weight": 0.80,
        "hhi": 0.38,
        "effective_number_of_assets": 1.0 / 0.38,
        "top_n": 2,
    }


def _diversification_data() -> dict[str, object]:
    return {
        "active_asset_count": 3,
        "effective_number_of_assets": 1.0 / 0.38,
        "weight_score": 81.57894736842105,
        "average_pairwise_correlation": 0.40,
        "correlation_score": 60.0,
        "overall_score": 48.94736842105263,
        "level": "Moderate",
        "defined_pair_count": 3,
        "total_pair_count": 3,
    }


def _risk_driver_data() -> dict[str, object]:
    return {
        "rank": 1,
        "symbol": "AAPL",
        "weight": 0.60,
        "annualized_asset_volatility": 0.20,
        "marginal_volatility_contribution": 0.18,
        "component_volatility_contribution": 0.108,
        "percentage_volatility_contribution": 0.675,
    }


def _risk_classification_data() -> dict[str, object]:
    return {
        "risk_score": 61.666666666666664,
        "risk_level": "High",
        "volatility_points": 2,
        "drawdown_points": 2,
        "concentration_points": 2,
        "diversification_points": 1,
        "metrics_used": [
            "volatility",
            "maximum_drawdown",
            "concentration",
            "diversification",
        ],
        "reasons": [
            "Elevated historical volatility",
            "Significant historical drawdown",
        ],
    }


def _asset_metrics_data() -> dict[str, object]:
    return {
        "symbol": "AAPL",
        "weight": 0.60,
        "cumulative_return": 0.12,
        "annualized_return": 0.18,
        "annualized_volatility": 0.20,
        "max_drawdown": -0.15,
        "sharpe_ratio": 0.90,
        "risk_classification": {
            "risk_score": 50.0,
            "risk_level": "High",
            "volatility_points": 2,
            "drawdown_points": 1,
            "metrics_used": ["volatility", "maximum_drawdown"],
            "reasons": ["Elevated historical volatility"],
        },
    }


def _correlation_pair_data() -> dict[str, object]:
    return {
        "asset_a": "AAPL",
        "asset_b": "MSFT",
        "correlation": 0.40,
    }


def _correlation_matrix_data() -> dict[str, object]:
    return {
        "symbols": ["AAPL", "MSFT"],
        "values": [[1.0, 0.40], [0.40, 1.0]],
    }


@pytest.mark.parametrize(
    ("model_type", "data"),
    [
        (MaximumDrawdownMetrics, _maximum_drawdown_data()),
        (ConcentrationMetrics, _concentration_data()),
        (DiversificationMetrics, _diversification_data()),
        (RiskDriverEntry, _risk_driver_data()),
        (RiskClassification, _risk_classification_data()),
        (AssetMetrics, _asset_metrics_data()),
        (CorrelationPair, _correlation_pair_data()),
        (CorrelationMatrix, _correlation_matrix_data()),
    ],
)
def test_atomic_models_reject_unknown_fields(
    model_type: type,
    data: dict[str, object],
) -> None:
    data["unexpected"] = True

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        model_type.model_validate(data)


@pytest.mark.parametrize(
    ("model_type", "data"),
    [
        (MaximumDrawdownMetrics, _maximum_drawdown_data()),
        (ConcentrationMetrics, _concentration_data()),
        (DiversificationMetrics, _diversification_data()),
        (RiskDriverEntry, _risk_driver_data()),
        (RiskClassification, _risk_classification_data()),
        (AssetMetrics, _asset_metrics_data()),
        (CorrelationPair, _correlation_pair_data()),
        (CorrelationMatrix, _correlation_matrix_data()),
    ],
)
def test_atomic_models_produce_json_safe_output(
    model_type: type,
    data: dict[str, object],
) -> None:
    result = model_type.model_validate(data).model_dump(mode="json")

    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize(
    ("model_type", "data"),
    [
        (MaximumDrawdownMetrics, _maximum_drawdown_data()),
        (ConcentrationMetrics, _concentration_data()),
        (DiversificationMetrics, _diversification_data()),
        (RiskDriverEntry, _risk_driver_data()),
        (RiskClassification, _risk_classification_data()),
        (AssetMetrics, _asset_metrics_data()),
        (CorrelationPair, _correlation_pair_data()),
        (CorrelationMatrix, _correlation_matrix_data()),
    ],
)
def test_atomic_models_do_not_mutate_caller_input(
    model_type: type,
    data: dict[str, object],
) -> None:
    original = deepcopy(data)

    model_type.model_validate(data)

    assert data == original


@pytest.mark.parametrize(
    "invalid_value",
    [True, "0.5", float("nan"), float("inf"), -float("inf")],
)
def test_required_float_fields_reject_non_json_or_non_finite_values(
    invalid_value: object,
) -> None:
    data = _asset_metrics_data()
    data["cumulative_return"] = invalid_value

    with pytest.raises(ValidationError):
        AssetMetrics.model_validate(data)


def test_maximum_drawdown_preserves_negative_value_and_dates() -> None:
    result = MaximumDrawdownMetrics.model_validate(
        _maximum_drawdown_data()
    )

    assert result.max_drawdown == pytest.approx(-0.25)
    assert result.peak_date == date(2026, 1, 10)
    assert result.trough_date == date(2026, 1, 20)
    assert result.model_dump(mode="json") == {
        "max_drawdown": -0.25,
        "peak_date": "2026-01-10",
        "trough_date": "2026-01-20",
    }


def test_maximum_drawdown_accepts_zero_with_unavailable_dates() -> None:
    result = MaximumDrawdownMetrics(
        max_drawdown=0,
        peak_date=None,
        trough_date=None,
    )

    assert result.max_drawdown == 0.0
    assert result.peak_date is None
    assert result.trough_date is None


@pytest.mark.parametrize("max_drawdown", [0.01, -1.01])
def test_maximum_drawdown_rejects_values_outside_current_range(
    max_drawdown: float,
) -> None:
    data = _maximum_drawdown_data()
    data["max_drawdown"] = max_drawdown

    with pytest.raises(ValidationError):
        MaximumDrawdownMetrics.model_validate(data)


def test_concentration_matches_every_public_result_field() -> None:
    result = ConcentrationMetrics.model_validate(_concentration_data())

    assert result.model_dump() == _concentration_data()


def test_concentration_accepts_single_asset_boundaries() -> None:
    result = ConcentrationMetrics(
        largest_weight=1,
        top_n_weight=1,
        hhi=1,
        effective_number_of_assets=1,
        top_n=1,
    )

    assert result.largest_weight == 1.0
    assert result.top_n_weight == 1.0
    assert result.hhi == 1.0
    assert result.effective_number_of_assets == 1.0
    assert result.top_n == 1


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("largest_weight", 0.0),
        ("largest_weight", 1.01),
        ("top_n_weight", 0.0),
        ("top_n_weight", 1.01),
        ("hhi", 0.0),
        ("hhi", 1.01),
        ("effective_number_of_assets", 0.0),
        ("top_n", 0),
        ("top_n", True),
        ("top_n", "2"),
    ],
)
def test_concentration_rejects_values_outside_confirmed_ranges(
    field: str,
    value: object,
) -> None:
    data = _concentration_data()
    data[field] = value

    with pytest.raises(ValidationError):
        ConcentrationMetrics.model_validate(data)


@pytest.mark.parametrize(
    ("level", "overall_score"),
    [
        ("Weak", 0.0),
        ("Moderate", 50.0),
        ("Strong", 100.0),
        ("Unavailable", None),
    ],
)
def test_diversification_accepts_each_current_level(
    level: str,
    overall_score: float | None,
) -> None:
    data = _diversification_data()
    data["level"] = level
    data["overall_score"] = overall_score
    if overall_score is None:
        data["average_pairwise_correlation"] = None
        data["correlation_score"] = None

    result = DiversificationMetrics.model_validate(data)

    assert result.level == level
    assert result.overall_score == overall_score


def test_diversification_preserves_unavailable_values_as_null() -> None:
    data = _diversification_data()
    data.update(
        {
            "average_pairwise_correlation": None,
            "correlation_score": None,
            "overall_score": None,
            "level": "Unavailable",
            "defined_pair_count": 0,
        }
    )

    result = DiversificationMetrics.model_validate(data)
    dumped = result.model_dump(mode="json")

    assert result.overall_score is None
    assert dumped["average_pairwise_correlation"] is None
    assert dumped["correlation_score"] is None
    assert dumped["overall_score"] is None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("weight_score", -0.01),
        ("weight_score", 100.01),
        ("average_pairwise_correlation", -1.01),
        ("average_pairwise_correlation", 1.01),
        ("correlation_score", -0.01),
        ("overall_score", 100.01),
        ("active_asset_count", 0),
        ("defined_pair_count", -1),
        ("total_pair_count", -1),
    ],
)
def test_diversification_rejects_values_outside_confirmed_ranges(
    field: str,
    value: object,
) -> None:
    data = _diversification_data()
    data[field] = value

    with pytest.raises(ValidationError):
        DiversificationMetrics.model_validate(data)


def test_diversification_rejects_unsupported_level() -> None:
    data = _diversification_data()
    data["level"] = "Excellent"

    with pytest.raises(ValidationError):
        DiversificationMetrics.model_validate(data)


@pytest.mark.parametrize(
    ("overall_score", "level"),
    [(None, "Weak"), (0.0, "Unavailable")],
)
def test_diversification_rejects_inconsistent_unavailable_level(
    overall_score: float | None,
    level: str,
) -> None:
    data = _diversification_data()
    data["overall_score"] = overall_score
    data["level"] = level

    with pytest.raises(ValidationError):
        DiversificationMetrics.model_validate(data)


@pytest.mark.parametrize(
    "component_contribution",
    [0.108, 0.0, -0.04],
)
def test_risk_driver_preserves_signed_contributions(
    component_contribution: float,
) -> None:
    data = _risk_driver_data()
    data["component_volatility_contribution"] = component_contribution

    result = RiskDriverEntry.model_validate(data)

    assert result.component_volatility_contribution == pytest.approx(
        component_contribution
    )


def test_risk_driver_normalizes_symbol() -> None:
    data = _risk_driver_data()
    data["symbol"] = " aapl "

    result = RiskDriverEntry.model_validate(data)

    assert result.symbol == "AAPL"


def test_risk_driver_keeps_supplied_rank_without_ranking_logic() -> None:
    first_data = _risk_driver_data()
    first_data["rank"] = 2
    second_data = _risk_driver_data()
    second_data["rank"] = 1
    second_data["symbol"] = "MSFT"

    first = RiskDriverEntry.model_validate(first_data)
    second = RiskDriverEntry.model_validate(second_data)

    assert first.rank == 2
    assert second.rank == 1


@pytest.mark.parametrize(
    "invalid_value",
    [float("nan"), float("inf"), -float("inf")],
)
def test_risk_driver_rejects_non_finite_contribution(
    invalid_value: float,
) -> None:
    data = _risk_driver_data()
    data["percentage_volatility_contribution"] = invalid_value

    with pytest.raises(ValidationError):
        RiskDriverEntry.model_validate(data)


@pytest.mark.parametrize(
    ("risk_level", "risk_score"),
    [
        ("Low", 0.0),
        ("Moderate", 25.0),
        ("High", 50.0),
        ("Very High", 100.0),
    ],
)
def test_risk_classification_accepts_each_current_level(
    risk_level: str,
    risk_score: float,
) -> None:
    data = _risk_classification_data()
    data["risk_level"] = risk_level
    data["risk_score"] = risk_score

    result = RiskClassification.model_validate(data)

    assert result.risk_level == risk_level
    assert result.risk_score == risk_score


def test_risk_classification_preserves_component_points_and_lists() -> None:
    result = RiskClassification.model_validate(
        _risk_classification_data()
    )

    assert result.volatility_points == 2
    assert result.drawdown_points == 2
    assert result.concentration_points == 2
    assert result.diversification_points == 1
    assert result.metrics_used == [
        "volatility",
        "maximum_drawdown",
        "concentration",
        "diversification",
    ]
    assert result.reasons == [
        "Elevated historical volatility",
        "Significant historical drawdown",
    ]


def test_risk_classification_preserves_unavailable_diversification() -> None:
    data = _risk_classification_data()
    data["diversification_points"] = None
    data["metrics_used"] = [
        "volatility",
        "maximum_drawdown",
        "concentration",
    ]

    result = RiskClassification.model_validate(data)

    assert result.diversification_points is None
    assert result.model_dump(mode="json")["diversification_points"] is None


def test_risk_classification_rejects_unsupported_level() -> None:
    data = _risk_classification_data()
    data["risk_level"] = "Extreme"

    with pytest.raises(ValidationError):
        RiskClassification.model_validate(data)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("risk_score", -0.01),
        ("risk_score", 100.01),
        ("volatility_points", -1),
        ("drawdown_points", 4),
        ("concentration_points", True),
        ("diversification_points", "1"),
    ],
)
def test_risk_classification_rejects_values_outside_current_scales(
    field: str,
    value: object,
) -> None:
    data = _risk_classification_data()
    data[field] = value

    with pytest.raises(ValidationError):
        RiskClassification.model_validate(data)


def test_asset_metrics_accepts_complete_current_metric_set() -> None:
    result = AssetMetrics.model_validate(_asset_metrics_data())

    assert result.model_dump() == _asset_metrics_data()


def test_asset_metrics_accepts_legacy_record_without_asset_risk() -> None:
    data = _asset_metrics_data()
    data.pop("risk_classification")

    result = AssetMetrics.model_validate(data)

    assert result.risk_classification is None


def test_asset_risk_classification_requires_asset_only_metric_order() -> None:
    data = _asset_metrics_data()["risk_classification"]
    assert isinstance(data, dict)

    result = AssetRiskClassification.model_validate(data)

    assert result.risk_level == "High"
    assert result.metrics_used == ["volatility", "maximum_drawdown"]

    data["metrics_used"] = ["maximum_drawdown", "volatility"]
    with pytest.raises(ValidationError, match="asset risk metrics_used"):
        AssetRiskClassification.model_validate(data)


def test_asset_metrics_normalizes_symbol_and_accepts_zero_weight() -> None:
    data = _asset_metrics_data()
    data["symbol"] = " aapl "
    data["weight"] = 0

    result = AssetMetrics.model_validate(data)

    assert result.symbol == "AAPL"
    assert result.weight == 0.0


def test_asset_metrics_preserves_negative_maximum_drawdown() -> None:
    result = AssetMetrics.model_validate(_asset_metrics_data())

    assert result.max_drawdown == pytest.approx(-0.15)


def test_asset_metrics_preserves_unavailable_sharpe_as_null() -> None:
    data = _asset_metrics_data()
    data["sharpe_ratio"] = None

    result = AssetMetrics.model_validate(data)

    assert result.sharpe_ratio is None
    assert result.model_dump(mode="json")["sharpe_ratio"] is None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("weight", -0.01),
        ("weight", 1.01),
        ("annualized_volatility", -0.01),
        ("max_drawdown", 0.01),
        ("max_drawdown", -1.01),
        ("sharpe_ratio", float("nan")),
        ("annualized_return", float("inf")),
    ],
)
def test_asset_metrics_rejects_invalid_metric_values(
    field: str,
    value: object,
) -> None:
    data = _asset_metrics_data()
    data[field] = value

    with pytest.raises(ValidationError):
        AssetMetrics.model_validate(data)


@pytest.mark.parametrize(
    "correlation",
    [0.40, 0.0, -0.40, -1.0, 1.0],
)
def test_correlation_pair_accepts_signed_values_and_boundaries(
    correlation: float,
) -> None:
    data = _correlation_pair_data()
    data["correlation"] = correlation

    result = CorrelationPair.model_validate(data)

    assert result.correlation == pytest.approx(correlation)


def test_correlation_pair_preserves_undefined_value_as_null() -> None:
    data = _correlation_pair_data()
    data["correlation"] = None

    result = CorrelationPair.model_validate(data)

    assert result.correlation is None
    assert result.model_dump(mode="json")["correlation"] is None


@pytest.mark.parametrize(
    ("asset_a", "asset_b"),
    [("AAPL", "AAPL"), ("AAPL", "aapl"), (" AAPL ", "aapl")],
)
def test_correlation_pair_rejects_same_normalized_symbol(
    asset_a: str,
    asset_b: str,
) -> None:
    data = _correlation_pair_data()
    data["asset_a"] = asset_a
    data["asset_b"] = asset_b

    with pytest.raises(
        ValidationError,
        match="correlation pair symbols must differ after normalization",
    ):
        CorrelationPair.model_validate(data)


@pytest.mark.parametrize("correlation", [-1.01, 1.01])
def test_correlation_pair_rejects_out_of_range_value(
    correlation: float,
) -> None:
    data = _correlation_pair_data()
    data["correlation"] = correlation

    with pytest.raises(ValidationError):
        CorrelationPair.model_validate(data)


def test_correlation_pair_preserves_pair_order() -> None:
    result = CorrelationPair(
        asset_a="MSFT",
        asset_b="AAPL",
        correlation=0.40,
    )

    assert result.asset_a == "MSFT"
    assert result.asset_b == "AAPL"


def test_correlation_matrix_accepts_one_asset_and_none_diagonal() -> None:
    result = CorrelationMatrix(symbols=[" aapl "], values=[[None]])

    assert result.symbols == ["AAPL"]
    assert result.values == [[None]]
    assert result.model_dump(mode="json")["values"] == [[None]]


def test_correlation_matrix_accepts_multiple_assets_and_undefined_values() -> None:
    result = CorrelationMatrix(
        symbols=["AAPL", "MSFT", "CASH"],
        values=[
            [1.0, 0.40, None],
            [0.40, 1.0, None],
            [None, None, None],
        ],
    )

    assert result.values[0][2] is None
    assert result.values[2] == [None, None, None]


def test_correlation_matrix_normalizes_and_preserves_symbol_order() -> None:
    result = CorrelationMatrix(
        symbols=[" beta ", "alpha"],
        values=[[1.0, 0.20], [0.20, 1.0]],
    )

    assert result.symbols == ["BETA", "ALPHA"]


def test_correlation_matrix_rejects_empty_symbols() -> None:
    with pytest.raises(ValidationError):
        CorrelationMatrix(symbols=[], values=[])


@pytest.mark.parametrize(
    "symbols",
    [
        ["AAPL", "AAPL"],
        ["AAPL", "aapl"],
        ["AAPL", " AAPL "],
    ],
)
def test_correlation_matrix_rejects_duplicate_normalized_symbols(
    symbols: list[str],
) -> None:
    with pytest.raises(
        ValidationError,
        match="correlation matrix symbols must be unique after normalization",
    ):
        CorrelationMatrix(
            symbols=symbols,
            values=[[1.0, 0.40], [0.40, 1.0]],
        )


@pytest.mark.parametrize(
    "values",
    [
        [[1.0, 0.40]],
        [[1.0, 0.40], [0.40, 1.0], [0.20, 0.30]],
    ],
)
def test_correlation_matrix_rejects_wrong_row_count(
    values: list[list[float]],
) -> None:
    with pytest.raises(
        ValidationError,
        match="correlation matrix must contain one row per symbol",
    ):
        CorrelationMatrix(symbols=["AAPL", "MSFT"], values=values)


@pytest.mark.parametrize(
    "values",
    [
        [[1.0], [0.40, 1.0]],
        [[1.0, 0.40, 0.20], [0.40, 1.0]],
    ],
)
def test_correlation_matrix_rejects_wrong_row_length(
    values: list[list[float]],
) -> None:
    with pytest.raises(
        ValidationError,
        match="each correlation matrix row must contain one value per symbol",
    ):
        CorrelationMatrix(symbols=["AAPL", "MSFT"], values=values)


@pytest.mark.parametrize(
    "invalid_value",
    [-1.01, 1.01, float("nan"), float("inf"), -float("inf")],
)
def test_correlation_matrix_rejects_invalid_value(
    invalid_value: float,
) -> None:
    with pytest.raises(ValidationError):
        CorrelationMatrix(
            symbols=["AAPL", "MSFT"],
            values=[[1.0, invalid_value], [0.40, 1.0]],
        )


def test_correlation_matrix_accepts_non_symmetric_values() -> None:
    result = CorrelationMatrix(
        symbols=["AAPL", "MSFT"],
        values=[[1.0, 0.20], [-0.40, None]],
    )

    assert result.values == [[1.0, 0.20], [-0.40, None]]


def test_correlation_matrix_preserves_nested_list_order() -> None:
    result = CorrelationMatrix(
        symbols=["BETA", "ALPHA"],
        values=[[None, -0.25], [0.75, 0.50]],
    )

    assert result.values[0] == [None, -0.25]
    assert result.values[1] == [0.75, 0.50]


def test_correlation_matrix_does_not_mutate_nested_input_lists() -> None:
    symbols = [" beta ", "alpha"]
    first_row = [None, -0.25]
    second_row = [0.75, 0.50]
    values = [first_row, second_row]
    data = {"symbols": symbols, "values": values}
    original = deepcopy(data)

    result = CorrelationMatrix.model_validate(data)

    assert data == original
    assert data["symbols"] is symbols
    assert data["values"] is values
    assert values[0] is first_row
    assert values[1] is second_row
    assert result.symbols == ["BETA", "ALPHA"]


def _second_asset_metrics_data() -> dict[str, object]:
    data = _asset_metrics_data()
    data.update(
        {
            "symbol": "MSFT",
            "weight": 0.40,
            "cumulative_return": 0.08,
            "annualized_return": 0.12,
            "annualized_volatility": 0.16,
            "max_drawdown": -0.10,
            "sharpe_ratio": 0.75,
            "risk_classification": {
                "risk_score": 100.0 / 3.0,
                "risk_level": "Moderate",
                "volatility_points": 1,
                "drawdown_points": 1,
                "metrics_used": ["volatility", "maximum_drawdown"],
                "reasons": [
                    "No major risk flags under Aura's current asset "
                    "thresholds"
                ],
            },
        }
    )
    return data


def _second_risk_driver_data() -> dict[str, object]:
    data = _risk_driver_data()
    data.update(
        {
            "rank": 2,
            "symbol": "MSFT",
            "weight": 0.40,
            "annualized_asset_volatility": 0.16,
            "marginal_volatility_contribution": 0.13,
            "component_volatility_contribution": 0.052,
            "percentage_volatility_contribution": 0.325,
        }
    )
    return data


def _portfolio_response_data() -> dict[str, object]:
    return {
        "start_date": "2026-01-01",
        "end_date": "2026-01-31",
        "portfolio_name": "Core Portfolio",
        "metadata": {
            "analysis_start": "2026-01-01",
            "analysis_end": "2026-01-20",
            "price_observation_count": 3,
            "return_observation_count": 2,
            "asset_count": 2,
        },
        "portfolio_metrics": {
            "cumulative_return": 0.10,
            "annualized_return": 0.15,
            "annualized_volatility": 0.16,
            "sharpe_ratio": 0.85,
        },
        "max_drawdown": _maximum_drawdown_data(),
        "concentration": _concentration_data(),
        "diversification": _diversification_data(),
        "risk_classification": _risk_classification_data(),
        "risk_drivers": {
            "portfolio_volatility": 0.16,
            "top_driver": "AAPL",
            "entries": [
                _risk_driver_data(),
                _second_risk_driver_data(),
            ],
        },
        "asset_metrics": [
            _asset_metrics_data(),
            _second_asset_metrics_data(),
        ],
        "correlation_matrix": _correlation_matrix_data(),
        "correlation_pairs": [_correlation_pair_data()],
        "portfolio_returns": [
            {"date": "2026-01-10", "portfolio_return": 0.04},
            {"date": "2026-01-20", "portfolio_return": 0.06},
        ],
        "asset_returns": [
            {
                "symbol": "AAPL",
                "points": [
                    {"date": "2026-01-10", "asset_return": 0.03},
                    {"date": "2026-01-20", "asset_return": 0.05},
                ],
            },
            {
                "symbol": "MSFT",
                "points": [
                    {"date": "2026-01-10", "asset_return": 0.02},
                    {"date": "2026-01-20", "asset_return": 0.04},
                ],
            },
        ],
    }


def test_portfolio_response_omits_unavailable_historical_value_context() -> None:
    response = PortfolioAnalysisResponse.model_validate(
        _portfolio_response_data()
    )

    assert response.historical_value_context is None
    assert "historical_value_context" not in response.model_dump(mode="json")


def test_portfolio_response_accepts_matching_fixed_share_value_context() -> None:
    data = _portfolio_response_data()
    data["historical_value_context"] = {
        "basis": "fixed-current-shares",
        "currency": "USD",
        "start_date": "2026-01-01",
        "end_date": "2026-01-20",
        "starting_value": "1000",
        "ending_value": "1100",
    }

    response = PortfolioAnalysisResponse.model_validate(data)

    context = response.historical_value_context
    assert context is not None
    assert context.starting_value == Decimal("1000")
    assert context.ending_value == Decimal("1100")
    assert response.model_dump(mode="json")["historical_value_context"] == {
        "basis": "fixed-current-shares",
        "currency": "USD",
        "start_date": "2026-01-01",
        "end_date": "2026-01-20",
        "starting_value": "1000",
        "ending_value": "1100",
    }


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("start_date", "2026-01-02", "dates must match"),
        ("ending_value", "1099", "must match portfolio cumulative return"),
    ],
)
def test_portfolio_response_rejects_inconsistent_historical_value_context(
    field: str,
    value: str,
    message: str,
) -> None:
    data = _portfolio_response_data()
    context = {
        "basis": "fixed-current-shares",
        "currency": "USD",
        "start_date": "2026-01-01",
        "end_date": "2026-01-20",
        "starting_value": "1000",
        "ending_value": "1100",
    }
    context[field] = value
    data["historical_value_context"] = context

    with pytest.raises(ValidationError, match=message):
        PortfolioAnalysisResponse.model_validate(data)


def _single_asset_response_data() -> dict[str, object]:
    data = _portfolio_response_data()
    data["metadata"] = {
        "analysis_start": "2026-01-01",
        "analysis_end": "2026-01-20",
        "price_observation_count": 3,
        "return_observation_count": 2,
        "asset_count": 1,
    }
    asset = _asset_metrics_data()
    asset["weight"] = 1.0
    data["asset_metrics"] = [asset]
    driver = _risk_driver_data()
    driver["weight"] = 1.0
    data["risk_drivers"] = {
        "portfolio_volatility": 0.16,
        "top_driver": "AAPL",
        "entries": [driver],
    }
    data["correlation_matrix"] = {
        "symbols": ["AAPL"],
        "values": [[1.0]],
    }
    data["correlation_pairs"] = []
    data["asset_returns"] = [data["asset_returns"][0]]
    return data


def _three_asset_response_data() -> dict[str, object]:
    data = _portfolio_response_data()
    symbols = ["AAPL", "MSFT", "BND"]
    weights = [0.1, 0.2, 0.7]

    asset_metrics: list[dict[str, object]] = []
    risk_entries: list[dict[str, object]] = []
    for rank, (symbol, weight) in enumerate(
        zip(symbols, weights),
        start=1,
    ):
        asset = _asset_metrics_data()
        asset["symbol"] = symbol
        asset["weight"] = weight
        asset_metrics.append(asset)

        driver = _risk_driver_data()
        driver["rank"] = rank
        driver["symbol"] = symbol
        driver["weight"] = weight
        risk_entries.append(driver)

    data["metadata"] = {
        "analysis_start": "2026-01-01",
        "analysis_end": "2026-01-20",
        "price_observation_count": 3,
        "return_observation_count": 2,
        "asset_count": 3,
    }
    data["asset_metrics"] = asset_metrics
    data["asset_returns"] = [
        {
            "symbol": symbol,
            "points": [
                {"date": "2026-01-10", "asset_return": 0.03},
                {"date": "2026-01-20", "asset_return": 0.05},
            ],
        }
        for symbol in symbols
    ]
    data["risk_drivers"] = {
        "portfolio_volatility": 0.16,
        "top_driver": "AAPL",
        "entries": risk_entries,
    }
    data["correlation_matrix"] = {
        "symbols": symbols,
        "values": [
            [1.0, 0.40, 0.10],
            [0.40, 1.0, -0.10],
            [0.10, -0.10, 1.0],
        ],
    }
    data["correlation_pairs"] = [
        {"asset_a": "AAPL", "asset_b": "MSFT", "correlation": 0.40},
        {"asset_a": "AAPL", "asset_b": "BND", "correlation": 0.10},
        {"asset_a": "MSFT", "asset_b": "BND", "correlation": -0.10},
    ]
    return data


def test_analysis_metadata_matches_exact_stable_engine_fields() -> None:
    data = _portfolio_response_data()["metadata"]

    result = AnalysisMetadata.model_validate(data)

    assert result.model_dump(mode="json") == {
        "analysis_start": "2026-01-01",
        "analysis_end": "2026-01-20",
        "price_observation_count": 3,
        "return_observation_count": 2,
        "asset_count": 2,
    }


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("price_observation_count", True),
        ("return_observation_count", "2"),
        ("asset_count", 0),
    ],
)
def test_analysis_metadata_rejects_invalid_numeric_fields(
    field: str,
    value: object,
) -> None:
    data = deepcopy(_portfolio_response_data()["metadata"])
    assert isinstance(data, dict)
    data[field] = value

    with pytest.raises(ValidationError):
        AnalysisMetadata.model_validate(data)


def test_analysis_metadata_rejects_inconsistent_observation_counts() -> None:
    data = deepcopy(_portfolio_response_data()["metadata"])
    assert isinstance(data, dict)
    data["return_observation_count"] = 1

    with pytest.raises(
        ValidationError,
        match="return_observation_count must equal",
    ):
        AnalysisMetadata.model_validate(data)


def test_analysis_metadata_rejects_unknown_field() -> None:
    data = deepcopy(_portfolio_response_data()["metadata"])
    assert isinstance(data, dict)
    data["debug"] = True

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        AnalysisMetadata.model_validate(data)


def test_portfolio_metrics_matches_exact_engine_scalar_fields() -> None:
    data = _portfolio_response_data()["portfolio_metrics"]

    result = PortfolioMetrics.model_validate(data)

    assert result.model_dump() == data


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("cumulative_return", True),
        ("annualized_return", "0.15"),
        ("annualized_volatility", -0.01),
        ("sharpe_ratio", float("nan")),
        ("sharpe_ratio", float("inf")),
        ("sharpe_ratio", -float("inf")),
    ],
)
def test_portfolio_metrics_rejects_invalid_values(
    field: str,
    value: object,
) -> None:
    data = deepcopy(_portfolio_response_data()["portfolio_metrics"])
    assert isinstance(data, dict)
    data[field] = value

    with pytest.raises(ValidationError):
        PortfolioMetrics.model_validate(data)


def test_portfolio_return_point_is_json_safe() -> None:
    result = PortfolioReturnPoint(
        date=date(2026, 1, 10),
        portfolio_return=0.04,
    )

    assert result.model_dump(mode="json") == {
        "date": "2026-01-10",
        "portfolio_return": 0.04,
    }


@pytest.mark.parametrize(
    "invalid_value",
    [True, "0.04", float("nan"), float("inf"), -float("inf")],
)
def test_portfolio_return_point_rejects_invalid_value(
    invalid_value: object,
) -> None:
    with pytest.raises(ValidationError):
        PortfolioReturnPoint(
            date=date(2026, 1, 10),
            portfolio_return=invalid_value,
        )


def test_asset_return_series_preserves_ordered_json_safe_points() -> None:
    result = AssetReturnSeries.model_validate(
        {
            "symbol": " aapl ",
            "points": [
                {"date": "2026-01-10", "asset_return": -0.02},
                {"date": "2026-01-20", "asset_return": 0.04},
            ],
        }
    )

    assert result.symbol == "AAPL"
    assert all(isinstance(point, AssetReturnPoint) for point in result.points)
    assert result.model_dump(mode="json") == {
        "symbol": "AAPL",
        "points": [
            {"date": "2026-01-10", "asset_return": -0.02},
            {"date": "2026-01-20", "asset_return": 0.04},
        ],
    }


def test_asset_return_series_rejects_non_increasing_dates() -> None:
    with pytest.raises(
        ValidationError,
        match="asset return dates must be strictly increasing",
    ):
        AssetReturnSeries.model_validate(
            {
                "symbol": "AAPL",
                "points": [
                    {"date": "2026-01-20", "asset_return": 0.04},
                    {"date": "2026-01-10", "asset_return": -0.02},
                ],
            }
        )


def test_risk_driver_analysis_preserves_public_result_fields() -> None:
    data = _portfolio_response_data()["risk_drivers"]

    result = RiskDriverAnalysis.model_validate(data)

    assert result.portfolio_volatility == pytest.approx(0.16)
    assert result.top_driver == "AAPL"
    assert [entry.symbol for entry in result.entries] == ["AAPL", "MSFT"]


def test_risk_driver_analysis_rejects_duplicate_symbols() -> None:
    data = deepcopy(_portfolio_response_data()["risk_drivers"])
    assert isinstance(data, dict)
    entries = data["entries"]
    assert isinstance(entries, list)
    entries[1]["symbol"] = " aapl "

    with pytest.raises(
        ValidationError,
        match="risk-driver symbols must be unique after normalization",
    ):
        RiskDriverAnalysis.model_validate(data)


def test_risk_driver_analysis_rejects_mismatched_top_driver() -> None:
    data = deepcopy(_portfolio_response_data()["risk_drivers"])
    assert isinstance(data, dict)
    data["top_driver"] = "MSFT"

    with pytest.raises(
        ValidationError,
        match="top_driver must match the first ranked",
    ):
        RiskDriverAnalysis.model_validate(data)


def test_response_accepts_valid_multi_asset_result() -> None:
    result = PortfolioAnalysisResponse.model_validate(
        _portfolio_response_data()
    )

    assert result.portfolio_name == "Core Portfolio"
    assert result.metadata.asset_count == 2
    assert [metric.symbol for metric in result.asset_metrics] == [
        "AAPL",
        "MSFT",
    ]
    assert [entry.symbol for entry in result.risk_drivers.entries] == [
        "AAPL",
        "MSFT",
    ]


def test_response_accepts_single_asset_with_empty_correlation_pairs() -> None:
    result = PortfolioAnalysisResponse.model_validate(
        _single_asset_response_data()
    )

    assert result.metadata.asset_count == 1
    assert result.correlation_matrix.symbols == ["AAPL"]
    assert result.correlation_pairs == []


def test_response_trims_portfolio_name() -> None:
    data = _portfolio_response_data()
    data["portfolio_name"] = "  Core Portfolio \t"

    result = PortfolioAnalysisResponse.model_validate(data)

    assert result.portfolio_name == "Core Portfolio"


@pytest.mark.parametrize("portfolio_name", ["", " \t "])
def test_response_rejects_empty_normalized_portfolio_name(
    portfolio_name: str,
) -> None:
    data = _portfolio_response_data()
    data["portfolio_name"] = portfolio_name

    with pytest.raises(
        ValidationError,
        match="portfolio_name cannot be empty after normalization",
    ):
        PortfolioAnalysisResponse.model_validate(data)


def test_response_rejects_non_string_portfolio_name() -> None:
    data = _portfolio_response_data()
    data["portfolio_name"] = 123

    with pytest.raises(ValidationError):
        PortfolioAnalysisResponse.model_validate(data)


def test_response_accepts_return_points_on_inclusive_boundaries() -> None:
    data = _portfolio_response_data()
    data["start_date"] = "2026-01-10"
    data["end_date"] = "2026-01-20"

    result = PortfolioAnalysisResponse.model_validate(data)

    assert result.portfolio_returns[0].date == result.start_date
    assert result.portfolio_returns[-1].date == result.end_date


def test_response_accepts_equal_period_dates_when_dated_values_match() -> None:
    data = _single_asset_response_data()
    data["start_date"] = "2026-01-10"
    data["end_date"] = "2026-01-10"
    data["metadata"] = {
        "analysis_start": "2026-01-10",
        "analysis_end": "2026-01-10",
        "price_observation_count": 2,
        "return_observation_count": 1,
        "asset_count": 1,
    }
    data["max_drawdown"] = {
        "max_drawdown": 0.0,
        "peak_date": None,
        "trough_date": None,
    }
    data["portfolio_returns"] = [
        {"date": "2026-01-10", "portfolio_return": 0.04}
    ]
    asset_returns = data["asset_returns"]
    assert isinstance(asset_returns, list)
    asset_returns[0]["points"] = [
        {"date": "2026-01-10", "asset_return": 0.03}
    ]

    result = PortfolioAnalysisResponse.model_validate(data)

    assert result.start_date == result.end_date
    assert result.portfolio_returns[0].date == result.start_date


def test_response_rejects_reversed_period_through_analysis_period() -> None:
    data = _portfolio_response_data()
    data["start_date"] = "2026-02-01"
    data["end_date"] = "2026-01-31"

    with pytest.raises(
        ValidationError,
        match="start_date must be on or before end_date",
    ):
        PortfolioAnalysisResponse.model_validate(data)


def test_response_rejects_unknown_top_level_field() -> None:
    data = _portfolio_response_data()
    data["report_id"] = 42

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        PortfolioAnalysisResponse.model_validate(data)


def test_response_rejects_unknown_nested_field() -> None:
    data = _portfolio_response_data()
    metrics = data["portfolio_metrics"]
    assert isinstance(metrics, dict)
    metrics["debug"] = True

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        PortfolioAnalysisResponse.model_validate(data)


def test_response_model_dump_is_json_safe_without_non_finite_values() -> None:
    result = PortfolioAnalysisResponse.model_validate(
        _portfolio_response_data()
    )
    dumped = result.model_dump(mode="json")

    serialized = json.dumps(dumped, allow_nan=False)

    assert '"start_date": "2026-01-01"' in serialized
    assert "NaN" not in serialized
    assert "Infinity" not in serialized


def test_response_rejects_duplicate_portfolio_return_dates() -> None:
    data = _portfolio_response_data()
    data["portfolio_returns"] = [
        {"date": "2026-01-10", "portfolio_return": 0.04},
        {"date": "2026-01-10", "portfolio_return": 0.06},
    ]

    with pytest.raises(
        ValidationError,
        match="portfolio return dates must be unique",
    ):
        PortfolioAnalysisResponse.model_validate(data)


def test_response_rejects_descending_portfolio_return_dates() -> None:
    data = _portfolio_response_data()
    data["portfolio_returns"] = [
        {"date": "2026-01-20", "portfolio_return": 0.06},
        {"date": "2026-01-10", "portfolio_return": 0.04},
    ]

    with pytest.raises(
        ValidationError,
        match="portfolio return dates must be strictly increasing",
    ):
        PortfolioAnalysisResponse.model_validate(data)


@pytest.mark.parametrize("point_date", ["2025-12-31", "2026-02-01"])
def test_response_rejects_portfolio_return_outside_period(
    point_date: str,
) -> None:
    data = _portfolio_response_data()
    returns = data["portfolio_returns"]
    assert isinstance(returns, list)
    returns[0]["date"] = point_date
    if point_date == "2026-02-01":
        returns.reverse()

    with pytest.raises(
        ValidationError,
        match="portfolio return dates must fall within",
    ):
        PortfolioAnalysisResponse.model_validate(data)


def test_response_accepts_non_consecutive_portfolio_return_dates() -> None:
    data = _portfolio_response_data()
    data["portfolio_returns"] = [
        {"date": "2026-01-02", "portfolio_return": 0.04},
        {"date": "2026-01-30", "portfolio_return": 0.06},
    ]
    asset_returns = data["asset_returns"]
    assert isinstance(asset_returns, list)
    for series in asset_returns:
        series["points"][0]["date"] = "2026-01-02"
        series["points"][1]["date"] = "2026-01-30"

    result = PortfolioAnalysisResponse.model_validate(data)

    assert [point.date for point in result.portfolio_returns] == [
        date(2026, 1, 2),
        date(2026, 1, 30),
    ]


def test_response_preserves_portfolio_return_order() -> None:
    result = PortfolioAnalysisResponse.model_validate(
        _portfolio_response_data()
    )

    assert [point.portfolio_return for point in result.portfolio_returns] == [
        0.04,
        0.06,
    ]


def test_response_rejects_duplicate_asset_metric_symbols() -> None:
    data = _portfolio_response_data()
    metrics = data["asset_metrics"]
    assert isinstance(metrics, list)
    metrics[1]["symbol"] = " aapl "

    with pytest.raises(
        ValidationError,
        match="asset-metric symbols must be unique after normalization",
    ):
        PortfolioAnalysisResponse.model_validate(data)


def test_response_rejects_mismatched_asset_and_matrix_symbols() -> None:
    data = _portfolio_response_data()
    metrics = data["asset_metrics"]
    assert isinstance(metrics, list)
    metrics[1]["symbol"] = "BND"

    with pytest.raises(
        ValidationError,
        match="asset-metric symbols must match correlation matrix symbols",
    ):
        PortfolioAnalysisResponse.model_validate(data)


def test_response_rejects_mismatched_driver_and_matrix_symbols() -> None:
    data = _portfolio_response_data()
    drivers = data["risk_drivers"]
    assert isinstance(drivers, dict)
    entries = drivers["entries"]
    assert isinstance(entries, list)
    entries[1]["symbol"] = "BND"

    with pytest.raises(
        ValidationError,
        match="risk-driver symbols must match correlation matrix symbols",
    ):
        PortfolioAnalysisResponse.model_validate(data)


@pytest.mark.parametrize(
    "weights",
    [(0.50, 0.49), (0.50, 0.51)],
)
def test_response_rejects_invalid_asset_weight_total(
    weights: tuple[float, float],
) -> None:
    data = _portfolio_response_data()
    metrics = data["asset_metrics"]
    assert isinstance(metrics, list)
    metrics[0]["weight"] = weights[0]
    metrics[1]["weight"] = weights[1]

    with pytest.raises(
        ValidationError,
        match="asset-metric weights must sum to 1.0",
    ):
        PortfolioAnalysisResponse.model_validate(data)


def test_response_accepts_floating_point_safe_asset_weight_total() -> None:
    result = PortfolioAnalysisResponse.model_validate(
        _three_asset_response_data()
    )

    assert [metric.weight for metric in result.asset_metrics] == [
        0.1,
        0.2,
        0.7,
    ]


def test_response_rejects_correlation_pair_with_unknown_symbol() -> None:
    data = _portfolio_response_data()
    pairs = data["correlation_pairs"]
    assert isinstance(pairs, list)
    pairs[0]["asset_b"] = "BND"

    with pytest.raises(
        ValidationError,
        match="correlation pair symbols must belong",
    ):
        PortfolioAnalysisResponse.model_validate(data)


def test_response_rejects_duplicate_unordered_correlation_pair() -> None:
    data = _portfolio_response_data()
    pairs = data["correlation_pairs"]
    assert isinstance(pairs, list)
    pairs.append(
        {
            "asset_a": "MSFT",
            "asset_b": "AAPL",
            "correlation": 0.40,
        }
    )

    with pytest.raises(
        ValidationError,
        match="duplicate unordered correlation pairs",
    ):
        PortfolioAnalysisResponse.model_validate(data)


def test_response_preserves_correlation_pair_internal_and_list_order() -> None:
    data = _three_asset_response_data()
    pairs = data["correlation_pairs"]
    assert isinstance(pairs, list)
    pairs.reverse()

    result = PortfolioAnalysisResponse.model_validate(data)

    assert [
        (pair.asset_a, pair.asset_b)
        for pair in result.correlation_pairs
    ] == [
        ("MSFT", "BND"),
        ("AAPL", "BND"),
        ("AAPL", "MSFT"),
    ]


def test_response_preserves_risk_driver_order() -> None:
    data = _portfolio_response_data()
    drivers = data["risk_drivers"]
    assert isinstance(drivers, dict)
    entries = drivers["entries"]
    assert isinstance(entries, list)
    entries.reverse()
    drivers["top_driver"] = "MSFT"

    result = PortfolioAnalysisResponse.model_validate(data)

    assert [entry.symbol for entry in result.risk_drivers.entries] == [
        "MSFT",
        "AAPL",
    ]


def test_response_preserves_asset_metric_order() -> None:
    data = _portfolio_response_data()
    metrics = data["asset_metrics"]
    assert isinstance(metrics, list)
    metrics.reverse()
    asset_returns = data["asset_returns"]
    assert isinstance(asset_returns, list)
    asset_returns.reverse()

    result = PortfolioAnalysisResponse.model_validate(data)

    assert [metric.symbol for metric in result.asset_metrics] == [
        "MSFT",
        "AAPL",
    ]


def test_response_rejects_partial_asset_risk_classification() -> None:
    data = _portfolio_response_data()
    metrics = data["asset_metrics"]
    assert isinstance(metrics, list)
    metrics[1].pop("risk_classification")

    with pytest.raises(
        ValidationError,
        match="asset risk classifications must be present for all assets",
    ):
        PortfolioAnalysisResponse.model_validate(data)


def test_response_accepts_legacy_analysis_without_asset_extensions() -> None:
    data = _portfolio_response_data()
    data.pop("asset_returns")
    metrics = data["asset_metrics"]
    assert isinstance(metrics, list)
    for metric in metrics:
        metric.pop("risk_classification")

    result = PortfolioAnalysisResponse.model_validate(data)

    assert result.asset_returns == []
    assert all(
        metric.risk_classification is None
        for metric in result.asset_metrics
    )


def test_response_rejects_asset_return_symbol_order_mismatch() -> None:
    data = _portfolio_response_data()
    asset_returns = data["asset_returns"]
    assert isinstance(asset_returns, list)
    asset_returns.reverse()

    with pytest.raises(
        ValidationError,
        match="asset-return series symbols and order must match",
    ):
        PortfolioAnalysisResponse.model_validate(data)


def test_response_rejects_asset_return_date_mismatch() -> None:
    data = _portfolio_response_data()
    asset_returns = data["asset_returns"]
    assert isinstance(asset_returns, list)
    asset_returns[0]["points"][0]["date"] = "2026-01-11"

    with pytest.raises(
        ValidationError,
        match="asset-return dates must match portfolio-return dates",
    ):
        PortfolioAnalysisResponse.model_validate(data)


def test_response_does_not_mutate_complete_caller_input() -> None:
    data = _portfolio_response_data()
    metadata = data["metadata"]
    returns = data["portfolio_returns"]
    drivers = data["risk_drivers"]
    assets = data["asset_metrics"]
    pairs = data["correlation_pairs"]
    matrix = data["correlation_matrix"]
    assert isinstance(drivers, dict)
    driver_entries = drivers["entries"]
    assert isinstance(matrix, dict)
    matrix_symbols = matrix["symbols"]
    matrix_values = matrix["values"]
    original = deepcopy(data)

    PortfolioAnalysisResponse.model_validate(data)

    assert data == original
    assert data["metadata"] is metadata
    assert data["portfolio_returns"] is returns
    assert data["risk_drivers"] is drivers
    assert drivers["entries"] is driver_entries
    assert data["asset_metrics"] is assets
    assert data["correlation_pairs"] is pairs
    assert data["correlation_matrix"] is matrix
    assert matrix["symbols"] is matrix_symbols
    assert matrix["values"] is matrix_values
