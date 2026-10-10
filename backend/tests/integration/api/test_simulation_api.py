from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date
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
from app.schemas.simulation import (
    AllocationSimulationRequest,
    AllocationSimulationResponse,
    CombinedSimulationRequest,
    CombinedSimulationResponse,
    HistoricalScenarioListResponse,
    HistoricalScenarioSimulationRequest,
    HistoricalScenarioSimulationResponse,
)
from app.services.allocation_simulation_service import (
    AllocationSymbolMismatchError,
    EmptyPortfolioError as AllocationEmptyPortfolioError,
)
from app.services.historical_scenario_service import (
    EmptyPortfolioError,
    HistoricalScenarioNotFoundError,
)
from app.services.market_data_service import MarketDataUnavailableError
from app.services.portfolio_baseline_resolver import (
    PortfolioBaselineKind,
    PortfolioBaselineResolution,
)
from app.services.portfolio_valuation_service import InvalidHoldingModeError
from app.services.simulation_execution import SimulationExecutionResult


OWNER_ID = UUID("62a1279e-bc8d-4c89-876d-a09250b50395")
OTHER_USER_ID = UUID("10000000-0000-0000-0000-000000000002")
PORTFOLIO_ID = UUID("e6518442-58cb-408f-ae3f-bf47fb00b555")
JWT_SECRET = "phase-5-historical-simulation-api-test-secret"
CATALOGUE_PATH = "/api/simulations/historical-scenarios"
SIMULATION_PATH = (
    f"/api/portfolios/{PORTFOLIO_ID}/simulations/historical-scenarios"
)
ALLOCATION_SIMULATION_PATH = (
    f"/api/portfolios/{PORTFOLIO_ID}/simulations/allocations"
)
COMBINED_SIMULATION_PATH = (
    f"/api/portfolios/{PORTFOLIO_ID}/simulations/combined"
)
REQUEST_HEADERS: dict[str, str] = {}
LEGACY_BASELINE = PortfolioBaselineResolution(
    baseline_kind=PortfolioBaselineKind.LEGACY,
    resolved_weights=(),
    valuation=None,
    valuation_as_of=None,
)


def _bridge_context_run(service: MagicMock) -> None:
    def run_with_context(**kwargs: object) -> object:
        forwarded = dict(kwargs)
        forwarded.pop("valuation_date")
        response = service.run(**forwarded)
        if response is None:
            return None
        return SimulationExecutionResult(
            response=response,
            baseline=LEGACY_BASELINE,
        )

    service.run_with_context.side_effect = run_with_context


def _post_case(
    request: pytest.FixtureRequest,
    fixture_name: str,
) -> tuple[object, str, dict[str, object], object]:
    if fixture_name == "api_harness":
        return (
            request.getfixturevalue(fixture_name),
            SIMULATION_PATH,
            {"scenario_id": "covid-19-shock-2020"},
            _simulation_response(),
        )
    if fixture_name == "allocation_api_harness":
        return (
            request.getfixturevalue(fixture_name),
            ALLOCATION_SIMULATION_PATH,
            _allocation_request_body(),
            _allocation_simulation_response(),
        )
    return (
        request.getfixturevalue(fixture_name),
        COMBINED_SIMULATION_PATH,
        _combined_request_body(),
        _combined_simulation_response(),
    )


@dataclass
class ApiHarness:
    client: TestClient
    session: MagicMock
    service: MagicMock
    history_service: MagicMock
    session_factory: MagicMock


@dataclass
class AllocationApiHarness:
    client: TestClient
    session: MagicMock
    service: MagicMock
    history_service: MagicMock
    session_factory: MagicMock


@dataclass
class CombinedApiHarness:
    client: TestClient
    session: MagicMock
    service: MagicMock
    service_type: MagicMock
    history_service: MagicMock
    session_factory: MagicMock


@pytest.fixture(autouse=True)
def bearer_request_headers() -> Iterator[None]:
    with patch.object(
        settings,
        "jwt_secret_key",
        SecretStr(JWT_SECRET),
    ):
        REQUEST_HEADERS["Authorization"] = (
            f"Bearer {create_access_token(OWNER_ID)}"
        )
        try:
            yield
        finally:
            REQUEST_HEADERS.clear()


@pytest.fixture(autouse=True)
def notifications_service():
    with patch.object(route_module, "NotificationService") as factory:
        yield factory.return_value


