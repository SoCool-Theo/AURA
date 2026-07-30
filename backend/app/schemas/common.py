"""Shared Pydantic conventions and primitives for Aura API contracts."""

from datetime import date
from typing import Annotated, Self

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Strict,
    model_validator,
)


class AuraBaseModel(BaseModel):
    """Base model for Aura request and response contracts."""

    model_config = ConfigDict(extra="forbid")


def _normalize_asset_symbol(value: object) -> object:
    if not isinstance(value, str):
        return value

    normalized = value.strip().upper()
    if not normalized:
        raise ValueError("asset symbol cannot be empty after normalization")
    return normalized


AssetSymbol = Annotated[
    str,
    Strict(),
    BeforeValidator(_normalize_asset_symbol),
]


class AnalysisPeriod(AuraBaseModel):
    """Inclusive start and end dates for an Aura analysis."""

    start_date: date
    end_date: date

    @model_validator(mode="after")
    def validate_date_order(self) -> Self:
        if self.start_date > self.end_date:
            raise ValueError("start_date must be on or before end_date")
        return self
