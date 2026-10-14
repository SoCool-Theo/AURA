"""Refresh-session and migration checks in an owned, temporary local database."""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
import os
from pathlib import Path
from uuid import uuid4
from types import SimpleNamespace

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
import jwt
from pydantic import SecretStr
import pytest
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.orm import Session

from app.api.dependencies import get_database_session
from app.core.config import settings
from app.core.security import create_access_token, hash_refresh_token
from app.database.models import User, WebRefreshToken, WebSession
from app.main import app
import app.services.web_session_service as web_session_module
from backend.app.core.config import settings as migration_settings
from backend.tests.integration.database.postgres_test_guard import validate_test_database_url

ROOT = Path(__file__).resolve().parents[4]
HEAD = "e9a1c3f5b7d2"
ORIGIN = {"Origin": "http://127.0.0.1:5173", "X-Aura-Web-Session": "1"}
LOGIN = {"email": "web@example.com", "password": "session-test-password"}


@pytest.fixture(scope="module")
def web_database():
    raw = os.environ.get("AURA_TEST_DATABASE_URL")
    if not raw:
        pytest.skip("AURA_TEST_DATABASE_URL is required for local PostgreSQL session checks")
    url = validate_test_database_url(raw)
    if url.query:
        pytest.fail("test database query overrides are forbidden")
    # Existing aura_test data and migration version remain untouched. Only this
    # randomly named database created by this fixture is eligible for deletion.
    name = "aura_test_web_sessions_" + uuid4().hex
    scratch_url = url.set(database=name)
    admin = create_engine(url, isolation_level="AUTOCOMMIT")
    engine = create_engine(scratch_url)
    original_url = migration_settings.database_url
    created = False
    try:
        with admin.connect() as connection:
            assert connection.scalar(text("SELECT current_database()")) == "aura_test"
            connection.execute(text(f'CREATE DATABASE "{name}"'))
            created = True
        migration_settings.database_url = scratch_url.render_as_string(hide_password=False)
        command.upgrade(Config(str(ROOT / "backend/alembic.ini")), "head")
        yield engine
    finally:
        migration_settings.database_url = original_url
        engine.dispose()
        try:
            if created:
                with admin.connect() as connection:
                    connection.execute(text(f'DROP DATABASE "{name}"'))
        finally:
            admin.dispose()


@pytest.fixture
def web_client(web_database, monkeypatch):
    monkeypatch.setattr(settings, "jwt_secret_key", SecretStr("web-session-test-secret-at-least-thirty-two-bytes"))
    monkeypatch.setattr(settings, "refresh_cookie_secure", False)
    monkeypatch.setattr(settings, "refresh_cookie_samesite", "lax")
    monkeypatch.setattr(settings, "refresh_session_idle_days", 7)
    monkeypatch.setattr(settings, "refresh_session_max_days", 30)
    with web_database.begin() as connection:
        connection.execute(text("TRUNCATE users CASCADE"))

    def database_session():
        with Session(web_database, expire_on_commit=False) as session:
            try:
                yield session
            except Exception:
                session.rollback()
                raise

    app.dependency_overrides[get_database_session] = database_session
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            assert client.post("/api/auth/register", json=LOGIN).status_code == 201
            yield client
    finally:
        app.dependency_overrides.pop(get_database_session, None)


