"""Live PostgreSQL verification for Aura's authentication HTTP workflow."""

from __future__ import annotations

from collections.abc import Iterator
import os
from pathlib import Path
from uuid import UUID

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import Engine, func, inspect, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.api.dependencies import get_database_session
from app.core.config import settings
from app.core.security import decode_access_token, verify_password
from app.database.connection import session_scope
from app.database.models import User
from app.main import app
from backend.app.core.config import settings as backend_settings
from backend.app.database.connection import create_database_engine


BACKEND_ROOT = Path(__file__).resolve().parents[3]
ALEMBIC_CONFIG_PATH = BACKEND_ROOT / "alembic.ini"
APPLICATION_TABLES = {
    "analyses",
    "holdings",
    "market_data",
    "portfolios",
    "users",
    "watchlist_items",
}
JWT_SECRET = "phase-5-live-postgresql-secret-value"
PASSWORD = "live-auth-password"


def _test_database_url() -> str:
    raw_url = os.getenv("AURA_TEST_DATABASE_URL")
    if not raw_url:
        pytest.skip(
            "AURA_TEST_DATABASE_URL is required for live PostgreSQL tests"
        )

    url = make_url(raw_url)
    if url.drivername != "postgresql+psycopg":
        pytest.fail(
            "AURA_TEST_DATABASE_URL must use postgresql+psycopg"
        )

    database_name = url.database or ""
    if database_name != "aura_test" and not database_name.startswith(
        "aura_test_"
    ):
        pytest.fail(
            "AURA_TEST_DATABASE_URL must target aura_test or aura_test_*"
        )
    return raw_url


def _alembic_config() -> Config:
    return Config(str(ALEMBIC_CONFIG_PATH))


def _table_names(engine: Engine) -> set[str]:
    return set(inspect(engine).get_table_names(schema="public"))


def _truncate_application_tables(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE TABLE analyses, holdings, portfolios, users, "
                "market_data CASCADE"
            )
        )


@pytest.fixture(scope="module")
def postgres_engine() -> Iterator[Engine]:
    raw_url = _test_database_url()
    engine = create_database_engine(raw_url)
    original_database_url = backend_settings.database_url
    upgraded = False
    initial_tables: set[str] = set()

    try:
        with engine.connect():
            initial_tables = _table_names(engine)

        unexpected_tables = initial_tables - {"alembic_version"}
        if unexpected_tables:
            pytest.fail(
                "Live test database must start empty; found tables: "
                f"{sorted(unexpected_tables)}"
            )

        if "alembic_version" in initial_tables:
            with engine.connect() as connection:
                revision_count = connection.scalar(
                    text("SELECT COUNT(*) FROM alembic_version")
                )
            if revision_count:
                pytest.fail(
                    "Live test database must not have an applied revision"
                )

        backend_settings.database_url = raw_url  # type: ignore[assignment]
        command.upgrade(_alembic_config(), "head")
        upgraded = True
        yield engine
    finally:
        try:
            if upgraded:
                command.downgrade(_alembic_config(), "base")
                remaining_tables = _table_names(engine) & APPLICATION_TABLES
                if remaining_tables:
                    raise AssertionError(
                        "Live test cleanup left application tables behind: "
                        f"{sorted(remaining_tables)}"
                    )
                if not initial_tables.issubset(_table_names(engine)):
                    raise AssertionError(
                        "Live test cleanup removed a pre-existing table"
                    )
        finally:
            backend_settings.database_url = original_database_url
            engine.dispose()


@pytest.fixture(scope="module")
def session_factory(
    postgres_engine: Engine,
) -> sessionmaker[Session]:
    return sessionmaker(
        bind=postgres_engine,
        class_=Session,
        autoflush=False,
        expire_on_commit=False,
    )


@pytest.fixture(scope="module")
def live_client(
    session_factory: sessionmaker[Session],
) -> Iterator[TestClient]:
    def override_database_session() -> Iterator[Session]:
        with session_scope(session_factory) as session:
            yield session

    previous_override = app.dependency_overrides.get(get_database_session)
    original_secret = settings.jwt_secret_key
    app.dependency_overrides[get_database_session] = override_database_session
    settings.jwt_secret_key = SecretStr(JWT_SECRET)

    try:
        with TestClient(app) as client:
            yield client
    finally:
        settings.jwt_secret_key = original_secret
        if previous_override is None:
            app.dependency_overrides.pop(get_database_session, None)
        else:
            app.dependency_overrides[get_database_session] = previous_override


@pytest.fixture(autouse=True)
def clean_application_rows(postgres_engine: Engine) -> Iterator[None]:
    _truncate_application_tables(postgres_engine)
    try:
        yield
    finally:
        _truncate_application_tables(postgres_engine)


