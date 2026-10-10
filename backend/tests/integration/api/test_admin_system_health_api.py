"""Real HTTP/Bearer/role/database reads with synthetic SQLite observations."""

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import patch
from uuid import UUID

from fastapi.testclient import TestClient
import jwt
from pydantic import SecretStr, ValidationError
import pytest
from sqlalchemy import JSON, MetaData, create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.api.dependencies as dependencies
import app.api.routes.admin as routes
import app.services.admin_system_health_service as service_module
from app.core.config import settings
from app.core.instruments import MARKET_UPDATE_SYMBOLS
from app.core.security import create_access_token
from app.database.models import MarketData, MarketDataRefreshState, User
from app.database.repositories.admin_system_health_repository import AdminSystemHealthRepository
from app.database.repositories.market_data_refresh_repository import MarketDataRefreshRepository
from app.main import app


SECRET = "admin-health-tests-secret-at-least-32-characters"
NOW = datetime(2026, 10, 10, 9, tzinfo=UTC)
PATH = "/api/admin/system-health"


class FrozenDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return NOW if tz is not None else NOW.replace(tzinfo=None)


@dataclass
class Harness:
    client: TestClient
    factory: sessionmaker[Session]
    admin_id: UUID
    customer_id: UUID

    def headers(self, user_id: UUID | None = None):
        return {"Authorization": f"Bearer {create_access_token(user_id or self.admin_id)}"}


