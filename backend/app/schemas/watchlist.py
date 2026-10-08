"""Strict public contracts for Aura Watchlist Backend V1."""

from datetime import date
from typing import Annotated, Self
from uuid import UUID

from pydantic import AwareDatetime, Field, model_validator

from .common import AssetSymbol, AuraBaseModel


_FinitePercent = Annotated[float, Field(allow_inf_nan=False)]
_PositiveFinitePrice = Annotated[
    float,
    Field(gt=0.0, allow_inf_nan=False),
]


class WatchlistCreateRequest(AuraBaseModel):
    """Request to observe one normalized Aura-supported asset."""

    symbol: AssetSymbol


class WatchlistItemResponse(AuraBaseModel):
    """One saved symbol enriched from persisted Aura market data."""

    id: UUID
    symbol: AssetSymbol
    latest_price: _PositiveFinitePrice | None
    latest_price_date: date | None
    daily_change_percent: _FinitePercent | None
    ytd_change_percent: _FinitePercent | None
    created_at: AwareDatetime

    @model_validator(mode="after")
    def validate_market_context(self) -> Self:
        if (self.latest_price is None) != (self.latest_price_date is None):
            raise ValueError(
                "latest_price and latest_price_date must be available together"
            )
        if self.latest_price is None and (
            self.daily_change_percent is not None
            or self.ytd_change_percent is not None
        ):
            raise ValueError(
                "change metrics require an available latest price"
            )
        return self


class WatchlistListResponse(AuraBaseModel):
    """A user's Watchlist in deterministic add order."""

    items: list[WatchlistItemResponse]
