from datetime import date

import pytest
from pydantic import BaseModel, TypeAdapter, ValidationError

from backend.app.schemas.common import (
    AnalysisPeriod,
    AssetSymbol,
    AuraBaseModel,
)


class _SymbolModel(BaseModel):
    symbol: AssetSymbol


def test_aura_base_model_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        AuraBaseModel(unexpected=True)


def test_asset_symbol_accepts_already_normalized_value() -> None:
    result = TypeAdapter(AssetSymbol).validate_python("AAPL")

    assert result == "AAPL"


def test_asset_symbol_converts_lowercase_letters_to_uppercase() -> None:
    result = TypeAdapter(AssetSymbol).validate_python("msft")

    assert result == "MSFT"


def test_asset_symbol_trims_surrounding_whitespace() -> None:
    result = TypeAdapter(AssetSymbol).validate_python("  aapl \t")

    assert result == "AAPL"


def test_asset_symbol_preserves_internal_punctuation() -> None:
    result = TypeAdapter(AssetSymbol).validate_python(" brk.b ")

    assert result == "BRK.B"


def test_asset_symbol_rejects_empty_string() -> None:
    with pytest.raises(
        ValidationError,
        match="asset symbol cannot be empty after normalization",
    ):
        TypeAdapter(AssetSymbol).validate_python("")


def test_asset_symbol_rejects_whitespace_only_string() -> None:
    with pytest.raises(
        ValidationError,
        match="asset symbol cannot be empty after normalization",
    ):
        TypeAdapter(AssetSymbol).validate_python(" \t ")


@pytest.mark.parametrize("value", [123, b"AAPL", None])
def test_asset_symbol_rejects_non_string_input(value: object) -> None:
    with pytest.raises(ValidationError, match="valid string"):
        TypeAdapter(AssetSymbol).validate_python(value)


def test_asset_symbol_repeated_validation_is_stable() -> None:
    adapter = TypeAdapter(AssetSymbol)
    first = adapter.validate_python(" aapl ")
    second = adapter.validate_python(first)

    assert first == "AAPL"
    assert second == first


def test_asset_symbol_works_as_a_reusable_model_field() -> None:
    result = _SymbolModel.model_validate({"symbol": " msft "})

    assert result.symbol == "MSFT"


def test_analysis_period_accepts_increasing_range() -> None:
    result = AnalysisPeriod.model_validate(
        {"start_date": "2026-01-01", "end_date": "2026-01-31"}
    )

    assert result.start_date == date(2026, 1, 1)
    assert result.end_date == date(2026, 1, 31)


def test_analysis_period_accepts_equal_dates() -> None:
    result = AnalysisPeriod(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 1),
    )

    assert result.start_date == result.end_date


def test_analysis_period_rejects_reversed_range() -> None:
    with pytest.raises(
        ValidationError,
        match="start_date must be on or before end_date",
    ):
        AnalysisPeriod(
            start_date=date(2026, 2, 1),
            end_date=date(2026, 1, 31),
        )


def test_analysis_period_accepts_python_date_input() -> None:
    start = date(2026, 3, 1)
    end = date(2026, 3, 15)

    result = AnalysisPeriod(start_date=start, end_date=end)

    assert result.start_date is start
    assert result.end_date is end


def test_analysis_period_serializes_dates_as_iso_json_strings() -> None:
    result = AnalysisPeriod(
        start_date=date(2026, 4, 1),
        end_date=date(2026, 4, 30),
    )

    assert result.model_dump_json() == (
        '{"start_date":"2026-04-01","end_date":"2026-04-30"}'
    )


def test_analysis_period_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        AnalysisPeriod.model_validate(
            {
                "start_date": "2026-01-01",
                "end_date": "2026-01-31",
                "timezone": "UTC",
            }
        )


def test_analysis_period_does_not_mutate_caller_input_mapping() -> None:
    data = {
        "start_date": "2026-05-01",
        "end_date": "2026-05-31",
    }
    original = data.copy()

    AnalysisPeriod.model_validate(data)

    assert data == original
    assert list(data) == list(original)
