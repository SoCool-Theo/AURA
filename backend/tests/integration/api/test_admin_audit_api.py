"""Real HTTP/Bearer/role/repository checks against synthetic SQLite storage."""

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from unittest.mock import patch
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from pydantic import SecretStr
import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.api.dependencies as dependencies
import app.api.routes.admin as admin_routes
from app.core.config import settings
from app.core.security import create_access_token
from app.database.models import AuditLog, User
from app.main import app
from app.schemas.audit_log import AuditEventCreate
from app.services.audit_log_service import AuditLogService


SECRET = "audit-api-test-secret-at-least-32-characters"
PATH = "/api/admin/audit-logs"
DAY = datetime(2026, 10, 10, tzinfo=UTC)


@dataclass
class Harness:
    client: TestClient
    factory: sessionmaker[Session]
    admin_id: UUID
    customer_id: UUID
    target_id: UUID

    def headers(self, user_id: UUID | None = None) -> dict[str, str]:
        return {"Authorization": f"Bearer {create_access_token(user_id or self.admin_id)}"}


@pytest.fixture
def harness() -> Iterator[Harness]:
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    User.__table__.create(engine)
    AuditLog.__table__.create(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with factory() as session:
        admin = User(email="admin@example.com", password_hash="encoded", role="ADMIN")
        customer = User(email="customer@example.com", password_hash="encoded", role="CUSTOMER")
        session.add_all([admin, customer])
        session.flush()
        target_id = uuid4()
        for index in range(3):
            row = AuditLogService(session).record(AuditEventCreate(
                actor_kind="OPERATOR", action="ADMIN_BOOTSTRAPPED", target_type="USER",
                target_id=target_id if index < 2 else uuid4(),
                details={"previous_role": "CUSTOMER", "new_role": "ADMIN"},
            ))
            row.id = UUID(int=index + 1)
            row.created_at = DAY
        session.commit()
        admin_id, customer_id = admin.id, customer.id
    try:
        with (
            patch.object(dependencies, "_get_session_factory", return_value=factory),
            patch.object(settings, "jwt_secret_key", SecretStr(SECRET)),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            yield Harness(client, factory, admin_id, customer_id, target_id)
    finally:
        engine.dispose()


def test_default_page_is_safe_ordered_and_read_only(harness: Harness) -> None:
    with patch.object(Session, "commit") as commit, patch.object(Session, "flush") as flush:
        response = harness.client.get(PATH, headers=harness.headers())
    assert response.status_code == 200
    payload = response.json()
    assert (payload["total"], payload["limit"], payload["offset"]) == (3, 25, 0)
    assert [item["id"] for item in payload["items"]] == [str(UUID(int=i)) for i in [3, 2, 1]]
    assert set(payload["items"][0]) == {
        "id", "actor_kind", "actor_user_id", "action", "target_type", "target_id", "details", "created_at",
    }
    assert payload["items"][0]["created_at"] == "2026-10-10T00:00:00Z"
    assert "password" not in response.text and "token" not in response.text and "email" not in response.text
    commit.assert_not_called()
    flush.assert_not_called()


def test_pagination_and_empty_page_preserve_filtered_total(harness: Harness) -> None:
    query = {"limit": 1, "offset": 1, "target_id": str(harness.target_id)}
    response = harness.client.get(PATH, headers=harness.headers(), params=query)
    assert response.status_code == 200
    assert response.json()["total"] == 2
    assert [item["id"] for item in response.json()["items"]] == [str(UUID(int=1))]
    query["offset"] = 2
    payload = harness.client.get(PATH, headers=harness.headers(), params=query).json()
    assert payload["items"] == [] and payload["total"] == 2


def test_combined_filters_and_timezone_offsets(harness: Harness) -> None:
    query = {
        "action": "ADMIN_BOOTSTRAPPED", "actor_kind": "OPERATOR", "target_type": "USER",
        "target_id": str(harness.target_id),
        "created_from": "2026-10-10T07:00:00+07:00", "created_to": "2026-10-10T00:00:00Z",
    }
    response = harness.client.get(PATH, headers=harness.headers(), params=query)
    assert response.status_code == 200 and response.json()["total"] == 2
    query["actor_user_id"] = str(harness.admin_id)
    payload = harness.client.get(PATH, headers=harness.headers(), params=query).json()
    assert payload["items"] == [] and payload["total"] == 0


@pytest.mark.parametrize("query", [
    {"limit": 0}, {"limit": 101}, {"offset": -1}, {"offset": 10001},
    {"action": "UNKNOWN"}, {"actor_kind": "CUSTOMER"}, {"target_type": "TOKEN"},
    {"target_id": "invalid"}, {"actor_user_id": "invalid"},
    {"created_from": "2026-10-10T00:00:00"}, {"created_to": "invalid"},
    {"created_from": "2026-10-11T00:00:00Z", "created_to": "2026-10-10T00:00:00Z"},
])
def test_invalid_query_is_422(harness: Harness, query: dict) -> None:
    with patch.object(admin_routes, "AuditLogService") as service:
        response = harness.client.get(PATH, headers=harness.headers(), params=query)
    assert response.status_code == 422
    service.assert_not_called()


def test_customers_and_missing_credentials_cannot_read_history(harness: Harness) -> None:
    with patch.object(admin_routes, "AuditLogService") as service:
        missing = harness.client.get(PATH)
        customer = harness.client.get(PATH, headers=harness.headers(harness.customer_id))
    assert missing.status_code == 401 and missing.headers["www-authenticate"] == "Bearer"
    assert customer.status_code == 403
    service.assert_not_called()


def test_demotion_revokes_access_with_same_token(harness: Harness) -> None:
    headers = harness.headers()
    assert harness.client.get(PATH, headers=headers).status_code == 200
    with harness.factory() as session:
        session.get(User, harness.admin_id).role = "CUSTOMER"
        session.commit()
    assert harness.client.get(PATH, headers=headers).status_code == 403


def test_database_failure_returns_sanitized_503(harness: Harness) -> None:
    with patch.object(admin_routes.AuditLogService, "list", side_effect=SQLAlchemyError("private database details")):
        response = harness.client.get(PATH, headers=harness.headers())
    assert response.status_code == 503
    assert response.json() == {"detail": "Audit history unavailable"}


def test_corrupt_secret_metadata_is_not_exposed(harness: Harness) -> None:
    with harness.factory() as session:
        session.get(AuditLog, UUID(int=1)).details = {"token": "private-value"}
        session.commit()
    response = harness.client.get(PATH, headers=harness.headers())
    assert response.status_code == 503 and "private-value" not in response.text


@pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
def test_history_has_no_http_write_methods(harness: Harness, method: str) -> None:
    assert getattr(harness.client, method)(PATH, headers=harness.headers()).status_code == 405


def test_openapi_only_exposes_protected_get() -> None:
    operation = app.openapi()["paths"][PATH]
    assert set(operation) == {"get"}
    assert operation["get"]["security"] == [{"HTTPBearer": []}]
    assert "requestBody" not in operation["get"]
