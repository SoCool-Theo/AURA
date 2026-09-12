from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.orm import Session

import app.api.dependencies as dependency_module
import app.api.routes.agent as route_module
import app.services.agent_service as agent_service_module
from app.agents.provider import (
    LLMProviderResponseError,
    LLMProviderTimeoutError,
    LLMProviderUnavailableError,
    ProviderRequest,
    ProviderResponse,
)
from app.core.config import settings
from app.core.security import create_access_token
from app.database.models import User
from app.main import app
from app.schemas.agent import AgentExplainResponse
from app.services.analysis_reporting_service import ReportNotFoundError
from app.services.market_data_service import MarketDataUnavailableError
from app.services.portfolio_valuation_service import InvalidHoldingModeError
from app.services.simulation_history_service import SimulationNotFoundError


OWNER_ID = UUID("62a1279e-bc8d-4c89-876d-a09250b50395")
PORTFOLIO_ID = UUID("e6518442-58cb-408f-ae3f-bf47fb00b555")
REPORT_ID = UUID("10000000-0000-0000-0000-000000000001")
SIMULATION_ID = UUID("30000000-0000-0000-0000-000000000001")
JWT_SECRET = "phase-8-agent-api-test-secret"
PATH = "/api/agent/explain"


class FakeProvider:
    def __init__(self) -> None:
        self.requests: list[ProviderRequest] = []
        self.error: Exception | None = None

    def generate(self, request: ProviderRequest) -> ProviderResponse:
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        return ProviderResponse("Aura explains the stored portfolio result.")


class FakeTools:
    mode = "available"
    instances: list["FakeTools"] = []

    def __init__(
        self,
        session: Session,
        *,
        user_id: UUID,
        portfolio_id: UUID,
        valuation_date: date,
    ) -> None:
        self.session = session
        self.user_id = user_id
        self.portfolio_id = portfolio_id
        self.valuation_date = valuation_date
        self.calls: list[str] = []
        self.portfolio_resolution_flags: list[bool] = []
        self.__class__.instances.append(self)

    def get_portfolio_context(
        self,
        *,
        resolve_current_baseline: bool = True,
    ) -> dict[str, object] | None:
        self.calls.append("portfolio")
        self.portfolio_resolution_flags.append(resolve_current_baseline)
        if self.mode == "missing-portfolio":
            return None
        if resolve_current_baseline and self.mode in {
            "missing-current-price",
            "stale-current-price",
        }:
            raise MarketDataUnavailableError(self.mode)
        if resolve_current_baseline and self.mode == "incompatible-holdings":
            raise InvalidHoldingModeError(self.mode)
        return {"id": str(self.portfolio_id), "name": "Core", "holdings": []}

    def get_latest_report(self) -> dict[str, object] | None:
        self.calls.append("latest_report")
        return {
            "available": True,
            "report": {"id": str(REPORT_ID), "analysis": {"max_drawdown": -0.2}},
        }

    def get_report(self, report_id: UUID) -> dict[str, object] | None:
        self.calls.append("report")
        if self.mode == "missing-report":
            raise ReportNotFoundError()
        return {"id": str(report_id), "analysis": {"max_drawdown": -0.2}}

    def get_simulation(self, simulation_id: UUID) -> dict[str, object] | None:
        self.calls.append("simulation")
        if self.mode == "missing-simulation":
            raise SimulationNotFoundError("Simulation not found")
        return {"id": str(simulation_id), "result": {"comparison": {"delta": -0.1}}}


@dataclass
class ApiHarness:
    client: TestClient
    session: MagicMock
    provider: FakeProvider


@pytest.fixture
def api_harness() -> Iterator[ApiHarness]:
    session = MagicMock(spec=Session)
    session.get.return_value = User(id=OWNER_ID)
    session_factory = MagicMock(return_value=session)
    provider = FakeProvider()
    FakeTools.mode = "available"
    FakeTools.instances = []
    app.dependency_overrides[route_module.get_agent_provider] = lambda: provider

    with (
        patch.object(dependency_module, "_get_session_factory", return_value=session_factory),
        patch.object(agent_service_module, "AuraAgentTools", FakeTools),
        patch.object(settings, "jwt_secret_key", SecretStr(JWT_SECRET)),
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        yield ApiHarness(client=client, session=session, provider=provider)
    app.dependency_overrides.pop(route_module.get_agent_provider, None)


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(OWNER_ID)}"}


