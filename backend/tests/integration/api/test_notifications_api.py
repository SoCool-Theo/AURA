"""Real persistence/API checks on isolated synthetic SQLite data, never live data."""

from datetime import date
from uuid import uuid4
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import JSON, MetaData, create_engine, delete, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_database_session
from app.core.config import settings
from app.core.security import create_access_token
from app.database.models import Analysis, Portfolio, Simulation, User
from app.database.models.notification import Notification, NotificationPreferences
from app.main import app
from app.schemas.notification import NotificationPreferencesUpdate
from app.services.notification_service import NotificationService


@pytest.fixture
def harness():
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    metadata = MetaData()
    models = [User, Portfolio, Analysis, Simulation, Notification, NotificationPreferences]
    tables = {model: model.__table__.to_metadata(metadata) for model in models}
    for table in tables.values():
        for column in table.columns:
            if isinstance(column.type, JSONB):
                column.type = JSON()
    with engine.connect() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")
    metadata.create_all(engine)
    users = [uuid4(), uuid4()]
    resources = []
    day = date(2026, 10, 3)
    with engine.begin() as connection:
        for index, user_id in enumerate(users):
            connection.execute(tables[User].insert(), {"id": user_id, "email": f"synthetic-{index}@example.com", "password_hash": "encoded"})
            for kind in ["CURRENT", "PLANNED", "LEGACY"]:
                portfolio_id, report_id = uuid4(), uuid4()
                connection.execute(tables[Portfolio].insert(), {"id": portfolio_id, "user_id": user_id, "name": "Private portfolio name", "portfolio_type": kind, "plan_currency": "USD" if kind == "PLANNED" else None})
                connection.execute(tables[Analysis].insert(), {"id": report_id, "portfolio_id": portfolio_id, "start_date": day, "end_date": day, "schema_version": "synthetic", "result_snapshot": {"private_balance": 98765}})
                resources.append((user_id, portfolio_id, "analysis", report_id))
                for simulation_type in ["allocation", "historical-scenario", "combined"]:
                    simulation_id = uuid4()
                    connection.execute(tables[Simulation].insert(), {"id": simulation_id, "portfolio_id": portfolio_id, "simulation_type": simulation_type, "scenario_id": None if simulation_type == "allocation" else "synthetic", "requested_start_date": day, "requested_end_date": day, "schema_version": "synthetic", "result_snapshot": {}})
                    resources.append((user_id, portfolio_id, "simulation", simulation_id))

    def sessions():
        with Session(engine) as session:
            try:
                yield session
            except Exception:
                session.rollback()
                raise

    app.dependency_overrides[get_database_session] = sessions
    with patch.object(settings, "jwt_secret_key", SecretStr("notifications-test-secret-at-least-32-bytes")):
        headers = [{"Authorization": f"Bearer {create_access_token(user)}"} for user in users]
        with TestClient(app, raise_server_exceptions=False) as client:
            yield client, engine, tables, users, resources, headers
    app.dependency_overrides.pop(get_database_session, None)
    engine.dispose()


def record_all(harness):
    _, engine, _, _, resources, _ = harness
    with Session(engine) as session:
        for user_id, portfolio_id, kind, resource_id in resources:
            NotificationService(session).record_saved(user_id=user_id, portfolio_id=portfolio_id, kind=kind, resource_id=resource_id)
        session.commit()


@pytest.mark.parametrize("method,path,body", [
    ("get", "/api/notifications", None),
    ("get", "/api/notifications/preferences", None),
    ("put", "/api/notifications/preferences", {"enabled": True, "analysis_enabled": True, "simulation_enabled": True}),
    ("post", "/api/notifications/read-all", None),
    ("post", f"/api/notifications/{uuid4()}/read", None),
])
def test_notifications_require_authentication(harness, method, path, body):
    client = harness[0]
    response = client.request(method, path, json=body, headers={"X-User-ID": str(harness[3][0])})
    assert response.status_code == 401


