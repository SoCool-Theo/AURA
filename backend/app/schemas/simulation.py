"""Strict JSON-safe contracts for historical scenario simulations."""

from datetime import date
import math
from typing import Annotated, Self
from uuid import UUID

from pydantic import Field, Strict, field_validator, model_validator

from .analytics import (
    FiniteFloat,
    MaximumDrawdownMetrics,
    NonNegativeFiniteFloat,
    PositiveInt,
)
from .common import AuraBaseModel


StrictString = Annotated[str, Strict()]


def _validate_scenario_id(value: str) -> str:
    if not value.strip():
        raise ValueError("scenario_id cannot be empty")
    if value != value.strip():
        raise ValueError(
            "scenario_id cannot contain leading or trailing whitespace"
        )
    return value


def _normalize_display_text(value: object, *, field_name: str) -> object:
    if not isinstance(value, str):
        return value

    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} cannot be empty after normalization")
    return normalized


class HistoricalScenarioResponse(AuraBaseModel):
    """One public predefined historical scenario."""

    id: StrictString
    display_name: StrictString
    description: StrictString
    requested_start_date: date
    requested_end_date: date

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        return _validate_scenario_id(value)

    @field_validator("display_name", "description", mode="before")
    @classmethod
    def normalize_display_text(
        cls,
        value: object,
        info: object,
    ) -> object:
        return _normalize_display_text(
            value,
            field_name=info.field_name,  # type: ignore[attr-defined]
        )

    @model_validator(mode="after")
    def validate_requested_dates(self) -> Self:
        if self.requested_start_date > self.requested_end_date:
            raise ValueError(
                "requested_start_date must be on or before requested_end_date"
            )
        return self


class HistoricalScenarioListResponse(AuraBaseModel):
    """A deterministically ordered catalogue of predefined scenarios."""

    scenarios: Annotated[
        list[HistoricalScenarioResponse],
        Field(min_length=1),
    ]

    @model_validator(mode="after")
    def validate_unique_ids(self) -> Self:
        scenario_ids = [scenario.id for scenario in self.scenarios]
        if len(scenario_ids) != len(set(scenario_ids)):
            raise ValueError("historical scenario IDs must be unique")
        return self


class HistoricalScenarioSimulationRequest(AuraBaseModel):
    """Select one predefined scenario by its exact stable ID."""

    scenario_id: StrictString

    @field_validator("scenario_id")
    @classmethod
    def validate_scenario_id(cls, value: str) -> str:
        return _validate_scenario_id(value)


class HistoricalScenarioSimulationMetadata(AuraBaseModel):
    """Effective aligned dates and observation counts used by simulation."""

    effective_start_date: date
    effective_end_date: date
    price_observation_count: PositiveInt
    return_observation_count: PositiveInt

    @model_validator(mode="after")
    def validate_dates_and_counts(self) -> Self:
        if self.effective_start_date > self.effective_end_date:
            raise ValueError(
                "effective_start_date must be on or before effective_end_date"
            )
        if self.return_observation_count != self.price_observation_count - 1:
            raise ValueError(
                "return_observation_count must equal "
                "price_observation_count minus one"
            )
        return self


class HistoricalScenarioTrajectoryPoint(AuraBaseModel):
    """One dated normalized portfolio value in caller-provided order."""

    date: date
    normalized_value: FiniteFloat


class HistoricalScenarioMetrics(AuraBaseModel):
    """Minimum metrics for one historical scenario simulation."""

    normalized_starting_value: FiniteFloat
    normalized_ending_value: FiniteFloat
    cumulative_return: FiniteFloat
    annualized_volatility: NonNegativeFiniteFloat
    sharpe_ratio: FiniteFloat | None
    maximum_drawdown: MaximumDrawdownMetrics

    @model_validator(mode="after")
    def validate_normalized_starting_value(self) -> Self:
        if self.normalized_starting_value != 1.0:
            raise ValueError("normalized_starting_value must equal 1.0")
        return self


class HistoricalScenarioSimulationResponse(AuraBaseModel):
    """Complete JSON-safe result for an owned saved portfolio and scenario."""

    portfolio_id: UUID
    portfolio_name: StrictString
    scenario: HistoricalScenarioResponse
    metadata: HistoricalScenarioSimulationMetadata
    metrics: HistoricalScenarioMetrics
    trajectory: Annotated[
        list[HistoricalScenarioTrajectoryPoint],
        Field(min_length=1),
    ]

    @field_validator("portfolio_name", mode="before")
    @classmethod
    def normalize_portfolio_name(cls, value: object) -> object:
        return _normalize_display_text(value, field_name="portfolio_name")

    @model_validator(mode="after")
    def validate_response_consistency(self) -> Self:
        dates = [point.date for point in self.trajectory]
        if len(dates) != len(set(dates)):
            raise ValueError("trajectory dates must be unique")
        if any(
            current <= previous
            for previous, current in zip(dates, dates[1:])
        ):
            raise ValueError("trajectory dates must be strictly increasing")

        if len(self.trajectory) != self.metadata.price_observation_count:
            raise ValueError(
                "trajectory length must match price_observation_count"
            )
        if dates[0] != self.metadata.effective_start_date:
            raise ValueError(
                "first trajectory date must match effective_start_date"
            )
        if dates[-1] != self.metadata.effective_end_date:
            raise ValueError(
                "last trajectory date must match effective_end_date"
            )
        if (
            self.metadata.effective_start_date
            < self.scenario.requested_start_date
            or self.metadata.effective_end_date
            > self.scenario.requested_end_date
        ):
            raise ValueError(
                "effective dates must fall within the requested scenario period"
            )

        if not math.isclose(
            self.trajectory[0].normalized_value,
            self.metrics.normalized_starting_value,
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            raise ValueError(
                "first trajectory value must match normalized_starting_value"
            )
        if not math.isclose(
            self.trajectory[-1].normalized_value,
            self.metrics.normalized_ending_value,
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            raise ValueError(
                "last trajectory value must match normalized_ending_value"
            )
        return self


__all__ = [
    "HistoricalScenarioResponse",
    "HistoricalScenarioListResponse",
    "HistoricalScenarioSimulationRequest",
    "HistoricalScenarioSimulationMetadata",
    "HistoricalScenarioTrajectoryPoint",
    "HistoricalScenarioMetrics",
    "HistoricalScenarioSimulationResponse",
]
