from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, date, datetime
import inspect
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.orm import Session

import app.api.dependencies as dependency_module
import app.api.routes.simulation as route_module
from app.core.config import settings
from app.core.security import create_access_token
from app.database.models import User
from app.main import app
from app.schemas.simulation_history import (
    SimulationBaselineHolding,
    SimulationBaselineValuationContext,
    SimulationHistoryDetailResponse,
    SimulationHistoryListResponse,
    SimulationHistorySummary,
    SimulationHistoryV2DetailResponse,
    SimulationHistoryV3DetailResponse,
)
from app.schemas.portfolio import PlannedPortfolioBaselineContext
from app.services.simulation_history_service import SimulationNotFoundError
from backend.tests.unit.services.test_simulation_history_mapper import (
    _response_for_type,
)


OWNER_ID = UUID("62a1279e-bc8d-4c89-876d-a09250b50395")
OTHER_USER_ID = UUID("72a1279e-bc8d-4c89-876d-a09250b50395")
PORTFOLIO_ID = UUID("e6518442-58cb-408f-ae3f-bf47fb00b555")
SIMULATION_ID = UUID("10000000-0000-0000-0000-000000000001")
JWT_SECRET = "phase-5-simulation-history-api-test-secret"
LIST_PATH = f"/api/portfolios/{PORTFOLIO_ID}/simulations"
DETAIL_PATH = f"{LIST_PATH}/{SIMULATION_ID}"
REQUEST_HEADERS: dict[str, str] = {}
CREATED_AT = datetime(2026, 8, 20, 9, 30, tzinfo=UTC)


def test_delete_simulation_commits_once_and_returns_empty_204(api_harness) -> None:
    api_harness.service.delete.return_value = True
    response = api_harness.client.delete(DETAIL_PATH, headers=REQUEST_HEADERS)
    assert response.status_code == 204
    assert response.content == b""
    api_harness.service.delete.assert_called_once_with(
        user_id=OWNER_ID, portfolio_id=PORTFOLIO_ID, simulation_id=SIMULATION_ID,
    )
    api_harness.session.commit.assert_called_once_with()
    api_harness.session.rollback.assert_not_called()


def test_delete_openapi_requires_auth_and_has_no_response_body() -> None:
    operation = app.openapi()["paths"]["/api/portfolios/{portfolio_id}/simulations/{simulation_id}"]["delete"]
    assert operation["security"] == [{"HTTPBearer": []}]
    assert "content" not in operation["responses"]["204"]


@pytest.mark.parametrize("path", [f"{LIST_PATH}/invalid", f"/api/portfolios/invalid/simulations/{SIMULATION_ID}"])
def test_delete_rejects_invalid_identifiers(api_harness, path) -> None:
    response = api_harness.client.delete(path, headers=REQUEST_HEADERS)
    assert response.status_code == 422
    api_harness.service.delete.assert_not_called()
    api_harness.session.commit.assert_not_called()


@pytest.mark.parametrize("parent_missing", [True, False])
def test_delete_missing_or_unowned_returns_safe_404(api_harness, parent_missing) -> None:
    if parent_missing:
        api_harness.service.delete.return_value = None
    else:
        api_harness.service.delete.side_effect = SimulationNotFoundError
    response = api_harness.client.delete(DETAIL_PATH, headers=REQUEST_HEADERS)
    assert response.status_code == 404
    assert response.json() == {"detail": "Portfolio not found" if parent_missing else "Simulation not found"}
    api_harness.session.commit.assert_not_called()
    api_harness.session.rollback.assert_called_once_with()


@pytest.mark.parametrize("headers", [{}, {"X-User-ID": str(OWNER_ID)}, {"Authorization": "Bearer invalid"}])
def test_delete_requires_bearer_authentication(api_harness, headers) -> None:
    response = api_harness.client.delete(DETAIL_PATH, headers=headers)
    assert response.status_code == 401
    api_harness.service.delete.assert_not_called()
    api_harness.session.commit.assert_not_called()


@pytest.mark.parametrize("commit_failure", [True, False])
def test_delete_failure_rolls_back_and_hides_internal_details(api_harness, commit_failure) -> None:
    api_harness.service.delete.return_value = True
    if commit_failure:
        api_harness.session.commit.side_effect = RuntimeError("private database details")
    else:
        api_harness.service.delete.side_effect = RuntimeError("private database details")
    response = api_harness.client.delete(DETAIL_PATH, headers=REQUEST_HEADERS)
    assert response.status_code == 500
    assert response.json() == {"detail": "Unable to delete simulation"}
    api_harness.session.rollback.assert_called_once_with()
    if not commit_failure:
        api_harness.session.commit.assert_not_called()


