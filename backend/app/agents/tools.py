"""Controlled read-only Aura context tools for a future AI agent."""

from collections.abc import Sequence
from copy import deepcopy
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from ..schemas.reporting import PortfolioReportResponse
from ..schemas.simulation_history import (
    SimulationHistoryDetailResponse,
    SimulationHistoryListResponse,
)
from ..services.analysis_reporting_service import AnalysisReportingService
from ..services.portfolio_service import PortfolioService
from ..services.simulation_history_service import SimulationHistoryService


MAX_TIME_SERIES_POINTS = 25


def _reduce_time_series(
    points: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Copy a chronological series with at most 25 evenly spaced points.

    Short series are copied in full. Longer series retain their first and last
    points and use floor-spaced intermediate indexes, preserving chronological
    order without calculating or altering any financial value.
    """
    if len(points) <= MAX_TIME_SERIES_POINTS:
        return deepcopy(list(points))

    last_index = len(points) - 1
    indexes = [
        (sample_index * last_index) // (MAX_TIME_SERIES_POINTS - 1)
        for sample_index in range(MAX_TIME_SERIES_POINTS - 1)
    ]
    indexes.append(last_index)
    return deepcopy([points[index] for index in indexes])


def _project_report(report: PortfolioReportResponse) -> dict[str, Any]:
    """Return the validated report fields suitable for a grounded explanation."""
    analysis = report.analysis.model_dump(mode="json")
    return {
        "id": str(report.id),
        "portfolio_id": str(report.portfolio_id),
        "created_at": report.created_at.isoformat(),
        "analysis": {
            "portfolio_name": analysis["portfolio_name"],
            "start_date": analysis["start_date"],
            "end_date": analysis["end_date"],
            "metadata": analysis["metadata"],
            "portfolio_metrics": analysis["portfolio_metrics"],
            "max_drawdown": analysis["max_drawdown"],
            "concentration": analysis["concentration"],
            "diversification": analysis["diversification"],
            "risk_classification": analysis["risk_classification"],
            "risk_drivers": analysis["risk_drivers"],
            "asset_metrics": analysis["asset_metrics"],
            "correlation_matrix": analysis["correlation_matrix"],
            "correlation_pairs": analysis["correlation_pairs"],
            "portfolio_returns": _reduce_time_series(
                analysis["portfolio_returns"]
            ),
        },
    }


def _project_simulation(
    simulation: SimulationHistoryDetailResponse,
) -> dict[str, Any]:
    """Return one validated saved simulation with reduced trajectories only."""
    result = simulation.result.model_dump(mode="json")
    if simulation.simulation_type == "historical-scenario":
        result["trajectory"] = _reduce_time_series(result["trajectory"])
    else:
        result["original"]["trajectory"] = _reduce_time_series(
            result["original"]["trajectory"]
        )
        result["modified"]["trajectory"] = _reduce_time_series(
            result["modified"]["trajectory"]
        )

    return {
        "id": str(simulation.id),
        "portfolio_id": str(simulation.portfolio_id),
        "simulation_type": simulation.simulation_type,
        "scenario_id": simulation.scenario_id,
        "requested_start_date": simulation.requested_start_date.isoformat(),
        "requested_end_date": simulation.requested_end_date.isoformat(),
        "created_at": simulation.created_at.isoformat(),
        "result": result,
    }


class AuraAgentTools:
    """Read validated Aura context through services bound to one owned portfolio.

    The authenticated user and portfolio identifiers are accepted only at
    construction. Individual operations intentionally accept only explicit
    report or simulation selectors, preventing a future LLM from selecting a
    different user or portfolio.
    """

    def __init__(
        self,
        session: Session,
        *,
        user_id: UUID,
        portfolio_id: UUID,
    ) -> None:
        self._session = session
        self._user_id = user_id
        self._portfolio_id = portfolio_id
        self._portfolio_service = PortfolioService(session)
        self._reporting_service = AnalysisReportingService(session)
        self._simulation_history_service = SimulationHistoryService(session)

    def get_portfolio_context(self) -> dict[str, Any] | None:
        """Return ordered holdings for the bound owned portfolio, if present."""
        portfolio = self._portfolio_service.get(
            user_id=self._user_id,
            portfolio_id=self._portfolio_id,
        )
        if portfolio is None:
            return None

        return {
            "id": str(portfolio.id),
            "name": portfolio.name,
            "holdings": [
                {
                    "symbol": holding.symbol,
                    "weight": float(holding.weight),
                }
                for holding in portfolio.holdings
            ],
        }

    def get_latest_report(self) -> dict[str, Any] | None:
        """Return the newest validated report or an explicit unavailable result."""
        history = self._reporting_service.list_reports(
            user_id=self._user_id,
            portfolio_id=self._portfolio_id,
        )
        if history is None:
            return None
        if not history.reports:
            return {"available": False}

        report = self._reporting_service.get_report(
            user_id=self._user_id,
            portfolio_id=self._portfolio_id,
            report_id=history.reports[0].id,
        )
        if report is None:
            return None
        return {"available": True, "report": _project_report(report)}

    def get_report(self, report_id: UUID) -> dict[str, Any] | None:
        """Return one validated report selected within the bound portfolio."""
        report = self._reporting_service.get_report(
            user_id=self._user_id,
            portfolio_id=self._portfolio_id,
            report_id=report_id,
        )
        if report is None:
            return None
        return _project_report(report)

    def list_simulations(self) -> dict[str, Any] | None:
        """Return newest-first metadata for saved simulations of this portfolio."""
        history: SimulationHistoryListResponse | None = (
            self._simulation_history_service.list_for_portfolio(
                user_id=self._user_id,
                portfolio_id=self._portfolio_id,
            )
        )
        if history is None:
            return None

        return {
            "simulations": [
                {
                    "id": str(simulation.id),
                    "portfolio_id": str(simulation.portfolio_id),
                    "simulation_type": simulation.simulation_type,
                    "scenario_id": simulation.scenario_id,
                    "requested_start_date": (
                        simulation.requested_start_date.isoformat()
                    ),
                    "requested_end_date": (
                        simulation.requested_end_date.isoformat()
                    ),
                    "created_at": simulation.created_at.isoformat(),
                }
                for simulation in history.simulations
            ]
        }

    def get_simulation(self, simulation_id: UUID) -> dict[str, Any] | None:
        """Return one validated saved simulation within the bound portfolio."""
        simulation = self._simulation_history_service.get(
            user_id=self._user_id,
            portfolio_id=self._portfolio_id,
            simulation_id=simulation_id,
        )
        if simulation is None:
            return None
        return _project_simulation(simulation)
