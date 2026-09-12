"""Orchestration for owned immutable simulation-history snapshots."""

from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from ..database.models import Simulation
from ..database.repositories import SimulationRepository
from ..schemas.simulation_history import (
    SimulationHistoryDetail,
    SimulationHistoryDetailResponse,
    SimulationHistoryListResponse,
    SimulationHistoryResult,
    SimulationHistorySummary,
    SimulationHistoryV2DetailResponse,
    SimulationType,
)
from .portfolio_baseline_resolver import (
    PortfolioBaselineKind,
    PortfolioBaselineResolution,
)
from .portfolio_service import PortfolioService
from .simulation_history_mapper import (
    simulation_response_to_snapshot,
    simulation_response_to_v2_snapshot,
    simulation_type_to_schema_version,
    simulation_type_to_v2_schema_version,
    restore_simulation_snapshot,
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
) -> SimulationHistoryDetail:
    """Revalidate a stored snapshot and map its complete history envelope."""
    restored = restore_simulation_snapshot(
        simulation_type=simulation.simulation_type,
        schema_version=simulation.schema_version,
        snapshot=simulation.result_snapshot,
    )
    validate_simulation_snapshot_consistency(
        simulation_type=simulation.simulation_type,
        response=restored.response,
        portfolio_id=simulation.portfolio_id,
        scenario_id=simulation.scenario_id,
        requested_start_date=simulation.requested_start_date,
        requested_end_date=simulation.requested_end_date,
    )
    summary = _simulation_to_summary(simulation).model_dump()
    if restored.baseline is None:
        return SimulationHistoryDetailResponse(
            **summary,
            result=restored.response,
        )
    return SimulationHistoryV2DetailResponse(
        **summary,
        schema_version=restored.schema_version,
        baseline=restored.baseline,
        result=restored.response,
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
        baseline: PortfolioBaselineResolution | None = None,
    ) -> SimulationHistoryDetail | None:
        """Persist one already-successful simulation for an owned portfolio."""
        portfolio = self._portfolio_service.get(
            user_id=user_id,
            portfolio_id=portfolio_id,
        )
        if portfolio is None:
            return None

        if (
            baseline is not None
            and baseline.baseline_kind is PortfolioBaselineKind.REAL
        ):
            if baseline.valuation is None:
                raise ValueError("real simulation baseline requires valuation")
            schema_version = simulation_type_to_v2_schema_version(
                simulation_type
            )
            snapshot = simulation_response_to_v2_snapshot(
                simulation_type=simulation_type,
                response=response,
                valuation=baseline.valuation,
            )
        else:
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
    ) -> SimulationHistoryDetail | None:
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
