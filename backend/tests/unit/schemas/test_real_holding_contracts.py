from copy import deepcopy
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID

import pytest
from pydantic import ValidationError

from backend.app.schemas.portfolio import (
    PortfolioHoldingInput,
    PortfolioHoldingResponse,
    PortfolioRealHoldingInput,
    PortfolioResponse,
)


HOLDING_ID = UUID("31000000-0000-0000-0000-000000000001")
PORTFOLIO_ID = UUID("32000000-0000-0000-0000-000000000001")


def _valid_real_input() -> dict[str, object]:
    return {
        "symbol": "AAPL",
        "invested_amount": Decimal("1500.000000000000"),
        "invested_currency": "USD",
        "shares": Decimal("10.000000000000"),
        "purchase_date": date(2026, 1, 10),
    }


def _valid_real_response() -> dict[str, object]:
    return {
        "id": HOLDING_ID,
        "symbol": "AAPL",
        "weight": None,
        "invested_amount": Decimal("1500.000000000000"),
        "invested_currency": "USD",
        "shares": Decimal("10.000000000000"),
        "purchase_date": date(2026, 1, 10),
        "position": 0,
    }


def test_real_input_accepts_normal_usd_holding_as_decimals() -> None:
    result = PortfolioRealHoldingInput.model_validate(_valid_real_input())

    assert result.symbol == "AAPL"
    assert result.invested_amount == Decimal("1500.000000000000")
    assert result.invested_currency == "USD"
    assert result.shares == Decimal("10.000000000000")
    assert type(result.invested_amount) is Decimal
    assert type(result.shares) is Decimal


def test_real_input_defaults_invested_currency_to_usd() -> None:
    data = _valid_real_input()
    data.pop("invested_currency")

    assert PortfolioRealHoldingInput.model_validate(
        data
    ).invested_currency == "USD"


def test_real_input_accepts_and_normalizes_explicit_thb() -> None:
    data = _valid_real_input()
    data["invested_currency"] = " thb "

    assert PortfolioRealHoldingInput.model_validate(
        data
    ).invested_currency == "THB"


def test_real_input_normalizes_symbol_with_existing_rules() -> None:
    data = _valid_real_input()
    data["symbol"] = " brk.b "

    assert PortfolioRealHoldingInput.model_validate(data).symbol == "BRK.B"


@pytest.mark.parametrize("currency", ["EUR", "JPY", "", 1, None])
def test_real_input_rejects_unsupported_currency(currency: object) -> None:
    data = _valid_real_input()
    data["invested_currency"] = currency

    with pytest.raises(ValidationError):
        PortfolioRealHoldingInput.model_validate(data)


@pytest.mark.parametrize(
    "field_name,value",
    [
        ("invested_amount", Decimal("10")),
        ("shares", Decimal("10")),
        ("shares", Decimal("0.123456789012")),
        ("shares", Decimal("0.000000000001")),
        ("invested_amount", Decimal("9999999999999999.999999999999")),
        ("shares", Decimal("9999999999999999.999999999999")),
    ],
)
def test_real_input_accepts_numeric_28_12_boundaries(
    field_name: str,
    value: Decimal,
) -> None:
    data = _valid_real_input()
    data[field_name] = value

    result = PortfolioRealHoldingInput.model_validate(data)

    assert getattr(result, field_name) == value
    assert type(getattr(result, field_name)) is Decimal


@pytest.mark.parametrize("field_name", ["invested_amount", "shares"])
@pytest.mark.parametrize(
    "value",
    [
        Decimal("10000000000000000"),
        Decimal("1.0000000000001"),
        Decimal("0"),
        Decimal("-1"),
        Decimal("NaN"),
        Decimal("Infinity"),
        Decimal("-Infinity"),
    ],
)
def test_real_input_rejects_unpersistable_or_non_positive_decimals(
    field_name: str,
    value: Decimal,
) -> None:
    data = _valid_real_input()
    data[field_name] = value

    with pytest.raises(ValidationError):
        PortfolioRealHoldingInput.model_validate(data)


def test_real_input_rejects_future_purchase_date() -> None:
    data = _valid_real_input()
    data["purchase_date"] = datetime.now(UTC).date() + timedelta(days=1)

    with pytest.raises(
        ValidationError,
        match="purchase_date must not be in the future",
    ):
        PortfolioRealHoldingInput.model_validate(data)


def test_real_input_accepts_current_utc_purchase_date() -> None:
    data = _valid_real_input()
    data["purchase_date"] = datetime.now(UTC).date()

    assert PortfolioRealHoldingInput.model_validate(
        data
    ).purchase_date == datetime.now(UTC).date()


@pytest.mark.parametrize(
    "forbidden_field",
    [
        "weight",
        "allocation",
        "current_allocation",
        "current_value",
        "latest_price",
        "fx_rate",
        "position",
    ],
)
def test_real_input_rejects_non_input_and_derived_fields(
    forbidden_field: str,
) -> None:
    data = _valid_real_input()
    data[forbidden_field] = 1

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        PortfolioRealHoldingInput.model_validate(data)