@pytest.fixture
def api_harness() -> Iterator[ApiHarness]:
    session = MagicMock(spec=Session)
    session.get.return_value = User(id=OWNER_ID)
    session_factory = MagicMock(return_value=session)
    service = MagicMock(spec=route_module.HistoricalScenarioService)
    _bridge_context_run(service)
    history_service = MagicMock(spec=route_module.SimulationHistoryService)

    with (
        patch.object(
            dependency_module,
            "_get_session_factory",
            return_value=session_factory,
        ),
        patch.object(
            route_module,
            "HistoricalScenarioService",
            return_value=service,
        ),
        patch.object(
            route_module,
            "SimulationHistoryService",
            return_value=history_service,
        ),
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        yield ApiHarness(
            client=client,
            session=session,
            service=service,
            history_service=history_service,
            session_factory=session_factory,
        )


@pytest.fixture
def allocation_api_harness() -> Iterator[AllocationApiHarness]:
    session = MagicMock(spec=Session)
    session.get.return_value = User(id=OWNER_ID)
    session_factory = MagicMock(return_value=session)
    service = MagicMock(spec=route_module.AllocationSimulationService)
    _bridge_context_run(service)
    history_service = MagicMock(spec=route_module.SimulationHistoryService)

    with (
        patch.object(
            dependency_module,
            "_get_session_factory",
            return_value=session_factory,
        ),
        patch.object(
            route_module,
            "AllocationSimulationService",
            return_value=service,
        ),
        patch.object(
            route_module,
            "SimulationHistoryService",
            return_value=history_service,
        ),
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        yield AllocationApiHarness(
            client=client,
            session=session,
            service=service,
            history_service=history_service,
            session_factory=session_factory,
        )


@pytest.fixture
def combined_api_harness() -> Iterator[CombinedApiHarness]:
    session = MagicMock(spec=Session)
    session.get.return_value = User(id=OWNER_ID)
    session_factory = MagicMock(return_value=session)
    service = MagicMock(spec=route_module.CombinedSimulationService)
    _bridge_context_run(service)
    history_service = MagicMock(spec=route_module.SimulationHistoryService)

    with (
        patch.object(
            dependency_module,
            "_get_session_factory",
            return_value=session_factory,
        ),
        patch.object(
            route_module,
            "CombinedSimulationService",
            return_value=service,
        ) as service_type,
        patch.object(
            route_module,
            "SimulationHistoryService",
            return_value=history_service,
        ),
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        yield CombinedApiHarness(
            client=client,
            session=session,
            service=service,
            service_type=service_type,
            history_service=history_service,
            session_factory=session_factory,
        )


def _simulation_response() -> HistoricalScenarioSimulationResponse:
    return HistoricalScenarioSimulationResponse.model_validate(
        {
            "portfolio_id": PORTFOLIO_ID,
            "portfolio_name": "Balanced Learning Portfolio",
            "scenario": {
                "id": "covid-19-shock-2020",
                "display_name": "COVID-19 Market Shock",
                "description": (
                    "A sharp market shock and early recovery period during "
                    "the COVID-19 disruption."
                ),
                "requested_start_date": "2020-02-01",
                "requested_end_date": "2020-04-30",
            },
            "metadata": {
                "effective_start_date": "2020-02-03",
                "effective_end_date": "2020-04-30",
                "price_observation_count": 4,
                "return_observation_count": 3,
            },
            "metrics": {
                "normalized_starting_value": 1.0,
                "normalized_ending_value": 0.95,
                "cumulative_return": -0.05,
                "annualized_volatility": 0.42,
                "sharpe_ratio": None,
                "maximum_drawdown": {
                    "max_drawdown": -0.25,
                    "peak_date": "2020-02-03",
                    "trough_date": "2020-03-23",
                },
            },
            "trajectory": [
                {"date": "2020-02-03", "normalized_value": 1.0},
                {"date": "2020-03-02", "normalized_value": 0.8},
                {"date": "2020-03-23", "normalized_value": 0.75},
                {"date": "2020-04-30", "normalized_value": 0.95},
            ],
        }
    )


def _q4_simulation_response() -> HistoricalScenarioSimulationResponse:
    payload = _simulation_response().model_dump(mode="python")
    payload["scenario"] = {
        "id": "q4-market-selloff-2018",
        "display_name": "Q4 2018 Market Selloff",
        "description": (
            "A sharp late-2018 market selloff marked by elevated volatility."
        ),
        "requested_start_date": date(2018, 10, 1),
        "requested_end_date": date(2018, 12, 31),
    }
    payload["metadata"] = {
        "effective_start_date": date(2018, 10, 1),
        "effective_end_date": date(2018, 12, 31),
        "price_observation_count": 4,
        "return_observation_count": 3,
    }
    payload["metrics"]["maximum_drawdown"] = {
        "max_drawdown": -0.25,
        "peak_date": date(2018, 10, 1),
        "trough_date": date(2018, 12, 24),
    }
    payload["trajectory"] = [
        {"date": date(2018, 10, 1), "normalized_value": 1.0},
        {"date": date(2018, 11, 1), "normalized_value": 0.8},
        {"date": date(2018, 12, 24), "normalized_value": 0.75},
        {"date": date(2018, 12, 31), "normalized_value": 0.95},
    ]
    return HistoricalScenarioSimulationResponse.model_validate(payload)


def _allocation_request_body() -> dict[str, object]:
    return {
        "start_date": "2020-02-01",
        "end_date": "2020-04-30",
        "modified_allocation": [
            {"symbol": "ALPHA", "weight": 0.5},
            {"symbol": "BETA", "weight": 0.5},
            {"symbol": "ZERO", "weight": 0.0},
        ],
    }


def _allocation_simulation_response() -> AllocationSimulationResponse:
    return AllocationSimulationResponse.model_validate(
        {
            "portfolio_id": PORTFOLIO_ID,
            "portfolio_name": "Balanced Learning Portfolio",
            "start_date": "2020-02-01",
            "end_date": "2020-04-30",
            "metadata": {
                "effective_start_date": "2020-02-03",
                "effective_end_date": "2020-04-30",
                "price_observation_count": 4,
                "return_observation_count": 3,
            },
            "original": {
                "allocation": [
                    {"symbol": "BETA", "weight": 0.4},
                    {"symbol": "ZERO", "weight": 0.0},
                    {"symbol": "ALPHA", "weight": 0.6},
                ],
                "metrics": {
                    "normalized_starting_value": 1.0,
                    "normalized_ending_value": 0.95,
                    "cumulative_return": -0.05,
                    "annualized_volatility": 0.42,
                    "sharpe_ratio": None,
                    "maximum_drawdown": {
                        "max_drawdown": -0.25,
                        "peak_date": "2020-02-03",
                        "trough_date": "2020-03-23",
                    },
                },
                "trajectory": [
                    {"date": "2020-02-03", "normalized_value": 1.0},
                    {"date": "2020-03-02", "normalized_value": 0.8},
                    {"date": "2020-03-23", "normalized_value": 0.75},
                    {"date": "2020-04-30", "normalized_value": 0.95},
                ],
            },
            "modified": {
                "allocation": [
                    {"symbol": "BETA", "weight": 0.5},
                    {"symbol": "ZERO", "weight": 0.0},
                    {"symbol": "ALPHA", "weight": 0.5},
                ],
                "metrics": {
                    "normalized_starting_value": 1.0,
                    "normalized_ending_value": 1.05,
                    "cumulative_return": 0.05,
                    "annualized_volatility": 0.3,
                    "sharpe_ratio": 1.2,
                    "maximum_drawdown": {
                        "max_drawdown": -0.1,
                        "peak_date": "2020-02-03",
                        "trough_date": "2020-03-02",
                    },
                },
                "trajectory": [
                    {"date": "2020-02-03", "normalized_value": 1.0},
                    {"date": "2020-03-02", "normalized_value": 0.9},
                    {"date": "2020-03-23", "normalized_value": 0.97},
                    {"date": "2020-04-30", "normalized_value": 1.05},
                ],
            },
            "comparison": {
                "normalized_ending_value_delta": 0.1,
                "cumulative_return_delta": 0.1,
                "annualized_volatility_delta": -0.12,
                "sharpe_ratio_delta": None,
                "maximum_drawdown_delta": 0.15,
            },
        }
    )


def _combined_request_body() -> dict[str, object]:
    return {
        "scenario_id": "covid-19-shock-2020",
        "modified_allocation": [
            {"symbol": "ALPHA", "weight": 0.5},
            {"symbol": "BETA", "weight": 0.5},
            {"symbol": "ZERO", "weight": 0.0},
        ],
    }


def _combined_simulation_response() -> CombinedSimulationResponse:
    allocation_response = _allocation_simulation_response()
    return CombinedSimulationResponse.model_validate(
        {
            "portfolio_id": allocation_response.portfolio_id,
            "portfolio_name": allocation_response.portfolio_name,
            "scenario": {
                "id": "covid-19-shock-2020",
                "display_name": "COVID-19 Market Shock",
                "description": (
                    "A sharp market shock and early recovery period during "
                    "the COVID-19 disruption."
                ),
                "requested_start_date": "2020-02-01",
                "requested_end_date": "2020-04-30",
            },
            "metadata": allocation_response.metadata,
            "original": allocation_response.original,
            "modified": allocation_response.modified,
            "comparison": allocation_response.comparison,
        }
    )


def _registered_methods() -> set[tuple[str, str]]:
    return {
        (path, method.upper())
        for path, operations in app.openapi()["paths"].items()
        for method in operations
    }


def test_public_catalogue_requires_no_authentication_database_or_service(
    api_harness: ApiHarness,
) -> None:
    response = api_harness.client.get(CATALOGUE_PATH)

    assert response.status_code == 200
    catalogue = HistoricalScenarioListResponse.model_validate(response.json())
    assert [scenario.id for scenario in catalogue.scenarios] == [
        "covid-19-shock-2020",
        "inflation-rate-shock-2022",
        "dot-com-bust-2000-2002",
        "global-financial-crisis-2007-2009",
        "q4-market-selloff-2018",
    ]
    assert [scenario.requested_start_date for scenario in catalogue.scenarios] == [
        date(2020, 2, 1),
        date(2022, 1, 1),
        date(2000, 3, 10),
        date(2007, 10, 9),
        date(2018, 10, 1),
    ]
    assert [scenario.requested_end_date for scenario in catalogue.scenarios] == [
        date(2020, 4, 30),
        date(2022, 12, 31),
        date(2002, 10, 9),
        date(2009, 3, 9),
        date(2018, 12, 31),
    ]
    assert [
        scenario.model_dump() for scenario in catalogue.scenarios[:2]
    ] == [
        {
            "id": "covid-19-shock-2020",
            "display_name": "COVID-19 Market Shock",
            "description": (
                "A sharp market shock and early recovery period during the "
                "COVID-19 disruption."
            ),
            "requested_start_date": date(2020, 2, 1),
            "requested_end_date": date(2020, 4, 30),
        },
        {
            "id": "inflation-rate-shock-2022",
            "display_name": "2022 Inflation and Rate Shock",
            "description": (
                "An extended cross-asset stress period associated with "
                "inflation and rising interest rates."
            ),
            "requested_start_date": date(2022, 1, 1),
            "requested_end_date": date(2022, 12, 31),
        },
    ]
    api_harness.session_factory.assert_not_called()
    api_harness.service.run.assert_not_called()
    api_harness.session.commit.assert_not_called()
    api_harness.session.flush.assert_not_called()


def test_public_catalogue_order_is_deterministic() -> None:
    with TestClient(app) as client:
        first = client.get(CATALOGUE_PATH)
        second = client.get(CATALOGUE_PATH)

    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert len(first.json()["scenarios"]) == 5


def test_public_catalogue_ignores_invalid_or_x_user_id_authentication(
    api_harness: ApiHarness,
) -> None:
    response = api_harness.client.get(
        CATALOGUE_PATH,
        headers={
            "Authorization": "Bearer not-a-jwt",
            "X-User-ID": str(OTHER_USER_ID),
        },
    )

    assert response.status_code == 200
    api_harness.session_factory.assert_not_called()
    api_harness.service.run.assert_not_called()


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"X-User-ID": str(OWNER_ID)},
        {"Authorization": "Bearer not-a-jwt"},
    ],
)
def test_post_rejects_missing_invalid_or_x_user_id_only_authentication(
    api_harness: ApiHarness,
    headers: dict[str, str],
) -> None:
    response = api_harness.client.post(
        SIMULATION_PATH,
        headers=headers,
        json={"scenario_id": "covid-19-shock-2020"},
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid or missing authentication credentials"
    }
    assert response.headers["www-authenticate"] == "Bearer"
    api_harness.service.run.assert_not_called()
    api_harness.history_service.save.assert_not_called()
    api_harness.session.commit.assert_not_called()


