"""Pure adapters and internal dataset contracts for asset forecasting.

The adapter consumes Aura's canonical persisted ``adjusted_close`` value. The
existing market-data cleaner may populate that field from an unadjusted close
when a provider does not supply an adjusted value; this module intentionally
does not reinterpret or repair that upstream provenance limitation.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
import math
from numbers import Real
from typing import TYPE_CHECKING

from ..core.instruments import (
    USER_ASSET_SYMBOLS,
    InstrumentType,
    get_instrument_metadata,
)
from ..database.models import MarketData

if TYPE_CHECKING:
    from .features import ForecastFeatureRow
    from .targets import ForecastTargetRow


MIN_LABEL_COMPLETE_TRAINING_ORIGINS = 756


class ForecastDataError(ValueError):
    """Raised when persisted observations cannot form safe forecast input."""


def _normalize_forecast_symbol(symbol: object) -> str:
    if not isinstance(symbol, str):
        raise ForecastDataError("forecast symbol must be a string")
    try:
        metadata = get_instrument_metadata(symbol)
    except (TypeError, ValueError) as error:
        raise ForecastDataError(f"unsupported forecast symbol: {symbol}") from error
    if (
        metadata.instrument_type is not InstrumentType.ASSET
        or metadata.provider_symbol not in USER_ASSET_SYMBOLS
    ):
        raise ForecastDataError(
            f"instrument is not a forecastable user asset: {metadata.provider_symbol}"
        )
    return metadata.provider_symbol


def _validated_price(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (Decimal, Real)):
        raise ForecastDataError(
            "forecast adjusted_close must be a real numeric value"
        )
    try:
        decimal_value = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError) as error:
        raise ForecastDataError(
            "forecast adjusted_close must be a real numeric value"
        ) from error
    if not decimal_value.is_finite() or decimal_value <= 0:
        raise ForecastDataError(
            "forecast adjusted_close must be positive and finite"
        )
    float_value = float(decimal_value)
    if not math.isfinite(float_value) or float_value <= 0.0:
        raise ForecastDataError(
            "forecast adjusted_close must be positive and finite"
        )
    return float_value


@dataclass(frozen=True, slots=True)
class ForecastPriceObservation:
    """One validated stored observation on an asset's own calendar."""

    date: date
    adjusted_close: float

    def __post_init__(self) -> None:
        if type(self.date) is not date:
            raise ForecastDataError("forecast observation date must be a date")
        if not math.isfinite(self.adjusted_close) or self.adjusted_close <= 0.0:
            raise ForecastDataError(
                "forecast adjusted_close must be positive and finite"
            )


@dataclass(frozen=True, slots=True)
class AssetPriceHistory:
    """Strictly ordered observations for one approved user asset."""

    symbol: str
    observations: tuple[ForecastPriceObservation, ...]

    def __post_init__(self) -> None:
        normalized = _normalize_forecast_symbol(self.symbol)
        if normalized != self.symbol:
            raise ForecastDataError("asset price-history symbol must be normalized")
        if not self.observations:
            raise ForecastDataError("asset price history cannot be empty")
        dates = tuple(observation.date for observation in self.observations)
        if any(current <= previous for previous, current in zip(dates, dates[1:])):
            raise ForecastDataError(
                "asset price-history dates must be unique and strictly increasing"
            )


@dataclass(frozen=True, slots=True)
class ForecastDatasetRow:
    """One past-only feature row paired with its completed future label."""

    features: ForecastFeatureRow
    target: ForecastTargetRow


@dataclass(frozen=True, slots=True)
class ForecastDataset:
    """Internal per-symbol Phase 2 dataset and enforcement metadata."""

    symbol: str
    feature_set_version: str
    target_set_version: str
    max_feature_lookback: int
    minimum_label_complete_training_origins: int
    price_observation_count: int
    feature_origin_count: int
    target_origin_count: int
    rows: tuple[ForecastDatasetRow, ...]

    @property
    def label_complete_origin_count(self) -> int:
        """Return origins that have both warmed-up features and complete labels."""
        return len(self.rows)


def build_price_histories(
    records: Iterable[MarketData],
) -> tuple[AssetPriceHistory, ...]:
    """Validate and group persisted rows without aligning asset calendars.

    Input order is irrelevant. Output symbols are sorted and each symbol's
    observations are sorted by date. Duplicate normalized symbol/date pairs
    are rejected rather than resolved silently. Missing dates are preserved as
    missing: no fill, interpolation, or synthetic observations are introduced.
    """
    grouped: dict[str, list[ForecastPriceObservation]] = {}
    seen: set[tuple[str, date]] = set()

    for record in records:
        try:
            raw_symbol = record.symbol
            observation_date = record.date
            raw_price = record.adjusted_close
        except AttributeError as error:
            raise ForecastDataError(
                "forecast records must expose symbol, date, and adjusted_close"
            ) from error

        symbol = _normalize_forecast_symbol(raw_symbol)
        if type(observation_date) is not date:
            raise ForecastDataError("forecast observation date must be a date")
        key = (symbol, observation_date)
        if key in seen:
            raise ForecastDataError(
                f"duplicate forecast observation: {symbol} {observation_date.isoformat()}"
            )
        seen.add(key)
        grouped.setdefault(symbol, []).append(
            ForecastPriceObservation(
                date=observation_date,
                adjusted_close=_validated_price(raw_price),
            )
        )

    return tuple(
        AssetPriceHistory(
            symbol=symbol,
            observations=tuple(
                sorted(grouped[symbol], key=lambda observation: observation.date)
            ),
        )
        for symbol in sorted(grouped)
    )


def build_forecast_dataset(history: AssetPriceHistory) -> ForecastDataset:
    """Join past-only features to label-complete targets by forecast origin."""
    from .features import (
        FEATURE_SET_VERSION,
        MAX_FEATURE_LOOKBACK,
        build_feature_rows,
    )
    from .targets import TARGET_SET_VERSION, build_target_rows

    feature_rows = build_feature_rows(history)
    target_rows = build_target_rows(history)
    targets_by_origin = {row.origin_date: row for row in target_rows}
    rows = tuple(
        ForecastDatasetRow(
            features=feature_row,
            target=targets_by_origin[feature_row.origin_date],
        )
        for feature_row in feature_rows
        if feature_row.origin_date in targets_by_origin
    )
    return ForecastDataset(
        symbol=history.symbol,
        feature_set_version=FEATURE_SET_VERSION,
        target_set_version=TARGET_SET_VERSION,
        max_feature_lookback=MAX_FEATURE_LOOKBACK,
        minimum_label_complete_training_origins=(
            MIN_LABEL_COMPLETE_TRAINING_ORIGINS
        ),
        price_observation_count=len(history.observations),
        feature_origin_count=len(feature_rows),
        target_origin_count=len(target_rows),
        rows=rows,
    )
