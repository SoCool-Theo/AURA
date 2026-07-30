from copy import deepcopy
from datetime import date
import json

import pytest
from pydantic import ValidationError

from backend.app.schemas.analytics import (
    AssetMetrics,
    ConcentrationMetrics,
    CorrelationMatrix,
    CorrelationPair,
    DiversificationMetrics,
    MaximumDrawdownMetrics,
    RiskClassification,
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
