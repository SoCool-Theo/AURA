"""Guarded PostgreSQL end-to-end verification for Watchlist Backend V1."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from decimal import Decimal
import os
from pathlib import Path
from uuid import UUID

from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi.testclient import TestClient
import pytest
from pydantic import SecretStr
from sqlalchemy import Engine, func, inspect, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.api.dependencies import get_database_session
from app.core.config import settings as app_settings
from app.core.security import create_access_token
from app.database.connection import session_scope
from app.database.models import MarketData, User, WatchlistItem
from app.main import app
from backend.app.database.connection import create_database_engine


BACKEND_ROOT = Path(__file__).resolve().parents[3]
ALEMBIC_CONFIG_PATH = BACKEND_ROOT / "alembic.ini"
APPLICATION_TABLES = {
    "analyses",
    "holdings",
    "market_data",
    "portfolios",
    "simulations",
    "users",
    "watchlist_items",
}
USER_A_ID = UUID("74000000-0000-0000-0000-000000000001")
USER_B_ID = UUID("74000000-0000-0000-0000-000000000002")
JWT_SECRET = "watchlist-live-postgresql-secret-at-least-32-bytes"
WATCHLIST_REVISION = "a8d3f1c6b2e7"
TEST_SOURCE = "watchlist-v1-live-test"
TEST_DATES = (
    date(2099, 1, 2),
    date(2099, 9, 18),
    date(2099, 9, 21),
)


def _test_database_url() -> str:
    raw_url = os.getenv("AURA_TEST_DATABASE_URL")
    if not raw_url:
        pytest.skip(
            "AURA_TEST_DATABASE_URL is required for live PostgreSQL tests"
        )
    url = make_url(raw_url)
    database_name = url.database or ""
    if url.drivername != "postgresql+psycopg":
        pytest.fail("AURA_TEST_DATABASE_URL must use postgresql+psycopg")
    if (url.host or "").casefold() not in {"127.0.0.1", "localhost"}:
        pytest.fail("Watchlist live tests require a loopback database host")
    if url.port != 5433:
        pytest.fail("Watchlist live tests require the approved port 5433")
    if database_name != "aura_test" and not database_name.startswith(
        "aura_test_"
    ):
        pytest.fail("AURA_TEST_DATABASE_URL must target aura_test or aura_test_*")
    return raw_url


def _alembic_config() -> Config:
    return Config(str(ALEMBIC_CONFIG_PATH))


def _table_names(engine: Engine) -> set[str]:
    return set(inspect(engine).get_table_names(schema="public"))


def _current_revision(engine: Engine) -> str | None:
    with engine.connect() as connection:
        return connection.scalar(text("SELECT version_num FROM alembic_version"))


def _row_counts(engine: Engine) -> dict[str, int]:
    with engine.connect() as connection:
        return {
            table_name: int(
                connection.scalar(
                    text(f'SELECT count(*) FROM "{table_name}"')
                )
                or 0
            )
            for table_name in APPLICATION_TABLES
        }


def _reserved_row_count(engine: Engine) -> int:
    with engine.connect() as connection:
        return int(
            connection.scalar(
                text(
                    "SELECT "
                    "(SELECT count(*) FROM users WHERE id IN (:user_a, :user_b)) + "
                    "(SELECT count(*) FROM market_data WHERE source = :source)"
                ),
                {
                    "user_a": USER_A_ID,
                    "user_b": USER_B_ID,
                    "source": TEST_SOURCE,
                },
            )
            or 0
        )


def _delete_reserved_rows(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(
            text("DELETE FROM users WHERE id IN (:user_a, :user_b)"),
            {"user_a": USER_A_ID, "user_b": USER_B_ID},
        )
        connection.execute(
            text("DELETE FROM market_data WHERE source = :source"),
            {"source": TEST_SOURCE},
        )


@pytest.fixture(scope="module")
def postgres_engine() -> Iterator[Engine]:
    raw_url = _test_database_url()
    engine = create_database_engine(raw_url)
    baseline_counts: dict[str, int] = {}
    try:
        with engine.connect():
            table_names = _table_names(engine)
        if not APPLICATION_TABLES <= table_names:
            pytest.fail(
                "Watchlist live database is missing required tables: "
                f"{sorted(APPLICATION_TABLES - table_names)}"
            )
        configured_head = ScriptDirectory.from_config(
            _alembic_config()
        ).get_current_head()
        assert configured_head == WATCHLIST_REVISION
        if _current_revision(engine) != WATCHLIST_REVISION:
            pytest.fail(
                "Watchlist live database must be upgraded to the current head"
            )
        if _reserved_row_count(engine):
            pytest.fail(
                "reserved Watchlist live-test identities already exist; "
                "refusing to overwrite them"
            )
        baseline_counts = _row_counts(engine)
        yield engine
    finally:
        try:
            _delete_reserved_rows(engine)
            if baseline_counts and _row_counts(engine) != baseline_counts:
                raise AssertionError(
                    "Watchlist live test changed non-test database rows"
                )
            if _current_revision(engine) != WATCHLIST_REVISION:
                raise AssertionError(
                    "Watchlist live test changed the Alembic revision"
                )
        finally:
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
    original_secret = app_settings.jwt_secret_key
    app.dependency_overrides[get_database_session] = override_database_session
    app_settings.jwt_secret_key = SecretStr(JWT_SECRET)
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app_settings.jwt_secret_key = original_secret
        if previous_override is None:
            app.dependency_overrides.pop(get_database_session, None)
        else:
            app.dependency_overrides[get_database_session] = previous_override


@pytest.fixture(autouse=True)
def clean_rows(postgres_engine: Engine) -> Iterator[None]:
    if _reserved_row_count(postgres_engine):
        pytest.fail(
            "reserved Watchlist test rows exist before test execution"
        )
    try:
        yield
    finally:
        _delete_reserved_rows(postgres_engine)


def _headers(user_id: UUID) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user_id)}"}


def test_live_authenticated_watchlist_crud_enrichment_and_isolation(
    live_client: TestClient,
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory.begin() as session:
        session.add_all([User(id=USER_A_ID), User(id=USER_B_ID)])
        session.add_all(
            [
                MarketData(
                    symbol="AAPL",
                    date=TEST_DATES[0],
                    adjusted_close=Decimal("100"),
                    volume=None,
                    source=TEST_SOURCE,
                ),
                MarketData(
                    symbol="AAPL",
                    date=TEST_DATES[1],
                    adjusted_close=Decimal("120"),
                    volume=None,
                    source=TEST_SOURCE,
                ),
                MarketData(
                    symbol="AAPL",
                    date=TEST_DATES[2],
                    adjusted_close=Decimal("126"),
                    volume=None,
                    source=TEST_SOURCE,
                ),
            ]
        )

    create_response = live_client.post(
        "/api/watchlist",
        headers=_headers(USER_A_ID),
        json={"symbol": " aapl "},
    )
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["symbol"] == "AAPL"
    assert created["latest_price"] == 126.0
    assert created["latest_price_date"] == "2099-09-21"
    assert created["daily_change_percent"] == 5.0
    assert created["ytd_change_percent"] == 26.0
    assert "user_id" not in created

    duplicate_response = live_client.post(
        "/api/watchlist",
        headers=_headers(USER_A_ID),
        json={"symbol": "AAPL"},
    )
    assert duplicate_response.status_code == 409

    other_list = live_client.get(
        "/api/watchlist",
        headers=_headers(USER_B_ID),
    )
    assert other_list.status_code == 200
    assert other_list.json() == {"items": []}
    other_delete = live_client.delete(
        "/api/watchlist/AAPL",
        headers=_headers(USER_B_ID),
    )
    assert other_delete.status_code == 404
    assert other_delete.json() == {"detail": "Watchlist item not found"}

    owner_list = live_client.get(
        "/api/watchlist",
        headers=_headers(USER_A_ID),
    )
    assert owner_list.status_code == 200
    assert owner_list.json()["items"] == [created]

    delete_response = live_client.delete(
        "/api/watchlist/aapl",
        headers=_headers(USER_A_ID),
    )
    assert delete_response.status_code == 204

    with session_factory() as fresh_session:
        assert fresh_session.scalar(
            select(func.count()).select_from(WatchlistItem)
        ) == 0
        assert fresh_session.scalar(
            select(func.count()).select_from(MarketData).where(
                MarketData.source == TEST_SOURCE
            )
        ) == 3


def test_live_unique_constraint_and_user_delete_cascade(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory.begin() as session:
        session.add(User(id=USER_A_ID))
        session.add(
            WatchlistItem(user_id=USER_A_ID, symbol="AAPL")
        )

    with session_factory() as session:
        session.add(WatchlistItem(user_id=USER_A_ID, symbol="AAPL"))
        with pytest.raises(IntegrityError) as raised:
            session.flush()
        assert raised.value.orig.diag.constraint_name == (
            "uq_watchlist_items_user_symbol"
        )
        session.rollback()

    with session_factory.begin() as session:
        session.execute(
            text("DELETE FROM users WHERE id = :id"),
            {"id": USER_A_ID},
        )

    with session_factory() as session:
        assert session.scalar(
            select(func.count()).select_from(WatchlistItem)
        ) == 0
