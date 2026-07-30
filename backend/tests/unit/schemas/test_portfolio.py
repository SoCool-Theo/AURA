from copy import deepcopy
from datetime import date

import pytest
from pydantic import ValidationError

from backend.app.schemas.portfolio import (
    PortfolioAnalysisRequest,
    PortfolioHoldingInput,
)


def _valid_request_data() -> dict[str, object]:
    return {
        "portfolio_name": "Core Portfolio",
        "holdings": [
            {"symbol": "AAPL", "weight": 0.60},
            {"symbol": "MSFT", "weight": 0.40},
        ],
        "start_date": "2026-01-01",
        "end_date": "2026-12-31",
    }


def test_holding_accepts_normalized_symbol_and_decimal_weight() -> None:
    result = PortfolioHoldingInput(symbol="AAPL", weight=0.40)

    assert result.symbol == "AAPL"
    assert result.weight == pytest.approx(0.40)


def test_holding_normalizes_lowercase_symbol_and_whitespace() -> None:
    result = PortfolioHoldingInput(symbol="  aapl ", weight=0.40)

    assert result.symbol == "AAPL"


def test_holding_preserves_symbol_punctuation() -> None:
    result = PortfolioHoldingInput(symbol=" brk.b ", weight=0.40)

    assert result.symbol == "BRK.B"


def test_holding_accepts_zero_weight() -> None:
    result = PortfolioHoldingInput(symbol="CASH", weight=0.0)

    assert result.weight == 0.0


def test_holding_accepts_weight_of_one() -> None:
    result = PortfolioHoldingInput(symbol="AAPL", weight=1.0)

    assert result.weight == 1.0


@pytest.mark.parametrize("weight", [-0.01, 1.01])
def test_holding_rejects_out_of_range_weight(weight: float) -> None:
    with pytest.raises(ValidationError):
        PortfolioHoldingInput(symbol="AAPL", weight=weight)


@pytest.mark.parametrize("weight", [float("nan"), float("inf"), -float("inf")])
def test_holding_rejects_non_finite_weight(weight: float) -> None:
    with pytest.raises(ValidationError):
        PortfolioHoldingInput(symbol="AAPL", weight=weight)


def test_holding_rejects_boolean_weight() -> None:
    with pytest.raises(ValidationError):
        PortfolioHoldingInput(symbol="AAPL", weight=True)


def test_holding_rejects_numeric_string_weight() -> None:
    with pytest.raises(ValidationError):
        PortfolioHoldingInput(symbol="AAPL", weight="0.4")


def test_holding_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        PortfolioHoldingInput.model_validate(
            {"symbol": "AAPL", "weight": 0.40, "shares": 10}
        )


def test_holding_does_not_mutate_input_mapping() -> None:
    data = {"symbol": " aapl ", "weight": 0.40}
    original = data.copy()

    result = PortfolioHoldingInput.model_validate(data)

    assert data == original
    assert result.symbol == "AAPL"


def test_request_accepts_valid_multi_holding_portfolio() -> None:
    result = PortfolioAnalysisRequest.model_validate(_valid_request_data())

    assert result.portfolio_name == "Core Portfolio"
    assert [holding.symbol for holding in result.holdings] == [
        "AAPL",
        "MSFT",
    ]
    assert result.start_date == date(2026, 1, 1)
    assert result.end_date == date(2026, 12, 31)


def test_request_accepts_single_holding_with_full_weight() -> None:
    data = _valid_request_data()
    data["holdings"] = [{"symbol": "AAPL", "weight": 1.0}]

    result = PortfolioAnalysisRequest.model_validate(data)

    assert len(result.holdings) == 1
    assert result.holdings[0].weight == 1.0


def test_request_trims_portfolio_name_whitespace() -> None:
    data = _valid_request_data()
    data["portfolio_name"] = "  Core Portfolio \t"

    result = PortfolioAnalysisRequest.model_validate(data)

    assert result.portfolio_name == "Core Portfolio"


@pytest.mark.parametrize("portfolio_name", ["", " \t "])
def test_request_rejects_empty_normalized_portfolio_name(
    portfolio_name: str,
) -> None:
    data = _valid_request_data()
    data["portfolio_name"] = portfolio_name

    with pytest.raises(
        ValidationError,
        match="portfolio_name cannot be empty after normalization",
    ):
        PortfolioAnalysisRequest.model_validate(data)


def test_request_rejects_non_string_portfolio_name() -> None:
    data = _valid_request_data()
    data["portfolio_name"] = 123

    with pytest.raises(ValidationError):
        PortfolioAnalysisRequest.model_validate(data)


