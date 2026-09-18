"""Atomic, JSON-safe Pydantic contracts for Aura analytics results."""

from datetime import date
import math
from typing import Annotated, Literal, Self

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


class AssetRiskClassification(AuraBaseModel):
    """Deterministic educational risk classification for one asset."""

    risk_score: ScoreFloat
    risk_level: Literal["Low", "Moderate", "High", "Very High"]
    volatility_points: RiskPoints
    drawdown_points: RiskPoints
    metrics_used: Annotated[
        list[Literal["volatility", "maximum_drawdown"]],
        Field(min_length=2, max_length=2),
    ]
    reasons: Annotated[list[str], Field(min_length=1)]

    @model_validator(mode="after")
    def validate_metrics_used(self) -> Self:
        if self.metrics_used != ["volatility", "maximum_drawdown"]:
            raise ValueError(
                "asset risk metrics_used must be volatility followed by "
                "maximum_drawdown"
            )
        return self


class AssetMetrics(AuraBaseModel):
    """The engine's public metrics for one portfolio asset."""

    symbol: AssetSymbol
    weight: UnitFloat
    cumulative_return: FiniteFloat
    annualized_return: FiniteFloat
    annualized_volatility: NonNegativeFiniteFloat
    max_drawdown: DrawdownFloat
    sharpe_ratio: FiniteFloat | None
    risk_classification: AssetRiskClassification | None = None


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


class AnalysisMetadata(AuraBaseModel):
    """Stable observation and asset metadata from the analytics engine."""

    analysis_start: date
    analysis_end: date
    price_observation_count: PositiveInt
    return_observation_count: PositiveInt
    asset_count: PositiveInt

    @model_validator(mode="after")
    def validate_observation_counts_and_dates(self) -> Self:
        if self.analysis_start > self.analysis_end:
            raise ValueError(
                "analysis_start must be on or before analysis_end"
            )
        if self.return_observation_count != self.price_observation_count - 1:
            raise ValueError(
                "return_observation_count must equal "
                "price_observation_count minus one"
            )
        return self


class PortfolioMetrics(AuraBaseModel):
    """The engine's top-level scalar portfolio metrics."""

    cumulative_return: FiniteFloat
    annualized_return: FiniteFloat
    annualized_volatility: NonNegativeFiniteFloat
    sharpe_ratio: FiniteFloat


class PortfolioReturnPoint(AuraBaseModel):
    """One dated periodically rebalanced portfolio return observation."""

    date: date
    portfolio_return: FiniteFloat


class AssetReturnPoint(AuraBaseModel):
    """One dated return observation for one analyzed asset."""

    date: date
    asset_return: FiniteFloat


class AssetReturnSeries(AuraBaseModel):
    """Ordered dated return observations for one analyzed asset."""

    symbol: AssetSymbol
    points: Annotated[list[AssetReturnPoint], Field(min_length=1)]

    @model_validator(mode="after")
    def validate_point_dates(self) -> Self:
        point_dates = [point.date for point in self.points]
        if len(point_dates) != len(set(point_dates)):
            raise ValueError("asset return dates must be unique")
        if any(
            current <= previous
            for previous, current in zip(point_dates, point_dates[1:])
        ):
            raise ValueError(
                "asset return dates must be strictly increasing"
            )
        return self


class RiskDriverAnalysis(AuraBaseModel):
    """Portfolio volatility and its already-ranked risk-driver entries."""

    portfolio_volatility: NonNegativeFiniteFloat
    top_driver: AssetSymbol
    entries: Annotated[list[RiskDriverEntry], Field(min_length=1)]

    @model_validator(mode="after")
    def validate_entries(self) -> Self:
        symbols = [entry.symbol for entry in self.entries]
        if len(symbols) != len(set(symbols)):
            raise ValueError(
                "risk-driver symbols must be unique after normalization"
            )
        if self.top_driver != self.entries[0].symbol:
            raise ValueError(
                "top_driver must match the first ranked risk-driver entry"
            )
        return self


