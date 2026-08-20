"""Strict contracts for immutable Aura simulation-history retrieval."""

from datetime import date
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import AwareDatetime, Strict, field_validator, model_validator

from .common import AuraBaseModel
from .simulation import (
    AllocationSimulationResponse,
    CombinedSimulationResponse,
    HistoricalScenarioSimulationResponse,
    _validate_scenario_id,
)


SimulationType = Literal[
    "historical-scenario",
    "allocation",
    "combined",
]
SimulationHistoryResult = (
    HistoricalScenarioSimulationResponse
    | AllocationSimulationResponse
    | CombinedSimulationResponse
)
StrictString = Annotated[str, Strict()]


class SimulationHistorySummary(AuraBaseModel):
    """Relational metadata for one immutable simulation snapshot."""

    id: UUID
    portfolio_id: UUID
    simulation_type: SimulationType
    scenario_id: StrictString | None
    requested_start_date: date
    requested_end_date: date
    created_at: AwareDatetime

    @field_validator("scenario_id")
    @classmethod
    def validate_scenario_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _validate_scenario_id(value)

    @model_validator(mode="after")
    def validate_metadata(self) -> Self:
        if self.requested_start_date > self.requested_end_date:
            raise ValueError(
                "requested_start_date must be on or before "
                "requested_end_date"
            )

        if self.simulation_type == "allocation":
            if self.scenario_id is not None:
                raise ValueError(
                    "scenario_id must be null for allocation simulations"
                )
        elif self.scenario_id is None:
            raise ValueError(
                "scenario_id is required for historical-scenario and "
                "combined simulations"
            )
        return self


class SimulationHistoryListResponse(AuraBaseModel):
    """An ordered collection of simulation-history summaries."""

    simulations: list[SimulationHistorySummary]


class SimulationHistoryDetailResponse(SimulationHistorySummary):
    """Simulation-history metadata and its canonical validated result."""

    result: SimulationHistoryResult

    @model_validator(mode="after")
    def validate_result_type(self) -> Self:
        expected_type = {
            "historical-scenario": HistoricalScenarioSimulationResponse,
            "allocation": AllocationSimulationResponse,
            "combined": CombinedSimulationResponse,
        }[self.simulation_type]
        if not isinstance(self.result, expected_type):
            raise ValueError(
                "result response type does not match simulation_type"
            )
        return self


__all__ = [
    "SimulationType",
    "SimulationHistoryResult",
    "SimulationHistorySummary",
    "SimulationHistoryListResponse",
    "SimulationHistoryDetailResponse",
]
