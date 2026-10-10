"""Synthetic persisted telemetry from real agent orchestration and protected admin reads."""

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date
from unittest.mock import patch
from uuid import UUID

from fastapi.testclient import TestClient
import jwt
from pydantic import SecretStr
import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.api.dependencies as dependencies
import app.api.routes.admin as admin_routes
import app.api.routes.agent as agent_routes
import app.services.agent_service as agent_module
from app.agents.provider import LLMProviderResponseError, LLMProviderTimeoutError, LLMProviderUnavailableError, ProviderResponse
from app.core.config import settings
from app.core.security import create_access_token
from app.database.models import AIRequestLog, User
from app.database.repositories.ai_monitoring_repository import AIMonitoringRepository
from app.main import app
from app.services.market_data_service import MarketDataUnavailableError
from app.services.portfolio_valuation_service import InvalidHoldingModeError


SECRET = "ai-monitoring-tests-secret-at-least-32-characters"
PORTFOLIO = UUID(int=100)
REPORT = UUID(int=101)
SIMULATION = UUID(int=102)
SUMMARY = "/api/admin/ai-monitoring"
REQUESTS = SUMMARY + "/requests"
EXPLAIN = "/api/agent/explain"


class FakeProvider:
    text = "PRIVATE_ANSWER: historical risk is explained by the saved results."
    error = None

    def __init__(self):
        self.calls = 0

    def generate(self, request):
        self.calls += 1
        if self.error is not None:
            raise self.error
        return ProviderResponse(self.text)


class FakeTools:
    error = None
    planned = False
    instances = []

    def __init__(self, session, *, user_id, portfolio_id, valuation_date):
        self.calls = []
        self.__class__.instances.append(self)

    def get_portfolio_context(self, *, resolve_current_baseline=True):
        self.calls.append("portfolio")
        if self.error is not None:
            raise self.error
        return {"id": str(PORTFOLIO), "name": "PRIVATE_PORTFOLIO", "holdings": [],
                "portfolio_type": "PLANNED" if self.planned else "CURRENT"}

    def get_latest_report(self):
        return {"available": True, "report": {"id": str(REPORT), "analysis": {"private_balance": "1234567"}}}

    def get_report(self, report_id):
        return {"id": str(report_id), "analysis": {"private_balance": "1234567"}}

    def get_simulation(self, simulation_id):
        return {"id": str(simulation_id), "result": {"private_balance": "1234567"}}


@dataclass
class Harness:
    client: TestClient
    factory: sessionmaker[Session]
    provider: FakeProvider

    def headers(self, admin=False):
        return {"Authorization": "Bearer " + create_access_token(UUID(int=1 if admin else 2))}

    def explain(self, **changes):
        return self.client.post(EXPLAIN, headers=self.headers(), json={
            "portfolio_id": str(PORTFOLIO), "message": "Explain PRIVATE_MESSAGE historical risk.", **changes,
        })

    def events(self):
        response = self.client.get(REQUESTS, headers=self.headers(admin=True))
        assert response.status_code == 200
        return response.json()