def test_authenticated_post_passes_validated_identity_portfolio_and_request(
    api_harness: ApiHarness,
) -> None:
    expected = _simulation_response()
    response_before = expected.model_dump(mode="python")
    events: list[str] = []
    api_harness.service.run.side_effect = lambda **kwargs: (
        events.append("simulate") or expected
    )
    api_harness.history_service.save.side_effect = lambda **kwargs: (
        events.append("save") or MagicMock()
    )
    api_harness.session.commit.side_effect = lambda: events.append("commit")

    response = api_harness.client.post(
        SIMULATION_PATH,
        headers=REQUEST_HEADERS,
        json={"scenario_id": "covid-19-shock-2020"},
    )

    assert response.status_code == 200
    assert response.json() == expected.model_dump(mode="json")
    assert (
        HistoricalScenarioSimulationResponse.model_validate(response.json())
        == expected
    )
    call = api_harness.service.run.call_args.kwargs
    assert call["user_id"] == OWNER_ID
    assert call["portfolio_id"] == PORTFOLIO_ID
    assert call["request"] == HistoricalScenarioSimulationRequest(
        scenario_id="covid-19-shock-2020"
    )
    assert response.json()["metrics"]["sharpe_ratio"] is None
    assert response.json()["metrics"]["maximum_drawdown"]["max_drawdown"] < 0
    assert [point["date"] for point in response.json()["trajectory"]] == [
        "2020-02-03",
        "2020-03-02",
        "2020-03-23",
        "2020-04-30",
    ]
    api_harness.history_service.save.assert_called_once_with(
        user_id=OWNER_ID,
        portfolio_id=PORTFOLIO_ID,
        simulation_type="historical-scenario",
        scenario_id="covid-19-shock-2020",
        requested_start_date=date(2020, 2, 1),
        requested_end_date=date(2020, 4, 30),
        response=expected,
        baseline=LEGACY_BASELINE,
    )
    assert api_harness.history_service.save.call_args.kwargs["response"] is expected
    assert expected.model_dump(mode="python") == response_before
    assert events == ["simulate", "save", "commit"]
    api_harness.session.commit.assert_called_once_with()
    api_harness.session.flush.assert_not_called()
    api_harness.session.rollback.assert_not_called()