def test_real_input_does_not_mutate_caller_owned_mapping() -> None:
    data = _valid_real_input()
    data["symbol"] = " aapl "
    data["invested_currency"] = " thb "
    original = deepcopy(data)

    result = PortfolioRealHoldingInput.model_validate(data)

    assert data == original
    assert result.symbol == "AAPL"
    assert result.invested_currency == "THB"


def test_existing_legacy_input_contract_is_unchanged() -> None:
    result = PortfolioHoldingInput(symbol="AAPL", weight=0.4)

    assert result.model_dump(mode="json") == {
        "symbol": "AAPL",
        "weight": 0.4,
    }
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        PortfolioHoldingInput.model_validate(_valid_real_input())


def test_legacy_response_preserves_weight_and_explicit_null_facts() -> None:
    result = PortfolioHoldingResponse.model_validate(
        {
            "id": HOLDING_ID,
            "symbol": "AAPL",
            "weight": 0.5,
            "invested_amount": None,
            "invested_currency": None,
            "shares": None,
            "purchase_date": None,
            "position": 0,
        }
    )

    assert result.weight == 0.5
    assert result.model_dump(mode="json") == {
        "id": str(HOLDING_ID),
        "symbol": "AAPL",
        "weight": 0.5,
        "invested_amount": None,
        "invested_currency": None,
        "shares": None,
        "purchase_date": None,
        "position": 0,
    }


def test_real_response_serializes_decimals_as_strings_and_weight_as_null() -> None:
    result = PortfolioHoldingResponse.model_validate(_valid_real_response())

    assert result.weight is None
    assert result.model_dump(mode="json") == {
        "id": str(HOLDING_ID),
        "symbol": "AAPL",
        "weight": None,
        "invested_amount": "1500.000000000000",
        "invested_currency": "USD",
        "shares": "10.000000000000",
        "purchase_date": "2026-01-10",
        "position": 0,
    }


def test_current_legacy_response_shape_remains_serialization_compatible() -> None:
    result = PortfolioHoldingResponse(
        symbol="AAPL",
        weight=0.5,
        position=0,
    )

    assert result.model_dump(mode="json") == {
        "symbol": "AAPL",
        "weight": 0.5,
        "position": 0,
    }


@pytest.mark.parametrize(
    "updates",
    [
        {"weight": 0.5},
        {"invested_amount": None},
        {"shares": None},
        {"invested_currency": None},
        {"purchase_date": None},
    ],
)
def test_real_response_rejects_hybrid_or_partial_modes(
    updates: dict[str, object],
) -> None:
    data = _valid_real_response()
    data.update(updates)

    with pytest.raises(
        ValidationError,
        match="exactly one legacy or real mode",
    ):
        PortfolioHoldingResponse.model_validate(data)


def test_response_rejects_empty_mode_and_explicit_null_id() -> None:
    with pytest.raises(ValidationError, match="exactly one legacy or real mode"):
        PortfolioHoldingResponse(symbol="AAPL", position=0)

    data = _valid_real_response()
    data["id"] = None
    with pytest.raises(ValidationError, match="id cannot be null"):
        PortfolioHoldingResponse.model_validate(data)


@pytest.mark.parametrize("mode", ["legacy", "real"])
def test_response_validates_complete_orm_style_attributes(mode: str) -> None:
    values = _valid_real_response()
    if mode == "legacy":
        values.update(
            weight=0.5,
            invested_amount=None,
            invested_currency=None,
            shares=None,
            purchase_date=None,
        )

    result = PortfolioHoldingResponse.model_validate(SimpleNamespace(**values))

    assert result.id == HOLDING_ID
    assert result.weight == (0.5 if mode == "legacy" else None)


def test_portfolio_response_preserves_mixed_holding_order() -> None:
    legacy = {
        "id": UUID("31000000-0000-0000-0000-000000000002"),
        "symbol": "BND",
        "weight": 0.4,
        "invested_amount": None,
        "invested_currency": None,
        "shares": None,
        "purchase_date": None,
        "position": 0,
    }
    real = _valid_real_response()
    real["position"] = 1

    result = PortfolioResponse(
        id=PORTFOLIO_ID,
        name="Mixed facts",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        updated_at=datetime(2026, 1, 2, tzinfo=UTC),
        holdings=[legacy, real],
    )

    assert [holding.symbol for holding in result.holdings] == ["BND", "AAPL"]
    assert [holding.position for holding in result.holdings] == [0, 1]


def test_contracts_contain_no_valuation_fields() -> None:
    forbidden = {
        "current_value_usd",
        "current_value",
        "total_portfolio_value",
        "latest_asset_price",
        "price_as_of",
        "current_allocation",
        "fx_rate",
        "fx_as_of",
    }

    assert not forbidden & PortfolioRealHoldingInput.model_fields.keys()
    assert not forbidden & PortfolioHoldingResponse.model_fields.keys()
