"""Orchestration for owned immutable simulation-history snapshots."""

from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from ..database.models import Simulation
from ..database.repositories import SimulationRepository
from ..schemas.simulation_history import (
    SimulationHistoryDetailResponse,
    SimulationHistoryListResponse,
    SimulationHistoryResult,
    SimulationHistorySummary,
    SimulationType,
)
from .portfolio_service import PortfolioService
from .simulation_history_mapper import (
    simulation_response_to_snapshot,
    simulation_snapshot_to_response,
    simulation_type_to_schema_version,
    validate_simulation_snapshot_consistency,
)


class SimulationNotFoundError(Exception):
    """Raised when a simulation is absent from an owned portfolio."""


def _simulation_to_summary(
    simulation: Simulation,
) -> SimulationHistorySummary:
    """Map relational history metadata without inspecting its snapshot."""
    return SimulationHistorySummary(
        id=simulation.id,
        portfolio_id=simulation.portfolio_id,
        simulation_type=simulation.simulation_type,
        scenario_id=simulation.scenario_id,
        requested_start_date=simulation.requested_start_date,
        requested_end_date=simulation.requested_end_date,
        created_at=simulation.created_at,
    )


def _simulation_to_detail(
    simulation: Simulation,
) -> SimulationHistoryDetailResponse:
    """Revalidate a stored snapshot and map its complete history envelope."""
    response = simulation_snapshot_to_response(
        simulation_type=simulation.simulation_type,
        schema_version=simulation.schema_version,
        snapshot=simulation.result_snapshot,
    )
    validate_simulation_snapshot_consistency(
        simulation_type=simulation.simulation_type,
        response=response,
        portfolio_id=simulation.portfolio_id,
        scenario_id=simulation.scenario_id,
        requested_start_date=simulation.requested_start_date,
        requested_end_date=simulation.requested_end_date,
    )
    return SimulationHistoryDetailResponse(
        **_simulation_to_summary(simulation).model_dump(),
        result=response,
    )


class SimulationHistoryService:
    """Coordinate owned simulation history without managing transactions."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._portfolio_service = PortfolioService(session)
        self._repository = SimulationRepository(session)

    def save(
        self,
        *,
        user_id: UUID,
        portfolio_id: UUID,
        simulation_type: SimulationType,
        scenario_id: str | None,
        requested_start_date: date,
        requested_end_date: date,
        response: SimulationHistoryResult,
    ) -> SimulationHistoryDetailResponse | None:
        """Persist one already-successful simulation for an owned portfolio."""
        portfolio = self._portfolio_service.get(
            user_id=user_id,
            portfolio_id=portfolio_id,
        )
        if portfolio is None:
            return None

        schema_version = simulation_type_to_schema_version(simulation_type)
        snapshot = simulation_response_to_snapshot(
            simulation_type=simulation_type,
            response=response,
        )
        validate_simulation_snapshot_consistency(
            simulation_type=simulation_type,
            response=response,
            portfolio_id=portfolio.id,
            scenario_id=scenario_id,
            requested_start_date=requested_start_date,
            requested_end_date=requested_end_date,
        )
        simulation = self._repository.create(
            portfolio_id=portfolio.id,
            simulation_type=simulation_type,
            scenario_id=scenario_id,
            requested_start_date=requested_start_date,
            requested_end_date=requested_end_date,
            schema_version=schema_version,
            result_snapshot=snapshot,
        )
        return _simulation_to_detail(simulation)

    def list_for_portfolio(
        self,
        *,
        user_id: UUID,
        portfolio_id: UUID,
    ) -> SimulationHistoryListResponse | None:
        """Return ordered metadata for one owned portfolio's simulations."""
        portfolio = self._portfolio_service.get(
            user_id=user_id,
            portfolio_id=portfolio_id,
        )
        if portfolio is None:
            return None

        simulations = self._repository.list_for_portfolio(portfolio.id)
        return SimulationHistoryListResponse(
            simulations=[
                _simulation_to_summary(simulation)
                for simulation in simulations
            ]
        )

    def get(
        self,
        *,
        user_id: UUID,
        portfolio_id: UUID,
        simulation_id: UUID,
    ) -> SimulationHistoryDetailResponse | None:
        """Return one owned simulation, distinguishing parent and item absence."""
        portfolio = self._portfolio_service.get(
            user_id=user_id,
            portfolio_id=portfolio_id,
        )
        if portfolio is None:
            return None

        simulation = self._repository.get_for_portfolio(
            portfolio_id=portfolio.id,
            simulation_id=simulation_id,
        )
        if simulation is None or simulation.portfolio_id != portfolio.id:
            raise SimulationNotFoundError("Simulation not found")
        return _simulation_to_detail(simulation)


__all__ = ["SimulationNotFoundError", "SimulationHistoryService"]
