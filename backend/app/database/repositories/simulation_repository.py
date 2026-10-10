"""Persistence operations for immutable Aura simulation snapshots."""

from copy import deepcopy
from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Simulation


class SimulationRepository:
    """Persist simulation snapshots within a caller-owned session."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        portfolio_id: UUID,
        simulation_type: str,
        scenario_id: str | None,
        requested_start_date: date,
        requested_end_date: date,
        schema_version: str,
        result_snapshot: dict[str, Any],
    ) -> Simulation:
        """Add one independent snapshot copy without committing."""
        simulation = Simulation(
            portfolio_id=portfolio_id,
            simulation_type=simulation_type,
            scenario_id=scenario_id,
            requested_start_date=requested_start_date,
            requested_end_date=requested_end_date,
            schema_version=schema_version,
            result_snapshot=deepcopy(result_snapshot),
        )
        self._session.add(simulation)
        self._session.flush()
        return simulation

    def list_for_portfolio(self, portfolio_id: UUID) -> list[Simulation]:
        """Return one portfolio's newest simulations deterministically."""
        statement = (
            select(Simulation)
            .where(Simulation.portfolio_id == portfolio_id)
            .order_by(Simulation.created_at.desc(), Simulation.id)
        )
        return list(self._session.scalars(statement).all())

    def get_for_portfolio(
        self,
        *,
        portfolio_id: UUID,
        simulation_id: UUID,
    ) -> Simulation | None:
        """Return one portfolio-scoped simulation, or ``None`` if absent."""
        statement = select(Simulation).where(
            Simulation.portfolio_id == portfolio_id,
            Simulation.id == simulation_id,
        )
        return self._session.scalar(statement)

    def delete(self, simulation: Simulation) -> None:
        """Remove one already-scoped snapshot without committing."""
        self._session.delete(simulation)
        self._session.flush()