def test_authenticated_post_accepts_new_q4_scenario_and_persists_response(
    api_harness: ApiHarness,
) -> None:
    expected = _q4_simulation_response()
    response_before = expected.model_dump(mode="python")
    events: list[str] = []
    api_harness.service.run.side_effect = lambda **kwargs: (
        events.append("simulate") or expected
    )
    api_harness.history_service.save.side_effect = lambda **kwargs: (
        events.append("save") or MagicMock()
    )
    api_harness.session.commit.side_effect = lambda: events.append("commit")

    response = api_harness.client.post(
        SIMULATION_PATH,
        headers=REQUEST_HEADERS,
        json={"scenario_id": "q4-market-selloff-2018"},
    )

    assert response.status_code == 200
    assert response.json() == expected.model_dump(mode="json")
    assert (
        HistoricalScenarioSimulationResponse.model_validate(response.json())
        == expected
    )
    api_harness.service.run.assert_called_once_with(
        user_id=OWNER_ID,
        portfolio_id=PORTFOLIO_ID,
        request=HistoricalScenarioSimulationRequest(
            scenario_id="q4-market-selloff-2018"
        ),
    )
    api_harness.history_service.save.assert_called_once_with(
        user_id=OWNER_ID,
        portfolio_id=PORTFOLIO_ID,
        simulation_type="historical-scenario",
        scenario_id="q4-market-selloff-2018",
        requested_start_date=date(2018, 10, 1),
        requested_end_date=date(2018, 12, 31),
        response=expected,
        baseline=LEGACY_BASELINE,
    )
    assert api_harness.history_service.save.call_args.kwargs["response"] is expected
    assert expected.model_dump(mode="python") == response_before
    assert events == ["simulate", "save", "commit"]
    api_harness.session.commit.assert_called_once_with()
    api_harness.session.rollback.assert_not_called()


def test_x_user_id_does_not_override_authenticated_bearer_user(
    api_harness: ApiHarness,
) -> None:
    api_harness.service.run.return_value = _simulation_response()

    response = api_harness.client.post(
        SIMULATION_PATH,
        headers={
            **REQUEST_HEADERS,
            "X-User-ID": str(OTHER_USER_ID),
        },
        json={"scenario_id": "covid-19-shock-2020"},
    )

    assert response.status_code == 200
    assert api_harness.service.run.call_args.kwargs["user_id"] == OWNER_ID
    api_harness.session.get.assert_called_once_with(User, OWNER_ID)


@pytest.mark.parametrize("failure_stage", ["history-save", "commit"])
def test_historical_persistence_and_commit_failures_are_sanitized(
    api_harness: ApiHarness,
    failure_stage: str,
) -> None:
    api_harness.service.run.return_value = _simulation_response()
    internal_detail = f"sensitive historical {failure_stage} failure"
    if failure_stage == "history-save":
        api_harness.history_service.save.side_effect = RuntimeError(
            internal_detail
        )
    else:
        api_harness.session.commit.side_effect = RuntimeError(internal_detail)

    response = api_harness.client.post(
        SIMULATION_PATH,
        headers=REQUEST_HEADERS,
        json={"scenario_id": "covid-19-shock-2020"},
    )

    assert response.status_code == 500
    assert response.json() == {"detail": "Unable to run historical scenario"}
    assert internal_detail not in response.text
    api_harness.service.run.assert_called_once()
    api_harness.history_service.save.assert_called_once()
    if failure_stage == "history-save":
        api_harness.session.commit.assert_not_called()
    else:
        api_harness.session.commit.assert_called_once_with()
    api_harness.session.rollback.assert_called_once_with()


@pytest.mark.parametrize("portfolio_state", ["missing", "wrong-owner"])
def test_missing_and_wrong_owner_portfolios_are_identical_not_found(
    api_harness: ApiHarness,
    portfolio_state: str,
) -> None:
    api_harness.service.run.return_value = None

    response = api_harness.client.post(
        SIMULATION_PATH,
        headers=REQUEST_HEADERS,
        json={"scenario_id": "covid-19-shock-2020"},
    )

    assert portfolio_state in {"missing", "wrong-owner"}
    assert response.status_code == 404
    assert response.json() == {"detail": "Portfolio not found"}
    api_harness.history_service.save.assert_not_called()
    api_harness.session.commit.assert_not_called()
    api_harness.session.rollback.assert_called_once_with()