def _payload(**changes: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "portfolio_id": str(PORTFOLIO_ID),
        "message": "Why is my portfolio risky?",
    }
    payload.update(changes)
    return payload


def test_openapi_registers_exact_agent_endpoint_and_safe_body(api_harness: ApiHarness) -> None:
    schema = api_harness.client.get("/openapi.json").json()
    operation = schema["paths"][PATH]["post"]
    request_schema = schema["components"]["schemas"]["AgentExplainRequest"]

    assert set(schema["paths"][PATH]) == {"post"}
    assert operation["tags"] == ["Agent"]
    assert request_schema["additionalProperties"] is False
    assert not {"user_id", "provider", "model", "system_prompt"}.intersection(
        request_schema["properties"]
    )
    assert api_harness.client.get("/api/health").status_code == 200


@pytest.mark.parametrize(
    "headers",
    [{}, {"Authorization": "Bearer not-a-jwt"}, {"X-User-ID": str(OWNER_ID)}],
)
def test_agent_endpoint_requires_existing_bearer_authentication(
    api_harness: ApiHarness,
    headers: dict[str, str],
) -> None:
    response = api_harness.client.post(PATH, headers=headers, json=_payload())

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert api_harness.provider.requests == []


@pytest.mark.parametrize(
    "payload",
    [
        {"portfolio_id": "not-a-uuid", "message": "Explain risk."},
        {"portfolio_id": str(PORTFOLIO_ID), "message": " \t\n "},
        {**_payload(), "unexpected": True},
        {**_payload(), "user_id": str(OWNER_ID)},
        {**_payload(), "provider": "demo"},
        {**_payload(), "model": "demo"},
    ],
)
def test_agent_request_uses_strict_existing_schema(
    api_harness: ApiHarness,
    payload: dict[str, object],
) -> None:
    response = api_harness.client.post(PATH, headers=_headers(), json=payload)

    assert response.status_code == 422
    assert api_harness.provider.requests == []


def test_owned_request_returns_public_response_with_grounded_sources(
    api_harness: ApiHarness,
) -> None:
    response = api_harness.client.post(PATH, headers=_headers(), json=_payload())

    assert response.status_code == 200
    validated = AgentExplainResponse.model_validate(response.json())
    assert [source.type for source in validated.sources] == ["portfolio", "report"]
    assert len(api_harness.provider.requests) == 1
    assert api_harness.provider.requests[0].grounded_context["portfolio"]["id"] == str(PORTFOLIO_ID)
    assert FakeTools.instances[0].portfolio_resolution_flags == [True]
    api_harness.session.commit.assert_not_called()
    api_harness.session.flush.assert_not_called()


def test_agent_route_captures_one_utc_valuation_date(
    api_harness: ApiHarness,
) -> None:
    valuation_date = date(2026, 9, 12)

    with patch.object(
        route_module,
        "_current_utc_date",
        return_value=valuation_date,
    ) as current_date:
        response = api_harness.client.post(
            PATH,
            headers=_headers(),
            json=_payload(),
        )

    assert response.status_code == 200
    current_date.assert_called_once_with()
    assert FakeTools.instances[0].valuation_date == valuation_date


@pytest.mark.parametrize(
    ("changes", "expected_sources"),
    [
        ({"report_id": str(REPORT_ID)}, ["portfolio", "report"]),
        ({"simulation_id": str(SIMULATION_ID)}, ["portfolio", "report", "simulation"]),
        (
            {"report_id": str(REPORT_ID), "simulation_id": str(SIMULATION_ID)},
            ["portfolio", "report", "simulation"],
        ),
    ],
)
def test_agent_accepts_optional_grounding_references(
    api_harness: ApiHarness,
    changes: dict[str, str],
    expected_sources: list[str],
) -> None:
    response = api_harness.client.post(
        PATH,
        headers=_headers(),
        json=_payload(**changes),
    )

    assert response.status_code == 200
    assert [source["type"] for source in response.json()["sources"]] == expected_sources
    assert len(api_harness.provider.requests) == 1