@pytest.fixture
def harness() -> Iterator[Harness]:
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    metadata = MetaData()
    for model in [User, MarketData, MarketDataRefreshState]:
        copied = model.__table__.to_metadata(metadata)
        for column in copied.columns:
            if isinstance(column.type, JSONB):
                column.type = JSON()
    metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with factory() as session:
        admin = User(id=UUID(int=1), email="admin@example.com", password_hash="private-hash", role="ADMIN")
        customer = User(id=UUID(int=2), email="customer@example.com", password_hash="private-hash", role="CUSTOMER")
        session.add_all([admin, customer])
        session.commit()
    try:
        with (
            patch.object(dependencies, "_get_session_factory", return_value=factory),
            patch.object(settings, "jwt_secret_key", SecretStr(SECRET)),
            patch.object(service_module, "datetime", FrozenDatetime),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            yield Harness(client, factory, admin.id, customer.id)
    finally:
        engine.dispose()


def test_real_database_ping_and_empty_market_cannot_claim_all_systems_operational(harness):
    response = harness.client.get(PATH, headers=harness.headers())
    assert response.status_code == 200
    payload = response.json()
    assert payload["checked_at"] == "2026-10-10T09:00:00Z"
    assert payload["status"] == "degraded" and payload["coverage"] == "partial"
    assert set(payload) == {"checked_at", "status", "coverage", "checks", "market_data"}
    assert [check["component"] for check in payload["checks"]] == [
        "api", "authentication", "database", "market_data_worker", "market_data", "market_data_refresh", "market_data_provider", "analytics",
    ]
    checks = {check["component"]: check for check in payload["checks"]}
    assert checks["api"] == {"component": "api", "status": "healthy", "reason": "request_received", "latency_ms": None}
    assert checks["authentication"]["reason"] == "admin_authorized"
    assert checks["database"]["reason"] == "database_query_succeeded"
    assert checks["database"]["status"] == "healthy" and checks["database"]["latency_ms"] >= 0
    assert checks["market_data_worker"]["status"] == "unknown"
    assert checks["market_data"]["reason"] == "observations_missing"
    assert checks["market_data_refresh"]["reason"] == "refresh_never_run"
    for name in ["market_data_provider", "analytics"]:
        assert checks[name] == {"component": name, "status": "not_checked", "reason": "probe_not_run", "latency_ms": None}
    assert all(check["latency_ms"] is None for check in payload["checks"] if check["component"] != "database")
    assert payload["market_data"]["data_status"] == "missing"
    assert len(payload["market_data"]["observations"]) == 18
    assert "private-hash" not in response.text and "admin@example.com" not in response.text


def test_current_stored_prices_do_not_prove_worker_or_provider_connectivity(harness):
    with harness.factory() as session:
        session.add_all([MarketData(symbol=symbol, date=date(2026, 10, 9), adjusted_close=Decimal("100.25"), volume=None, source="Synthetic")
                         for symbol in MARKET_UPDATE_SYMBOLS])
        session.add(MarketDataRefreshState(id=1, status="success", attempt_count=1, stored_count=18,
                                          updated_symbols=list(MARKET_UPDATE_SYMBOLS)))
        session.commit()
    response = harness.client.get(PATH, headers=harness.headers())
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "unknown" and payload["coverage"] == "partial"
    checks = {check["component"]: check for check in payload["checks"]}
    assert checks["market_data"]["status"] == "healthy"
    assert checks["market_data_worker"]["status"] == "unknown"
    assert checks["market_data_provider"]["status"] == "not_checked"
    assert checks["market_data_refresh"]["status"] == "healthy"
    assert payload["market_data"]["checked_at"] == payload["checked_at"]


def test_reads_have_fixed_queries_no_writes_or_refresh(harness):
    with (
        patch.object(Session, "execute", autospec=True, side_effect=Session.execute) as execute,
        patch.object(Session, "commit") as commit,
        patch.object(Session, "flush") as flush,
        patch.object(Session, "add") as add,
        patch("app.services.market_data_refresh_service.run_market_data_refresh") as refresh,
    ):
        response = harness.client.get(PATH, headers=harness.headers())
    assert response.status_code == 200
    # Authorization, SELECT 1, singleton refresh state, grouped latest dates.
    assert execute.call_count == 4
    assert str(execute.call_args_list[1].args[1]) == "SELECT 1"
    commit.assert_not_called()
    flush.assert_not_called()
    add.assert_not_called()
    refresh.assert_not_called()


def test_post_authorization_ping_failure_returns_structured_unavailability_without_further_reads(harness):
    with (
        patch.object(AdminSystemHealthRepository, "database_responds", side_effect=SQLAlchemyError("postgresql://user:private-password@example.invalid/database")),
        patch.object(service_module, "MarketDataStatusService") as market,
    ):
        response = harness.client.get(PATH, headers=harness.headers())
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "unavailable" and payload["market_data"] is None
    checks = {check["component"]: check for check in payload["checks"]}
    assert checks["database"]["reason"] == "database_query_failed"
    assert all(checks[name]["reason"] == "database_unavailable" for name in ["market_data_worker", "market_data", "market_data_refresh"])
    market.assert_not_called()
    assert "private-password" not in response.text and "example.invalid" not in response.text


def test_status_query_failure_retains_ping_evidence_and_does_not_hide_failure(harness):
    with patch.object(MarketDataRefreshRepository, "get", side_effect=SQLAlchemyError("private schema error")):
        response = harness.client.get(PATH, headers=harness.headers())
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "degraded" and payload["market_data"] is None
    checks = {check["component"]: check for check in payload["checks"]}
    assert checks["database"]["status"] == "healthy"
    assert all(checks[name]["status"] == "unavailable" and checks[name]["reason"] == "market_status_unavailable"
               for name in ["market_data_worker", "market_data", "market_data_refresh"])
    assert "private schema error" not in response.text


def test_invalid_persisted_status_is_sanitized_as_unavailable(harness):
    with harness.factory() as session:
        session.add(MarketDataRefreshState(id=1, status="failed", error_code="private unknown error", attempt_count=1))
        session.commit()
    response = harness.client.get(PATH, headers=harness.headers())
    assert response.status_code == 200
    assert response.json()["status"] == "degraded" and response.json()["market_data"] is None
    assert "private unknown error" not in response.text


@pytest.mark.parametrize("kind", ["missing", "wrong_scheme", "invalid", "expired", "wrong_signature", "header_only", "customer", "forged_role", "demoted", "deleted"])
def test_authorization_cannot_be_bypassed_or_fail_open(harness, kind):
    headers = harness.headers()
    expected = 401
    if kind == "missing":
        headers = {}
    elif kind == "wrong_scheme":
        headers = {"Authorization": "Basic abc"}
    elif kind == "invalid":
        headers = {"Authorization": "Bearer invalid"}
    elif kind == "header_only":
        headers = {"X-User-ID": str(harness.admin_id)}
    elif kind in {"expired", "wrong_signature", "forged_role"}:
        user_id = harness.customer_id if kind == "forged_role" else harness.admin_id
        claims = jwt.decode(create_access_token(user_id), SECRET, algorithms=["HS256"])
        secret = SECRET
        if kind == "expired":
            claims["exp"] = 0
        elif kind == "wrong_signature":
            secret = "wrong-test-secret-at-least-32-characters"
        else:
            claims["role"] = "ADMIN"
            expected = 403
        headers = {"Authorization": "Bearer " + jwt.encode(claims, secret, algorithm="HS256")}
    elif kind == "customer":
        headers = harness.headers(harness.customer_id)
        expected = 403
    else:
        with harness.factory() as session:
            admin = session.get(User, harness.admin_id)
            if kind == "demoted":
                admin.role = "CUSTOMER"
                expected = 403
            else:
                session.delete(admin)
            session.commit()
    with patch.object(routes, "AdminSystemHealthService") as service:
        response = harness.client.get(PATH, headers=headers)
    assert response.status_code == expected
    service.assert_not_called()


@pytest.mark.parametrize("failure", [SQLAlchemyError("private connection error"), ValidationError.from_exception_data("Synthetic", [])])
def test_unhandled_service_database_or_validation_failure_is_sanitized_503(harness, failure):
    with patch.object(routes.AdminSystemHealthService, "get", side_effect=failure):
        response = harness.client.get(PATH, headers=harness.headers())
    assert response.status_code == 503
    assert response.json() == {"detail": "Admin system health unavailable"}


def test_health_is_get_only_and_requires_bearer_in_openapi(harness):
    path = app.openapi()["paths"][PATH]
    assert set(path) == {"get"} and path["get"]["security"] == [{"HTTPBearer": []}]
    assert "requestBody" not in path["get"]
    for method in ["post", "put", "patch", "delete"]:
        assert harness.client.request(method, PATH, headers=harness.headers()).status_code == 405


def test_public_health_remains_database_independent_and_unchanged(harness):
    with patch.object(dependencies, "_get_session_factory", side_effect=RuntimeError("private database configuration")) as factory:
        response = harness.client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "app_name": settings.app_name, "environment": settings.app_env}
    factory.assert_not_called()