def test_request_rejects_empty_holdings() -> None:
    data = _valid_request_data()
    data["holdings"] = []

    with pytest.raises(ValidationError):
        PortfolioAnalysisRequest.model_validate(data)


@pytest.mark.parametrize(
    "symbols",
    [
        ("AAPL", "AAPL"),
        ("AAPL", "aapl"),
        ("AAPL", " AAPL "),
    ],
)
def test_request_rejects_duplicate_normalized_symbols(
    symbols: tuple[str, str],
) -> None:
    data = _valid_request_data()
    data["holdings"] = [
        {"symbol": symbols[0], "weight": 0.50},
        {"symbol": symbols[1], "weight": 0.50},
    ]

    with pytest.raises(
        ValidationError,
        match="holding symbols must be unique after normalization",
    ):
        PortfolioAnalysisRequest.model_validate(data)


@pytest.mark.parametrize(
    "weights",
    [
        (0.50, 0.499_999_998),
        (0.50, 0.500_000_002),
    ],
)
def test_request_rejects_weight_total_outside_tolerance(
    weights: tuple[float, float],
) -> None:
    data = _valid_request_data()
    data["holdings"] = [
        {"symbol": "AAPL", "weight": weights[0]},
        {"symbol": "MSFT", "weight": weights[1]},
    ]

    with pytest.raises(
        ValidationError,
        match="holding weights must sum to 1.0",
    ):
        PortfolioAnalysisRequest.model_validate(data)


def test_request_accepts_floating_point_safe_weight_total() -> None:
    data = _valid_request_data()
    data["holdings"] = [
        {"symbol": "A", "weight": 0.1},
        {"symbol": "B", "weight": 0.2},
        {"symbol": "C", "weight": 0.7},
    ]

    result = PortfolioAnalysisRequest.model_validate(data)

    assert [holding.weight for holding in result.holdings] == [
        0.1,
        0.2,
        0.7,
    ]


def test_request_accepts_equal_start_and_end_dates() -> None:
    data = _valid_request_data()
    data["start_date"] = "2026-06-01"
    data["end_date"] = "2026-06-01"

    result = PortfolioAnalysisRequest.model_validate(data)

    assert result.start_date == result.end_date


def test_request_rejects_reversed_date_range_through_analysis_period() -> None:
    data = _valid_request_data()
    data["start_date"] = "2026-12-31"
    data["end_date"] = "2026-01-01"

    with pytest.raises(
        ValidationError,
        match="start_date must be on or before end_date",
    ):
        PortfolioAnalysisRequest.model_validate(data)


def test_request_rejects_unknown_top_level_field() -> None:
    data = _valid_request_data()
    data["owner_id"] = 42

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        PortfolioAnalysisRequest.model_validate(data)


def test_request_rejects_unknown_nested_holding_field() -> None:
    data = _valid_request_data()
    holdings = data["holdings"]
    assert isinstance(holdings, list)
    holdings[0]["shares"] = 10

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        PortfolioAnalysisRequest.model_validate(data)


def test_request_preserves_holding_order() -> None:
    data = _valid_request_data()
    data["holdings"] = [
        {"symbol": "BETA", "weight": 0.20},
        {"symbol": "ALPHA", "weight": 0.50},
        {"symbol": "CASH", "weight": 0.30},
    ]

    result = PortfolioAnalysisRequest.model_validate(data)

    assert [holding.symbol for holding in result.holdings] == [
        "BETA",
        "ALPHA",
        "CASH",
    ]


def test_request_model_dump_json_mode_is_json_safe() -> None:
    result = PortfolioAnalysisRequest.model_validate(_valid_request_data())

    assert result.model_dump(mode="json") == {
        "start_date": "2026-01-01",
        "end_date": "2026-12-31",
        "portfolio_name": "Core Portfolio",
        "holdings": [
            {"symbol": "AAPL", "weight": 0.60},
            {"symbol": "MSFT", "weight": 0.40},
        ],
    }


def test_request_does_not_mutate_caller_owned_input_structures() -> None:
    first_holding = {"symbol": " aapl ", "weight": 0.60}
    second_holding = {"symbol": "msft", "weight": 0.40}
    holdings = [first_holding, second_holding]
    data = {
        "portfolio_name": "  Core Portfolio ",
        "holdings": holdings,
        "start_date": "2026-01-01",
        "end_date": "2026-12-31",
    }
    original = deepcopy(data)

    result = PortfolioAnalysisRequest.model_validate(data)

    assert data == original
    assert data["holdings"] is holdings
    assert holdings[0] is first_holding
    assert holdings[1] is second_holding
    assert result.portfolio_name == "Core Portfolio"
    assert [holding.symbol for holding in result.holdings] == [
        "AAPL",
        "MSFT",
    ]
