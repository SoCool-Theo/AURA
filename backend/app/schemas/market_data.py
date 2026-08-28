"""Pydantic contracts for prepared daily historical market data."""

from datetime import date
from typing import Annotated, Self

from pydantic import (
    BeforeValidator,
    Field,
    Strict,
    field_validator,
    model_validator,
)

from .common import AnalysisPeriod, AssetSymbol, AuraBaseModel


def _require_json_numeric_value(value: object) -> object:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(
            "adjusted_close must be an integer or floating-point number"
        )
    return value


class HistoricalMarketDataRequest(AnalysisPeriod):
    """Request prepared daily data for ordered, unique asset symbols."""

    symbols: Annotated[list[AssetSymbol], Field(min_length=1)]

    @model_validator(mode="after")
    def validate_unique_symbols(self) -> Self:
        if len(self.symbols) != len(set(self.symbols)):
            raise ValueError("symbols must be unique after normalization")
        return self


class HistoricalPricePoint(AuraBaseModel):
    """One prepared daily adjusted-close and optional volume observation."""

    date: date
    adjusted_close: Annotated[
        float,
        BeforeValidator(_require_json_numeric_value),
        Field(gt=0.0, allow_inf_nan=False),
    ]
    volume: Annotated[int, Field(strict=True, ge=0)] | None = None


class AssetPriceSeries(AuraBaseModel):
    """Prepared, strictly ordered daily observations for one asset."""

    symbol: AssetSymbol
    source: Annotated[str, Strict()]
    points: Annotated[
        list[HistoricalPricePoint],
        Field(min_length=1),
    ]

    @field_validator("source", mode="before")
    @classmethod
    def normalize_source(cls, value: object) -> object:
        if not isinstance(value, str):
            return value

        normalized = value.strip()
        if not normalized:
            raise ValueError("source cannot be empty after normalization")
        return normalized

    @model_validator(mode="after")
    def validate_point_dates(self) -> Self:
        point_dates = [point.date for point in self.points]
        if len(point_dates) != len(set(point_dates)):
            raise ValueError("point dates must be unique")
        if any(
            current <= previous
            for previous, current in zip(point_dates, point_dates[1:])
        ):
            raise ValueError("point dates must be strictly increasing")
        return self


class HistoricalMarketDataResponse(AnalysisPeriod):
    """Prepared daily series bounded by an inclusive response period."""

    series: Annotated[list[AssetPriceSeries], Field(min_length=1)]

    @model_validator(mode="after")
    def validate_series(self) -> Self:
        symbols = [asset_series.symbol for asset_series in self.series]
        if len(symbols) != len(set(symbols)):
            raise ValueError(
                "series symbols must be unique after normalization"
            )

        if any(
            point.date < self.start_date or point.date > self.end_date
            for asset_series in self.series
            for point in asset_series.points
        ):
            raise ValueError(
                "point dates must fall within the inclusive response period"
            )
        return self
