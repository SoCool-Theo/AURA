"""Mocked DB/provider boundary: authenticated status is strictly read-only."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

import app.api.routes.market_data as routes
from app.api.dependencies import get_current_user, get_database_session
from app.database.models import User
from app.main import app
from app.schemas.market_data_status import MarketDataStatusResponse


@pytest.fixture
def harness():
    session, service = MagicMock(), MagicMock(spec=routes.MarketDataStatusService)
    app.dependency_overrides[get_database_session] = lambda: session
    with patch.object(routes, "MarketDataStatusService", return_value=service), TestClient(app, raise_server_exceptions=False) as client:
        try:
            yield client, session, service
        finally:
            app.dependency_overrides.clear()


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer invalid"}, {"Authorization": "Basic invalid"}])
def test_status_requires_authentication(harness, headers):
    client, session, service = harness
    response = client.get("/api/market-data/status", headers=headers)
    assert response.status_code == 401
    service.get.assert_not_called()
    session.commit.assert_not_called()


def test_status_is_safe_read_only_and_has_no_refresh_operation(harness):
    client, session, service = harness
    app.dependency_overrides[get_current_user] = lambda: User(id=uuid4())
    now = datetime(2026, 10, 6, 10, tzinfo=UTC)
    service.get.return_value = MarketDataStatusResponse(checked_at=now, update_time_utc="02:00",
        next_scheduled_at=now + timedelta(days=1), worker_status="unknown", worker_last_seen_at=None,
        last_run_status="never", last_attempt_at=None, last_finished_at=None, last_complete_at=None,
        attempt_count=0, stored_count=0, updated_symbols=[], failed_symbols=[], error_code=None,
        data_status="missing", observations=[])
    response = client.get("/api/market-data/status")
    assert response.status_code == 200
    assert response.json()["mode"] == "daily"
    assert response.json()["worker_status"] == "unknown"
    assert response.json()["last_complete_at"] is None
    session.commit.assert_not_called()
    session.add.assert_not_called()
    assert set(app.openapi()["paths"]["/api/market-data/status"]) == {"get"}
    assert client.post("/api/market-data/status").status_code == 405


def test_database_failure_returns_sanitized_unavailability_not_fake_success(harness):
    client, session, service = harness
    app.dependency_overrides[get_current_user] = lambda: User(id=uuid4())
    service.get.side_effect = RuntimeError("private password and database URL")
    response = client.get("/api/market-data/status")
    assert response.status_code == 503
    assert response.json() == {"detail": "Market-data status is temporarily unavailable"}
    assert "private" not in response.text
    session.commit.assert_not_called()
