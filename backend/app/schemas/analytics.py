"""Atomic, JSON-safe Pydantic contracts for Aura analytics results."""

from datetime import date
from typing import Annotated, Literal, Self

from pydantic import BeforeValidator, Field, model_validator

from .common import AssetSymbol, AuraBaseModel


def _require_json_numeric_value(value: object) -> object:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("value must be an integer or floating-point number")
    return value


FiniteFloat = Annotated[
    float,
    BeforeValidator(_require_json_numeric_value),
    Field(allow_inf_nan=False),
]
NonNegativeFiniteFloat = Annotated[
    float,
    BeforeValidator(_require_json_numeric_value),
    Field(ge=0.0, allow_inf_nan=False),
]
PositiveFiniteFloat = Annotated[
    float,
    BeforeValidator(_require_json_numeric_value),
    Field(gt=0.0, allow_inf_nan=False),
]
UnitFloat = Annotated[
    float,
    BeforeValidator(_require_json_numeric_value),
    Field(ge=0.0, le=1.0, allow_inf_nan=False),
]
PositiveUnitFloat = Annotated[
    float,
    BeforeValidator(_require_json_numeric_value),
    Field(gt=0.0, le=1.0, allow_inf_nan=False),
]
DrawdownFloat = Annotated[
    float,
    BeforeValidator(_require_json_numeric_value),
    Field(ge=-1.0, le=0.0, allow_inf_nan=False),
]
ScoreFloat = Annotated[
    float,
    BeforeValidator(_require_json_numeric_value),
    Field(ge=0.0, le=100.0, allow_inf_nan=False),
]
CorrelationFloat = Annotated[
    float,
    BeforeValidator(_require_json_numeric_value),
    Field(ge=-1.0, le=1.0, allow_inf_nan=False),
]
NonNegativeInt = Annotated[int, Field(strict=True, ge=0)]
PositiveInt = Annotated[int, Field(strict=True, gt=0)]
RiskPoints = Annotated[int, Field(strict=True, ge=0, le=3)]


class MaximumDrawdownMetrics(AuraBaseModel):
    """Maximum drawdown and its active peak-to-trough dates."""

    max_drawdown: DrawdownFloat
    peak_date: date | None
    trough_date: date | None


class ConcentrationMetrics(AuraBaseModel):
    """Quantitative portfolio concentration metrics."""

    largest_weight: PositiveUnitFloat
    top_n_weight: PositiveUnitFloat
    hhi: PositiveUnitFloat
    effective_number_of_assets: PositiveFiniteFloat
    top_n: PositiveInt


class DiversificationMetrics(AuraBaseModel):
    """Quantitative diversification scores and available pair coverage."""

    active_asset_count: PositiveInt
    effective_number_of_assets: PositiveFiniteFloat
    weight_score: ScoreFloat
    average_pairwise_correlation: CorrelationFloat | None
    correlation_score: ScoreFloat | None
    overall_score: ScoreFloat | None
    level: Literal["Weak", "Moderate", "Strong", "Unavailable"]
    defined_pair_count: NonNegativeInt
    total_pair_count: NonNegativeInt

    @model_validator(mode="after")
    def validate_unavailable_level(self) -> Self:
        if self.overall_score is None and self.level != "Unavailable":
            raise ValueError(
                "level must be Unavailable when overall_score is unavailable"
            )
        if self.overall_score is not None and self.level == "Unavailable":
            raise ValueError(
                "level cannot be Unavailable when overall_score is available"
            )
        return self


class RiskDriverEntry(AuraBaseModel):
    """One already-ranked, signed portfolio volatility contribution."""

    rank: PositiveInt
    symbol: AssetSymbol
    weight: UnitFloat
    annualized_asset_volatility: NonNegativeFiniteFloat
    marginal_volatility_contribution: FiniteFloat
    component_volatility_contribution: FiniteFloat
    percentage_volatility_contribution: FiniteFloat


class RiskClassification(AuraBaseModel):
    """Aura's deterministic educational portfolio-risk classification."""

    risk_score: ScoreFloat
    risk_level: Literal["Low", "Moderate", "High", "Very High"]
    volatility_points: RiskPoints
    drawdown_points: RiskPoints
    concentration_points: RiskPoints
    diversification_points: RiskPoints | None
    metrics_used: Annotated[
        list[
            Literal[
                "volatility",
                "maximum_drawdown",
                "concentration",
                "diversification",
            ]
        ],
        Field(min_length=3),
    ]
    reasons: Annotated[list[str], Field(min_length=1)]


class AssetMetrics(AuraBaseModel):
    """The engine's public metrics for one portfolio asset."""

    symbol: AssetSymbol
    weight: UnitFloat
    cumulative_return: FiniteFloat
    annualized_return: FiniteFloat
    annualized_volatility: NonNegativeFiniteFloat
    max_drawdown: DrawdownFloat
    sharpe_ratio: FiniteFloat | None


class CorrelationPair(AuraBaseModel):
    """One ordered pair of assets and their optional correlation."""

    asset_a: AssetSymbol
    asset_b: AssetSymbol
    correlation: CorrelationFloat | None

    @model_validator(mode="after")
    def validate_distinct_symbols(self) -> Self:
        if self.asset_a == self.asset_b:
            raise ValueError(
                "correlation pair symbols must differ after normalization"
            )
        return self


class CorrelationMatrix(AuraBaseModel):
    """An ordered, square, JSON-safe asset-correlation matrix."""

    symbols: Annotated[list[AssetSymbol], Field(min_length=1)]
    values: list[list[CorrelationFloat | None]]

    @model_validator(mode="after")
    def validate_shape_and_symbols(self) -> Self:
        if len(self.symbols) != len(set(self.symbols)):
            raise ValueError(
                "correlation matrix symbols must be unique after normalization"
            )

        size = len(self.symbols)
        if len(self.values) != size:
            raise ValueError(
                "correlation matrix must contain one row per symbol"
            )
        if any(len(row) != size for row in self.values):
            raise ValueError(
                "each correlation matrix row must contain one value per symbol"
            )
        return self
