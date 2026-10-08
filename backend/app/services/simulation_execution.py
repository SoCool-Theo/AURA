"""Internal immutable context returned by simulation orchestration."""

from dataclasses import dataclass
from typing import Generic, TypeVar

from ..schemas.simulation import (
    AllocationSimulationResponse,
    CombinedSimulationResponse,
    HistoricalScenarioSimulationResponse,
)
from .portfolio_baseline_resolver import PortfolioBaselineResolution


SimulationResponse = (
    HistoricalScenarioSimulationResponse
    | AllocationSimulationResponse
    | CombinedSimulationResponse
)
_SimulationResponseT = TypeVar("_SimulationResponseT", bound=SimulationResponse)


@dataclass(frozen=True, slots=True)
class SimulationExecutionResult(Generic[_SimulationResponseT]):
    """Live-compatible response plus its immutable original baseline."""

    response: _SimulationResponseT
    baseline: PortfolioBaselineResolution


__all__ = ["SimulationExecutionResult", "SimulationResponse"]