def test_unknown_scenario_maps_to_approved_not_found(
    api_harness: ApiHarness,
) -> None:
    api_harness.service.run.side_effect = HistoricalScenarioNotFoundError(
        "Historical scenario not found"
    )

    response = api_harness.client.post(
        SIMULATION_PATH,
        headers=REQUEST_HEADERS,
        json={"scenario_id": "unknown-scenario"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Historical scenario not found"}
    api_harness.history_service.save.assert_not_called()
    request = api_harness.service.run.call_args.kwargs["request"]
    assert request.scenario_id == "unknown-scenario"


def test_empty_portfolio_maps_to_unprocessable_detail(
    api_harness: ApiHarness,
) -> None:
    detail = "portfolio must contain at least one holding"
    api_harness.service.run.side_effect = EmptyPortfolioError(detail)

    response = api_harness.client.post(
        SIMULATION_PATH,
        headers=REQUEST_HEADERS,
        json={"scenario_id": "covid-19-shock-2020"},
    )

    assert response.status_code == 422
    assert response.json() == {"detail": detail}
    api_harness.history_service.save.assert_not_called()


def test_missing_symbols_map_to_unprocessable_with_order_preserved(
    api_harness: ApiHarness,
) -> None:
    detail = "market data is unavailable for requested symbols: MSFT, BND"
    api_harness.service.run.side_effect = ValueError(detail)

    response = api_harness.client.post(
        SIMULATION_PATH,
        headers=REQUEST_HEADERS,
        json={"scenario_id": "covid-19-shock-2020"},
    )

    assert response.status_code == 422
    assert response.json() == {"detail": detail}
    api_harness.history_service.save.assert_not_called()


def test_insufficient_aligned_history_maps_to_unprocessable(
    api_harness: ApiHarness,
) -> None:
    detail = "prices must contain at least three rows for historical simulation"
    api_harness.service.run.side_effect = ValueError(detail)

    response = api_harness.client.post(
        SIMULATION_PATH,
        headers=REQUEST_HEADERS,
        json={"scenario_id": "covid-19-shock-2020"},
    )

    assert response.status_code == 422
    assert response.json() == {"detail": detail}
    api_harness.history_service.save.assert_not_called()


@pytest.mark.parametrize(
    "failure",
    [
        RuntimeError("sensitive database failure"),
        ValueError("unexpected internal analytics detail"),
    ],
)
def test_unexpected_failure_maps_to_generic_internal_error(
    api_harness: ApiHarness,
    failure: Exception,
) -> None:
    api_harness.service.run.side_effect = failure

    response = api_harness.client.post(
        SIMULATION_PATH,
        headers=REQUEST_HEADERS,
        json={"scenario_id": "covid-19-shock-2020"},
    )

    assert response.status_code == 500
    assert response.json() == {"detail": "Unable to run historical scenario"}
    assert str(failure) not in response.text
    api_harness.history_service.save.assert_not_called()
    api_harness.session.commit.assert_not_called()


@pytest.mark.parametrize(
    "body",
    [
        {"scenario_id": " "},
        {
            "scenario_id": "covid-19-shock-2020",
            "allocation": "not accepted",
        },
    ],
)
def test_request_schema_validation_remains_framework_owned(
    api_harness: ApiHarness,
    body: dict[str, str],
) -> None:
    response = api_harness.client.post(
        SIMULATION_PATH,
        headers=REQUEST_HEADERS,
        json=body,
    )

    assert response.status_code == 422
    api_harness.service.run.assert_not_called()


def test_malformed_portfolio_uuid_uses_existing_framework_validation(
    api_harness: ApiHarness,
) -> None:
    response = api_harness.client.post(
        "/api/portfolios/not-a-uuid/simulations/historical-scenarios",
        headers=REQUEST_HEADERS,
        json={"scenario_id": "covid-19-shock-2020"},
    )

    assert response.status_code == 422
    api_harness.service.run.assert_not_called()


def test_authenticated_allocation_post_persists_and_preserves_response(
    allocation_api_harness: AllocationApiHarness,
) -> None:
    expected = _allocation_simulation_response()
    request_body = _allocation_request_body()
    response_before = expected.model_dump(mode="python")
    events: list[str] = []
    allocation_api_harness.service.run.side_effect = lambda **kwargs: (
        events.append("simulate") or expected
    )
    allocation_api_harness.history_service.save.side_effect = lambda **kwargs: (
        events.append("save") or MagicMock()
    )
    allocation_api_harness.session.commit.side_effect = lambda: events.append(
        "commit"
    )

    response = allocation_api_harness.client.post(
        ALLOCATION_SIMULATION_PATH,
        headers=REQUEST_HEADERS,
        json=request_body,
    )

    assert response.status_code == 200
    assert response.json() == expected.model_dump(mode="json")
    assert AllocationSimulationResponse.model_validate(response.json()) == expected
    allocation_api_harness.service.run.assert_called_once_with(
        user_id=OWNER_ID,
        portfolio_id=PORTFOLIO_ID,
        request=AllocationSimulationRequest.model_validate(request_body),
    )
    assert response.json()["original"] == expected.model_dump(mode="json")[
        "original"
    ]
    assert response.json()["modified"] == expected.model_dump(mode="json")[
        "modified"
    ]
    assert response.json()["comparison"] == expected.model_dump(mode="json")[
        "comparison"
    ]
    assert response.json()["comparison"]["sharpe_ratio_delta"] is None
    assert [
        holding["symbol"]
        for holding in response.json()["original"]["allocation"]
    ] == ["BETA", "ZERO", "ALPHA"]
    assert [
        holding["symbol"]
        for holding in response.json()["modified"]["allocation"]
    ] == ["BETA", "ZERO", "ALPHA"]
    allocation_api_harness.history_service.save.assert_called_once_with(
        user_id=OWNER_ID,
        portfolio_id=PORTFOLIO_ID,
        simulation_type="allocation",
        scenario_id=None,
        requested_start_date=date(2020, 2, 1),
        requested_end_date=date(2020, 4, 30),
        response=expected,
        baseline=LEGACY_BASELINE,
    )
    assert (
        allocation_api_harness.history_service.save.call_args.kwargs["response"]
        is expected
    )
    assert expected.model_dump(mode="python") == response_before
    assert events == ["simulate", "save", "commit"]
    allocation_api_harness.session.commit.assert_called_once_with()
    allocation_api_harness.session.flush.assert_not_called()
    allocation_api_harness.session.rollback.assert_not_called()


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": "Bearer not-a-jwt"},
        {"X-User-ID": str(OWNER_ID)},
    ],
)
def test_allocation_post_requires_existing_bearer_authentication(
    allocation_api_harness: AllocationApiHarness,
    headers: dict[str, str],
) -> None:
    response = allocation_api_harness.client.post(
        ALLOCATION_SIMULATION_PATH,
        headers=headers,
        json=_allocation_request_body(),
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid or missing authentication credentials"
    }
    assert response.headers["www-authenticate"] == "Bearer"
    allocation_api_harness.service.run.assert_not_called()
    allocation_api_harness.history_service.save.assert_not_called()
    allocation_api_harness.session.commit.assert_not_called()