@pytest.fixture
def harness() -> Iterator[Harness]:
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    for model in [User, AIRequestLog]:
        model.__table__.create(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with factory() as session:
        session.add_all([User(id=UUID(int=1), email="admin@example.com", password_hash="PRIVATE_HASH", role="ADMIN"),
                         User(id=UUID(int=2), email="customer@example.com", password_hash="PRIVATE_HASH", role="CUSTOMER")])
        session.commit()
    provider = FakeProvider()
    FakeTools.error, FakeTools.planned, FakeTools.instances = None, False, []
    try:
        with (
            patch.object(dependencies, "_get_session_factory", return_value=factory),
            patch.object(settings, "jwt_secret_key", SecretStr(SECRET)),
            patch.object(agent_routes, "get_agent_provider", return_value=provider),
            patch.object(agent_module, "AuraAgentTools", FakeTools),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            yield Harness(client, factory, provider)
    finally:
        engine.dispose()


def test_completed_request_commits_only_content_free_metadata_with_actual_timing(harness):
    with patch.object(agent_routes, "perf_counter", side_effect=[100, 100.025]) as clock:
        response = harness.explain(simulation_id=str(SIMULATION), history=[
            {"role": "user", "content": "PRIVATE_HISTORY"}, {"role": "assistant", "content": "PRIVATE_HISTORY_REPLY"},
        ])
    assert response.status_code == 200 and "PRIVATE_ANSWER" in response.json()["answer"]
    assert len(response.json()["sources"]) == 3 and harness.provider.calls == 1
    events = harness.events()
    assert events["total"] == 1
    event = events["items"][0]
    assert (event["outcome"], event["http_status"], event["provider_kind"], event["provider_called"], event["duration_ms"]) == (
        "COMPLETED", 200, "custom", True, 25.0,
    )
    assert all(event[key] for key in ["has_portfolio_source", "has_report_source", "has_simulation_source"])
    assert event["limitation_count"] == 1 and event["error_code"] is event["guardrail_reason"] is event["refusal_stage"] is None
    assert event["created_at"].endswith("Z") and event["started_at"].endswith("Z")
    for secret in ["PRIVATE_ANSWER", "PRIVATE_MESSAGE", "PRIVATE_HISTORY", "PRIVATE_PORTFOLIO", "PRIVATE_HASH", "1234567",
                   "customer@example.com", str(PORTFOLIO), str(REPORT), str(SIMULATION), SECRET]:
        assert secret not in str(events)
    assert not {"user_id", "portfolio_id", "message", "answer", "history", "model", "details"}.intersection(event)
    clock.assert_called_with()


@pytest.mark.parametrize("stage", ["INPUT", "OUTPUT"])
def test_advice_refusals_are_logged_at_the_actual_stage_and_keep_http_200(harness, stage):
    if stage == "OUTPUT":
        harness.provider.text = "You should buy AAPL."
    response = harness.explain(message="Should I buy AAPL?" if stage == "INPUT" else "Explain historical risk.")
    assert response.status_code == 200 and response.json()["sources"] == []
    event = harness.events()["items"][0]
    assert (event["outcome"], event["refusal_stage"], event["guardrail_reason"]) == ("REFUSED", stage, "investment_advice")
    assert event["provider_called"] == (stage == "OUTPUT")
    assert harness.provider.calls == (1 if stage == "OUTPUT" else 0)
    assert event["limitation_count"] == 0 and not event["has_portfolio_source"]
    if stage == "INPUT":
        assert FakeTools.instances[0].calls == []


@pytest.mark.parametrize("error,http_status,code", [
    (LLMProviderTimeoutError(), 503, "PROVIDER_TIMEOUT"),
    (LLMProviderUnavailableError(), 503, "PROVIDER_UNAVAILABLE"),
    (LLMProviderResponseError(), 502, "INVALID_PROVIDER_RESPONSE"),
    (RuntimeError("PRIVATE_PROVIDER_ERROR"), 500, "INTERNAL_ERROR"),
])
def test_provider_errors_are_durable_and_preserve_customer_error_mapping(harness, error, http_status, code):
    harness.provider.error = error
    response = harness.explain()
    assert response.status_code == http_status and "PRIVATE_PROVIDER_ERROR" not in response.text
    event = harness.events()["items"][0]
    assert (event["outcome"], event["http_status"], event["error_code"], event["provider_called"]) == ("ERROR", http_status, code, True)
    assert "PRIVATE_PROVIDER_ERROR" not in str(event)


@pytest.mark.parametrize("error,http_status,code", [
    (MarketDataUnavailableError("PRIVATE_MARKET_ERROR"), 503, "MARKET_DATA_UNAVAILABLE"),
    (InvalidHoldingModeError("PRIVATE_HOLDING_ERROR"), 409, "HOLDING_STATE_INVALID"),
    (SQLAlchemyError("PRIVATE_DATABASE_ERROR"), 500, "INTERNAL_ERROR"),
])
def test_context_failures_log_without_claiming_a_provider_call(harness, error, http_status, code):
    FakeTools.error = error
    assert harness.explain().status_code == http_status
    event = harness.events()["items"][0]
    assert event["error_code"] == code and event["provider_called"] is False
    assert harness.provider.calls == 0 and "PRIVATE_" not in str(event)


def test_unconfigured_provider_is_logged_after_validation_without_network_call(harness):
    with patch.object(agent_routes, "get_agent_provider", side_effect=agent_routes._provider_unavailable()):
        response = harness.explain()
    assert response.status_code == 503 and harness.provider.calls == 0
    event = harness.events()["items"][0]
    assert event["error_code"] == "PROVIDER_UNAVAILABLE" and event["provider_called"] is False


def test_planned_ownership_rejection_records_safe_reason_without_output_content(harness):
    FakeTools.planned = True
    harness.provider.text = "You currently own AAPL in your current portfolio."
    assert harness.explain().status_code == 502
    event = harness.events()["items"][0]
    assert event["outcome"] == "ERROR" and event["guardrail_reason"] == "planned_ownership_claim"
    assert event["error_code"] == "UNSAFE_PROVIDER_OUTPUT" and event["refusal_stage"] is None
    assert "currently own" not in str(event)


@pytest.mark.parametrize("outcome", ["COMPLETED", "ERROR"])
def test_recording_failure_rolls_back_event_and_preserves_primary_response(harness, outcome, caplog):
    original = AIMonitoringRepository.record
    def fail_after_insert(repository, **values):
        original(repository, **values)
        raise RuntimeError("PRIVATE_TELEMETRY_ERROR")
    if outcome == "ERROR":
        harness.provider.error = LLMProviderTimeoutError()
    with patch.object(AIMonitoringRepository, "record", fail_after_insert):
        response = harness.explain()
    assert response.status_code == (200 if outcome == "COMPLETED" else 503)
    assert harness.events()["total"] == 0
    assert "AI monitoring metadata could not be stored" in caplog.text
    assert "PRIVATE_TELEMETRY_ERROR" not in caplog.text and "PRIVATE_MESSAGE" not in caplog.text


def test_monitoring_commit_failure_rolls_back_without_failing_successful_explanation(harness):
    with patch.object(Session, "commit", side_effect=SQLAlchemyError("PRIVATE_COMMIT_ERROR")):
        response = harness.explain()
    assert response.status_code == 200 and harness.events()["total"] == 0


def test_invalid_and_unauthenticated_explanations_are_not_logged_or_resolved(harness):
    with patch.object(agent_routes, "get_agent_provider") as resolve:
        assert harness.client.post(EXPLAIN, json={"portfolio_id": str(PORTFOLIO), "message": "Explain risk."}).status_code == 401
        assert harness.explain(message="").status_code == 422
        assert harness.explain(user_id=str(UUID(int=1))).status_code == 422
    resolve.assert_not_called()
    assert harness.events()["total"] == 0


def test_summary_counts_real_events_and_distinguishes_provider_attempts_from_refusals(harness):
    assert harness.explain().status_code == 200
    assert harness.explain(message="Should I buy AAPL?").status_code == 200
    harness.provider.error = LLMProviderTimeoutError()
    assert harness.explain().status_code == 503
    response = harness.client.get(SUMMARY, headers=harness.headers(admin=True))
    assert response.status_code == 200
    payload = response.json()
    assert {key: payload[key] for key in ["total", "completed", "refused", "errors", "provider_calls", "input_refusals", "output_refusals"]} == {
        "total": 3, "completed": 1, "refused": 1, "errors": 1, "provider_calls": 2, "input_refusals": 1, "output_refusals": 0,
    }
    assert payload["average_duration_ms"] >= 0
    assert payload["configuration"]["connectivity"] == "not_checked"
    assert payload["configuration"]["telemetry_mode"] == "best_effort_metadata"
    assert payload["first_recorded_at"].endswith("Z")


@pytest.mark.parametrize("params,expected", [
    ({"outcome": "REFUSED"}, 1), ({"refusal_stage": "INPUT"}, 1),
    ({"outcome": "REFUSED", "refusal_stage": "OUTPUT"}, 0),
    ({"provider_kind": "custom"}, 2), ({"provider_kind": "groq"}, 0),
    ({"error_code": "PROVIDER_TIMEOUT"}, 0), ({"limit": 1, "offset": 10000}, 2),
])
def test_admin_list_filters_pagination_and_empty_page_total(harness, params, expected):
    harness.explain()
    harness.explain(message="Should I sell AAPL?")
    response = harness.client.get(REQUESTS, headers=harness.headers(admin=True), params=params)
    assert response.status_code == 200
    assert response.json()["total"] == expected
    if params.get("offset") == 10000:
        assert response.json()["items"] == []


@pytest.mark.parametrize("path", [SUMMARY, REQUESTS])
def test_admin_reads_are_one_query_plus_auth_without_writes_or_provider_resolution(harness, path):
    with patch.object(Session, "commit") as commit, patch.object(Session, "flush") as flush, \
         patch.object(Session, "execute", autospec=True, side_effect=Session.execute) as execute, \
         patch.object(agent_routes, "get_agent_provider") as resolve:
        response = harness.client.get(path, headers=harness.headers(admin=True))
    assert response.status_code == 200 and execute.call_count == 2
    commit.assert_not_called()
    flush.assert_not_called()
    resolve.assert_not_called()
    if path == SUMMARY:
        assert response.json()["total"] == 0 and response.json()["average_duration_ms"] is None


@pytest.mark.parametrize("path", [SUMMARY, REQUESTS])
def test_admin_reads_require_persisted_admin_and_ignore_forged_role(harness, path):
    with patch.object(admin_routes, "AIMonitoringService") as service:
        assert harness.client.get(path).status_code == 401
        assert harness.client.get(path, headers=harness.headers()).status_code == 403
        claims = jwt.decode(create_access_token(UUID(int=2)), SECRET, algorithms=["HS256"])
        claims["role"] = "ADMIN"
        assert harness.client.get(path, headers={"Authorization": "Bearer " + jwt.encode(claims, SECRET, algorithm="HS256")}).status_code == 403
        with harness.factory() as session:
            session.get(User, UUID(int=1)).role = "CUSTOMER"
            session.commit()
        assert harness.client.get(path, headers=harness.headers(admin=True)).status_code == 403
    service.assert_not_called()


@pytest.mark.parametrize("params", [
    {"limit": 0}, {"limit": 101}, {"offset": -1}, {"offset": 10001}, {"outcome": "fake"},
    {"provider_kind": "url"}, {"refusal_stage": "BEFORE"}, {"error_code": "arbitrary text"},
    {"created_from": "2026-10-10"}, {"created_from": "2026-10-11T00:00:00Z", "created_to": "2026-10-10T00:00:00Z"},
])
def test_invalid_admin_filters_are_422_before_service(harness, params):
    with patch.object(admin_routes, "AIMonitoringService") as service:
        response = harness.client.get(REQUESTS, headers=harness.headers(admin=True), params=params)
    assert response.status_code == 422
    service.assert_not_called()


@pytest.mark.parametrize("path,method,detail", [
    (SUMMARY, "summary", "AI monitoring summary unavailable"),
    (REQUESTS, "list", "AI monitoring requests unavailable"),
])
def test_admin_database_failures_are_sanitized_503(harness, path, method, detail):
    with patch.object(AIMonitoringRepository, method, side_effect=SQLAlchemyError("PRIVATE_DATABASE_ERROR")):
        response = harness.client.get(path, headers=harness.headers(admin=True))
    assert response.status_code == 503 and response.json() == {"detail": detail}


def test_configuration_exposes_only_presence_and_never_keys_or_model_text(harness):
    with patch.object(settings, "aura_llm_provider", "groq"), patch.object(settings, "groq_api_key", SecretStr("PRIVATE_PROVIDER_KEY")), \
         patch.object(settings, "aura_llm_model", "PRIVATE_MODEL_VALUE"):
        response = harness.client.get(SUMMARY, headers=harness.headers(admin=True))
    assert response.status_code == 200
    assert response.json()["configuration"] == {"configured_provider": "groq", "model_configured": True, "credential_configured": True,
        "ready": True, "connectivity": "not_checked", "telemetry_mode": "best_effort_metadata", "advice_guard_enabled": True}
    assert "PRIVATE_PROVIDER_KEY" not in response.text and "PRIVATE_MODEL_VALUE" not in response.text


def test_admin_monitoring_has_no_mutation_or_guardrail_disable_endpoint(harness):
    for path in [SUMMARY, REQUESTS]:
        operation = app.openapi()["paths"][path]
        assert set(operation) == {"get"} and operation["get"]["security"] == [{"HTTPBearer": []}]
        for method in ["post", "put", "patch", "delete"]:
            assert harness.client.request(method, path, headers=harness.headers(admin=True)).status_code == 405