def test_live_registration_login_me_duplicate_and_cleanup(
    live_client: TestClient,
    session_factory: sessionmaker[Session],
) -> None:
    register_response = live_client.post(
        "/api/auth/register",
        json={
            "email": "  Live.User@Example.COM  ",
            "password": PASSWORD,
        },
    )

    assert register_response.status_code == 201
    registered = register_response.json()
    assert registered["email"] == "live.user@example.com"
    assert set(registered) == {
        "id",
        "email",
        "display_name",
        "phone_number",
        "preferred_language",
        "timezone",
        "created_at",
        "updated_at",
    }
    assert registered["display_name"] is None
    assert registered["phone_number"] is None
    assert registered["preferred_language"] == "en"
    assert registered["timezone"] == "Asia/Bangkok"
    user_id = UUID(registered["id"])

    with session_factory() as session:
        persisted = session.scalar(
            select(User).where(User.email == "live.user@example.com")
        )
        assert persisted is not None
        assert persisted.id == user_id
        assert persisted.password_hash != PASSWORD
        assert verify_password(PASSWORD, persisted.password_hash)

    duplicate_response = live_client.post(
        "/api/auth/register",
        json={
            "email": "LIVE.USER@EXAMPLE.COM",
            "password": "different-password",
        },
    )
    assert duplicate_response.status_code == 409
    assert duplicate_response.json() == {
        "detail": "Email already registered"
    }

    with session_factory() as session:
        assert session.scalar(select(func.count(User.id))) == 1

    login_response = live_client.post(
        "/api/auth/login",
        json={
            "email": " live.user@EXAMPLE.com ",
            "password": PASSWORD,
        },
    )
    assert login_response.status_code == 200
    token_payload = login_response.json()
    assert token_payload["token_type"] == "bearer"
    assert decode_access_token(token_payload["access_token"]) == user_id

    me_response = live_client.get(
        "/api/auth/me",
        headers={
            "Authorization": f"Bearer {token_payload['access_token']}"
        },
    )
    assert me_response.status_code == 200
    assert me_response.json() == registered

    profile_response = live_client.patch(
        "/api/auth/me",
        headers={
            "Authorization": f"Bearer {token_payload['access_token']}"
        },
        json={
            "display_name": "Live Investor",
            "phone_number": "+66 81 234 5678",
            "preferred_language": "th",
            "timezone": "Asia/Yangon",
            "email": "updated.live@example.com",
            "current_password": PASSWORD,
        },
    )
    assert profile_response.status_code == 200
    profile = profile_response.json()
    assert profile["email"] == "updated.live@example.com"
    assert profile["display_name"] == "Live Investor"
    assert profile["phone_number"] == "+66 81 234 5678"
    assert profile["preferred_language"] == "th"
    assert profile["timezone"] == "Asia/Yangon"

    replacement_password = "replacement-live-password"
    password_response = live_client.put(
        "/api/auth/me/password",
        headers={
            "Authorization": f"Bearer {token_payload['access_token']}"
        },
        json={
            "current_password": PASSWORD,
            "new_password": replacement_password,
        },
    )
    assert password_response.status_code == 204

    old_login = live_client.post(
        "/api/auth/login",
        json={
            "email": "updated.live@example.com",
            "password": PASSWORD,
        },
    )
    assert old_login.status_code == 401
    new_login = live_client.post(
        "/api/auth/login",
        json={
            "email": "updated.live@example.com",
            "password": replacement_password,
        },
    )
    assert new_login.status_code == 200

    with session_factory() as session:
        updated_user = session.get(User, user_id)
        assert updated_user is not None
        assert updated_user.email == "updated.live@example.com"
        assert updated_user.display_name == "Live Investor"
        assert updated_user.phone_number == "+66 81 234 5678"
        assert updated_user.preferred_language == "th"
        assert updated_user.timezone == "Asia/Yangon"
        assert updated_user.password_hash is not None
        assert verify_password(
            replacement_password,
            updated_user.password_hash,
        )


def test_live_credentialless_user_remains_valid_but_cannot_login(
    live_client: TestClient,
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory.begin() as session:
        legacy_user = User()
        session.add(legacy_user)
        session.flush()
        legacy_user_id = legacy_user.id

    response = live_client.post(
        "/api/auth/login",
        json={
            "email": "legacy@example.com",
            "password": "legacy-password",
        },
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid email or password"}
    assert response.headers["www-authenticate"] == "Bearer"
    with session_factory() as session:
        persisted = session.get(User, legacy_user_id)
        assert persisted is not None
        assert persisted.email is None
        assert persisted.password_hash is None
