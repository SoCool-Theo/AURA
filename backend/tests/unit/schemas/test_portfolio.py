from copy import deepcopy
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from pydantic import ValidationError

from backend.app.schemas.portfolio import (
    PortfolioAnalysisRequest,
    PortfolioCreateRequest,
    PortfolioDuplicateRequest,
    PortfolioHoldingInput,
    PortfolioHoldingResponse,
    PortfolioHoldingsReplaceRequest,
    PortfolioListResponse,
    PortfolioResponse,
    PortfolioSummaryResponse,
    PortfolioUpdateRequest,
    PortfolioValuationResponse,
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


def _valid_response_data() -> dict[str, object]:
    return {
        "id": "c3eef91a-0f86-497a-8a7f-a3a908fde211",
        "name": "Core Portfolio",
        "created_at": "2026-08-17T09:30:00+07:00",
        "updated_at": "2026-08-17T10:45:00+07:00",
        "holdings": [
            {"symbol": "AAPL", "weight": 0.60, "position": 0},
            {"symbol": "MSFT", "weight": 0.40, "position": 1},
        ],
    }


def _real_holding_data(
    symbol: str = "AAPL",
    *,
    invested_amount: str = "1500.00",
    invested_currency: str | None = "USD",
    shares: str = "10.25",
) -> dict[str, object]:
    holding: dict[str, object] = {
        "symbol": symbol,
        "invested_amount": invested_amount,
        "shares": shares,
        "purchase_date": "2026-01-10",
    }
    if invested_currency is not None:
        holding["invested_currency"] = invested_currency
    return holding


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


@pytest.mark.parametrize(
    "request_type",
    [
        PortfolioCreateRequest,
        PortfolioUpdateRequest,
        PortfolioDuplicateRequest,
    ],
)
def test_crud_name_request_accepts_valid_name(request_type: type) -> None:
    result = request_type(name="Core Portfolio")

    assert result.name == "Core Portfolio"


@pytest.mark.parametrize(
    "request_type",
    [
        PortfolioCreateRequest,
        PortfolioUpdateRequest,
        PortfolioDuplicateRequest,
    ],
)
def test_crud_name_request_trims_surrounding_whitespace(
    request_type: type,
) -> None:
    result = request_type(name="  Core Portfolio \t")

    assert result.name == "Core Portfolio"


@pytest.mark.parametrize(
    "request_type",
    [
        PortfolioCreateRequest,
        PortfolioUpdateRequest,
        PortfolioDuplicateRequest,
    ],
)
@pytest.mark.parametrize("name", ["", " \t "])
def test_crud_name_request_rejects_empty_normalized_name(
    request_type: type,
    name: str,
) -> None:
    with pytest.raises(
        ValidationError,
        match="name cannot be empty after normalization",
    ):
        request_type(name=name)


@pytest.mark.parametrize(
    "request_type",
    [
        PortfolioCreateRequest,
        PortfolioUpdateRequest,
        PortfolioDuplicateRequest,
    ],
)
def test_crud_name_request_rejects_non_string(
    request_type: type,
) -> None:
    with pytest.raises(ValidationError):
        request_type(name=123)


@pytest.mark.parametrize(
    "request_type",
    [
        PortfolioCreateRequest,
        PortfolioUpdateRequest,
        PortfolioDuplicateRequest,
    ],
)
def test_crud_name_request_rejects_unknown_field(
    request_type: type,
) -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        request_type.model_validate({"name": "Core", "user_id": "hidden"})


def test_crud_holdings_replace_accepts_real_usd_holding() -> None:
    result = PortfolioHoldingsReplaceRequest.model_validate(
        {"holdings": [_real_holding_data()]}
    )

    holding = result.holdings[0]
    assert holding.symbol == "AAPL"
    assert holding.invested_amount == Decimal("1500.00")
    assert holding.invested_currency == "USD"
    assert holding.shares == Decimal("10.25")
    assert holding.purchase_date == date(2026, 1, 10)


def test_crud_holdings_replace_defaults_currency_and_accepts_thb() -> None:
    result = PortfolioHoldingsReplaceRequest.model_validate(
        {
            "holdings": [
                _real_holding_data("AAPL", invested_currency=None),
                _real_holding_data("MSFT", invested_currency=" thb "),
            ]
        }
    )

    assert [holding.invested_currency for holding in result.holdings] == [
        "USD",
        "THB",
    ]


def test_crud_holdings_replace_normalizes_symbols_and_preserves_order() -> None:
    result = PortfolioHoldingsReplaceRequest.model_validate(
        {
            "holdings": [
                _real_holding_data(" aapl "),
                _real_holding_data("msft"),
                _real_holding_data(" btc-usd "),
            ]
        }
    )

    assert [holding.symbol for holding in result.holdings] == [
        "AAPL",
        "MSFT",
        "BTC-USD",
    ]


def test_crud_holdings_replace_rejects_duplicate_normalized_symbols() -> None:
    with pytest.raises(
        ValidationError,
        match="holding symbols must be unique after normalization",
    ):
        PortfolioHoldingsReplaceRequest.model_validate(
            {
                "holdings": [
                    _real_holding_data("AAPL"),
                    _real_holding_data(" aapl "),
                ]
            }
        )


def test_crud_holdings_replace_rejects_manual_weight() -> None:
    holding = _real_holding_data()
    holding["weight"] = 1.0

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        PortfolioHoldingsReplaceRequest.model_validate(
            {"holdings": [holding]}
        )


def test_crud_holdings_replace_has_no_total_weight_requirement() -> None:
    result = PortfolioHoldingsReplaceRequest.model_validate(
        {
            "holdings": [
                _real_holding_data("AAPL", invested_amount="1.25"),
                _real_holding_data("MSFT", invested_amount="99999.75"),
            ]
        }
    )

    assert [holding.invested_amount for holding in result.holdings] == [
        Decimal("1.25"),
        Decimal("99999.75"),
    ]


def test_crud_holdings_replace_rejects_empty_holdings() -> None:
    with pytest.raises(ValidationError):
        PortfolioHoldingsReplaceRequest(holdings=[])


def test_crud_holdings_replace_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        holding = _real_holding_data()
        holding["current_value"] = "1500.00"
        PortfolioHoldingsReplaceRequest.model_validate(
            {"holdings": [holding]}
        )


def test_crud_holdings_replace_does_not_mutate_caller_input() -> None:
    first = _real_holding_data(" aapl ")
    second = _real_holding_data("msft", invested_currency=" thb ")
    holdings = [first, second]
    data = {"holdings": holdings}
    original = deepcopy(data)

    result = PortfolioHoldingsReplaceRequest.model_validate(data)

    assert data == original
    assert data["holdings"] is holdings
    assert holdings[0] is first
    assert holdings[1] is second
    assert [holding.symbol for holding in result.holdings] == ["AAPL", "MSFT"]


def test_crud_holding_response_accepts_persisted_shape_and_json_number() -> None:
    result = PortfolioHoldingResponse.model_validate(
        {"symbol": "AAPL", "weight": 0.40, "position": 2}
    )

    assert result.symbol == "AAPL"
    assert result.position == 2
    assert result.model_dump(mode="json") == {
        "symbol": "AAPL",
        "weight": 0.40,
        "position": 2,
    }


@pytest.mark.parametrize(
    "weight",
    [float("nan"), float("inf"), -float("inf"), -0.01, 1.01],
)
def test_crud_holding_response_rejects_invalid_weight(weight: float) -> None:
    with pytest.raises(ValidationError):
        PortfolioHoldingResponse(
            symbol="AAPL",
            weight=weight,
            position=0,
        )


@pytest.mark.parametrize("position", [-1, True, 1.5])
def test_crud_holding_response_rejects_invalid_position(
    position: object,
) -> None:
    with pytest.raises(ValidationError):
        PortfolioHoldingResponse(
            symbol="AAPL",
            weight=1.0,
            position=position,
        )


def test_crud_holding_response_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        PortfolioHoldingResponse.model_validate(
            {
                "symbol": "AAPL",
                "weight": 1.0,
                "position": 0,
                "current_value": 10,
            }
        )


def _valid_valuation_response_data(
    *,
    currency: str = "USD",
) -> dict[str, object]:
    fx: dict[str, object] | None = None
    total_current_value = "250.000000000000"
    current_value = "250.000000000000"
    if currency == "THB":
        fx = {
            "pair": "USD/THB",
            "provider_symbol": "THB=X",
            "rate": "32.500000000000",
            "as_of": "2026-09-11",
        }
        total_current_value = "8125.000000000000000000000000"
        current_value = total_current_value
    return {
        "portfolio_id": "c3eef91a-0f86-497a-8a7f-a3a908fde211",
        "valuation_currency": currency,
        "requested_date": "2026-09-12",
        "oldest_price_as_of": "2026-09-10",
        "newest_price_as_of": "2026-09-11",
        "total_current_value_usd": "250.000000000000",
        "total_current_value": total_current_value,
        "fx": fx,
        "holdings": [
            {
                "id": "a3eef91a-0f86-497a-8a7f-a3a908fde211",
                "symbol": "AAPL",
                "invested_amount": "200.000000000000",
                "invested_currency": "USD",
                "shares": "2.000000000000",
                "purchase_date": "2026-01-10",
                "position": 0,
                "asset_price": "125.000000000000",
                "asset_quote_currency": "USD",
                "price_as_of": "2026-09-11",
                "current_value_usd": "250.000000000000",
                "current_value": current_value,
                "current_allocation": "1",
            }
        ],
    }


@pytest.mark.parametrize("currency", ["USD", "THB"])
def test_valuation_response_preserves_decimal_json_contract(
    currency: str,
) -> None:
    result = PortfolioValuationResponse.model_validate(
        _valid_valuation_response_data(currency=currency)
    )

    serialized = result.model_dump(mode="json")

    assert serialized["valuation_currency"] == currency
    assert serialized["total_current_value_usd"] == "250.000000000000"
    assert isinstance(serialized["total_current_value"], str)
    holding = serialized["holdings"][0]
    assert holding["asset_price"] == "125.000000000000"
    assert holding["current_allocation"] == "1"


def test_valuation_response_rejects_currency_fx_mismatch() -> None:
    data = _valid_valuation_response_data()
    data["fx"] = {
        "pair": "USD/THB",
        "provider_symbol": "THB=X",
        "rate": "32.5",
        "as_of": "2026-09-11",
    }

    with pytest.raises(ValidationError, match="USD valuation must not"):
        PortfolioValuationResponse.model_validate(data)

    thb_data = _valid_valuation_response_data(currency="THB")
    thb_data["fx"] = None
    with pytest.raises(ValidationError, match="THB valuation requires"):
        PortfolioValuationResponse.model_validate(thb_data)


def test_valuation_response_rejects_unknown_fields_and_future_observations() -> None:
    data = _valid_valuation_response_data()
    data["calculated_total"] = "250"
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        PortfolioValuationResponse.model_validate(data)

    future_data = _valid_valuation_response_data()
    future_data["newest_price_as_of"] = "2026-09-13"
    with pytest.raises(ValidationError, match="must not be after requested_date"):
        PortfolioValuationResponse.model_validate(future_data)


def test_crud_portfolio_response_accepts_complete_end_user_shape() -> None:
    result = PortfolioResponse.model_validate(_valid_response_data())

    assert result.id == UUID("c3eef91a-0f86-497a-8a7f-a3a908fde211")
    assert result.name == "Core Portfolio"
    assert result.created_at == datetime(2026, 8, 17, 2, 30, tzinfo=UTC)
    assert result.updated_at == datetime(2026, 8, 17, 3, 45, tzinfo=UTC)
    assert [holding.symbol for holding in result.holdings] == ["AAPL", "MSFT"]


def test_crud_portfolio_response_does_not_require_or_expose_user_id() -> None:
    result = PortfolioResponse.model_validate(_valid_response_data())

    assert "user_id" not in result.model_dump()

    data = _valid_response_data()
    data["user_id"] = "6ae886f2-9e7a-4808-80a3-9a911a7a1458"
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        PortfolioResponse.model_validate(data)


def test_crud_portfolio_response_preserves_holding_order() -> None:
    data = _valid_response_data()
    data["holdings"] = [
        {"symbol": "BETA", "weight": 0.20, "position": 0},
        {"symbol": "ALPHA", "weight": 0.50, "position": 1},
        {"symbol": "CASH", "weight": 0.30, "position": 2},
    ]

    result = PortfolioResponse.model_validate(data)

    assert [holding.symbol for holding in result.holdings] == [
        "BETA",
        "ALPHA",
        "CASH",
    ]


def test_crud_portfolio_response_rejects_naive_timestamps() -> None:
    data = _valid_response_data()
    data["created_at"] = "2026-08-17T09:30:00"

    with pytest.raises(ValidationError):
        PortfolioResponse.model_validate(data)


def test_crud_portfolio_response_rejects_unknown_field_without_mutation() -> None:
    data = _valid_response_data()
    original = deepcopy(data)
    data["analysis"] = {"risk": "high"}
    invalid_snapshot = deepcopy(data)

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        PortfolioResponse.model_validate(data)

    assert data == invalid_snapshot
    assert original == _valid_response_data()


def test_crud_summary_response_accepts_lightweight_shape() -> None:
    data = _valid_response_data()

    result = PortfolioSummaryResponse.model_validate(
        {key: data[key] for key in ("id", "name", "created_at", "updated_at")}
    )

    assert result.name == "Core Portfolio"
    assert result.model_dump().keys() == {
        "id",
        "name",
        "created_at",
        "updated_at",
    }


def test_crud_summary_response_rejects_unknown_field() -> None:
    data = _valid_response_data()

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        PortfolioSummaryResponse.model_validate(data)


def test_crud_list_response_allows_empty_portfolios() -> None:
    result = PortfolioListResponse(portfolios=[])

    assert result.portfolios == []


def test_crud_list_response_preserves_portfolio_order() -> None:
    shared = {
        "created_at": "2026-08-17T09:30:00+07:00",
        "updated_at": "2026-08-17T10:45:00+07:00",
    }
    data = {
        "portfolios": [
            {
                "id": "00000000-0000-0000-0000-000000000002",
                "name": "Second ID First",
                **shared,
            },
            {
                "id": "00000000-0000-0000-0000-000000000001",
                "name": "First ID Second",
                **shared,
            },
        ]
    }

    result = PortfolioListResponse.model_validate(data)

    assert [portfolio.name for portfolio in result.portfolios] == [
        "Second ID First",
        "First ID Second",
    ]


def test_crud_list_response_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        PortfolioListResponse.model_validate(
            {"portfolios": [], "total": 0}
        )