def login(client):
    response = client.post("/api/auth/web/login", headers=ORIGIN, json=LOGIN)
    assert response.status_code == 200, response.text
    return response.json()["access_token"], client.cookies.get("aura_refresh"), response


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def test_web_login_rotation_hashes_and_unchanged_mobile_contract(web_client, web_database):
    token, cookie, response = login(web_client)
    assert set(response.json()) == {"access_token", "token_type"}
    assert response.headers["cache-control"] == "no-store"
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "SameSite=lax" in response.headers["set-cookie"]
    assert "Max-Age=604800" in response.headers["set-cookie"]
    assert "Path=/api/auth/web" in response.headers["set-cookie"]
    assert web_client.get("/api/auth/me", headers=bearer(token)).status_code == 200
    with Session(web_database) as session:
        record = session.scalar(select(WebSession))
        original_created, original_expires = record.created_at, record.expires_at
        assert original_expires - original_created == timedelta(days=30)
        digest = session.scalar(select(WebRefreshToken))
        assert digest.token_hash == hash_refresh_token(cookie)
        assert cookie not in repr(digest.__dict__)
    response = web_client.post("/api/auth/web/refresh", headers=ORIGIN)
    assert response.status_code == 200
    assert web_client.cookies.get("aura_refresh") != cookie
    with Session(web_database) as session:
        record = session.scalar(select(WebSession))
        assert record.created_at == original_created and record.expires_at == original_expires
        assert session.get(WebRefreshToken, hash_refresh_token(cookie)).used_at is not None
        assert len(session.scalars(select(WebRefreshToken)).all()) == 2
    mobile = web_client.post("/api/auth/login", json=LOGIN)
    assert mobile.status_code == 200 and "set-cookie" not in mobile.headers
    claims = jwt.decode(mobile.json()["access_token"], settings.jwt_secret_key.get_secret_value(), algorithms=["HS256"])
    assert set(claims) == {"sub", "iat", "exp"}


@pytest.mark.parametrize("boundary", ["idle", "absolute"])
def test_expired_sessions_reject_access_and_refresh(web_client, web_database, boundary):
    token, _, _ = login(web_client)
    now = datetime.now(UTC)
    with Session(web_database) as session:
        record = session.scalar(select(WebSession))
        record.created_at = now - timedelta(days=31)
        record.last_activity_at = now - timedelta(days=7, seconds=1) if boundary == "idle" else now
        record.expires_at = now + timedelta(days=1) if boundary == "idle" else now - timedelta(seconds=1)
        session.commit()
    assert web_client.get("/api/auth/me", headers=bearer(token)).status_code == 401
    response = web_client.post("/api/auth/web/refresh", headers=ORIGIN)
    assert response.status_code == 401
    assert web_client.cookies.get("aura_refresh") is None


def test_api_activity_extends_idle_deadline_without_moving_absolute_limit(web_client, web_database):
    token, _, _ = login(web_client)
    with Session(web_database) as session:
        record = session.scalar(select(WebSession))
        expiration = record.expires_at
        record.created_at = datetime.now(UTC) - timedelta(days=10)
        record.last_activity_at = datetime.now(UTC) - timedelta(days=6)
        session.commit()
    assert web_client.get("/api/auth/me", headers=bearer(token)).status_code == 200
    with Session(web_database) as session:
        record = session.scalar(select(WebSession))
        assert datetime.now(UTC) - record.last_activity_at < timedelta(seconds=5)
        assert record.expires_at == expiration


@pytest.mark.parametrize("boundary", ["idle", "absolute"])
def test_session_expires_at_the_exact_policy_boundary(web_client, web_database, monkeypatch, boundary):
    token, cookie, _ = login(web_client)
    now = datetime.now(UTC)
    with Session(web_database) as session:
        record = session.scalar(select(WebSession))
        record.created_at = now - timedelta(days=30)
        record.last_activity_at = now - timedelta(days=7) if boundary == "idle" else now
        record.expires_at = now + timedelta(days=1) if boundary == "idle" else now
        session.commit()
    monkeypatch.setattr(web_session_module, "datetime", SimpleNamespace(now=lambda _: now))
    assert web_client.get("/api/auth/me", headers=bearer(token)).status_code == 401
    assert web_client.post("/api/auth/web/refresh", headers={**ORIGIN, "Cookie": f"aura_refresh={cookie}"}).status_code == 401


def test_failed_login_preserves_session_and_successful_login_replaces_it(web_client):
    token, cookie, _ = login(web_client)
    for credentials in ({**LOGIN, "password": "incorrect-password"}, {**LOGIN, "email": "missing@example.com"}):
        response = web_client.post("/api/auth/web/login", headers=ORIGIN, json=credentials)
        assert response.status_code == 401
        assert response.json() == {"detail": "Invalid email or password"}
        assert web_client.cookies.get("aura_refresh") == cookie
    assert web_client.get("/api/auth/me", headers=bearer(token)).status_code == 200
    new_token, _, _ = login(web_client)
    assert web_client.get("/api/auth/me", headers=bearer(token)).status_code == 401
    assert web_client.get("/api/auth/me", headers=bearer(new_token)).status_code == 200


