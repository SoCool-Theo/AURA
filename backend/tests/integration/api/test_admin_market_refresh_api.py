"""Durable manual requests, real permissions, idempotency and audit rollback."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from pydantic import SecretStr
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_database_session
from app.core.config import settings
from app.core.security import create_access_token
from app.database.models import AuditLog, MarketDataRefreshRun, User
from app.database.repositories.market_data_refresh_repository import MarketDataRefreshRepository
from app.database.repositories.market_data_refresh_run_repository import MarketDataRefreshRunRepository
from app.main import app
from app.scheduler.market_data_lock import MarketDataRefreshBusyError
from app.services.audit_log_service import AuditLogService


@pytest.fixture
def harness():
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    for model in (User, AuditLog, MarketDataRefreshRun):
        model.__table__.create(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        session.add_all([User(id=UUID(int=1), role="ADMIN", email="admin@example.com", password_hash="synthetic"),
                         User(id=UUID(int=2), email="customer@example.com", password_hash="synthetic")])
        session.commit()
    def sessions():
        with factory() as session:
            yield session
    overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_database_session] = sessions
    state = SimpleNamespace(worker_running=True, worker_heartbeat_at=datetime.now(UTC))
    try:
        with patch.object(settings, "jwt_secret_key", SecretStr("synthetic-manual-refresh-secret-at-least32")), patch.object(MarketDataRefreshRepository, "get", return_value=state), TestClient(app) as client:
            yield client, factory, state
    finally:
        app.dependency_overrides.clear(); app.dependency_overrides.update(overrides)
        engine.dispose()


def bearer(user=1):
    return {"Authorization": f"Bearer {create_access_token(UUID(int=user))}"}


def request(client, run_id=None, headers=None, **extra):
    return client.post("/api/admin/market-data/refresh", headers=headers if headers is not None else bearer(),
                       json={"request_id": str(run_id or uuid4()), **extra})


def test_queue_replay_and_safe_history_no_provider_execution(harness):
    client, factory, state = harness
    run_id = uuid4()
    response = request(client, run_id)
    assert response.status_code == 202
    assert response.json()["status"] == "queued"
    assert response.json()["started_at"] is None and response.json()["attempt_count"] == 0
    state.worker_running = False  # Replay still confirms the same accepted row.
    assert request(client, run_id).json() == response.json()
    with factory() as session:
        assert len(session.scalars(select(MarketDataRefreshRun)).all()) == 1
        events = session.scalars(select(AuditLog)).all()
        assert len(events) == 1 and events[0].target_id == run_id
        assert events[0].details == {"mode": "daily"}
    history = client.get("/api/admin/market-data/refresh-runs", headers=bearer()).json()
    assert history["total"] == 1 and history["items"] == [response.json()]
    audit = client.get("/api/admin/audit-logs", headers=bearer(), params={"action": "MARKET_REFRESH_REQUESTED"})
    assert audit.status_code == 200
    assert audit.json()["items"][0]["target_type"] == "MARKET_REFRESH"


def test_second_request_is_rejected_until_the_queued_request_is_consumed(harness):
    client, factory, _ = harness
    assert request(client).status_code == 202
    assert request(client).status_code == 409
    with factory() as session:
        assert len(session.scalars(select(MarketDataRefreshRun)).all()) == 1
        assert len(session.scalars(select(AuditLog)).all()) == 1


@pytest.mark.parametrize("headers,code", [({}, 401), ("customer", 403)])
def test_non_admin_requests_and_history_are_denied(harness, headers, code):
    client, factory, _ = harness
    headers = bearer(2) if headers == "customer" else headers
    assert request(client, headers=headers).status_code == code
    assert client.get("/api/admin/market-data/refresh-runs", headers=headers).status_code == code
    with factory() as session:
        assert session.scalar(select(MarketDataRefreshRun.id)) is None


@pytest.mark.parametrize("heartbeat,running", [(None, True), (datetime.now(UTC)-timedelta(minutes=4), True), (datetime.now(UTC)+timedelta(minutes=4), True), (datetime.now(UTC), False)])
def test_offline_stale_and_future_heartbeats_do_not_queue(harness, heartbeat, running):
    client, factory, state = harness
    state.worker_heartbeat_at, state.worker_running = heartbeat, running
    response = request(client)
    assert response.status_code == 409 and response.json()["detail"] == "Market-data worker is offline"
    with factory() as session:
        assert session.scalar(select(AuditLog.id)) is None


def test_busy_scheduled_or_cli_lock_does_not_queue(harness):
    client, factory, _ = harness
    with patch.object(MarketDataRefreshRunRepository, "lock_requests", side_effect=MarketDataRefreshBusyError()):
        assert request(client).status_code == 409
    with factory() as session:
        assert session.scalar(select(MarketDataRefreshRun.id)) is None


@pytest.mark.parametrize("field, value", [("symbols", ["AAPL"]), ("database_url", "private"), ("end_date", "2099-01-01"), ("mode", "streaming")])
def test_http_cannot_choose_universe_dates_credentials_or_live_mode(harness, field, value):
    client, _, _ = harness
    assert request(client, **{field: value}).status_code == 422


@pytest.mark.parametrize("operation", ["audit", "commit"])
def test_failure_rolls_back_request_and_audit_without_exposing_details(harness, operation):
    client, factory, _ = harness
    target, name = (AuditLogService, "record") if operation == "audit" else (Session, "commit")
    with patch.object(target, name, side_effect=SQLAlchemyError("secret connection string")):
        response = request(client)
    assert response.status_code == 503
    assert response.json() == {"detail": "Market-data refresh request unavailable"}
    with factory() as session:
        assert session.scalar(select(MarketDataRefreshRun.id)) is None
        assert session.scalar(select(AuditLog.id)) is None


def test_history_has_stable_order_and_bounded_pagination(harness):
    client, factory, _ = harness
    now = datetime.now(UTC)
    with factory() as session:
        session.add_all([MarketDataRefreshRun(id=UUID(int=i), trigger="SCHEDULED", status="success", requested_at=now) for i in range(10, 13)])
        session.commit()
    history = client.get("/api/admin/market-data/refresh-runs", headers=bearer(), params={"limit": 1, "offset": 1})
    assert history.status_code == 200 and history.json()["items"][0]["id"] == str(UUID(int=11))
    for params in ({"limit": 101}, {"offset": -1}):
        assert client.get("/api/admin/market-data/refresh-runs", headers=bearer(), params=params).status_code == 422
