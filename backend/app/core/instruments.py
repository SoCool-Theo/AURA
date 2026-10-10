"""Small code-owned registry for Aura market instruments."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Mapping


class InstrumentType(StrEnum):
    """Instrument categories required by Aura's valuation infrastructure."""

    ASSET = "asset"
    FX = "fx"


@dataclass(frozen=True, slots=True)
class InstrumentMetadata:
    """Stable provider and currency facts for one supported instrument."""

    provider_symbol: str
    instrument_type: InstrumentType
    quote_currency: str
    base_currency: str | None = None


class UnknownMarketInstrumentError(ValueError):
    """Raised when a symbol has no approved Aura instrument metadata."""


USER_ASSET_SYMBOLS: tuple[str, ...] = (
    "AAPL",
    "MSFT",
    "TSLA",
    "NVDA",
    "AMZN",
    "GOOGL",
    "META",
    "SPY",
    "QQQ",
    "DIA",
    "VTI",
    "GLD",
    "SLV",
    "BND",
    "TLT",
    "BTC-USD",
    "ETH-USD",
)
USD_THB_FX_SYMBOL = "THB=X"
INTERNAL_MARKET_SYMBOLS: tuple[str, ...] = (USD_THB_FX_SYMBOL,)
MARKET_UPDATE_SYMBOLS: tuple[str, ...] = (
    USER_ASSET_SYMBOLS + INTERNAL_MARKET_SYMBOLS
)


_INSTRUMENT_REGISTRY: Mapping[str, InstrumentMetadata] = MappingProxyType(
    {
        **{
            symbol: InstrumentMetadata(
                provider_symbol=symbol,
                instrument_type=InstrumentType.ASSET,
                quote_currency="USD",
            )
            for symbol in USER_ASSET_SYMBOLS
        },
        USD_THB_FX_SYMBOL: InstrumentMetadata(
            provider_symbol=USD_THB_FX_SYMBOL,
            instrument_type=InstrumentType.FX,
            base_currency="USD",
            quote_currency="THB",
        ),
    }
)


def _normalize_instrument_symbol(symbol: str) -> str:
    if not isinstance(symbol, str):
        raise TypeError("instrument symbol must be a string")
    normalized = symbol.strip().upper()
    if not normalized:
        raise ValueError("instrument symbol cannot be blank")
    return normalized


def get_instrument_metadata(symbol: str) -> InstrumentMetadata:
    """Return approved metadata or fail explicitly for an unknown symbol."""
    normalized = _normalize_instrument_symbol(symbol)
    try:
        return _INSTRUMENT_REGISTRY[normalized]
    except KeyError as error:
        raise UnknownMarketInstrumentError(
            f"unknown market instrument: {normalized}"
        ) from error


def is_user_asset_symbol(symbol: str) -> bool:
    """Return whether the normalized symbol is an approved user asset."""
    try:
        metadata = get_instrument_metadata(symbol)
    except UnknownMarketInstrumentError:
        return False
    return metadata.instrument_type is InstrumentType.ASSET