@dataclass
class ApiHarness:
    client: TestClient
    session: MagicMock
    service: MagicMock
    service_type: MagicMock


@pytest.fixture(autouse=True)
def bearer_request_headers() -> Iterator[None]:
    with patch.object(settings, "jwt_secret_key", SecretStr(JWT_SECRET)):
        REQUEST_HEADERS["Authorization"] = (
            f"Bearer {create_access_token(OWNER_ID)}"
        )
        try:
            yield
        finally:
            REQUEST_HEADERS.clear()


@pytest.fixture
def api_harness() -> Iterator[ApiHarness]:
    session = MagicMock(spec=Session)
    session.get.return_value = User(id=OWNER_ID)
    session_factory = MagicMock(return_value=session)
    service = MagicMock(spec=route_module.SimulationHistoryService)

    with (
        patch.object(
            dependency_module,
            "_get_session_factory",
            return_value=session_factory,
        ),
        patch.object(
            route_module,
            "SimulationHistoryService",
            return_value=service,
        ) as service_type,
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        yield ApiHarness(
            client=client,
            session=session,
            service=service,
            service_type=service_type,
        )


def _summary(
    simulation_type: str,
    *,
    simulation_id: UUID = SIMULATION_ID,
) -> SimulationHistorySummary:
    return SimulationHistorySummary(
        id=simulation_id,
        portfolio_id=PORTFOLIO_ID,
        simulation_type=simulation_type,  # type: ignore[arg-type]
        scenario_id=(
            None
            if simulation_type == "allocation"
            else "covid-19-shock-2020"
        ),
        requested_start_date=date(2020, 2, 1),
        requested_end_date=date(2020, 4, 30),
        created_at=CREATED_AT,
    )


def _detail(simulation_type: str) -> SimulationHistoryDetailResponse:
    summary = _summary(simulation_type)
    result = _response_for_type(simulation_type).model_dump(mode="json")
    result["portfolio_id"] = str(PORTFOLIO_ID)
    return SimulationHistoryDetailResponse(
        **summary.model_dump(),
        result=result,
    )


def _v2_detail() -> SimulationHistoryV2DetailResponse:
    summary = _summary("allocation")
    result = _response_for_type("allocation").model_dump(mode="json")
    result["portfolio_id"] = str(PORTFOLIO_ID)
    return SimulationHistoryV2DetailResponse(
        **summary.model_dump(),
        schema_version="allocation-simulation-response-v2",
        result=result,
        baseline=SimulationBaselineValuationContext(
            valuation_currency="USD",
            valuation_date=date(2026, 9, 12),
            oldest_price_as_of=date(2026, 9, 11),
            newest_price_as_of=date(2026, 9, 12),
            total_current_value_usd="1000.00",
            holdings=[
                SimulationBaselineHolding(
                    id=UUID("53000000-0000-0000-0000-000000000001"),
                    symbol="AAPL",
                    invested_amount="500.00",
                    invested_currency="THB",
                    shares="4.00",
                    purchase_date=date(2026, 1, 2),
                    position=0,
                    asset_price="150.00",
                    asset_quote_currency="USD",
                    price_as_of=date(2026, 9, 12),
                    current_value_usd="600.00",
                    current_allocation="0.60",
                ),
                SimulationBaselineHolding(
                    id=UUID("53000000-0000-0000-0000-000000000002"),
                    symbol="BND",
                    invested_amount="400.00",
                    invested_currency="USD",
                    shares="5.00",
                    purchase_date=date(2026, 2, 3),
                    position=1,
                    asset_price="80.00",
                    asset_quote_currency="USD",
                    price_as_of=date(2026, 9, 11),
                    current_value_usd="400.00",
                    current_allocation="0.40",
                ),
            ],
        ),
    )


def _v3_detail() -> SimulationHistoryV3DetailResponse:
    summary = _summary("allocation")
    result = _response_for_type("allocation").model_dump(mode="json")
    result["portfolio_id"] = str(PORTFOLIO_ID)
    return SimulationHistoryV3DetailResponse(
        **summary.model_dump(),
        schema_version="allocation-simulation-response-v3",
        result=result,
        baseline=PlannedPortfolioBaselineContext(
            portfolio_type="PLANNED",
            baseline_source="proposed-amount-target-allocation",
            plan_currency="THB",
            total_proposed_amount="10000",
            hypothetical_notice=(
                "Hypothetical historical analysis only; not a forecast, "
                "recommendation, or executable order."
            ),
            holdings=[
                {
                    "id": "53000000-0000-0000-0000-000000000001",
                    "symbol": "MSFT",
                    "proposed_amount": "6000",
                    "target_allocation": "0.6",
                    "position": 0,
                },
                {
                    "id": "53000000-0000-0000-0000-000000000002",
                    "symbol": "AAPL",
                    "proposed_amount": "4000",
                    "target_allocation": "0.4",
                    "position": 1,
                },
            ],
        ),
    )


def _registered_methods() -> set[tuple[str, str]]:
    return {
        (path, method.upper())
        for path, operations in app.openapi()["paths"].items()
        for method in operations
    }


def _assert_route_did_not_manage_session(api_harness: ApiHarness) -> None:
    api_harness.session.commit.assert_not_called()
    api_harness.session.flush.assert_not_called()


def test_history_get_routes_and_existing_simulation_posts_are_registered() -> None:
    methods = _registered_methods()

    assert (
        "/api/portfolios/{portfolio_id}/simulations",
        "GET",
    ) in methods
    assert (
        "/api/portfolios/{portfolio_id}/simulations/{simulation_id}",
        "GET",
    ) in methods
    assert (
        "/api/portfolios/{portfolio_id}/simulations/historical-scenarios",
        "POST",
    ) in methods
    assert (
        "/api/portfolios/{portfolio_id}/simulations/allocations",
        "POST",
    ) in methods
    assert (
        "/api/portfolios/{portfolio_id}/simulations/combined",
        "POST",
    ) in methods


def test_authenticated_list_returns_contract_and_preserves_service_order(
    api_harness: ApiHarness,
) -> None:
    combined = _summary("combined", simulation_id=UUID(int=3))
    allocation = _summary("allocation", simulation_id=UUID(int=2))
    historical = _summary("historical-scenario", simulation_id=UUID(int=1))
    history = SimulationHistoryListResponse(
        simulations=[combined, allocation, historical]
    )
    api_harness.service.list_for_portfolio.return_value = history

    response = api_harness.client.get(LIST_PATH, headers=REQUEST_HEADERS)

    assert response.status_code == 200
    assert response.json() == history.model_dump(mode="json")
    assert SimulationHistoryListResponse.model_validate(response.json()) == history
    assert [item["id"] for item in response.json()["simulations"]] == [
        str(combined.id),
        str(allocation.id),
        str(historical.id),
    ]
    assert response.json()["simulations"][0]["scenario_id"] == (
        "covid-19-shock-2020"
    )
    assert response.json()["simulations"][1]["scenario_id"] is None
    assert response.json()["simulations"][2]["simulation_type"] == (
        "historical-scenario"
    )
    api_harness.service_type.assert_called_once_with(api_harness.session)
    api_harness.service.list_for_portfolio.assert_called_once_with(
        user_id=OWNER_ID,
        portfolio_id=PORTFOLIO_ID,
    )
    api_harness.service.get.assert_not_called()
    api_harness.service.save.assert_not_called()
    _assert_route_did_not_manage_session(api_harness)
    api_harness.session.rollback.assert_not_called()


def test_authenticated_list_allows_empty_owned_history(
    api_harness: ApiHarness,
) -> None:
    api_harness.service.list_for_portfolio.return_value = (
        SimulationHistoryListResponse(simulations=[])
    )

    response = api_harness.client.get(LIST_PATH, headers=REQUEST_HEADERS)

    assert response.status_code == 200
    assert response.json() == {"simulations": []}
    _assert_route_did_not_manage_session(api_harness)


@pytest.mark.parametrize("portfolio_state", ["missing", "wrong-owner"])
def test_list_missing_and_wrong_owner_are_identical_not_found(
    api_harness: ApiHarness,
    portfolio_state: str,
) -> None:
    api_harness.service.list_for_portfolio.return_value = None

    response = api_harness.client.get(LIST_PATH, headers=REQUEST_HEADERS)

    assert portfolio_state in {"missing", "wrong-owner"}
    assert response.status_code == 404
    assert response.status_code != 403
    assert response.json() == {"detail": "Portfolio not found"}
    _assert_route_did_not_manage_session(api_harness)


def test_list_unexpected_failure_is_sanitized(api_harness: ApiHarness) -> None:
    internal_detail = "SELECT result_snapshot FROM simulations: secret-json"
    api_harness.service.list_for_portfolio.side_effect = RuntimeError(
        internal_detail
    )

    response = api_harness.client.get(LIST_PATH, headers=REQUEST_HEADERS)

    assert response.status_code == 500
    assert response.json() == {
        "detail": "Unable to retrieve simulation history"
    }
    assert internal_detail not in response.text
    _assert_route_did_not_manage_session(api_harness)


@pytest.mark.parametrize(
    ("simulation_type", "expected_result_type"),
    [
        ("historical-scenario", "historical-scenario"),
        ("allocation", "allocation"),
        ("combined", "combined"),
    ],
)
def test_authenticated_detail_returns_exact_validated_result_contract(
    api_harness: ApiHarness,
    simulation_type: str,
    expected_result_type: str,
) -> None:
    detail = _detail(simulation_type)
    api_harness.service.get.return_value = detail

    response = api_harness.client.get(DETAIL_PATH, headers=REQUEST_HEADERS)

    assert response.status_code == 200
    assert response.json() == detail.model_dump(mode="json")
    validated = SimulationHistoryDetailResponse.model_validate(response.json())
    assert validated == detail
    assert "result" in response.json()
    assert response.json()["simulation_type"] == expected_result_type
    assert response.json()["result"]["portfolio_id"] == str(PORTFOLIO_ID)
    api_harness.service_type.assert_called_once_with(api_harness.session)
    api_harness.service.get.assert_called_once_with(
        user_id=OWNER_ID,
        portfolio_id=PORTFOLIO_ID,
        simulation_id=SIMULATION_ID,
    )
    api_harness.service.list_for_portfolio.assert_not_called()
    api_harness.service.save.assert_not_called()
    _assert_route_did_not_manage_session(api_harness)
    api_harness.session.rollback.assert_not_called()


def test_authenticated_v2_detail_exposes_frozen_baseline_around_same_result(
    api_harness: ApiHarness,
) -> None:
    detail = _v2_detail()
    api_harness.service.get.return_value = detail

    response = api_harness.client.get(DETAIL_PATH, headers=REQUEST_HEADERS)

    assert response.status_code == 200
    assert response.json() == detail.model_dump(mode="json")
    validated = SimulationHistoryV2DetailResponse.model_validate(
        response.json()
    )
    assert validated == detail
    assert response.json()["schema_version"] == (
        "allocation-simulation-response-v2"
    )
    assert response.json()["baseline"]["valuation_currency"] == "USD"
    assert response.json()["baseline"]["valuation_date"] == "2026-09-12"
    assert [
        holding["symbol"]
        for holding in response.json()["baseline"]["holdings"]
    ] == ["AAPL", "BND"]
    assert response.json()["result"] == detail.result.model_dump(mode="json")
    api_harness.service.get.assert_called_once_with(
        user_id=OWNER_ID,
        portfolio_id=PORTFOLIO_ID,
        simulation_id=SIMULATION_ID,
    )
    _assert_route_did_not_manage_session(api_harness)


def test_authenticated_v3_detail_exposes_frozen_planned_baseline(
    api_harness: ApiHarness,
) -> None:
    detail = _v3_detail()
    api_harness.service.get.return_value = detail

    response = api_harness.client.get(DETAIL_PATH, headers=REQUEST_HEADERS)

    assert response.status_code == 200
    assert response.json() == detail.model_dump(mode="json")
    validated = SimulationHistoryV3DetailResponse.model_validate(
        response.json()
    )
    assert validated == detail
    assert response.json()["schema_version"] == (
        "allocation-simulation-response-v3"
    )
    assert response.json()["baseline"]["portfolio_type"] == "PLANNED"
    assert response.json()["baseline"]["plan_currency"] == "THB"
    assert "estimated_shares" not in response.json()["baseline"]["holdings"][0]
    _assert_route_did_not_manage_session(api_harness)


def test_openapi_history_detail_includes_all_snapshot_generations(
    api_harness: ApiHarness,
) -> None:
    schema = api_harness.client.get("/openapi.json").json()
    response_schema = schema["paths"][
        "/api/portfolios/{portfolio_id}/simulations/{simulation_id}"
    ]["get"]["responses"]["200"]["content"]["application/json"]["schema"]

    assert response_schema["anyOf"] == [
        {"$ref": "#/components/schemas/SimulationHistoryDetailResponse"},
        {"$ref": "#/components/schemas/SimulationHistoryV2DetailResponse"},
        {"$ref": "#/components/schemas/SimulationHistoryV3DetailResponse"},
    ]


@pytest.mark.parametrize("portfolio_state", ["missing", "wrong-owner"])
def test_detail_unowned_portfolio_maps_to_portfolio_not_found(
    api_harness: ApiHarness,
    portfolio_state: str,
) -> None:
    api_harness.service.get.return_value = None

    response = api_harness.client.get(DETAIL_PATH, headers=REQUEST_HEADERS)

    assert portfolio_state in {"missing", "wrong-owner"}
    assert response.status_code == 404
    assert response.status_code != 403
    assert response.json() == {"detail": "Portfolio not found"}
    _assert_route_did_not_manage_session(api_harness)


@pytest.mark.parametrize("simulation_state", ["missing", "other-portfolio"])
def test_detail_missing_and_wrong_association_are_identical_not_found(
    api_harness: ApiHarness,
    simulation_state: str,
) -> None:
    api_harness.service.get.side_effect = SimulationNotFoundError(
        "Simulation not found"
    )

    response = api_harness.client.get(DETAIL_PATH, headers=REQUEST_HEADERS)

    assert simulation_state in {"missing", "other-portfolio"}
    assert response.status_code == 404
    assert response.status_code != 403
    assert response.json() == {"detail": "Simulation not found"}
    api_harness.service.get.assert_called_once_with(
        user_id=OWNER_ID,
        portfolio_id=PORTFOLIO_ID,
        simulation_id=SIMULATION_ID,
    )
    _assert_route_did_not_manage_session(api_harness)


@pytest.mark.parametrize(
    "failure",
    [
        ValueError("unsupported mapper schema: private-v9"),
        RuntimeError("corrupt JSONB payload with secret holdings"),
    ],
)
def test_detail_unexpected_or_corrupt_failure_is_sanitized(
    api_harness: ApiHarness,
    failure: Exception,
) -> None:
    api_harness.service.get.side_effect = failure

    response = api_harness.client.get(DETAIL_PATH, headers=REQUEST_HEADERS)

    assert response.status_code == 500
    assert response.json() == {"detail": "Unable to retrieve simulation"}
    assert str(failure) not in response.text
    _assert_route_did_not_manage_session(api_harness)


@pytest.mark.parametrize("path", [LIST_PATH, DETAIL_PATH])
@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": "Bearer not-a-jwt"},
        {"X-User-ID": str(OWNER_ID)},
    ],
)
def test_history_gets_require_existing_bearer_authentication(
    api_harness: ApiHarness,
    path: str,
    headers: dict[str, str],
) -> None:
    response = api_harness.client.get(path, headers=headers)

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid or missing authentication credentials"
    }
    assert response.headers["www-authenticate"] == "Bearer"
    api_harness.service.list_for_portfolio.assert_not_called()
    api_harness.service.get.assert_not_called()
    api_harness.service.save.assert_not_called()
    _assert_route_did_not_manage_session(api_harness)


