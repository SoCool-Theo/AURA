"""Controlled read-only Aura context tools for the grounded AI agent."""

from collections.abc import Sequence
from copy import deepcopy
from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from ..database.models import Portfolio, PortfolioType
from ..schemas.portfolio import PLANNED_PORTFOLIO_HYPOTHETICAL_NOTICE
from ..schemas.reporting import (
    PortfolioReportDetailResponse,
    PortfolioReportV2Response,
    PortfolioReportV3Response,
)
from ..schemas.simulation_history import (
    SimulationHistoryDetail,
    SimulationHistoryListResponse,
    SimulationHistoryV2DetailResponse,
    SimulationHistoryV3DetailResponse,
)
from ..services.analysis_reporting_service import AnalysisReportingService
from ..services.portfolio_baseline_resolver import (
    PortfolioBaselineKind,
    PortfolioBaselineResolutionService,
)
from ..services.portfolio_service import PortfolioService
from ..services.portfolio_valuation_service import PortfolioDisplayCurrency
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


def _project_report(report: PortfolioReportDetailResponse) -> dict[str, Any]:
    """Return the validated report fields suitable for a grounded explanation."""
    analysis = report.analysis.model_dump(mode="json")
    projected = {
        "id": str(report.id),
        "portfolio_id": str(report.portfolio_id),
        "created_at": report.created_at.isoformat(),
        "schema_version": getattr(
            report,
            "schema_version",
            "portfolio-analysis-response-v1",
        ),
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
    if isinstance(report, PortfolioReportV2Response):
        projected["portfolio_type"] = PortfolioType.CURRENT.value
        projected["baseline_source"] = "current-valuation"
        projected["valuation"] = report.valuation.model_dump(mode="json")
        projected["holdings"] = [
            _without_internal_id(holding.model_dump(mode="json"))
            for holding in report.holdings
        ]
    elif isinstance(report, PortfolioReportV3Response):
        projected["portfolio_type"] = PortfolioType.PLANNED.value
        projected["baseline_source"] = (
            "proposed-amount-target-allocation"
        )
        baseline = report.baseline.model_dump(mode="json")
        baseline["holdings"] = [
            _without_internal_id(holding)
            for holding in baseline["holdings"]
        ]
        projected["baseline"] = baseline
    else:
        projected["portfolio_type"] = PortfolioType.LEGACY.value
        projected["baseline_source"] = "saved-weights"
    return projected


def _project_simulation(
    simulation: SimulationHistoryDetail,
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

    projected = {
        "id": str(simulation.id),
        "portfolio_id": str(simulation.portfolio_id),
        "simulation_type": simulation.simulation_type,
        "scenario_id": simulation.scenario_id,
        "requested_start_date": simulation.requested_start_date.isoformat(),
        "requested_end_date": simulation.requested_end_date.isoformat(),
        "created_at": simulation.created_at.isoformat(),
        "schema_version": getattr(
            simulation,
            "schema_version",
            f"{simulation.simulation_type}-simulation-response-v1",
        ),
        "result": result,
    }
    if isinstance(simulation, SimulationHistoryV2DetailResponse):
        projected["portfolio_type"] = PortfolioType.CURRENT.value
        projected["baseline_source"] = "current-valuation"
    elif isinstance(simulation, SimulationHistoryV3DetailResponse):
        projected["portfolio_type"] = PortfolioType.PLANNED.value
        projected["baseline_source"] = (
            "proposed-amount-target-allocation"
        )
    else:
        projected["portfolio_type"] = PortfolioType.LEGACY.value
        projected["baseline_source"] = "saved-weights"
    if isinstance(
        simulation,
        (
            SimulationHistoryV2DetailResponse,
            SimulationHistoryV3DetailResponse,
        ),
    ):
        baseline = simulation.baseline.model_dump(mode="json")
        baseline["holdings"] = [
            _without_internal_id(holding)
            for holding in baseline["holdings"]
        ]
        projected["baseline"] = baseline
    return projected


def _without_internal_id(payload: dict[str, Any]) -> dict[str, Any]:
    """Copy a validated context object without its internal holding ID."""
    projected = deepcopy(payload)
    projected.pop("id", None)
    return projected


def _project_persisted_portfolio(portfolio: Portfolio) -> dict[str, Any]:
    """Return safe portfolio identity plus legacy weights when available.

    A selected immutable V2 or V3 report/simulation owns its authoritative
    baseline. Current or planned holding facts are intentionally omitted so
    they cannot conflict with frozen context after a portfolio edit.
    """
    projected: dict[str, Any] = {
        "id": str(portfolio.id),
        "name": portfolio.name,
    }
    holdings = tuple(portfolio.holdings)
    if holdings and all(
        holding.weight is not None
        and holding.proposed_amount is None
        and holding.invested_amount is None
        and holding.invested_currency is None
        and holding.shares is None
        and holding.purchase_date is None
        for holding in holdings
    ):
        projected["portfolio_type"] = PortfolioType.LEGACY.value
        projected["baseline_source"] = "saved-weights"
        projected["holdings"] = [
            {
                "symbol": holding.symbol,
                "weight": float(holding.weight),
            }
            for holding in holdings
        ]
    elif portfolio.portfolio_type == PortfolioType.PLANNED.value:
        projected["portfolio_type"] = PortfolioType.PLANNED.value
    else:
        projected["portfolio_type"] = PortfolioType.CURRENT.value
    return projected


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
        valuation_date: date,
    ) -> None:
        if type(valuation_date) is not date:
            raise TypeError("valuation_date must be a date")
        self._session = session
        self._user_id = user_id
        self._portfolio_id = portfolio_id
        self._valuation_date = valuation_date
        self._portfolio_service = PortfolioService(session)
        self._baseline_resolver = PortfolioBaselineResolutionService(session)
        self._reporting_service = AnalysisReportingService(session)
        self._simulation_history_service = SimulationHistoryService(session)

    def get_portfolio_context(
        self,
        *,
        resolve_current_baseline: bool = True,
    ) -> dict[str, Any] | None:
        """Return ordered holdings for the bound owned portfolio, if present."""
        portfolio = self._portfolio_service.get(
            user_id=self._user_id,
            portfolio_id=self._portfolio_id,
        )
        if portfolio is None:
            return None

        if not resolve_current_baseline:
            return _project_persisted_portfolio(portfolio)

        baseline = self._baseline_resolver.resolve(
            portfolio=portfolio,
            valuation_date=self._valuation_date,
            display_currency=PortfolioDisplayCurrency.USD,
        )
        if baseline.baseline_kind is PortfolioBaselineKind.LEGACY:
            return {
                "id": str(portfolio.id),
                "name": portfolio.name,
                "portfolio_type": PortfolioType.LEGACY.value,
                "baseline_source": "saved-weights",
                "holdings": [
                    {
                        "symbol": holding.symbol,
                        "weight": float(holding.weight),
                    }
                    for holding in baseline.resolved_weights
                ],
            }

        if baseline.baseline_kind is PortfolioBaselineKind.PLANNED:
            allocation = baseline.planned_allocation
            if allocation is None or baseline.valuation is not None:
                raise ValueError(
                    "planned AI portfolio baseline is inconsistent"
                )
            if len(baseline.resolved_weights) != len(allocation.holdings):
                raise ValueError(
                    "planned AI portfolio baseline is inconsistent"
                )
            holdings: list[dict[str, Any]] = []
            for resolved, holding in zip(
                baseline.resolved_weights,
                allocation.holdings,
                strict=True,
            ):
                if (
                    resolved.symbol != holding.symbol
                    or resolved.weight != holding.target_allocation
                ):
                    raise ValueError(
                        "planned AI portfolio baseline is inconsistent"
                    )
                holdings.append(
                    {
                        "symbol": holding.symbol,
                        "proposed_amount": str(holding.proposed_amount),
                        "target_allocation": str(
                            holding.target_allocation
                        ),
                        "position": holding.position,
                    }
                )
            return {
                "id": str(portfolio.id),
                "name": portfolio.name,
                "portfolio_type": PortfolioType.PLANNED.value,
                "baseline_source": (
                    "proposed-amount-target-allocation"
                ),
                "plan_currency": allocation.plan_currency,
                "total_proposed_amount": str(
                    allocation.total_proposed_amount
                ),
                "hypothetical_notice": (
                    PLANNED_PORTFOLIO_HYPOTHETICAL_NOTICE
                ),
                "holdings": holdings,
            }

        valuation = baseline.valuation
        if valuation is None:
            raise ValueError("real AI portfolio baseline requires valuation")
        if len(baseline.resolved_weights) != len(valuation.holdings):
            raise ValueError("real AI portfolio baseline is inconsistent")

        holdings: list[dict[str, Any]] = []
        for resolved, holding in zip(
            baseline.resolved_weights,
            valuation.holdings,
            strict=True,
        ):
            if (
                resolved.symbol != holding.symbol
                or resolved.weight != holding.current_allocation
            ):
                raise ValueError("real AI portfolio baseline is inconsistent")
            holdings.append(
                {
                    "symbol": holding.symbol,
                    "weight": float(resolved.weight),
                    "invested_amount": (
                        None
                        if holding.invested_amount is None
                        else str(holding.invested_amount)
                    ),
                    "invested_currency": holding.invested_currency,
                    "shares": str(holding.shares),
                    "purchase_date": (
                        None
                        if holding.purchase_date is None
                        else holding.purchase_date.isoformat()
                    ),
                    "position": holding.position,
                    "asset_price": str(holding.asset_price),
                    "asset_quote_currency": holding.asset_quote_currency,
                    "price_as_of": holding.price_as_of.isoformat(),
                    "current_value_usd": str(holding.current_value_usd),
                    "current_allocation": str(holding.current_allocation),
                }
            )

        return {
            "id": str(portfolio.id),
            "name": portfolio.name,
            "portfolio_type": PortfolioType.CURRENT.value,
            "baseline_source": "current-valuation",
            "valuation": {
                "valuation_currency": "USD",
                "valuation_date": valuation.requested_date.isoformat(),
                "oldest_price_as_of": valuation.oldest_price_as_of.isoformat(),
                "newest_price_as_of": valuation.newest_price_as_of.isoformat(),
                "total_current_value_usd": str(
                    valuation.total_current_value_usd
                ),
            },
            "holdings": holdings,
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
