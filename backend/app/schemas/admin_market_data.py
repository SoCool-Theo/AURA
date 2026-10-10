"""Read-only administration of persisted prices, including internal FX data."""

from datetime import date
from decimal import Decimal
from typing import Annotated, Literal, Self

from pydantic import AwareDatetime, Field, field_validator, model_validator

from .common import AuraBaseModel


Count = Annotated[int, Field(ge=0)]
Price = Annotated[Decimal, Field(gt=0, allow_inf_nan=False)]


class AdminMarketDataQuery(AuraBaseModel):
    limit: Annotated[int, Field(ge=1, le=100)] = 25
    offset: Annotated[int, Field(ge=0, le=10000)] = 0
    symbol: Annotated[str, Field(min_length=1, max_length=64)] | None = None
    date_from: date | None = None
    date_to: date | None = None

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("symbol cannot be blank")
        return normalized

    @model_validator(mode="after")
    def date_order(self) -> Self:
        if self.date_from is not None and self.date_to is not None and self.date_from > self.date_to:
            raise ValueError("date_from must be on or before date_to")
        return self


class AdminMarketObservation(AuraBaseModel):
    symbol: str
    date: date
    adjusted_close: Price
    volume: Count | None
    source: str


class AdminMarketObservationsResponse(AuraBaseModel):
    items: list[AdminMarketObservation]
    total: Count
    limit: int
    offset: int


class AdminMarketInstrument(AuraBaseModel):
    symbol: str
    required_for_refresh: bool
    kind: Literal["asset", "fx", "unknown"]
    quote_currency: str | None
    base_currency: str | None
    total_records: Count
    first_price_date: date | None
    latest_price_date: date | None
    latest_adjusted_close: Price | None
    latest_volume: Count | None
    latest_source: str | None
    age_days: Count | None
    freshness: Literal["current", "stale", "missing", "unknown"]


class AdminMarketInventoryResponse(AuraBaseModel):
    checked_at: AwareDatetime
    total_records: Count
    stored_symbols: Count
    required_symbols: Count
    present_required_symbols: Count
    current_required_symbols: Count
    stale_required_symbols: Count
    missing_required_symbols: Count
    unexpected_symbols: Count
    instruments: list[AdminMarketInstrument]
