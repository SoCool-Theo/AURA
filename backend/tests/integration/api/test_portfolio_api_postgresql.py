"""Live PostgreSQL integration coverage for the portfolio HTTP API."""

from __future__ import annotations

import os
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Iterator
from uuid import UUID

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, inspect, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, selectinload, sessionmaker

from app.api.dependencies import get_database_session
from app.database.connection import session_scope
from app.database.models import Holding, Portfolio, User
from app.main import app
from backend.app.core.config import settings
from backend.app.database.connection import create_database_engine


BACKEND_ROOT = Path(__file__).resolve().parents[3]
ALEMBIC_CONFIG_PATH = BACKEND_ROOT / "alembic.ini"
APPLICATION_TABLES = {
    "analyses",
    "holdings",
    "market_data",
    "portfolios",
    "users",
}

USER_A_ID = UUID("10000000-0000-0000-0000-000000000001")
USER_B_ID = UUID("10000000-0000-0000-0000-000000000002")
UNKNOWN_USER_ID = UUID("10000000-0000-0000-0000-000000000099")


def _test_database_url() -> str:
    raw_url = os.getenv("AURA_TEST_DATABASE_URL")
    if not raw_url:
        pytest.skip("AURA_TEST_DATABASE_URL is required for live PostgreSQL tests")

    url = make_url(raw_url)
    if url.drivername != "postgresql+psycopg":
        pytest.fail("AURA_TEST_DATABASE_URL must use the postgresql+psycopg driver")

    database_name = url.database or ""
    if database_name != "aura_test" and not database_name.startswith("aura_test_"):
        pytest.fail("AURA_TEST_DATABASE_URL must target aura_test or aura_test_*")

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
    original_database_url = settings.database_url
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
                pytest.fail("Live test database must not have an applied revision")

        settings.database_url = raw_url
        command.upgrade(_alembic_config(), "head")
        upgraded = True
        yield engine
    finally:
        try:
            if upgraded:
                command.downgrade(_alembic_config(), "base")
                remaining_application_tables = (
                    _table_names(engine) & APPLICATION_TABLES
                )
                if remaining_application_tables:
                    raise AssertionError(
                        "Live test cleanup left application tables behind: "
                        f"{sorted(remaining_application_tables)}"
                    )

                if not initial_tables.issubset(_table_names(engine)):
                    raise AssertionError(
                        "Live test cleanup removed a table that existed before setup"
                    )
        finally:
            settings.database_url = original_database_url
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
    app.dependency_overrides[get_database_session] = override_database_session

    try:
        with TestClient(app) as client:
            yield client
    finally:
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


def _create_users(
    session_factory: sessionmaker[Session],
    *user_ids: UUID,
) -> None:
    with session_factory.begin() as session:
        session.add_all(User(id=user_id) for user_id in user_ids)


def _portfolio_with_holdings(
    session_factory: sessionmaker[Session],
    portfolio_id: UUID,
) -> Portfolio | None:
    with session_factory() as session:
        return session.scalar(
            select(Portfolio)
            .options(selectinload(Portfolio.holdings))
            .where(Portfolio.id == portfolio_id)
        )


def _headers(user_id: UUID) -> dict[str, str]:
    return {"X-User-ID": str(user_id)}


def _assert_portfolio_payload(
    payload: dict[str, object],
    *,
    portfolio_id: UUID,
    name: str,
    holdings: list[dict[str, object]],
) -> None:
    assert set(payload) == {
        "id",
        "name",
        "created_at",
        "updated_at",
        "holdings",
    }
    assert UUID(str(payload["id"])) == portfolio_id
    assert payload["name"] == name
    assert payload["holdings"] == holdings
    assert datetime.fromisoformat(str(payload["created_at"]).replace("Z", "+00:00"))
    assert datetime.fromisoformat(str(payload["updated_at"]).replace("Z", "+00:00"))
    assert "user_id" not in payload