@pytest.mark.parametrize("failure_stage", ["history-save", "commit"])
def test_allocation_persistence_and_commit_failures_are_sanitized(
    allocation_api_harness: AllocationApiHarness,
    failure_stage: str,
) -> None:
    allocation_api_harness.service.run.return_value = (
        _allocation_simulation_response()
    )
    internal_detail = f"sensitive allocation {failure_stage} failure"
    if failure_stage == "history-save":
        allocation_api_harness.history_service.save.side_effect = RuntimeError(
            internal_detail
        )
    else:
        allocation_api_harness.session.commit.side_effect = RuntimeError(
            internal_detail
        )

    response = allocation_api_harness.client.post(
        ALLOCATION_SIMULATION_PATH,
        headers=REQUEST_HEADERS,
        json=_allocation_request_body(),
    )

    assert response.status_code == 500
    assert response.json() == {
        "detail": "Unable to run allocation simulation"
    }
    assert internal_detail not in response.text
    allocation_api_harness.service.run.assert_called_once()
    allocation_api_harness.history_service.save.assert_called_once()
    if failure_stage == "history-save":
        allocation_api_harness.session.commit.assert_not_called()
    else:
        allocation_api_harness.session.commit.assert_called_once_with()
    allocation_api_harness.session.rollback.assert_called_once_with()


@pytest.mark.parametrize("portfolio_state", ["missing", "wrong-owner"])
def test_allocation_missing_and_wrong_owner_are_identical_not_found(
    allocation_api_harness: AllocationApiHarness,
    portfolio_state: str,
) -> None:
    allocation_api_harness.service.run.return_value = None

    response = allocation_api_harness.client.post(
        ALLOCATION_SIMULATION_PATH,
        headers=REQUEST_HEADERS,
        json=_allocation_request_body(),
    )

    assert portfolio_state in {"missing", "wrong-owner"}
    assert response.status_code == 404
    assert response.json() == {"detail": "Portfolio not found"}
    allocation_api_harness.service.run.assert_called_once()
    allocation_api_harness.history_service.save.assert_not_called()
    allocation_api_harness.session.commit.assert_not_called()
    allocation_api_harness.session.rollback.assert_called_once_with()


@pytest.mark.parametrize(
    ("failure", "detail"),
    [
        (
            AllocationSymbolMismatchError(
                "modified allocation symbols must exactly match saved "
                "portfolio symbols"
            ),
            "modified allocation symbols must exactly match saved portfolio "
            "symbols",
        ),
        (
            AllocationEmptyPortfolioError(
                "portfolio must contain at least one holding"
            ),
            "portfolio must contain at least one holding",
        ),
        (
            ValueError(
                "market data is unavailable for requested symbols: MSFT, BND"
            ),
            "market data is unavailable for requested symbols: MSFT, BND",
        ),
        (
            ValueError(
                "prices must contain at least three rows for historical "
                "simulation"
            ),
            "prices must contain at least three rows for historical simulation",
        ),
    ],
)
def test_expected_allocation_failures_preserve_detail_as_unprocessable(
    allocation_api_harness: AllocationApiHarness,
    failure: Exception,
    detail: str,
) -> None:
    allocation_api_harness.service.run.side_effect = failure

    response = allocation_api_harness.client.post(
        ALLOCATION_SIMULATION_PATH,
        headers=REQUEST_HEADERS,
        json=_allocation_request_body(),
    )

    assert response.status_code == 422
    assert response.json() == {"detail": detail}
    allocation_api_harness.service.run.assert_called_once()
    allocation_api_harness.history_service.save.assert_not_called()
    allocation_api_harness.session.commit.assert_not_called()


@pytest.mark.parametrize(
    "failure",
    [
        RuntimeError("sensitive allocation database failure"),
        ValueError("unexpected internal allocation analytics detail"),
    ],
)
def test_unexpected_allocation_failure_is_stable_and_private(
    allocation_api_harness: AllocationApiHarness,
    failure: Exception,
) -> None:
    allocation_api_harness.service.run.side_effect = failure

    response = allocation_api_harness.client.post(
        ALLOCATION_SIMULATION_PATH,
        headers=REQUEST_HEADERS,
        json=_allocation_request_body(),
    )

    assert response.status_code == 500
    assert response.json() == {
        "detail": "Unable to run allocation simulation"
    }
    assert str(failure) not in response.text
    allocation_api_harness.service.run.assert_called_once()
    allocation_api_harness.history_service.save.assert_not_called()
    allocation_api_harness.session.commit.assert_not_called()