def test_access_expiration_is_capped_by_original_session_maximum(web_client, web_database):
    login(web_client)
    with Session(web_database) as session:
        record = session.scalar(select(WebSession))
        record.expires_at = datetime.now(UTC) + timedelta(minutes=3)
        deadline = int(record.expires_at.timestamp())
        session.commit()
    response = web_client.post("/api/auth/web/refresh", headers=ORIGIN)
    assert response.status_code == 200
    claims = jwt.decode(response.json()["access_token"], settings.jwt_secret_key.get_secret_value(), algorithms=["HS256"])
    assert claims["exp"] == deadline
    assert int(response.headers["set-cookie"].split("Max-Age=")[1].split(";")[0]) <= 180


def test_replay_revokes_session_but_preserves_other_browser_session(web_client, web_database):
    old_access, old_cookie, _ = login(web_client)
    response = web_client.post("/api/auth/web/refresh", headers=ORIGIN)
    assert response.status_code == 200
    rotated_access = response.json()["access_token"]
    rotated_cookie = web_client.cookies.get("aura_refresh")
    # Give the second browser its own session without replacing the first cookie.
    with TestClient(app, raise_server_exceptions=False) as second:
        second_access, _, _ = login(second)
        with Session(web_database) as session:
            session.get(WebRefreshToken, hash_refresh_token(old_cookie)).used_at -= timedelta(seconds=10)
            session.commit()
        replay = web_client.post("/api/auth/web/refresh", headers={**ORIGIN, "Cookie": f"aura_refresh={old_cookie}"})
        assert replay.status_code == 401
        assert web_client.get("/api/auth/me", headers=bearer(old_access)).status_code == 401
        assert web_client.get("/api/auth/me", headers=bearer(rotated_access)).status_code == 401
        assert web_client.post("/api/auth/web/refresh", headers={**ORIGIN, "Cookie": f"aura_refresh={rotated_cookie}"}).status_code == 401
        assert second.get("/api/auth/me", headers=bearer(second_access)).status_code == 200


def test_concurrent_rotation_returns_one_success_and_retryable_conflict(web_client):
    _, cookie, _ = login(web_client)
    def exchange(_):
        with TestClient(app, raise_server_exceptions=False) as client:
            return client.post("/api/auth/web/refresh", headers={**ORIGIN, "Cookie": f"aura_refresh={cookie}"})
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(exchange, range(2)))
    assert sorted(response.status_code for response in responses) == [200, 409]
    conflict = next(response for response in responses if response.status_code == 409)
    assert "set-cookie" not in conflict.headers
    successful = next(response for response in responses if response.status_code == 200)
    assert web_client.get("/api/auth/me", headers=bearer(successful.json()["access_token"])).status_code == 200


def test_logout_revokes_access_cookie_and_is_idempotent(web_client):
    token, cookie, _ = login(web_client)
    assert web_client.post("/api/auth/web/logout", headers=ORIGIN).status_code == 204
    assert web_client.cookies.get("aura_refresh") is None
    assert web_client.get("/api/auth/me", headers=bearer(token)).status_code == 401
    assert web_client.post("/api/auth/web/refresh", headers={**ORIGIN, "Cookie": f"aura_refresh={cookie}"}).status_code == 401
    assert web_client.post("/api/auth/web/logout", headers=ORIGIN).status_code == 204


def test_stale_tab_logout_does_not_revoke_a_replacement_browser_session(web_client, web_database):
    login(web_client)
    with Session(web_database) as session:
        old_session_id = session.scalar(select(WebSession.id))
    token, cookie, _ = login(web_client)
    response = web_client.post("/api/auth/web/logout", headers={**ORIGIN, "X-Aura-Web-Session-Id": str(old_session_id)})
    assert response.status_code == 204 and "set-cookie" not in response.headers
    assert web_client.cookies.get("aura_refresh") == cookie
    assert web_client.get("/api/auth/me", headers=bearer(token)).status_code == 200