def test_complete_crud_duplicate_and_persistence_across_fresh_sessions(
    live_client: TestClient,
    session_factory: sessionmaker[Session],
) -> None:
    _create_users(session_factory, USER_A_ID)
    headers = _headers(USER_A_ID)

    create_response = live_client.post(
        "/api/portfolios",
        headers=headers,
        json={"name": "Primary Portfolio"},
    )
    assert create_response.status_code == 201
    created = create_response.json()
    portfolio_id = UUID(created["id"])
    _assert_portfolio_payload(
        created,
        portfolio_id=portfolio_id,
        name="Primary Portfolio",
        holdings=[],
    )

    persisted_after_create = _portfolio_with_holdings(session_factory, portfolio_id)
    assert persisted_after_create is not None
    assert persisted_after_create.user_id == USER_A_ID
    assert persisted_after_create.name == "Primary Portfolio"

    list_response = live_client.get("/api/portfolios", headers=headers)
    assert list_response.status_code == 200
    summaries = list_response.json()["portfolios"]
    assert len(summaries) == 1
    assert set(summaries[0]) == {"id", "name", "created_at", "updated_at"}
    assert summaries[0]["id"] == str(portfolio_id)
    assert summaries[0]["name"] == "Primary Portfolio"
    assert "user_id" not in summaries[0]

    get_response = live_client.get(
        f"/api/portfolios/{portfolio_id}", headers=headers
    )
    assert get_response.status_code == 200
    assert get_response.json() == created

    rename_response = live_client.patch(
        f"/api/portfolios/{portfolio_id}",
        headers=headers,
        json={"name": "Long-Term Portfolio"},
    )
    assert rename_response.status_code == 200
    _assert_portfolio_payload(
        rename_response.json(),
        portfolio_id=portfolio_id,
        name="Long-Term Portfolio",
        holdings=[],
    )

    holdings_payload = {
        "holdings": [
            {"symbol": "AAPL", "weight": 0.6},
            {"symbol": "MSFT", "weight": 0.4},
        ]
    }
    holdings_response = live_client.put(
        f"/api/portfolios/{portfolio_id}/holdings",
        headers=headers,
        json=holdings_payload,
    )
    assert holdings_response.status_code == 200
    updated = holdings_response.json()
    expected_holdings = [
        {"symbol": "AAPL", "weight": 0.6, "position": 0},
        {"symbol": "MSFT", "weight": 0.4, "position": 1},
    ]
    _assert_portfolio_payload(
        updated,
        portfolio_id=portfolio_id,
        name="Long-Term Portfolio",
        holdings=expected_holdings,
    )

    persisted_after_mutation = _portfolio_with_holdings(
        session_factory, portfolio_id
    )
    assert persisted_after_mutation is not None
    assert persisted_after_mutation.name == "Long-Term Portfolio"
    assert [holding.symbol for holding in persisted_after_mutation.holdings] == [
        "AAPL",
        "MSFT",
    ]
    assert [holding.weight for holding in persisted_after_mutation.holdings] == [
        Decimal("0.600000"),
        Decimal("0.400000"),
    ]
    assert [holding.position for holding in persisted_after_mutation.holdings] == [
        0,
        1,
    ]

    duplicate_response = live_client.post(
        f"/api/portfolios/{portfolio_id}/duplicate",
        headers=headers,
        json={"name": "Long-Term Portfolio Copy"},
    )
    assert duplicate_response.status_code == 201
    duplicate = duplicate_response.json()
    duplicate_id = UUID(duplicate["id"])
    assert duplicate_id != portfolio_id
    _assert_portfolio_payload(
        duplicate,
        portfolio_id=duplicate_id,
        name="Long-Term Portfolio Copy",
        holdings=expected_holdings,
    )

    with session_factory() as session:
        source_holding_ids = set(
            session.scalars(
                select(Holding.id).where(Holding.portfolio_id == portfolio_id)
            )
        )
        duplicate_holding_ids = set(
            session.scalars(
                select(Holding.id).where(Holding.portfolio_id == duplicate_id)
            )
        )
    assert len(source_holding_ids) == 2
    assert len(duplicate_holding_ids) == 2
    assert source_holding_ids.isdisjoint(duplicate_holding_ids)

    delete_response = live_client.delete(
        f"/api/portfolios/{portfolio_id}", headers=headers
    )
    assert delete_response.status_code == 204
    assert delete_response.content == b""

    deleted_get_response = live_client.get(
        f"/api/portfolios/{portfolio_id}", headers=headers
    )
    assert deleted_get_response.status_code == 404
    assert deleted_get_response.json() == {"detail": "Portfolio not found"}

    duplicate_get_response = live_client.get(
        f"/api/portfolios/{duplicate_id}", headers=headers
    )
    assert duplicate_get_response.status_code == 200
    assert duplicate_get_response.json() == duplicate

    with session_factory() as session:
        assert session.get(Portfolio, portfolio_id) is None
        assert session.get(Portfolio, duplicate_id) is not None


