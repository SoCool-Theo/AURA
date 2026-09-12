import pytest

from backend.app.core.instruments import (
    INTERNAL_MARKET_SYMBOLS,
    MARKET_UPDATE_SYMBOLS,
    USER_ASSET_SYMBOLS,
    USD_THB_FX_SYMBOL,
    InstrumentType,
    UnknownMarketInstrumentError,
    get_instrument_metadata,
    is_user_asset_symbol,
)
from backend.app.data_pipeline.fetcher import DEFAULT_SYMBOLS


def test_user_asset_symbols_preserve_existing_public_default_contract() -> None:
    assert USER_ASSET_SYMBOLS == DEFAULT_SYMBOLS
    assert len(USER_ASSET_SYMBOLS) == 17
    assert USD_THB_FX_SYMBOL not in USER_ASSET_SYMBOLS


def test_asset_metadata_identifies_aapl_as_usd_quoted_user_asset() -> None:
    metadata = get_instrument_metadata(" aapl ")

    assert metadata.provider_symbol == "AAPL"
    assert metadata.instrument_type is InstrumentType.ASSET
    assert metadata.base_currency is None
    assert metadata.quote_currency == "USD"
    assert is_user_asset_symbol("aapl") is True


def test_usd_thb_metadata_identifies_internal_fx_direction() -> None:
    metadata = get_instrument_metadata("thb=x")

    assert metadata.provider_symbol == "THB=X"
    assert metadata.instrument_type is InstrumentType.FX
    assert metadata.base_currency == "USD"
    assert metadata.quote_currency == "THB"
    assert is_user_asset_symbol("THB=X") is False


def test_market_update_symbols_add_only_required_internal_fx() -> None:
    assert INTERNAL_MARKET_SYMBOLS == ("THB=X",)
    assert MARKET_UPDATE_SYMBOLS == USER_ASSET_SYMBOLS + ("THB=X",)
    assert len(MARKET_UPDATE_SYMBOLS) == 18


def test_unknown_instrument_behavior_is_explicit() -> None:
    with pytest.raises(
        UnknownMarketInstrumentError,
        match="unknown market instrument: UNKNOWN",
    ):
        get_instrument_metadata("unknown")

    assert is_user_asset_symbol("unknown") is False
