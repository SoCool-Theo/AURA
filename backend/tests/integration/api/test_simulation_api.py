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
    HistoricalScenarioListResponse,
    HistoricalScenarioSimulationRequest,
    HistoricalScenarioSimulationResponse,
)
from app.services.historical_scenario_service import (
    EmptyPortfolioError,
    HistoricalScenarioNotFoundError,
)


OWNER_ID = UUID("62a1279e-bc8d-4c89-876d-a09250b50395")
OTHER_USER_ID = UUID("10000000-0000-0000-0000-000000000002")
PORTFOLIO_ID = UUID("e6518442-58cb-408f-ae3f-bf47fb00b555")
JWT_SECRET = "phase-5-historical-simulation-api-test-secret"
CATALOGUE_PATH = "/api/simulations/historical-scenarios"
SIMULATION_PATH = (
    f"/api/portfolios/{PORTFOLIO_ID}/simulations/historical-scenarios"
)
REQUEST_HEADERS: dict[str, str] = {}


@dataclass
class ApiHarness:
    client: TestClient
    session: MagicMock
    service: MagicMock
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


@pytest.fixture
def api_harness() -> Iterator[ApiHarness]:
    session = MagicMock(spec=Session)
    session.get.return_value = User(id=OWNER_ID)
    session_factory = MagicMock(return_value=session)
    service = MagicMock(spec=route_module.HistoricalScenarioService)

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
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        yield ApiHarness(
            client=client,
            session=session,
            service=service,
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
    ]
    assert [scenario.requested_start_date for scenario in catalogue.scenarios] == [
        date(2020, 2, 1),
        date(2022, 1, 1),
    ]
    assert [scenario.requested_end_date for scenario in catalogue.scenarios] == [
        date(2020, 4, 30),
        date(2022, 12, 31),
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
    assert len(first.json()["scenarios"]) == 2


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
    api_harness.session.commit.assert_not_called()


def test_authenticated_post_passes_validated_identity_portfolio_and_request(
    api_harness: ApiHarness,
) -> None:
    expected = _simulation_response()
    api_harness.service.run.return_value = expected

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
    api_harness.session.commit.assert_not_called()
    api_harness.session.flush.assert_not_called()
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


def test_route_source_is_read_only_and_has_no_persistence_or_manual_auth() -> None:
    source = inspect.getsource(route_module)

    for forbidden_reference in (
        "session.commit",
        "session.flush",
        "save_snapshot",
        "AnalysisRepository",
        "Authorization",
        "decode_access_token",
        "X-User-ID",
        "yfinance",
        "read_csv",
    ):
        assert forbidden_reference not in source


def test_new_and_existing_route_surface_remains_registered(
    api_harness: ApiHarness,
) -> None:
    methods = _registered_methods()

    assert ("/api/simulations/historical-scenarios", "GET") in methods
    assert (
        "/api/portfolios/{portfolio_id}/simulations/historical-scenarios",
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
