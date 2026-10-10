"""Admin overview acceptance using synthetic SQLite data and real HTTP/auth."""

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from unittest.mock import patch
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
import jwt
from pydantic import SecretStr
import pytest
from sqlalchemy import JSON, MetaData, create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.api.dependencies as dependencies
import app.api.routes.admin as routes
import app.services.admin_overview_service as service_module
from app.core.config import settings
from app.core.security import create_access_token
from app.database.models import Analysis, Portfolio, Simulation, User
from app.main import app


SECRET = "admin-overview-tests-secret-at-least-32-characters"
NOW = datetime(2026, 10, 10, 9, tzinfo=UTC)
TODAY = NOW.replace(hour=0)
START = TODAY - timedelta(days=29)
PATHS = ["/api/admin/dashboard", "/api/admin/users"]


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
    legacy_id: UUID

    def headers(self, user_id: UUID | None = None) -> dict[str, str]:
        return {"Authorization": f"Bearer {create_access_token(user_id or self.admin_id)}"}


@pytest.fixture
def harness() -> Iterator[Harness]:
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    metadata = MetaData()
    for model in [User, Portfolio, Analysis, Simulation]:
        copied = model.__table__.to_metadata(metadata)
        for column in copied.columns:
            if isinstance(column.type, JSONB):
                column.type = JSON()
    metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with factory() as session:
        admin = User(id=UUID(int=1), email="admin@example.com", password_hash="private-hash", role="ADMIN", created_at=START - timedelta(seconds=1))
        customer = User(id=UUID(int=2), email="customer@example.com", display_name="Investor", phone_number="+66 123456", password_hash="private-hash", role="CUSTOMER", created_at=TODAY)
        legacy = User(id=UUID(int=3), role="CUSTOMER", created_at=TODAY)
        literal = User(id=UUID(int=4), email="literal@example.com", display_name="100%_\\match", password_hash="private-hash", created_at=START)
        session.add_all([admin, customer, legacy, literal])
        session.flush()
        portfolios = []
        for user, kind, timestamp in [
            (customer, "CURRENT", TODAY), (customer, "PLANNED", TODAY - timedelta(days=6)),
            (legacy, "LEGACY", START),
        ]:
            portfolio = Portfolio(user_id=user.id, name="Private portfolio", portfolio_type=kind,
                                  plan_currency="THB" if kind == "PLANNED" else None, created_at=timestamp)
            session.add(portfolio)
            portfolios.append(portfolio)
        session.flush()
        # Saved reports straddle all calendar boundaries, including future data.
        for timestamp in [START - timedelta(microseconds=1), START, TODAY - timedelta(days=6),
                          TODAY - timedelta(days=1), TODAY - timedelta(microseconds=1), TODAY,
                          TODAY + timedelta(days=1) - timedelta(microseconds=1), TODAY + timedelta(days=1)]:
            session.add(Analysis(portfolio_id=portfolios[0].id, start_date=date(2026, 1, 1), end_date=date(2026, 2, 1),
                                 schema_version="synthetic", result_snapshot={"private_payload": "not returned"}, created_at=timestamp))
        for timestamp in [TODAY - timedelta(days=7), TODAY - timedelta(days=1), TODAY]:
            session.add(Simulation(portfolio_id=portfolios[0].id, simulation_type="allocation", scenario_id=None,
                                   requested_start_date=date(2026, 1, 1), requested_end_date=date(2026, 2, 1),
                                   schema_version="synthetic", result_snapshot={"private_payload": "not returned"}, created_at=timestamp))
        session.commit()
    try:
        with (
            patch.object(dependencies, "_get_session_factory", return_value=factory),
            patch.object(settings, "jwt_secret_key", SecretStr(SECRET)),
            patch.object(service_module, "datetime", FrozenDatetime),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            yield Harness(client, factory, admin.id, customer.id, legacy.id)
    finally:
        engine.dispose()


def test_dashboard_counts_saved_rows_once_and_uses_half_open_utc_windows(harness: Harness) -> None:
    response = harness.client.get(PATHS[0], headers=harness.headers())
    assert response.status_code == 200
    payload = response.json()
    assert payload["generated_at"] == "2026-10-10T09:00:00Z"
    assert payload["timezone"] == "UTC"
    assert payload["window_start"] == "2026-09-11" and payload["window_end"] == "2026-10-10"
    assert payload["users"] == {"total": 4, "customers": 3, "admins": 1, "registered": 3, "legacy": 1, "new_last_7_days": 2}
    assert payload["portfolios"] == {"total": 3, "current": 1, "planned": 1, "legacy": 1, "new_last_7_days": 2}
    assert payload["saved_reports"] == {"total": 8, "today": 2, "yesterday": 2, "last_7_days": 5}
    assert payload["saved_simulations"] == {"total": 3, "today": 1, "yesterday": 1, "last_7_days": 2}
    assert len(payload["daily"]) == 30
    assert payload["daily"][0] == {"date": "2026-09-11", "new_users": 1, "new_portfolios": 1, "saved_reports": 1, "saved_simulations": 0}
    assert payload["daily"][-1] == {"date": "2026-10-10", "new_users": 2, "new_portfolios": 1, "saved_reports": 2, "saved_simulations": 1}
    assert payload["daily"][1] == {"date": "2026-09-12", "new_users": 0, "new_portfolios": 0, "saved_reports": 0, "saved_simulations": 0}
    assert sum(item["saved_reports"] for item in payload["daily"]) == 6
    assert sum(item["saved_simulations"] for item in payload["daily"][-7:]) == 2
    assert "system_health" not in payload and "active_users" not in payload
    assert "private_payload" not in response.text and "Private portfolio" not in response.text


def test_directory_is_safe_includes_legacy_and_correct_portfolio_counts(harness: Harness) -> None:
    response = harness.client.get(PATHS[1], headers=harness.headers())
    assert response.status_code == 200
    payload = response.json()
    assert (payload["total"], payload["limit"], payload["offset"]) == (4, 25, 0)
    assert [item["id"] for item in payload["items"]] == [str(UUID(int=i)) for i in [3, 2, 4, 1]]
    by_id = {item["id"]: item for item in payload["items"]}
    assert by_id[str(harness.customer_id)]["portfolio_count"] == 2
    assert by_id[str(harness.admin_id)]["portfolio_count"] == 0
    legacy = by_id[str(harness.legacy_id)]
    assert legacy["account_type"] == "LEGACY" and legacy["email"] is None and legacy["portfolio_count"] == 1
    assert set(legacy) == {"id", "email", "display_name", "role", "account_type", "created_at", "updated_at", "portfolio_count"}
    for sensitive in ["password", "private-hash", "phone_number", "+66 123456", "private_payload", "Private portfolio", "status"]:
        assert sensitive not in response.text


@pytest.mark.parametrize("query,expected", [
    ({"q": "  INVESTOR  "}, [2]), ({"q": "customer@"}, [2]),
    ({"q": "%_\\"}, [4]), ({"q": "%"}, [4]), ({"q": "_"}, [4]),
    ({"q": "' OR 1=1 --"}, []), ({"role": "ADMIN"}, [1]),
    ({"account_type": "LEGACY"}, [3]),
    ({"account_type": "REGISTERED", "role": "CUSTOMER"}, [2, 4]),
    ({"q": "Investor", "role": "ADMIN"}, []),
    ({"q": "   "}, [3, 2, 4, 1]),
])
def test_directory_search_and_filters_are_literal_and_combined(harness: Harness, query, expected) -> None:
    response = harness.client.get(PATHS[1], headers=harness.headers(), params=query)
    assert response.status_code == 200
    payload = response.json()
    assert [item["id"] for item in payload["items"]] == [str(UUID(int=i)) for i in expected]
    assert payload["total"] == len(expected)


def test_directory_offset_beyond_page_keeps_matching_total(harness: Harness) -> None:
    query = {"role": "CUSTOMER", "limit": 1, "offset": 1}
    payload = harness.client.get(PATHS[1], headers=harness.headers(), params=query).json()
    assert payload["total"] == 3 and payload["items"][0]["id"] == str(harness.customer_id)
    query["offset"] = 10000
    payload = harness.client.get(PATHS[1], headers=harness.headers(), params=query).json()
    assert payload == {"items": [], "total": 3, "limit": 1, "offset": 10000}


@pytest.mark.parametrize("query", [
    {"limit": 0}, {"limit": 101}, {"offset": -1}, {"offset": 10001},
    {"q": "x" * 101}, {"role": "OWNER"}, {"account_type": "ACTIVE"},
])
def test_directory_invalid_query_is_422_without_service_call(harness: Harness, query) -> None:
    with patch.object(routes, "AdminOverviewService") as service:
        response = harness.client.get(PATHS[1], headers=harness.headers(), params=query)
    assert response.status_code == 422
    service.assert_not_called()


@pytest.mark.parametrize("path", PATHS)
def test_reads_are_one_repository_statement_and_do_not_write(harness: Harness, path: str) -> None:
    with (
        patch.object(Session, "commit") as commit,
        patch.object(Session, "flush") as flush,
        patch.object(Session, "execute", autospec=True, side_effect=Session.execute) as execute,
    ):
        response = harness.client.get(path, headers=harness.headers())
    assert response.status_code == 200
    # Authentication SELECT plus exactly one overview query, regardless of rows.
    assert execute.call_count == 2
    commit.assert_not_called()
    flush.assert_not_called()
    sql = str(execute.call_args.args[1])
    assert "password_hash" not in sql and "result_snapshot" not in sql


@pytest.mark.parametrize("path", PATHS)
def test_missing_customer_forged_claim_and_demotion_are_denied(harness: Harness, path: str) -> None:
    with patch.object(routes, "AdminOverviewService") as service:
        assert harness.client.get(path).status_code == 401
        assert harness.client.get(path, headers={"X-User-ID": str(harness.admin_id)}).status_code == 401
        customer_token = create_access_token(harness.customer_id)
        claims = jwt.decode(customer_token, SECRET, algorithms=["HS256"])
        claims["role"] = "ADMIN"
        forged = jwt.encode(claims, SECRET, algorithm="HS256")
        assert harness.client.get(path, headers={"Authorization": f"Bearer {forged}"}).status_code == 403
        admin_headers = harness.headers()
        with harness.factory() as session:
            session.get(User, harness.admin_id).role = "CUSTOMER"
            session.commit()
        assert harness.client.get(path, headers=admin_headers).status_code == 403
    service.assert_not_called()


@pytest.mark.parametrize("path,method,detail", [
    (PATHS[0], "dashboard", "Admin dashboard unavailable"),
    (PATHS[1], "list_users", "Admin user directory unavailable"),
])
def test_database_failure_is_sanitized_503(harness: Harness, path, method, detail) -> None:
    with patch.object(routes.AdminOverviewService, method, side_effect=SQLAlchemyError("private database details")):
        response = harness.client.get(path, headers=harness.headers())
    assert response.status_code == 503 and response.json() == {"detail": detail}


@pytest.mark.parametrize("path", PATHS)
@pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
def test_overview_has_no_write_methods(harness: Harness, path, method) -> None:
    assert getattr(harness.client, method)(path, headers=harness.headers()).status_code == 405


def test_empty_database_resources_zero_fill_dashboard(harness: Harness) -> None:
    with harness.factory() as session:
        # Delete only fixture-owned synthetic rows, in dependency order.
        for model in [Analysis, Simulation, Portfolio]:
            session.query(model).delete()
        session.query(User).filter(User.id != harness.admin_id).delete()
        session.commit()
    payload = harness.client.get(PATHS[0], headers=harness.headers()).json()
    assert payload["users"]["total"] == 1
    assert payload["portfolios"]["total"] == payload["saved_reports"]["total"] == payload["saved_simulations"]["total"] == 0
    assert len(payload["daily"]) == 30
    assert all(sum(row[field] for field in ["new_users", "new_portfolios", "saved_reports", "saved_simulations"]) == 0 for row in payload["daily"])


def test_openapi_overview_is_protected_read_only() -> None:
    for path in PATHS:
        operations = app.openapi()["paths"][path]
        assert set(operations) == {"get"}
        assert operations["get"]["security"] == [{"HTTPBearer": []}]
        assert "requestBody" not in operations["get"]