def test_password_change_revokes_all_web_sessions(web_client):
    first, cookie, _ = login(web_client)
    with TestClient(app, raise_server_exceptions=False) as second:
        other, _, _ = login(second)
        response = web_client.put("/api/auth/me/password", headers=bearer(first), json={
            "current_password": LOGIN["password"], "new_password": "replacement-session-password",
        })
        assert response.status_code == 204
        assert web_client.cookies.get("aura_refresh") is None
        for token in (first, other):
            assert second.get("/api/auth/me", headers=bearer(token)).status_code == 401
        assert second.post("/api/auth/web/refresh", headers=ORIGIN).status_code == 401
        assert web_client.post("/api/auth/web/refresh", headers={**ORIGIN, "Cookie": f"aura_refresh={cookie}"}).status_code == 401


def test_deleted_account_cascades_session_and_token_rows(web_client, web_database):
    token, cookie, _ = login(web_client)
    assert web_client.request("DELETE", "/api/auth/me", headers=bearer(token), json={"current_password": LOGIN["password"]}).status_code == 204
    with Session(web_database) as session:
        assert session.scalar(select(WebSession)) is None
        assert session.scalar(select(WebRefreshToken)) is None
    assert web_client.post("/api/auth/web/refresh", headers={**ORIGIN, "Cookie": f"aura_refresh={cookie}"}).status_code == 401


@pytest.mark.parametrize("endpoint", ["login", "refresh", "logout"])
@pytest.mark.parametrize("headers", [{}, {"Origin": "https://attacker.invalid", "X-Aura-Web-Session": "1"}, {"Origin": ORIGIN["Origin"]}])
def test_cookie_endpoints_require_explicit_origin_and_csrf_header(web_client, endpoint, headers):
    response = web_client.post(f"/api/auth/web/{endpoint}", headers=headers, json=LOGIN if endpoint == "login" else None)
    assert response.status_code == 403


@pytest.mark.parametrize("cookie", ["", "malformed", "x" * 43, "x" * 5000])
def test_missing_unknown_or_malformed_refresh_cookies_fail_closed(web_client, cookie):
    response = web_client.post("/api/auth/web/refresh", headers={**ORIGIN, "Cookie": f"aura_refresh={cookie}"})
    assert response.status_code == 401


def test_production_cookie_security_and_cors_preflight(web_client, monkeypatch):
    monkeypatch.setattr(settings, "refresh_cookie_secure", True)
    _, _, response = login(web_client)
    assert "Secure" in response.headers["set-cookie"] and "HttpOnly" in response.headers["set-cookie"]
    preflight = web_client.options("/api/auth/web/refresh", headers={
        "Origin": ORIGIN["Origin"], "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "X-Aura-Web-Session",
    })
    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-credentials"] == "true"


def test_session_subject_mismatch_is_rejected(web_client, web_database):
    login(web_client)
    with Session(web_database) as session:
        session_id = session.scalar(select(WebSession.id))
    assert web_client.post("/api/auth/register", json={**LOGIN, "email": "other@example.com"}).status_code == 201
    with Session(web_database) as session:
        user_id = session.scalar(select(User.id).where(User.email == "other@example.com"))
    forged_binding = create_access_token(user_id, session_id=session_id)
    assert web_client.get("/api/auth/me", headers=bearer(forged_binding)).status_code == 401


def test_web_session_migration_round_trip_preserves_existing_account(web_client, web_database):
    assert {"web_sessions", "web_refresh_tokens"} <= set(inspect(web_database).get_table_names())
    original_url = migration_settings.database_url
    migration_settings.database_url = web_database.url.render_as_string(hide_password=False)
    try:
        command.downgrade(Config(str(ROOT / "backend/alembic.ini")), "d6e8f0a2b4c6")
        assert "web_sessions" not in inspect(web_database).get_table_names()
        with web_database.connect() as connection:
            assert connection.scalar(text("SELECT count(*) FROM users")) == 1
        command.upgrade(Config(str(ROOT / "backend/alembic.ini")), HEAD)
    finally:
        migration_settings.database_url = original_url
