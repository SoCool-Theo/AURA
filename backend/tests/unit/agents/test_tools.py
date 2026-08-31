from copy import deepcopy
from datetime import UTC, datetime
from decimal import Decimal
import json
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest
from sqlalchemy.orm import Session

from backend.app.agents.tools import (
    MAX_TIME_SERIES_POINTS,
    AuraAgentTools,
    _reduce_time_series,
)
from backend.app.database.models import Holding, Portfolio
from backend.app.schemas.reporting import PortfolioReportListResponse, PortfolioReportResponse
from backend.app.schemas.simulation_history import (
    SimulationHistoryDetailResponse,
    SimulationHistoryListResponse,
)
from backend.app.services.analysis_reporting_service import ReportNotFoundError
from backend.app.services.simulation_history_service import SimulationNotFoundError
import backend.app.agents.tools as tools_module
from backend.tests.unit.schemas.test_reporting import _valid_report_data
from backend.tests.unit.schemas.test_simulation_history import (
    _response_for_type,
    _summary_payload,
)


_USER_ID = UUID("30000000-0000-0000-0000-000000000001")
_PORTFOLIO_ID = UUID("20000000-0000-0000-0000-000000000001")
_REPORT_ID = UUID("10000000-0000-0000-0000-000000000001")
_SIMULATION_ID = UUID("40000000-0000-0000-0000-000000000001")


def _portfolio() -> Portfolio:
    portfolio = Portfolio(
        id=_PORTFOLIO_ID,
        user_id=_USER_ID,
        name="Learning Portfolio",
    )
    portfolio.holdings.extend(
        [
            Holding(
                portfolio_id=_PORTFOLIO_ID,
                symbol="BND",
                weight=Decimal("0"),
                position=0,
            ),
            Holding(
                portfolio_id=_PORTFOLIO_ID,
                symbol="AAPL",
                weight=Decimal("1.0"),
                position=1,
            ),
        ]
    )
    return portfolio


def _report() -> PortfolioReportResponse:
    data = _valid_report_data()
    data["id"] = str(_REPORT_ID)
    data["portfolio_id"] = str(_PORTFOLIO_ID)
    analysis = data["analysis"]
    assert isinstance(analysis, dict)
    asset_metrics = analysis["asset_metrics"]
    assert isinstance(asset_metrics, list)
    assert isinstance(asset_metrics[0], dict)
    asset_metrics[0]["sharpe_ratio"] = None
    risk_drivers = analysis["risk_drivers"]
    assert isinstance(risk_drivers, dict)
    entries = risk_drivers["entries"]
    assert isinstance(entries, list)
    assert isinstance(entries[0], dict)
    entries[0]["component_volatility_contribution"] = -0.25
    return PortfolioReportResponse.model_validate(data)


def _simulation_detail(simulation_type: str) -> SimulationHistoryDetailResponse:
    payload = _summary_payload(
        simulation_type,
        simulation_id=str(_SIMULATION_ID),
    )
    payload["portfolio_id"] = str(_PORTFOLIO_ID)
    result = _response_for_type(simulation_type).model_dump(mode="json")
    result["portfolio_id"] = str(_PORTFOLIO_ID)
    payload["result"] = result
    return SimulationHistoryDetailResponse.model_validate(payload)


def _tools_with_services() -> tuple[
    AuraAgentTools,
    MagicMock,
    MagicMock,
    MagicMock,
    MagicMock,
]:
    session = MagicMock(spec=Session)
    portfolio_service = MagicMock()
    reporting_service = MagicMock()
    simulation_service = MagicMock()
    with (
        patch.object(
            tools_module,
            "PortfolioService",
            return_value=portfolio_service,
        ),
        patch.object(
            tools_module,
            "AnalysisReportingService",
            return_value=reporting_service,
        ),
        patch.object(
            tools_module,
            "SimulationHistoryService",
            return_value=simulation_service,
        ),
    ):
        tools = AuraAgentTools(
            session,
            user_id=_USER_ID,
            portfolio_id=_PORTFOLIO_ID,
        )
    return tools, session, portfolio_service, reporting_service, simulation_service


def _assert_session_lifecycle_untouched(session: MagicMock) -> None:
    session.commit.assert_not_called()
    session.rollback.assert_not_called()
    session.close.assert_not_called()