def test_wrong_owner_receives_uniform_not_found_and_cannot_mutate(
    live_client: TestClient,
    session_factory: sessionmaker[Session],
) -> None:
    _create_users(session_factory, USER_A_ID, USER_B_ID)
    owner_headers = _headers(USER_A_ID)
    other_headers = _headers(USER_B_ID)

    create_response = live_client.post(
        "/api/portfolios",
        headers=owner_headers,
        json={"name": "Private Portfolio"},
    )
    assert create_response.status_code == 201
    portfolio_id = UUID(create_response.json()["id"])

    replace_response = live_client.put(
        f"/api/portfolios/{portfolio_id}/holdings",
        headers=owner_headers,
        json={"holdings": [{"symbol": "NVDA", "weight": 1.0}]},
    )
    assert replace_response.status_code == 200

    wrong_owner_responses = [
        live_client.get(
            f"/api/portfolios/{portfolio_id}", headers=other_headers
        ),
        live_client.patch(
            f"/api/portfolios/{portfolio_id}",
            headers=other_headers,
            json={"name": "Unauthorized Rename"},
        ),
        live_client.put(
            f"/api/portfolios/{portfolio_id}/holdings",
            headers=other_headers,
            json={
                "holdings": [{"symbol": "MSFT", "weight": 1.0}]
            },
        ),
        live_client.post(
            f"/api/portfolios/{portfolio_id}/duplicate",
            headers=other_headers,
            json={"name": "Unauthorized Copy"},
        ),
        live_client.delete(
            f"/api/portfolios/{portfolio_id}", headers=other_headers
        ),
    ]

    for response in wrong_owner_responses:
        assert response.status_code == 404
        assert response.json() == {"detail": "Portfolio not found"}

    persisted = _portfolio_with_holdings(session_factory, portfolio_id)
    assert persisted is not None
    assert persisted.user_id == USER_A_ID
    assert persisted.name == "Private Portfolio"
    assert [holding.symbol for holding in persisted.holdings] == ["NVDA"]
    assert [holding.weight for holding in persisted.holdings] == [
        Decimal("1.000000")
    ]

    with session_factory() as session:
        portfolio_ids = list(session.scalars(select(Portfolio.id)))
    assert portfolio_ids == [portfolio_id]

    owner_get_response = live_client.get(
        f"/api/portfolios/{portfolio_id}", headers=owner_headers
    )
    assert owner_get_response.status_code == 200
    assert owner_get_response.json() == replace_response.json()


def test_existing_owner_succeeds_and_unknown_valid_owner_is_rejected(
    live_client: TestClient,
    session_factory: sessionmaker[Session],
) -> None:
    _create_users(session_factory, USER_A_ID)

    existing_owner_response = live_client.get(
        "/api/portfolios", headers=_headers(USER_A_ID)
    )
    assert existing_owner_response.status_code == 200
    assert existing_owner_response.json() == {"portfolios": []}

    unknown_owner_response = live_client.get(
        "/api/portfolios", headers=_headers(UNKNOWN_USER_ID)
    )
    assert unknown_owner_response.status_code == 404
    assert unknown_owner_response.json() == {"detail": "User not found"}