def test_inbox_is_private_paginated_deduplicated_and_contains_no_financial_payload(harness):
    client, engine, _, users, resources, headers = harness
    record_all(harness)
    record_all(harness)
    response = client.get("/api/notifications?limit=5", headers=headers[0])
    data = response.json()
    assert response.status_code == 200
    assert data["total"] == data["unread_count"] == 12
    assert len(data["items"]) == 5
    owned = {str(resource[3]) for resource in resources if resource[0] == users[0]}
    assert all(item["resource_id"] in owned for item in data["items"])
    for forbidden in ["98765", "Private portfolio", "password", "result_snapshot", "user_id", "email"]:
        assert forbidden not in response.text
    page = client.get("/api/notifications?limit=5&offset=5", headers=headers[0]).json()
    assert not ({item["id"] for item in data["items"]} & {item["id"] for item in page["items"]})
    with Session(engine) as session:
        service = NotificationService(session)
        other = next(resource for resource in resources if resource[0] == users[1])
        with pytest.raises(ValueError):
            service.record_saved(user_id=users[0], portfolio_id=other[1], kind=other[2], resource_id=other[3])


def test_read_one_all_and_missing_ids_are_owner_scoped_and_idempotent(harness):
    client, _, _, _, _, headers = harness
    record_all(harness)
    own = client.get("/api/notifications", headers=headers[0]).json()["items"][0]
    path = f"/api/notifications/{own['id']}/read"
    assert client.post(path, headers=headers[1]).status_code == 404
    assert client.post(f"/api/notifications/{uuid4()}/read", headers=headers[0]).status_code == 404
    assert client.post(path, headers=headers[0]).status_code == 204
    first = client.get("/api/notifications", headers=headers[0]).json()
    assert first["unread_count"] == 11
    timestamp = next(item["read_at"] for item in first["items"] if item["id"] == own["id"])
    assert client.post(path, headers=headers[0]).content == b""
    second = client.get("/api/notifications", headers=headers[0]).json()
    assert next(item["read_at"] for item in second["items"] if item["id"] == own["id"]) == timestamp
    assert client.post("/api/notifications/read-all", headers=headers[0]).status_code == 204
    assert client.get("/api/notifications", headers=headers[0]).json()["unread_count"] == 0
    assert client.get("/api/notifications", headers=headers[1]).json()["unread_count"] == 12


@pytest.mark.parametrize("values,expected", [
    ({"enabled": False, "analysis_enabled": True, "simulation_enabled": True}, 0),
    ({"enabled": True, "analysis_enabled": False, "simulation_enabled": True}, 9),
    ({"enabled": True, "analysis_enabled": True, "simulation_enabled": False}, 3),
])
def test_account_preferences_keep_existing_messages_and_control_only_future_events(harness, values, expected):
    client, _, _, _, _, headers = harness
    defaults = {"enabled": True, "analysis_enabled": True, "simulation_enabled": True}
    assert client.get("/api/notifications/preferences", headers=headers[0]).json() == defaults
    assert client.put("/api/notifications/preferences", headers=headers[0], json=values).json() == values
    assert client.get("/api/notifications/preferences", headers=headers[0]).json() == values
    assert client.get("/api/notifications/preferences", headers=headers[1]).json() == defaults
    record_all(harness)
    assert client.get("/api/notifications", headers=headers[0]).json()["total"] == expected
    off = {**values, "enabled": False}
    client.put("/api/notifications/preferences", headers=headers[0], json=off)
    assert client.get("/api/notifications", headers=headers[0]).json()["total"] == expected


@pytest.mark.parametrize("body", [{}, {"enabled": "false", "analysis_enabled": True, "simulation_enabled": True}, {"enabled": True, "analysis_enabled": True, "simulation_enabled": True, "user_id": str(uuid4())}])
def test_preference_requests_are_complete_strict_and_reject_owner_overrides(harness, body):
    assert harness[0].put("/api/notifications/preferences", json=body, headers=harness[5][0]).status_code == 422