class PortfolioAnalysisResponse(AnalysisPeriod):
    """Complete JSON-safe destination contract for portfolio analytics."""

    portfolio_name: Annotated[str, Strict()]
    metadata: AnalysisMetadata
    portfolio_metrics: PortfolioMetrics
    max_drawdown: MaximumDrawdownMetrics
    concentration: ConcentrationMetrics
    diversification: DiversificationMetrics
    risk_classification: RiskClassification
    risk_drivers: RiskDriverAnalysis
    asset_metrics: Annotated[list[AssetMetrics], Field(min_length=1)]
    correlation_matrix: CorrelationMatrix
    correlation_pairs: list[CorrelationPair]
    portfolio_returns: Annotated[
        list[PortfolioReturnPoint],
        Field(min_length=1),
    ]
    asset_returns: list[AssetReturnSeries] = Field(default_factory=list)

    @field_validator("portfolio_name", mode="before")
    @classmethod
    def normalize_portfolio_name(cls, value: object) -> object:
        if not isinstance(value, str):
            return value

        normalized = value.strip()
        if not normalized:
            raise ValueError(
                "portfolio_name cannot be empty after normalization"
            )
        return normalized

    @model_validator(mode="after")
    def validate_response_consistency(self) -> Self:
        return_dates = [point.date for point in self.portfolio_returns]
        if len(return_dates) != len(set(return_dates)):
            raise ValueError("portfolio return dates must be unique")
        if any(
            current <= previous
            for previous, current in zip(return_dates, return_dates[1:])
        ):
            raise ValueError(
                "portfolio return dates must be strictly increasing"
            )
        if any(
            point_date < self.start_date or point_date > self.end_date
            for point_date in return_dates
        ):
            raise ValueError(
                "portfolio return dates must fall within the inclusive "
                "response period"
            )

        asset_symbols = [metric.symbol for metric in self.asset_metrics]
        if len(asset_symbols) != len(set(asset_symbols)):
            raise ValueError(
                "asset-metric symbols must be unique after normalization"
            )

        classified_asset_count = sum(
            metric.risk_classification is not None
            for metric in self.asset_metrics
        )
        if classified_asset_count not in (0, len(self.asset_metrics)):
            raise ValueError(
                "asset risk classifications must be present for all assets "
                "or absent for legacy responses"
            )

        matrix_symbols = set(self.correlation_matrix.symbols)
        if set(asset_symbols) != matrix_symbols:
            raise ValueError(
                "asset-metric symbols must match correlation matrix symbols"
            )

        driver_symbols = {
            entry.symbol for entry in self.risk_drivers.entries
        }
        if driver_symbols != matrix_symbols:
            raise ValueError(
                "risk-driver symbols must match correlation matrix symbols"
            )

        if self.asset_returns:
            series_symbols = [series.symbol for series in self.asset_returns]
            if series_symbols != asset_symbols:
                raise ValueError(
                    "asset-return series symbols and order must match "
                    "asset metrics"
                )
            for series in self.asset_returns:
                series_dates = [point.date for point in series.points]
                if series_dates != return_dates:
                    raise ValueError(
                        "asset-return dates must match portfolio-return dates"
                    )
                if any(
                    point_date < self.start_date
                    or point_date > self.end_date
                    for point_date in series_dates
                ):
                    raise ValueError(
                        "asset return dates must fall within the inclusive "
                        "response period"
                    )

        total_weight = math.fsum(
            metric.weight for metric in self.asset_metrics
        )
        if not math.isclose(
            total_weight,
            1.0,
            rel_tol=0.0,
            abs_tol=1e-9,
        ):
            raise ValueError(
                "asset-metric weights must sum to 1.0 within an absolute "
                "tolerance of 1e-9"
            )

        pair_keys: set[frozenset[str]] = set()
        for pair in self.correlation_pairs:
            if (
                pair.asset_a not in matrix_symbols
                or pair.asset_b not in matrix_symbols
            ):
                raise ValueError(
                    "correlation pair symbols must belong to the "
                    "correlation matrix"
                )
            pair_key = frozenset((pair.asset_a, pair.asset_b))
            if pair_key in pair_keys:
                raise ValueError(
                    "duplicate unordered correlation pairs are not allowed"
                )
            pair_keys.add(pair_key)

        if self.metadata.asset_count != len(matrix_symbols):
            raise ValueError(
                "metadata asset_count must match the portfolio symbol count"
            )
        if self.metadata.return_observation_count != len(
            self.portfolio_returns
        ):
            raise ValueError(
                "metadata return_observation_count must match the number "
                "of portfolio return observations"
            )
        return self
