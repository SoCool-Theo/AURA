"""Public current asset outlook contracts; ratios are numeric decimal values."""

from datetime import date
from typing import Annotated, Literal, Self

from pydantic import Field, field_validator, model_validator

from ..core.instruments import USER_ASSET_SYMBOLS
from .common import AssetSymbol, AuraBaseModel


FORECAST_LIMITATIONS: tuple[str, ...] = (
    "Forecasts are probabilistic estimates, not guarantees of future performance.",
    "This outlook is for educational risk analysis and is not investment advice.",
    "Prediction intervals have a nominal 80% coverage level; future observed coverage may differ.",
)
_FiniteValue = Annotated[float, Field(strict=True, allow_inf_nan=False)]
_NonNegativeFiniteValue = Annotated[
    float, Field(strict=True, ge=0, allow_inf_nan=False)
]
_ArtifactVersion = Annotated[str, Field(pattern=r"^forecast-v[0-9]+-[0-9]{8}$")]


class ForecastPredictionInterval(AuraBaseModel):
    """Frozen empirical prediction bounds for a future realized target."""

    lower: _FiniteValue
    upper: _FiniteValue
    coverage: Literal[0.80]

    @model_validator(mode="after")
    def validate_order(self) -> Self:
        if self.lower > self.upper:
            raise ValueError("prediction interval lower must not exceed upper")
        return self


class VolatilityPredictionInterval(ForecastPredictionInterval):
    lower: _NonNegativeFiniteValue
    upper: _NonNegativeFiniteValue


class AssetOutlookResponse(AuraBaseModel):
    """Authenticated 30-day asset estimate with public model provenance."""

    symbol: AssetSymbol
    forecast_origin_date: date
    horizon_days: Literal[30]
    expected_return_30d: _FiniteValue
    return_prediction_interval: ForecastPredictionInterval
    forecast_realized_volatility_30d: _NonNegativeFiniteValue
    volatility_prediction_interval: VolatilityPredictionInterval
    market_data_as_of: date
    market_data_age_days: Annotated[int, Field(strict=True, ge=0, le=4)]
    artifact_version: _ArtifactVersion
    return_model_id: Literal[
        "historical_average", "moving_average_90_calendar_days",
        "linear_regression_v1", "arima_1_0_1_v1", "random_forest_v1",
    ]
    volatility_model_id: Literal[
        "historical_average", "moving_average_90_calendar_days",
        "volatility_linear_regression_v1", "volatility_arima_1_0_1_v1",
        "volatility_random_forest_v1",
    ]
    limitations: list[str]

    @field_validator("symbol")
    @classmethod
    def validate_supported_symbol(cls, value: str) -> str:
        if value not in USER_ASSET_SYMBOLS:
            raise ValueError("unsupported forecast asset symbol")
        return value

    @field_validator("limitations")
    @classmethod
    def validate_educational_limitations(cls, value: list[str]) -> list[str]:
        if tuple(value) != FORECAST_LIMITATIONS:
            raise ValueError("forecast limitations must use approved educational wording")
        return value

    @model_validator(mode="after")
    def validate_market_context(self) -> Self:
        if self.market_data_as_of != self.forecast_origin_date:
            raise ValueError("market data date must match the forecast origin")
        return self