@pytest.mark.parametrize("path", [LIST_PATH, DETAIL_PATH])
def test_x_user_id_cannot_override_authenticated_bearer_user(
    api_harness: ApiHarness,
    path: str,
) -> None:
    api_harness.service.list_for_portfolio.return_value = (
        SimulationHistoryListResponse(simulations=[])
    )
    api_harness.service.get.return_value = _detail("allocation")

    response = api_harness.client.get(
        path,
        headers={**REQUEST_HEADERS, "X-User-ID": str(OTHER_USER_ID)},
    )

    assert response.status_code == 200
    api_harness.session.get.assert_called_once_with(User, OWNER_ID)
    called = (
        api_harness.service.list_for_portfolio
        if path == LIST_PATH
        else api_harness.service.get
    )
    assert called.call_args.kwargs["user_id"] == OWNER_ID
    _assert_route_did_not_manage_session(api_harness)


def test_history_routes_do_not_own_transaction_or_snapshot_mapping() -> None:
    list_source = inspect.getsource(route_module.list_simulation_history)
    detail_source = inspect.getsource(route_module.get_simulation_history)
    combined_source = f"{list_source}\n{detail_source}"

    assert "session.commit" not in combined_source
    assert "session.rollback" not in combined_source
    assert "session.close" not in combined_source
    assert "Simulation(" not in combined_source
    assert "result_snapshot" not in combined_source
    assert "simulation_snapshot_to_response" not in combined_source
    assert ".save(" not in combined_source