def test_portfolio_context_uses_bound_identity_and_projects_ordered_holdings() -> None:
    tools, session, portfolio_service, _, _ = _tools_with_services()
    portfolio = _portfolio()
    portfolio_service.get.return_value = portfolio

    context = tools.get_portfolio_context()

    portfolio_service.get.assert_called_once_with(
        user_id=_USER_ID,
        portfolio_id=_PORTFOLIO_ID,
    )
    assert context == {
        "id": str(_PORTFOLIO_ID),
        "name": "Learning Portfolio",
        "holdings": [
            {"symbol": "BND", "weight": 0.0},
            {"symbol": "AAPL", "weight": 1.0},
        ],
    }
    assert context is not portfolio
    assert all(not isinstance(value, Holding) for value in context["holdings"])
    json.dumps(context)
    _assert_session_lifecycle_untouched(session)


def test_portfolio_context_preserves_service_not_found_result() -> None:
    tools, _, portfolio_service, _, _ = _tools_with_services()
    portfolio_service.get.return_value = None

    assert tools.get_portfolio_context() is None


def test_latest_report_uses_newest_summary_then_validated_detail() -> None:
    tools, session, _, reporting_service, _ = _tools_with_services()
    report = _report()
    reporting_service.list_reports.return_value = PortfolioReportListResponse(
        reports=[
            {"id": _REPORT_ID, "portfolio_id": _PORTFOLIO_ID, "start_date": "2026-01-01", "end_date": "2026-01-31", "created_at": "2026-08-20T09:30:00+00:00"},
            {"id": uuid4(), "portfolio_id": _PORTFOLIO_ID, "start_date": "2025-01-01", "end_date": "2025-01-31", "created_at": "2026-08-19T09:30:00+00:00"},
        ]
    )
    reporting_service.get_report.return_value = report

    context = tools.get_latest_report()

    reporting_service.list_reports.assert_called_once_with(
        user_id=_USER_ID,
        portfolio_id=_PORTFOLIO_ID,
    )
    reporting_service.get_report.assert_called_once_with(
        user_id=_USER_ID,
        portfolio_id=_PORTFOLIO_ID,
        report_id=_REPORT_ID,
    )
    reporting_service.create_report.assert_not_called()
    assert context is not None
    assert context["available"] is True
    assert context["report"]["id"] == str(_REPORT_ID)
    _assert_session_lifecycle_untouched(session)


def test_latest_report_returns_explicit_unavailable_context_when_history_is_empty() -> None:
    tools, _, _, reporting_service, _ = _tools_with_services()
    reporting_service.list_reports.return_value = PortfolioReportListResponse(
        reports=[]
    )

    assert tools.get_latest_report() == {"available": False}
    reporting_service.get_report.assert_not_called()
    reporting_service.create_report.assert_not_called()


def test_latest_report_preserves_missing_portfolio_result() -> None:
    tools, _, _, reporting_service, _ = _tools_with_services()
    reporting_service.list_reports.return_value = None

    assert tools.get_latest_report() is None
    reporting_service.get_report.assert_not_called()


def test_specific_report_uses_bound_identity_and_preserves_not_found_error() -> None:
    tools, _, _, reporting_service, _ = _tools_with_services()
    report = _report()
    reporting_service.get_report.return_value = report

    context = tools.get_report(_REPORT_ID)

    reporting_service.get_report.assert_called_once_with(
        user_id=_USER_ID,
        portfolio_id=_PORTFOLIO_ID,
        report_id=_REPORT_ID,
    )
    assert context["analysis"]["risk_classification"] == report.analysis.model_dump(
        mode="json"
    )["risk_classification"]

    reporting_service.get_report.side_effect = ReportNotFoundError
    with pytest.raises(ReportNotFoundError):
        tools.get_report(_REPORT_ID)


def test_report_projection_preserves_authoritative_signed_and_nullable_values() -> None:
    tools, _, _, reporting_service, _ = _tools_with_services()
    report = _report()
    source_before = report.model_dump(mode="python")
    reporting_service.get_report.return_value = report

    context = tools.get_report(_REPORT_ID)

    assert context is not None
    assert context["analysis"]["max_drawdown"]["max_drawdown"] < 0
    assert context["analysis"]["risk_drivers"]["entries"][0][
        "component_volatility_contribution"
    ] == -0.25
    assert context["analysis"]["asset_metrics"][0]["sharpe_ratio"] is None
    assert report.model_dump(mode="python") == source_before