def test_authenticated_combined_post_persists_and_preserves_response(
    combined_api_harness: CombinedApiHarness,
) -> None:
    expected = _combined_simulation_response()
    request_body = _combined_request_body()
    response_before = expected.model_dump(mode="python")
    events: list[str] = []
    combined_api_harness.service.run.side_effect = lambda **kwargs: (
        events.append("simulate") or expected
    )
    combined_api_harness.history_service.save.side_effect = lambda **kwargs: (
        events.append("save") or MagicMock()
    )
    combined_api_harness.session.commit.side_effect = lambda: events.append(
        "commit"
    )

    response = combined_api_harness.client.post(
        COMBINED_SIMULATION_PATH,
        headers=REQUEST_HEADERS,
        json=request_body,
    )

    assert response.status_code == 200
    assert response.json() == expected.model_dump(mode="json")
    assert CombinedSimulationResponse.model_validate(response.json()) == expected
    combined_api_harness.service_type.assert_called_once_with(
        combined_api_harness.session
    )
    combined_api_harness.service.run.assert_called_once_with(
        user_id=OWNER_ID,
        portfolio_id=PORTFOLIO_ID,
        request=CombinedSimulationRequest.model_validate(request_body),
    )
    assert list(response.json()) == [
        "portfolio_id",
        "portfolio_name",
        "scenario",
        "metadata",
        "original",
        "modified",
        "comparison",
    ]
    assert response.json()["scenario"]["requested_start_date"] == "2020-02-01"
    assert response.json()["metadata"]["effective_start_date"] == "2020-02-03"
    assert response.json()["original"] == expected.model_dump(mode="json")[
        "original"
    ]
    assert response.json()["modified"] == expected.model_dump(mode="json")[
        "modified"
    ]
    assert response.json()["comparison"] == expected.model_dump(mode="json")[
        "comparison"
    ]
    assert response.json()["comparison"]["sharpe_ratio_delta"] is None
    combined_api_harness.history_service.save.assert_called_once_with(
        user_id=OWNER_ID,
        portfolio_id=PORTFOLIO_ID,
        simulation_type="combined",
        scenario_id="covid-19-shock-2020",
        requested_start_date=date(2020, 2, 1),
        requested_end_date=date(2020, 4, 30),
        response=expected,
        baseline=LEGACY_BASELINE,
    )
    assert (
        combined_api_harness.history_service.save.call_args.kwargs["response"]
        is expected
    )
    assert expected.model_dump(mode="python") == response_before
    assert events == ["simulate", "save", "commit"]
    combined_api_harness.session.commit.assert_called_once_with()
    combined_api_harness.session.flush.assert_not_called()
    combined_api_harness.session.rollback.assert_not_called()


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": "Bearer not-a-jwt"},
        {"X-User-ID": str(OWNER_ID)},
    ],
)
def test_combined_post_requires_existing_bearer_authentication(
    combined_api_harness: CombinedApiHarness,
    headers: dict[str, str],
) -> None:
    response = combined_api_harness.client.post(
        COMBINED_SIMULATION_PATH,
        headers=headers,
        json=_combined_request_body(),
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid or missing authentication credentials"
    }
    assert response.headers["www-authenticate"] == "Bearer"
    combined_api_harness.service.run.assert_not_called()
    combined_api_harness.history_service.save.assert_not_called()
    combined_api_harness.session.commit.assert_not_called()


@pytest.mark.parametrize("failure_stage", ["history-save", "commit"])
def test_combined_persistence_and_commit_failures_are_sanitized(
    combined_api_harness: CombinedApiHarness,
    failure_stage: str,
) -> None:
    combined_api_harness.service.run.return_value = (
        _combined_simulation_response()
    )
    internal_detail = f"sensitive combined {failure_stage} failure"
    if failure_stage == "history-save":
        combined_api_harness.history_service.save.side_effect = RuntimeError(
            internal_detail
        )
    else:
        combined_api_harness.session.commit.side_effect = RuntimeError(
            internal_detail
        )

    response = combined_api_harness.client.post(
        COMBINED_SIMULATION_PATH,
        headers=REQUEST_HEADERS,
        json=_combined_request_body(),
    )

    assert response.status_code == 500
    assert response.json() == {"detail": "Unable to run combined simulation"}
    assert internal_detail not in response.text
    combined_api_harness.service.run.assert_called_once()
    combined_api_harness.history_service.save.assert_called_once()
    if failure_stage == "history-save":
        combined_api_harness.session.commit.assert_not_called()
    else:
        combined_api_harness.session.commit.assert_called_once_with()
    combined_api_harness.session.rollback.assert_called_once_with()


@pytest.mark.parametrize("portfolio_state", ["missing", "wrong-owner"])
def test_combined_missing_and_wrong_owner_are_identical_not_found(
    combined_api_harness: CombinedApiHarness,
    portfolio_state: str,
) -> None:
    combined_api_harness.service.run.return_value = None

    response = combined_api_harness.client.post(
        COMBINED_SIMULATION_PATH,
        headers=REQUEST_HEADERS,
        json=_combined_request_body(),
    )

    assert portfolio_state in {"missing", "wrong-owner"}
    assert response.status_code == 404
    assert response.status_code != 403
    assert response.json() == {"detail": "Portfolio not found"}
    combined_api_harness.service.run.assert_called_once()
    combined_api_harness.history_service.save.assert_not_called()
    combined_api_harness.session.commit.assert_not_called()
    combined_api_harness.session.rollback.assert_called_once_with()