@pytest.mark.parametrize("query", ["limit=0", "limit=101", "offset=-1", "offset=10001"])
def test_pagination_is_bounded(harness, query):
    assert harness[0].get(f"/api/notifications?{query}", headers=harness[5][0]).status_code == 422


@pytest.mark.parametrize("target,remaining", [(Analysis, 11), (Simulation, 11), (Portfolio, 8), (User, 0)])
def test_target_and_account_deletion_cascade_without_affecting_other_accounts(harness, target, remaining):
    client, engine, tables, users, resources, headers = harness
    record_all(harness)
    preferences = {"enabled": True, "analysis_enabled": True, "simulation_enabled": True}
    for header in headers:
        assert client.put("/api/notifications/preferences", headers=header, json=preferences).status_code == 200
    chosen = resources[0] if target != Simulation else resources[1]
    identifier = users[0] if target == User else chosen[1] if target == Portfolio else chosen[3]
    with engine.begin() as connection:
        connection.execute(delete(tables[target]).where(tables[target].c.id == identifier))
    with engine.connect() as connection:
        assert len(connection.execute(select(tables[Notification].c.id).where(tables[Notification].c.user_id == users[0])).all()) == remaining
        if target == User:
            assert connection.execute(select(tables[NotificationPreferences].c.user_id).where(tables[NotificationPreferences].c.user_id == users[0])).first() is None
    assert client.get("/api/notifications", headers=headers[1]).json()["total"] == 12
    assert client.get("/api/notifications/preferences", headers=headers[1]).json() == preferences


def test_missing_and_wrong_portfolio_targets_cannot_create_notifications(harness):
    _, engine, _, users, resources, _ = harness
    own, different = resources[0], resources[4]
    with Session(engine) as session:
        service = NotificationService(session)
        for portfolio_id, resource_id in [(own[1], uuid4()), (different[1], own[3])]:
            with pytest.raises(ValueError):
                service.record_saved(user_id=users[0], portfolio_id=portfolio_id, kind="analysis", resource_id=resource_id)
        assert service.list(users[0], limit=25, offset=0).total == 0


@pytest.mark.parametrize("method,path", [("get", "/api/notifications"), ("get", "/api/notifications/preferences"), ("put", "/api/notifications/preferences"), ("post", "/api/notifications/read-all"), ("post", f"/api/notifications/{uuid4()}/read")])
def test_unexpected_failures_are_sanitized(harness, method, path):
    client, _, _, _, _, headers = harness
    with patch("app.api.routes.notifications.NotificationService", side_effect=RuntimeError("secret database detail")):
        response = client.request(method, path, headers=headers[0], json={"enabled": True, "analysis_enabled": True, "simulation_enabled": True} if method == "put" else None)
    assert response.status_code == 500
    assert response.json() == {"detail": "Unable to process notifications"}


def test_preference_update_invalidates_same_session_cached_settings(harness):
    _, engine, _, users, _, _ = harness
    with Session(engine) as session:
        service = NotificationService(session)
        service.update_preferences(users[0], NotificationPreferencesUpdate(enabled=True, analysis_enabled=True, simulation_enabled=True))
        assert service.preferences(users[0]).enabled is True
        service.update_preferences(users[0], NotificationPreferencesUpdate(enabled=False, analysis_enabled=True, simulation_enabled=True))
        assert service.preferences(users[0]).enabled is False


def test_notifications_and_preferences_follow_caller_rollback(harness):
    client, engine, _, users, resources, headers = harness
    with Session(engine) as session:
        resource = resources[0]
        service = NotificationService(session)
        service.record_saved(user_id=resource[0], portfolio_id=resource[1], kind=resource[2], resource_id=resource[3])
        service.update_preferences(users[0], NotificationPreferencesUpdate(enabled=False, analysis_enabled=False, simulation_enabled=False))
        session.rollback()
    assert client.get("/api/notifications", headers=headers[0]).json()["total"] == 0
    assert client.get("/api/notifications/preferences", headers=headers[0]).json()["enabled"] is True