def test_simulation_list_uses_bound_identity_and_preserves_newest_first_order() -> None:
    tools, session, _, _, simulation_service = _tools_with_services()
    newest = _simulation_detail("combined")
    older = _simulation_detail("allocation")
    older.id = uuid4()
    simulation_service.list_for_portfolio.return_value = SimulationHistoryListResponse(
        simulations=[newest, older]
    )

    context = tools.list_simulations()

    simulation_service.list_for_portfolio.assert_called_once_with(
        user_id=_USER_ID,
        portfolio_id=_PORTFOLIO_ID,
    )
    assert context is not None
    assert [item["id"] for item in context["simulations"]] == [
        str(newest.id),
        str(older.id),
    ]
    assert context["simulations"][0]["simulation_type"] == "combined"
    assert context["simulations"][0]["scenario_id"] == "covid-19-shock-2020"
    _assert_session_lifecycle_untouched(session)


@pytest.mark.parametrize(
    "simulation_type",
    ["historical-scenario", "allocation", "combined"],
)
def test_specific_simulation_projects_each_validated_type(simulation_type: str) -> None:
    tools, _, _, _, simulation_service = _tools_with_services()
    simulation = _simulation_detail(simulation_type)
    source_before = simulation.model_dump(mode="python")
    simulation_service.get.return_value = simulation

    context = tools.get_simulation(_SIMULATION_ID)

    simulation_service.get.assert_called_once_with(
        user_id=_USER_ID,
        portfolio_id=_PORTFOLIO_ID,
        simulation_id=_SIMULATION_ID,
    )
    assert context is not None
    assert context["simulation_type"] == simulation_type
    assert context["result"]["portfolio_id"] == str(_PORTFOLIO_ID)
    assert simulation.model_dump(mode="python") == source_before


def test_specific_simulation_preserves_not_found_error_and_never_runs_simulation() -> None:
    tools, _, _, _, simulation_service = _tools_with_services()
    simulation_service.get.side_effect = SimulationNotFoundError("Simulation not found")

    with pytest.raises(SimulationNotFoundError):
        tools.get_simulation(_SIMULATION_ID)

    assert not hasattr(tools, "run_simulation")
    assert not hasattr(tools, "save_simulation")
    assert not hasattr(tools_module, "AnalysisService")


def test_simulation_projection_preserves_negative_drawdown_none_sharpe_and_deltas() -> None:
    tools, _, _, _, simulation_service = _tools_with_services()
    simulation = _simulation_detail("combined")
    simulation_service.get.return_value = simulation

    context = tools.get_simulation(_SIMULATION_ID)

    assert context is not None
    assert context["result"]["original"]["metrics"]["maximum_drawdown"][
        "max_drawdown"
    ] < 0
    assert context["result"]["comparison"] == simulation.result.comparison.model_dump(
        mode="json"
    )


def test_time_series_reduction_keeps_short_series_and_copies_input() -> None:
    points = [{"date": f"2026-01-{index:02d}", "value": index} for index in range(1, 4)]
    before = deepcopy(points)

    reduced = _reduce_time_series(points)

    assert reduced == points
    assert reduced is not points
    assert reduced[0] is not points[0]
    assert points == before


def test_time_series_reduction_is_capped_chronological_and_endpoint_preserving() -> None:
    points = [
        {"date": f"2026-01-{index:03d}", "value": index}
        for index in range(40)
    ]
    before = deepcopy(points)

    reduced = _reduce_time_series(points)

    assert len(reduced) == MAX_TIME_SERIES_POINTS
    assert reduced[0] == points[0]
    assert reduced[-1] == points[-1]
    assert [point["value"] for point in reduced] == sorted(
        point["value"] for point in reduced
    )
    assert points == before


def test_tool_identity_cannot_be_overridden_and_no_unsafe_capabilities_exist() -> None:
    tools, _, _, _, _ = _tools_with_services()

    with pytest.raises(TypeError):
        tools.get_portfolio_context(user_id=uuid4())  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        tools.list_simulations(portfolio_id=uuid4())  # type: ignore[call-arg]

    for name in (
        "execute_sql",
        "query_database",
        "raw_market_data",
        "run_python",
        "run_shell",
        "read_file",
        "fetch_url",
    ):
        assert not hasattr(tools, name)
