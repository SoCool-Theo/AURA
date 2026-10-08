from copy import deepcopy
from datetime import UTC, date, datetime
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
from backend.app.database.models import Holding, Portfolio, PortfolioType
from backend.app.schemas.reporting import (
    PortfolioReportListResponse,
    PortfolioReportResponse,
    PortfolioReportV2Response,
    PortfolioReportV3Response,
)
from backend.app.schemas.simulation_history import (
    SimulationBaselineHolding,
    SimulationBaselineValuationContext,
    SimulationHistoryDetailResponse,
    SimulationHistoryListResponse,
    SimulationHistoryV2DetailResponse,
    SimulationHistoryV3DetailResponse,
)
from backend.app.schemas.portfolio import PlannedPortfolioBaselineContext
from backend.app.services.analysis_reporting_service import ReportNotFoundError
from backend.app.services.market_data_service import MarketDataUnavailableError
from backend.app.services.portfolio_valuation_service import (
    PortfolioDisplayCurrency,
    PortfolioValuationService,
)
from backend.app.services.simulation_history_service import SimulationNotFoundError
import backend.app.agents.tools as tools_module
from backend.tests.unit.schemas.test_reporting import (
    _valid_report_data,
    _valid_v2_report_data,
    _valid_v3_report_data,
)
from backend.tests.unit.schemas.test_simulation_history import (
    _response_for_type,
    _summary_payload,
)
from backend.tests.unit.services.test_portfolio_analysis_preparation_service import (
    _valuation_result,
)


_USER_ID = UUID("30000000-0000-0000-0000-000000000001")
_PORTFOLIO_ID = UUID("20000000-0000-0000-0000-000000000001")
_REPORT_ID = UUID("10000000-0000-0000-0000-000000000001")
_SIMULATION_ID = UUID("40000000-0000-0000-0000-000000000001")
_VALUATION_DATE = date(2026, 9, 12)


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


def _real_portfolio() -> Portfolio:
    portfolio = Portfolio(
        id=_PORTFOLIO_ID,
        user_id=_USER_ID,
        name="Real Holdings",
    )
    portfolio.holdings.extend(
        [
            Holding(
                id=UUID("53000000-0000-0000-0000-000000000001"),
                portfolio_id=_PORTFOLIO_ID,
                symbol="AAPL",
                weight=None,
                invested_amount=Decimal("999999.000000000000"),
                invested_currency="THB",
                shares=Decimal("1.000000000000"),
                purchase_date=date(2026, 1, 1),
                position=0,
            ),
            Holding(
                id=UUID("53000000-0000-0000-0000-000000000002"),
                portfolio_id=_PORTFOLIO_ID,
                symbol="BND",
                weight=None,
                invested_amount=Decimal("999999.000000000000"),
                invested_currency="USD",
                shares=Decimal("1.000000000000"),
                purchase_date=date(2026, 1, 2),
                position=1,
            ),
        ]
    )
    return portfolio


