"""Read-only composition for combined historical allocation simulations."""

from uuid import UUID

from sqlalchemy.orm import Session

from ..scenarios.definitions import (
    HistoricalScenarioDefinition,
    get_historical_scenario,
)
from ..schemas.simulation import (
    AllocationSimulationRequest,
    AllocationSimulationResponse,
    CombinedSimulationRequest,
    CombinedSimulationResponse,
)
from .allocation_simulation_service import AllocationSimulationService
from .historical_scenario_service import HistoricalScenarioNotFoundError


def _map_combined_simulation_response(
    *,
    scenario: HistoricalScenarioDefinition,
    allocation_response: AllocationSimulationResponse,
) -> CombinedSimulationResponse:
    """Compose validated scenario and allocation results without recalculation."""
    return CombinedSimulationResponse.model_validate(
        {
            "portfolio_id": allocation_response.portfolio_id,
            "portfolio_name": allocation_response.portfolio_name,
            "scenario": {
                "id": scenario.id,
                "display_name": scenario.display_name,
                "description": scenario.description,
                "requested_start_date": scenario.requested_start_date,
                "requested_end_date": scenario.requested_end_date,
            },
            "metadata": allocation_response.metadata,
            "original": allocation_response.original,
            "modified": allocation_response.modified,
            "comparison": allocation_response.comparison,
        }
    )


class CombinedSimulationService:
    """Coordinate combined simulations through existing allocation behavior."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._allocation_simulation_service = AllocationSimulationService(
            session
        )

    def run(
        self,
        *,
        user_id: UUID,
        portfolio_id: UUID,
        request: CombinedSimulationRequest,
    ) -> CombinedSimulationResponse | None:
        """Compare saved and modified allocations during one scenario."""
        scenario = get_historical_scenario(request.scenario_id)
        if scenario is None:
            raise HistoricalScenarioNotFoundError(
                "Historical scenario not found"
            )

        allocation_request = AllocationSimulationRequest(
            start_date=scenario.requested_start_date,
            end_date=scenario.requested_end_date,
            modified_allocation=request.modified_allocation,
        )
        allocation_response = self._allocation_simulation_service.run(
            user_id=user_id,
            portfolio_id=portfolio_id,
            request=allocation_request,
        )
        if allocation_response is None:
            return None

        return _map_combined_simulation_response(
            scenario=scenario,
            allocation_response=allocation_response,
        )


__all__ = ["CombinedSimulationService"]
