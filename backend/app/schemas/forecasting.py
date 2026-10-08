"""Public current asset outlook contracts; ratios are numeric decimal values."""

from datetime import date
import math
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from ..core.instruments import USER_ASSET_SYMBOLS
from .common import AssetSymbol, AuraBaseModel
from .forecasting_monetary import PortfolioMonetaryProjectionResponse, validate_monetary_projection


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


PORTFOLIO_FORECAST_LIMITATIONS: tuple[str, ...] = (
    "Forecasts are probabilistic estimates, not guarantees of future performance.",
    "Portfolio forecast volatility combines forecast marginal asset volatility with historical correlations.",
    "Historical correlations may change in future markets.",
    "This outlook is for educational risk analysis and is not investment advice.",
    "Component prediction intervals are individually calibrated; no calibrated portfolio prediction interval is provided.",
)


class PortfolioOutlookComponent(AssetOutlookResponse):
    """Complete asset outlook with authoritative weight and signed contribution."""

    current_weight: Annotated[float, Field(strict=True, ge=0, le=1, allow_inf_nan=False)]
    forecast_volatility_contribution: _FiniteValue
    forecast_volatility_contribution_share: _FiniteValue


class PortfolioOutlookResponse(AuraBaseModel):
    """30-day composition, deliberately without a portfolio prediction interval."""

    portfolio_id: UUID
    portfolio_name: str
    baseline_kind: Literal["current", "legacy", "planned"]
    horizon_days: Literal[30]
    expected_return_30d: _FiniteValue
    forecast_realized_volatility_30d: _NonNegativeFiniteValue
    correlation_as_of_date: date
    correlation_observation_count: Annotated[int, Field(strict=True, ge=60, le=252)]
    market_data_as_of: date
    artifact_version: _ArtifactVersion
    components: Annotated[list[PortfolioOutlookComponent], Field(min_length=1)]
    monetary_projection: PortfolioMonetaryProjectionResponse | None = None
    limitations: list[str]

    @field_validator("limitations")
    @classmethod
    def validate_limitations(cls, value: list[str]) -> list[str]:
        if tuple(value) != PORTFOLIO_FORECAST_LIMITATIONS:
            raise ValueError("portfolio limitations must use approved wording")
        return value

    @model_validator(mode="after")
    def validate_composition_context(self) -> Self:
        validate_monetary_projection(self.monetary_projection, self.baseline_kind, self.expected_return_30d)
        if len({c.symbol for c in self.components}) != len(self.components):
            raise ValueError("portfolio components must be unique")
        if not math.isclose(math.fsum(c.current_weight for c in self.components), 1, rel_tol=0, abs_tol=1e-10):
            raise ValueError("portfolio weights must sum to one")
        if self.correlation_as_of_date != min(c.forecast_origin_date for c in self.components):
            raise ValueError("correlation cutoff must use the earliest origin")
        if self.market_data_as_of != min(c.market_data_as_of for c in self.components):
            raise ValueError("portfolio market date must use the oldest component")
        if any(c.artifact_version != self.artifact_version for c in self.components):
            raise ValueError("component artifact versions must match")
        return self