def _planned_portfolio() -> Portfolio:
    portfolio = Portfolio(
        id=_PORTFOLIO_ID,
        user_id=_USER_ID,
        name="Planned Portfolio",
        portfolio_type=PortfolioType.PLANNED.value,
        plan_currency="USD",
    )
    portfolio.holdings.extend(
        [
            Holding(
                id=UUID("53000000-0000-0000-0000-000000000001"),
                portfolio_id=_PORTFOLIO_ID,
                symbol="AAPL",
                proposed_amount=Decimal("600"),
                position=0,
            ),
            Holding(
                id=UUID("53000000-0000-0000-0000-000000000002"),
                portfolio_id=_PORTFOLIO_ID,
                symbol="BND",
                proposed_amount=Decimal("400"),
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


def _v2_simulation_detail() -> SimulationHistoryV2DetailResponse:
    payload = _summary_payload(
        "allocation",
        simulation_id=str(_SIMULATION_ID),
    )
    payload["portfolio_id"] = str(_PORTFOLIO_ID)
    result = _response_for_type("allocation").model_dump(mode="json")
    result["portfolio_id"] = str(_PORTFOLIO_ID)
    return SimulationHistoryV2DetailResponse(
        **payload,
        schema_version="allocation-simulation-response-v2",
        result=result,
        baseline=SimulationBaselineValuationContext(
            valuation_currency="USD",
            valuation_date=_VALUATION_DATE,
            oldest_price_as_of=_VALUATION_DATE,
            newest_price_as_of=_VALUATION_DATE,
            total_current_value_usd="100",
            holdings=[
                SimulationBaselineHolding(
                    id=UUID("53000000-0000-0000-0000-000000000001"),
                    symbol="AAPL",
                    invested_amount="999999",
                    invested_currency="THB",
                    shares="1",
                    purchase_date=date(2026, 1, 1),
                    position=0,
                    asset_price="100",
                    asset_quote_currency="USD",
                    price_as_of=_VALUATION_DATE,
                    current_value_usd="60",
                    current_allocation="0.6",
                ),
                SimulationBaselineHolding(
                    id=UUID("53000000-0000-0000-0000-000000000002"),
                    symbol="BND",
                    invested_amount="999999",
                    invested_currency="USD",
                    shares="1",
                    purchase_date=date(2026, 1, 2),
                    position=1,
                    asset_price="100",
                    asset_quote_currency="USD",
                    price_as_of=_VALUATION_DATE,
                    current_value_usd="40",
                    current_allocation="0.4",
                ),
            ],
        ),
    )


def _v3_simulation_detail() -> SimulationHistoryV3DetailResponse:
    payload = _summary_payload(
        "allocation",
        simulation_id=str(_SIMULATION_ID),
    )
    payload["portfolio_id"] = str(_PORTFOLIO_ID)
    result = _response_for_type("allocation").model_dump(mode="json")
    result["portfolio_id"] = str(_PORTFOLIO_ID)
    return SimulationHistoryV3DetailResponse(
        **payload,
        schema_version="allocation-simulation-response-v3",
        result=result,
        baseline=PlannedPortfolioBaselineContext(
            portfolio_type="PLANNED",
            baseline_source="proposed-amount-target-allocation",
            plan_currency="USD",
            total_proposed_amount="1000",
            hypothetical_notice=(
                "Hypothetical historical analysis only; not a forecast, "
                "recommendation, or executable order."
            ),
            holdings=[
                {
                    "id": "53000000-0000-0000-0000-000000000001",
                    "symbol": "MSFT",
                    "proposed_amount": "600",
                    "target_allocation": "0.6",
                    "position": 0,
                },
                {
                    "id": "53000000-0000-0000-0000-000000000002",
                    "symbol": "AAPL",
                    "proposed_amount": "400",
                    "target_allocation": "0.4",
                    "position": 1,
                },
            ],
        ),
    )


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
            valuation_date=_VALUATION_DATE,
        )
    valuation_service = MagicMock(spec=PortfolioValuationService)
    tools._baseline_resolver._valuation_service = valuation_service
    tools._test_valuation_service = valuation_service
    return tools, session, portfolio_service, reporting_service, simulation_service


def _assert_session_lifecycle_untouched(session: MagicMock) -> None:
    session.commit.assert_not_called()
    session.rollback.assert_not_called()
    session.close.assert_not_called()
    session.flush.assert_not_called()


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
        "portfolio_type": "LEGACY",
        "baseline_source": "saved-weights",
        "holdings": [
            {"symbol": "BND", "weight": 0.0},
            {"symbol": "AAPL", "weight": 1.0},
        ],
    }
    assert context is not portfolio
    assert all(not isinstance(value, Holding) for value in context["holdings"])
    tools._test_valuation_service.value.assert_not_called()
    json.dumps(context)
    _assert_session_lifecycle_untouched(session)


def test_real_portfolio_context_uses_one_authoritative_usd_valuation() -> None:
    tools, session, portfolio_service, _, _ = _tools_with_services()
    portfolio = _real_portfolio()
    valuation = _valuation_result()
    portfolio_service.get.return_value = portfolio
    tools._test_valuation_service.value.return_value = valuation

    context = tools.get_portfolio_context()

    tools._test_valuation_service.value.assert_called_once_with(
        tuple(portfolio.holdings),
        requested_date=_VALUATION_DATE,
        display_currency=PortfolioDisplayCurrency.USD,
    )
    assert context == {
        "id": str(_PORTFOLIO_ID),
        "name": "Real Holdings",
        "portfolio_type": "CURRENT",
        "baseline_source": "current-valuation",
        "valuation": {
            "valuation_currency": "USD",
            "valuation_date": "2026-09-12",
            "oldest_price_as_of": "2026-09-12",
            "newest_price_as_of": "2026-09-12",
            "total_current_value_usd": "100",
        },
        "holdings": [
            {
                "symbol": "AAPL",
                "weight": 0.6,
                "invested_amount": "999999.000000000000",
                "invested_currency": "THB",
                "shares": "1.000000000000",
                "purchase_date": "2026-01-01",
                "position": 0,
                "asset_price": "100.000000000000",
                "asset_quote_currency": "USD",
                "price_as_of": "2026-09-12",
                "current_value_usd": "60.00000000000000000000000000",
                "current_allocation": "0.6000000000000000000000000000",
            },
            {
                "symbol": "BND",
                "weight": 0.4,
                "invested_amount": "999999.000000000000",
                "invested_currency": "USD",
                "shares": "1.000000000000",
                "purchase_date": "2026-01-02",
                "position": 1,
                "asset_price": "100.000000000000",
                "asset_quote_currency": "USD",
                "price_as_of": "2026-09-12",
                "current_value_usd": "40.00000000000000000000000000",
                "current_allocation": "0.4000000000000000000000000000",
            },
        ],
    }
    assert valuation.fx_context is None
    assert "fx" not in context["valuation"]
    assert all("id" not in holding for holding in context["holdings"])
    _assert_session_lifecycle_untouched(session)


def test_planned_portfolio_context_uses_price_independent_target_weights() -> None:
    tools, session, portfolio_service, reporting_service, simulation_service = (
        _tools_with_services()
    )
    portfolio_service.get.return_value = _planned_portfolio()

    context = tools.get_portfolio_context()

    assert context == {
        "id": str(_PORTFOLIO_ID),
        "name": "Planned Portfolio",
        "portfolio_type": "PLANNED",
        "baseline_source": "proposed-amount-target-allocation",
        "plan_currency": "USD",
        "total_proposed_amount": "1000",
        "hypothetical_notice": (
            "Hypothetical historical analysis only; not a forecast, "
            "recommendation, or executable order."
        ),
        "holdings": [
            {
                "symbol": "AAPL",
                "proposed_amount": "600",
                "target_allocation": "0.600000000000000000",
                "position": 0,
            },
            {
                "symbol": "BND",
                "proposed_amount": "400",
                "target_allocation": "0.400000000000000000",
                "position": 1,
            },
        ],
    }
    assert all("id" not in holding for holding in context["holdings"])
    assert all(
        "estimated_shares" not in holding
        for holding in context["holdings"]
    )
    tools._test_valuation_service.value.assert_not_called()
    reporting_service.assert_not_called()
    simulation_service.assert_not_called()
    _assert_session_lifecycle_untouched(session)


def test_saved_context_preserves_legacy_weights_without_current_data() -> None:
    tools, session, portfolio_service, _, _ = _tools_with_services()
    portfolio_service.get.return_value = _portfolio()

    context = tools.get_portfolio_context(resolve_current_baseline=False)

    assert context == {
        "id": str(_PORTFOLIO_ID),
        "name": "Learning Portfolio",
        "portfolio_type": "LEGACY",
        "baseline_source": "saved-weights",
        "holdings": [
            {"symbol": "BND", "weight": 0.0},
            {"symbol": "AAPL", "weight": 1.0},
        ],
    }
    tools._test_valuation_service.value.assert_not_called()
    _assert_session_lifecycle_untouched(session)


def test_saved_context_uses_real_portfolio_identity_without_current_data() -> None:
    tools, session, portfolio_service, _, _ = _tools_with_services()
    portfolio_service.get.return_value = _real_portfolio()
    tools._test_valuation_service.value.side_effect = (
        MarketDataUnavailableError("stale AAPL price")
    )

    context = tools.get_portfolio_context(resolve_current_baseline=False)

    assert context is not None
    assert context == {
        "id": str(_PORTFOLIO_ID),
        "name": "Real Holdings",
        "portfolio_type": "CURRENT",
    }
    tools._test_valuation_service.value.assert_not_called()
    _assert_session_lifecycle_untouched(session)


def test_saved_context_uses_planned_identity_without_live_plan_values() -> None:
    tools, session, portfolio_service, _, _ = _tools_with_services()
    portfolio_service.get.return_value = _planned_portfolio()

    context = tools.get_portfolio_context(resolve_current_baseline=False)

    assert context == {
        "id": str(_PORTFOLIO_ID),
        "name": "Planned Portfolio",
        "portfolio_type": "PLANNED",
    }
    tools._test_valuation_service.value.assert_not_called()
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


def test_v2_report_projection_preserves_frozen_valuation_and_holdings() -> None:
    tools, session, _, reporting_service, _ = _tools_with_services()
    report = PortfolioReportV2Response.model_validate(_valid_v2_report_data())
    source_before = report.model_dump(mode="python")
    reporting_service.get_report.return_value = report
    tools._test_valuation_service.value.side_effect = (
        MarketDataUnavailableError("current prices are stale")
    )

    context = tools.get_report(_REPORT_ID)

    assert context is not None
    assert context["schema_version"] == "portfolio-analysis-response-v2"
    assert context["valuation"] == report.valuation.model_dump(mode="json")
    assert [holding["symbol"] for holding in context["holdings"]] == [
        "AAPL",
        "MSFT",
        "BND",
    ]
    assert context["holdings"][0]["current_value"] == "1000.000000000000"
    assert all("id" not in holding for holding in context["holdings"])
    tools._test_valuation_service.value.assert_not_called()
    assert report.model_dump(mode="python") == source_before
    _assert_session_lifecycle_untouched(session)


def test_v3_report_projects_frozen_planned_baseline_without_ids() -> None:
    tools, session, _, reporting_service, _ = _tools_with_services()
    report = PortfolioReportV3Response.model_validate(_valid_v3_report_data())
    source_before = report.model_dump(mode="python")
    reporting_service.get_report.return_value = report

    context = tools.get_report(_REPORT_ID)

    assert context is not None
    assert context["schema_version"] == "portfolio-analysis-response-v3"
    assert context["portfolio_type"] == "PLANNED"
    assert context["baseline_source"] == (
        "proposed-amount-target-allocation"
    )
    assert context["baseline"]["plan_currency"] == "USD"
    assert context["baseline"]["total_proposed_amount"] == "10000"
    assert all(
        "id" not in holding
        for holding in context["baseline"]["holdings"]
    )
    assert all(
        "estimated_shares" not in holding
        for holding in context["baseline"]["holdings"]
    )
    assert report.model_dump(mode="python") == source_before
    _assert_session_lifecycle_untouched(session)


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


def test_v2_simulation_projection_preserves_frozen_baseline_without_ids() -> None:
    tools, session, _, _, simulation_service = _tools_with_services()
    simulation = _v2_simulation_detail()
    source_before = simulation.model_dump(mode="python")
    simulation_service.get.return_value = simulation
    tools._test_valuation_service.value.side_effect = (
        MarketDataUnavailableError("current prices are missing")
    )

    context = tools.get_simulation(_SIMULATION_ID)

    assert context is not None
    assert context["schema_version"] == "allocation-simulation-response-v2"
    assert context["baseline"]["valuation_date"] == "2026-09-12"
    assert context["baseline"]["total_current_value_usd"] == "100"
    assert [holding["current_allocation"] for holding in context["baseline"]["holdings"]] == [
        "0.6",
        "0.4",
    ]
    assert all(
        "id" not in holding
        for holding in context["baseline"]["holdings"]
    )
    assert context["result"] == simulation.result.model_dump(mode="json")
    tools._test_valuation_service.value.assert_not_called()
    assert simulation.model_dump(mode="python") == source_before
    _assert_session_lifecycle_untouched(session)


def test_v3_simulation_projects_frozen_planned_baseline_without_ids() -> None:
    tools, session, _, _, simulation_service = _tools_with_services()
    simulation = _v3_simulation_detail()
    source_before = simulation.model_dump(mode="python")
    simulation_service.get.return_value = simulation

    context = tools.get_simulation(_SIMULATION_ID)

    assert context is not None
    assert context["schema_version"] == (
        "allocation-simulation-response-v3"
    )
    assert context["portfolio_type"] == "PLANNED"
    assert context["baseline_source"] == (
        "proposed-amount-target-allocation"
    )
    assert context["baseline"]["plan_currency"] == "USD"
    assert context["baseline"]["total_proposed_amount"] == "1000"
    assert all(
        "id" not in holding
        for holding in context["baseline"]["holdings"]
    )
    assert context["result"] == simulation.result.model_dump(mode="json")
    assert simulation.model_dump(mode="python") == source_before
    _assert_session_lifecycle_untouched(session)


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
