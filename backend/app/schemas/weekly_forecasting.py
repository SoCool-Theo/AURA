"""Additive experimental weekly contracts; all numbers are decimal ratios."""

from datetime import date
import math
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from ..core.instruments import USER_ASSET_SYMBOLS
from .common import AssetSymbol, AuraBaseModel
from .forecasting_monetary import PortfolioMonetaryProjectionResponse, validate_monetary_projection
from .forecasting import (
    FORECAST_LIMITATIONS, PORTFOLIO_FORECAST_LIMITATIONS,
    ForecastPredictionInterval, VolatilityPredictionInterval,
)


WeeklyHorizon = Literal[7, 14, 21]
FiniteValue = Annotated[float, Field(strict=True, allow_inf_nan=False)]
NonNegativeValue = Annotated[float, Field(strict=True, ge=0, allow_inf_nan=False)]
WeeklyWarning = Literal[
    "arima_fit_convergence_warning", "empty_volatility_intervals_counted_as_misses",
    "final_interval_coverage_below_nominal",
]
EXPERIMENTAL_LIMITATIONS = (
    "Weekly V1 is experimental with mixed per-asset quality; it is not approved as reliable predictions.",
    "Overlapping labels are not independent observations; the reused V1 snapshot is not a fresh untouched holdout.",
)
WEEKLY_ASSET_LIMITATIONS = FORECAST_LIMITATIONS + EXPERIMENTAL_LIMITATIONS
WEEKLY_PORTFOLIO_LIMITATIONS = PORTFOLIO_FORECAST_LIMITATIONS + EXPERIMENTAL_LIMITATIONS


def _strict_horizon(value):
    if type(value) is not int or value not in (7, 14, 21):
        raise ValueError("weekly horizon must be an integer 7, 14 or 21")
    return value


class WeeklyAssetOutlookResponse(AuraBaseModel):
    symbol: AssetSymbol
    forecast_origin_date: date
    horizon_days: WeeklyHorizon
    horizon_unit: Literal["calendar_days"]
    expected_return: FiniteValue
    return_prediction_interval: ForecastPredictionInterval
    forecast_realized_volatility: NonNegativeValue
    volatility_prediction_interval: VolatilityPredictionInterval
    market_data_as_of: date
    market_data_age_days: Annotated[int, Field(strict=True, ge=0, le=4)]
    artifact_version: Literal["forecast-weekly-v1-20260917"]
    return_model_id: Literal[
        "historical_average", "moving_average_90_calendar_days",
        "linear_regression_v1", "arima_1_0_1_v1", "random_forest_v1",
    ]
    volatility_model_id: Literal[
        "historical_average", "moving_average_90_calendar_days",
        "volatility_linear_regression_v1", "volatility_arima_1_0_1_v1", "volatility_random_forest_v1",
    ]
    experimental: Literal[True]
    predictive_quality_approved: Literal[False]
    quality_status: Literal["experimental_educational_not_predictive_quality_approved"]
    return_warning_codes: list[WeeklyWarning]
    volatility_warning_codes: list[WeeklyWarning]
    limitations: list[str]

    @field_validator("horizon_days", mode="before")
    @classmethod
    def strict_horizon(cls, value):
        return _strict_horizon(value)

    @field_validator("symbol")
    @classmethod
    def supported_symbol(cls, value: str) -> str:
        if value not in USER_ASSET_SYMBOLS:
            raise ValueError("unsupported forecast asset symbol")
        return value

    @field_validator("limitations")
    @classmethod
    def educational_wording(cls, value: list[str]) -> list[str]:
        if tuple(value) != WEEKLY_ASSET_LIMITATIONS:
            raise ValueError("weekly limitations must use approved wording")
        return value

    @model_validator(mode="after")
    def market_context(self) -> Self:
        if self.market_data_as_of != self.forecast_origin_date:
            raise ValueError("market data date must match the forecast origin")
        return self


class WeeklyPortfolioOutlookComponent(WeeklyAssetOutlookResponse):
    current_weight: Annotated[float, Field(strict=True, ge=0, le=1, allow_inf_nan=False)]
    forecast_volatility_contribution: FiniteValue
    forecast_volatility_contribution_share: FiniteValue


class WeeklyPortfolioOutlookResponse(AuraBaseModel):
    portfolio_id: UUID
    portfolio_name: str
    baseline_kind: Literal["current", "legacy", "planned"]
    horizon_days: WeeklyHorizon
    horizon_unit: Literal["calendar_days"]
    expected_return: FiniteValue
    forecast_realized_volatility: NonNegativeValue
    correlation_as_of_date: date
    correlation_observation_count: Annotated[int, Field(strict=True, ge=60, le=252)]
    market_data_as_of: date
    artifact_version: Literal["forecast-weekly-v1-20260917"]
    experimental: Literal[True]
    predictive_quality_approved: Literal[False]
    quality_status: Literal["experimental_educational_not_predictive_quality_approved"]
    components: Annotated[list[WeeklyPortfolioOutlookComponent], Field(min_length=1)]
    monetary_projection: PortfolioMonetaryProjectionResponse | None = None
    limitations: list[str]

    @field_validator("horizon_days", mode="before")
    @classmethod
    def strict_horizon(cls, value):
        return _strict_horizon(value)

    @field_validator("limitations")
    @classmethod
    def educational_wording(cls, value: list[str]) -> list[str]:
        if tuple(value) != WEEKLY_PORTFOLIO_LIMITATIONS:
            raise ValueError("weekly portfolio limitations must use approved wording")
        return value

    @model_validator(mode="after")
    def composition_context(self) -> Self:
        validate_monetary_projection(self.monetary_projection, self.baseline_kind, self.expected_return)
        if len({c.symbol for c in self.components}) != len(self.components):
            raise ValueError("portfolio components must be unique")
        if not math.isclose(math.fsum(c.current_weight for c in self.components), 1., rel_tol=0, abs_tol=1e-10):
            raise ValueError("portfolio weights must sum to one")
        if any(c.horizon_days != self.horizon_days or c.artifact_version != self.artifact_version for c in self.components):
            raise ValueError("component horizons and artifact versions must match")
        if self.correlation_as_of_date != min(c.forecast_origin_date for c in self.components):
            raise ValueError("correlation cutoff must use earliest origin")
        if self.market_data_as_of != min(c.market_data_as_of for c in self.components):
            raise ValueError("market data date must use oldest component")
        return self