def test_combined_unknown_scenario_maps_to_existing_not_found(
    combined_api_harness: CombinedApiHarness,
) -> None:
    combined_api_harness.service.run.side_effect = (
        HistoricalScenarioNotFoundError("Historical scenario not found")
    )
    body = _combined_request_body()
    body["scenario_id"] = "unknown-scenario"

    response = combined_api_harness.client.post(
        COMBINED_SIMULATION_PATH,
        headers=REQUEST_HEADERS,
        json=body,
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Historical scenario not found"}
    combined_api_harness.service.run.assert_called_once()
    combined_api_harness.history_service.save.assert_not_called()
    request = combined_api_harness.service.run.call_args.kwargs["request"]
    assert request.scenario_id == "unknown-scenario"


@pytest.mark.parametrize(
    ("failure", "detail"),
    [
        (
            AllocationSymbolMismatchError(
                "modified allocation symbols must exactly match saved "
                "portfolio symbols"
            ),
            "modified allocation symbols must exactly match saved portfolio "
            "symbols",
        ),
        (
            AllocationEmptyPortfolioError(
                "portfolio must contain at least one holding"
            ),
            "portfolio must contain at least one holding",
        ),
        (
            ValueError(
                "market data is unavailable for requested symbols: MSFT, BND"
            ),
            "market data is unavailable for requested symbols: MSFT, BND",
        ),
        (
            ValueError(
                "prices must contain at least three rows for historical "
                "simulation"
            ),
            "prices must contain at least three rows for historical simulation",
        ),
    ],
)
def test_combined_expected_failures_preserve_detail_as_unprocessable(
    combined_api_harness: CombinedApiHarness,
    failure: Exception,
    detail: str,
) -> None:
    combined_api_harness.service.run.side_effect = failure

    response = combined_api_harness.client.post(
        COMBINED_SIMULATION_PATH,
        headers=REQUEST_HEADERS,
        json=_combined_request_body(),
    )

    assert response.status_code == 422
    assert response.json() == {"detail": detail}
    combined_api_harness.service.run.assert_called_once()
    combined_api_harness.history_service.save.assert_not_called()
    combined_api_harness.session.commit.assert_not_called()


@pytest.mark.parametrize(
    "failure",
    [
        RuntimeError("sensitive combined database failure"),
        ValueError("unexpected internal combined analytics detail"),
    ],
)
def test_unexpected_combined_failure_is_stable_and_private(
    combined_api_harness: CombinedApiHarness,
    failure: Exception,
) -> None:
    combined_api_harness.service.run.side_effect = failure

    response = combined_api_harness.client.post(
        COMBINED_SIMULATION_PATH,
        headers=REQUEST_HEADERS,
        json=_combined_request_body(),
    )

    assert response.status_code == 500
    assert response.json() == {
        "detail": "Unable to run combined simulation"
    }
    assert str(failure) not in response.text
    combined_api_harness.service.run.assert_called_once()
    combined_api_harness.history_service.save.assert_not_called()
    combined_api_harness.session.commit.assert_not_called()


@pytest.mark.parametrize(
    "body",
    [
        {"scenario_id": "covid-19-shock-2020"},
        {
            **_combined_request_body(),
            "scenario_id": " ",
        },
        {
            **_combined_request_body(),
            "unexpected": "forbidden",
        },
    ],
)
def test_malformed_combined_request_uses_framework_validation(
    combined_api_harness: CombinedApiHarness,
    body: dict[str, object],
) -> None:
    response = combined_api_harness.client.post(
        COMBINED_SIMULATION_PATH,
        headers=REQUEST_HEADERS,
        json=body,
    )

    assert response.status_code == 422
    combined_api_harness.service.run.assert_not_called()


def test_route_source_uses_only_approved_history_and_transaction_boundaries(
) -> None:
    source = inspect.getsource(route_module)

    for forbidden_reference in (
        "session.flush",
        "save_snapshot",
        "AnalysisRepository",
        "SimulationRepository",
        "session.add",
        "Authorization",
        "decode_access_token",
        "X-User-ID",
        "yfinance",
        "read_csv",
    ):
        assert forbidden_reference not in source

    assert source.count("SimulationHistoryService(session).save(") == 3
    assert source.count("session.commit()") == 4
    assert source.count("SimulationHistoryService(session).delete(") == 1


def test_new_and_existing_route_surface_remains_registered(
    api_harness: ApiHarness,
) -> None:
    methods = _registered_methods()

    assert ("/api/simulations/historical-scenarios", "GET") in methods
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
    assert ("/api/health", "GET") in methods
    assert ("/api/auth/register", "POST") in methods
    assert ("/api/auth/login", "POST") in methods
    assert ("/api/auth/me", "GET") in methods
    assert ("/api/portfolios", "GET") in methods
    assert ("/api/portfolios/{portfolio_id}", "GET") in methods
    assert ("/api/portfolios/{portfolio_id}/reports", "POST") in methods

    health = api_harness.client.get("/api/health")
    assert health.status_code == 200
    assert health.json() == {
        "status": "healthy",
        "app_name": settings.app_name,
        "environment": settings.app_env,
    }


def test_app_import_and_public_health_keep_database_initialization_lazy() -> None:
    assert dependency_module._get_session_factory.cache_info().currsize == 0

    with (
        patch.object(
            dependency_module,
            "create_database_engine",
        ) as create_database_engine,
        TestClient(app) as client,
    ):
        response = client.get("/api/health")

    assert response.status_code == 200
    create_database_engine.assert_not_called()


@pytest.mark.parametrize(
    "fixture_name",
    ["api_harness", "allocation_api_harness", "combined_api_harness"],
)
def test_each_post_captures_one_utc_valuation_date_at_route_boundary(
    request: pytest.FixtureRequest,
    fixture_name: str,
    notifications_service,
) -> None:
    harness, path, body, expected = _post_case(request, fixture_name)
    harness.service.run.return_value = expected
    harness.history_service.save.return_value = MagicMock()
    fixed_date = date(2026, 9, 12)

    with patch.object(
        route_module,
        "_current_utc_date",
        return_value=fixed_date,
    ) as current_date:
        response = harness.client.post(
            path,
            headers=REQUEST_HEADERS,
            json=body,
        )

    assert response.status_code == 200
    notifications_service.record_saved.assert_called_once_with(user_id=OWNER_ID, portfolio_id=PORTFOLIO_ID, kind="simulation", resource_id=harness.history_service.save.return_value.id)
    current_date.assert_called_once_with()
    assert harness.service.run_with_context.call_count == 1
    assert (
        harness.service.run_with_context.call_args.kwargs["valuation_date"]
        == fixed_date
    )
    harness.history_service.save.assert_called_once()
    harness.session.commit.assert_called_once_with()


@pytest.mark.parametrize(
    "fixture_name",
    ["api_harness", "allocation_api_harness", "combined_api_harness"],
)
def test_real_incompatible_holding_state_maps_to_private_conflict_without_save(
    request: pytest.FixtureRequest,
    fixture_name: str,
) -> None:
    harness, path, body, _ = _post_case(request, fixture_name)
    harness.service.run.side_effect = InvalidHoldingModeError(
        "sensitive mixed holding details"
    )

    response = harness.client.post(path, headers=REQUEST_HEADERS, json=body)

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Portfolio cannot be simulated in its current holding state"
    }
    assert "sensitive mixed holding details" not in response.text
    harness.history_service.save.assert_not_called()
    harness.session.commit.assert_not_called()


@pytest.mark.parametrize(
    "fixture_name",
    ["api_harness", "allocation_api_harness", "combined_api_harness"],
)
@pytest.mark.parametrize(
    "internal_detail",
    [
        "sensitive missing current asset price details",
        "sensitive stale current asset price details",
    ],
    ids=["missing", "stale"],
)
def test_current_asset_price_failure_maps_to_503_without_history_or_commit(
    request: pytest.FixtureRequest,
    fixture_name: str,
    internal_detail: str,
) -> None:
    harness, path, body, _ = _post_case(request, fixture_name)
    harness.service.run.side_effect = MarketDataUnavailableError(internal_detail)

    response = harness.client.post(path, headers=REQUEST_HEADERS, json=body)

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Required current market data is unavailable"
    }
    assert internal_detail not in response.text
    harness.history_service.save.assert_not_called()
    harness.session.commit.assert_not_called()