@pytest.mark.parametrize("message", ["Should I buy AAPL?", "Should I sell NVDA?"])
def test_advice_refusal_is_successful_without_provider_or_data_lookups(
    api_harness: ApiHarness,
    message: str,
) -> None:
    response = api_harness.client.post(
        PATH,
        headers=_headers(),
        json=_payload(message=message),
    )

    assert response.status_code == 200
    assert response.json()["sources"] == []
    assert "can't recommend whether you should buy, sell, or hold" in response.json()["answer"]
    assert api_harness.provider.requests == []
    assert len(FakeTools.instances) == 1
    assert FakeTools.instances[0].calls == []


@pytest.mark.parametrize(
    ("mode", "payload", "detail"),
    [
        ("missing-portfolio", _payload(), "Portfolio not found"),
        ("missing-report", _payload(report_id=str(REPORT_ID)), "Report not found"),
        ("missing-simulation", _payload(simulation_id=str(SIMULATION_ID)), "Simulation not found"),
    ],
)
def test_private_resource_errors_use_existing_not_found_messages(
    api_harness: ApiHarness,
    mode: str,
    payload: dict[str, object],
    detail: str,
) -> None:
    FakeTools.mode = mode
    response = api_harness.client.post(PATH, headers=_headers(), json=payload)

    assert response.status_code == 404
    assert response.status_code != 403
    assert response.json() == {"detail": detail}
    assert api_harness.provider.requests == []


@pytest.mark.parametrize(
    "mode",
    ["missing-current-price", "stale-current-price"],
)
def test_real_live_portfolio_current_data_failures_map_to_503_without_fallback(
    api_harness: ApiHarness,
    mode: str,
) -> None:
    FakeTools.mode = mode

    response = api_harness.client.post(
        PATH,
        headers=_headers(),
        json=_payload(),
    )

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Required current market data is unavailable"
    }
    assert FakeTools.instances[0].portfolio_resolution_flags == [True]
    assert api_harness.provider.requests == []


def test_incompatible_holding_state_maps_to_409(
    api_harness: ApiHarness,
) -> None:
    FakeTools.mode = "incompatible-holdings"

    response = api_harness.client.post(
        PATH,
        headers=_headers(),
        json=_payload(),
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Portfolio cannot be explained in its current holding state"
    }
    assert api_harness.provider.requests == []


@pytest.mark.parametrize(
    "changes",
    [
        {"report_id": str(REPORT_ID)},
        {"simulation_id": str(SIMULATION_ID)},
    ],
)
def test_saved_context_explanation_is_independent_of_stale_current_prices(
    api_harness: ApiHarness,
    changes: dict[str, str],
) -> None:
    FakeTools.mode = "stale-current-price"

    response = api_harness.client.post(
        PATH,
        headers=_headers(),
        json=_payload(**changes),
    )

    assert response.status_code == 200
    assert FakeTools.instances[0].portfolio_resolution_flags == [False]
    assert len(api_harness.provider.requests) == 1


@pytest.mark.parametrize(
    ("error", "status_code", "detail"),
    [
        (LLMProviderTimeoutError(), 503, "AI explanation service is currently unavailable."),
        (LLMProviderUnavailableError(), 503, "AI explanation service is currently unavailable."),
        (LLMProviderResponseError(), 502, "AI explanation service returned an invalid response."),
    ],
)
def test_provider_failures_are_safely_mapped(
    api_harness: ApiHarness,
    error: Exception,
    status_code: int,
    detail: str,
) -> None:
    api_harness.provider.error = error
    response = api_harness.client.post(PATH, headers=_headers(), json=_payload())

    assert response.status_code == status_code
    assert response.json() == {"detail": detail}
    assert "secret" not in response.text
    assert len(api_harness.provider.requests) == 1


def test_default_provider_truthfully_returns_unavailable_after_authentication() -> None:
    session = MagicMock(spec=Session)
    session.get.return_value = User(id=OWNER_ID)
    session_factory = MagicMock(return_value=session)
    with (
        patch.object(dependency_module, "_get_session_factory", return_value=session_factory),
        patch.object(settings, "jwt_secret_key", SecretStr(JWT_SECRET)),
        patch.object(settings, "aura_llm_provider", None),
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        response = client.post(PATH, headers=_headers(), json=_payload())

    assert response.status_code == 503
    assert response.json() == {"detail": "AI explanation service is currently unavailable."}
    session.commit.assert_not_called()
