"""Live PostgreSQL verification for Aura's historical scenario API."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
import math
import os
from pathlib import Path
import sys
from uuid import UUID, uuid4


BACKEND_ROOT = Path(__file__).resolve().parents[3]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from fastapi.testclient import TestClient
import pandas as pd
import pytest
from pydantic import SecretStr
from sqlalchemy import Engine, func, inspect, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.api.dependencies import get_database_session
from app.core.config import settings as app_settings
from app.core.security import verify_password
from app.database.connection import session_scope
from app.database.models import Analysis, MarketData, Portfolio, User
from app.database.repositories import PortfolioRepository
from app.main import app
from app.scenarios.definitions import (
    HISTORICAL_SCENARIOS,
    get_historical_scenario,
)
from app.scenarios.simulator import simulate_historical_scenario
from app.schemas.simulation import (
    HistoricalScenarioListResponse,
    HistoricalScenarioResponse,
    HistoricalScenarioSimulationResponse,
)
from app.services.market_data_service import MarketDataService
from backend.app.core.config import settings as migration_settings
from backend.app.database.connection import create_database_engine


ALEMBIC_CONFIG_PATH = BACKEND_ROOT / "alembic.ini"
APPLICATION_TABLES = {
    "analyses",
    "holdings",
    "market_data",
    "portfolios",
    "users",
}
JWT_SECRET = "phase-6-live-historical-scenario-api-secret"
PASSWORD = "Phase6-live-password!"
SCENARIO_ID = "covid-19-shock-2020"
CATALOGUE_PATH = "/api/simulations/historical-scenarios"
COMMON_DATES = (
    date(2020, 2, 3),
    date(2020, 2, 5),
    date(2020, 2, 6),
    date(2020, 2, 7),
)


@dataclass(frozen=True)
class AuthenticatedAccount:
    id: UUID
    email: str
    password: str
    headers: dict[str, str]


@dataclass(frozen=True)
class PersistenceState:
    portfolio: tuple[object, ...]
    holdings: tuple[tuple[object, ...], ...]
    market_data: tuple[tuple[object, ...], ...]
    analysis_count: int
    table_names: frozenset[str]


def _test_database_url() -> str:
    raw_url = os.getenv("AURA_TEST_DATABASE_URL")
    if not raw_url:
        pytest.fail(
            "AURA_TEST_DATABASE_URL is required for live PostgreSQL tests",
            pytrace=False,
        )

    url = make_url(raw_url)
    if url.drivername != "postgresql+psycopg":
        pytest.fail(
            "AURA_TEST_DATABASE_URL must use postgresql+psycopg",
            pytrace=False,
        )

    database_name = url.database or ""
    if (
        database_name != "aura_test"
        and not database_name.startswith("aura_test_")
    ):
        pytest.fail(
            "AURA_TEST_DATABASE_URL must target aura_test or aura_test_*",
            pytrace=False,
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


def _require_empty_application_tables(engine: Engine) -> None:
    with engine.connect() as connection:
        counts = {
            table_name: int(
                connection.scalar(
                    text(f'SELECT COUNT(*) FROM "{table_name}"')
                )
                or 0
            )
            for table_name in sorted(APPLICATION_TABLES)
        }
    populated = {
        table_name: count
        for table_name, count in counts.items()
        if count
    }
    if populated:
        pytest.fail(
            "Live test database contains pre-existing application rows: "
            f"{populated}",
            pytrace=False,
        )


@pytest.fixture(scope="module")
def postgres_engine() -> Iterator[Engine]:
    raw_url = _test_database_url()
    engine = create_database_engine(raw_url)
    original_database_url = migration_settings.database_url
    owns_schema = False
    schema_ready = False

    try:
        with engine.connect() as connection:
            initial_tables = set(
                inspect(connection).get_table_names(schema="public")
            )
            initial_revision = MigrationContext.configure(
                connection
            ).get_current_revision()

        unexpected_tables = initial_tables - APPLICATION_TABLES - {
            "alembic_version"
        }
        if unexpected_tables:
            pytest.fail(
                "Live test database contains unexpected public tables: "
                f"{sorted(unexpected_tables)}",
                pytrace=False,
            )

        existing_application_tables = initial_tables & APPLICATION_TABLES
        expected_head = ScriptDirectory.from_config(
            _alembic_config()
        ).get_current_head()
        if existing_application_tables:
            if existing_application_tables != APPLICATION_TABLES:
                pytest.fail(
                    "Live test database has an incomplete application schema",
                    pytrace=False,
                )
            if initial_revision != expected_head:
                pytest.fail(
                    "Live test database migrations are not current",
                    pytrace=False,
                )
            _require_empty_application_tables(engine)
        else:
            if initial_revision is not None:
                pytest.fail(
                    "Live test database has a revision without its schema",
                    pytrace=False,
                )
            migration_settings.database_url = raw_url  # type: ignore[assignment]
            command.upgrade(_alembic_config(), "head")
            owns_schema = True

        schema_ready = True
        yield engine
    finally:
        try:
            if schema_ready:
                _truncate_application_tables(engine)
            if owns_schema:
                command.downgrade(_alembic_config(), "base")
        finally:
            migration_settings.database_url = original_database_url
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
    original_jwt_secret = app_settings.jwt_secret_key
    app.dependency_overrides[get_database_session] = override_database_session
    app_settings.jwt_secret_key = SecretStr(JWT_SECRET)

    try:
        with TestClient(app) as client:
            yield client
    finally:
        app_settings.jwt_secret_key = original_jwt_secret
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


def _register_and_login(
    client: TestClient,
    *,
    email: str,
    password: str = PASSWORD,
) -> AuthenticatedAccount:
    canonical_email = email.strip().casefold()
    registration = client.post(
        "/api/auth/register",
        json={"email": email, "password": password},
    )
    assert registration.status_code == 201
    assert registration.json()["email"] == canonical_email
    user_id = UUID(registration.json()["id"])

    login = client.post(
        "/api/auth/login",
        json={"email": canonical_email, "password": password},
    )
    assert login.status_code == 200
    assert login.json()["token_type"] == "bearer"
    access_token = login.json()["access_token"]
    assert access_token
    return AuthenticatedAccount(
        id=user_id,
        email=canonical_email,
        password=password,
        headers={"Authorization": f"Bearer {access_token}"},
    )


def _create_portfolio(
    client: TestClient,
    *,
    account: AuthenticatedAccount,
    name: str,
    holdings: Sequence[tuple[str, float]],
) -> UUID:
    created = client.post(
        "/api/portfolios",
        headers=account.headers,
        json={"name": name},
    )
    assert created.status_code == 201
    portfolio_id = UUID(created.json()["id"])

    replaced = client.put(
        f"/api/portfolios/{portfolio_id}/holdings",
        headers=account.headers,
        json={
            "holdings": [
                {"symbol": symbol, "weight": weight}
                for symbol, weight in holdings
            ]
        },
    )
    assert replaced.status_code == 200
    assert [item["symbol"] for item in replaced.json()["holdings"]] == [
        symbol for symbol, _ in holdings
    ]
    assert [item["position"] for item in replaced.json()["holdings"]] == list(
        range(len(holdings))
    )
    assert [item["weight"] for item in replaced.json()["holdings"]] == pytest.approx(
        [weight for _, weight in holdings]
    )
    return portfolio_id


def _market_frame(
    rows: Sequence[tuple[str, date, float, int | None]],
) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.to_datetime([row[1] for row in rows]),
            "symbol": pd.Series([row[0] for row in rows], dtype="string"),
            "adjusted_close": pd.Series(
                [row[2] for row in rows],
                dtype="float64",
            ),
            "volume": pd.Series([row[3] for row in rows], dtype="Int64"),
            "source": pd.Series(
                ["phase-6-live"] * len(rows),
                dtype="string",
            ),
        }
    )


def _store_market_data(
    session_factory: sessionmaker[Session],
    rows: Sequence[tuple[str, date, float, int | None]],
) -> None:
    with session_factory.begin() as session:
        assert MarketDataService(session).store(_market_frame(rows)) == len(rows)


def _persistence_state(
    session_factory: sessionmaker[Session],
    postgres_engine: Engine,
    portfolio_id: UUID,
) -> PersistenceState:
    with session_factory() as session:
        portfolio = PortfolioRepository(session).get_with_holdings(portfolio_id)
        assert portfolio is not None
        portfolio_state = (
            portfolio.id,
            portfolio.user_id,
            portfolio.name,
            portfolio.created_at,
            portfolio.updated_at,
        )
        holding_state = tuple(
            (
                holding.id,
                holding.portfolio_id,
                holding.symbol,
                holding.weight,
                holding.position,
                holding.created_at,
                holding.updated_at,
            )
            for holding in portfolio.holdings
        )
        market_state = tuple(
            (
                row.symbol,
                row.date,
                row.adjusted_close,
                row.volume,
                row.source,
            )
            for row in session.scalars(
                select(MarketData).order_by(MarketData.symbol, MarketData.date)
            ).all()
        )
        analysis_count = int(
            session.scalar(select(func.count()).select_from(Analysis)) or 0
        )

    return PersistenceState(
        portfolio=portfolio_state,
        holdings=holding_state,
        market_data=market_state,
        analysis_count=analysis_count,
        table_names=frozenset(_table_names(postgres_engine)),
    )


def _simulation_path(portfolio_id: UUID) -> str:
    return (
        f"/api/portfolios/{portfolio_id}"
        "/simulations/historical-scenarios"
    )


def test_live_public_catalogue_and_authentication_boundary(
    live_client: TestClient,
    session_factory: sessionmaker[Session],
    postgres_engine: Engine,
) -> None:
    with postgres_engine.connect() as connection:
        server_version = connection.scalar(text("SHOW server_version"))
    assert isinstance(server_version, str)
    assert server_version

    catalogue_response = live_client.get(CATALOGUE_PATH)
    assert catalogue_response.status_code == 200
    expected_catalogue = HistoricalScenarioListResponse(
        scenarios=[
            HistoricalScenarioResponse(
                id=scenario.id,
                display_name=scenario.display_name,
                description=scenario.description,
                requested_start_date=scenario.requested_start_date,
                requested_end_date=scenario.requested_end_date,
            )
            for scenario in HISTORICAL_SCENARIOS
        ]
    )
    assert catalogue_response.json() == expected_catalogue.model_dump(mode="json")

    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(User)) == 0
        assert session.scalar(select(func.count()).select_from(Portfolio)) == 0
        assert session.scalar(select(func.count()).select_from(MarketData)) == 0

    protected_path = _simulation_path(uuid4())
    for headers in (
        {},
        {"Authorization": "Bearer not-a-valid-token"},
        {"X-User-ID": str(uuid4())},
    ):
        response = live_client.post(
            protected_path,
            headers=headers,
            json={"scenario_id": SCENARIO_ID},
        )
        assert response.status_code == 401
        assert response.json() == {
            "detail": "Invalid or missing authentication credentials"
        }
        assert response.headers["www-authenticate"] == "Bearer"


def test_live_complete_simulation_alignment_and_read_only_persistence(
    live_client: TestClient,
    session_factory: sessionmaker[Session],
    postgres_engine: Engine,
) -> None:
    account = _register_and_login(
        live_client,
        email="  PHASE6-OWNER@Example.COM ",
    )
    portfolio_id = _create_portfolio(
        live_client,
        account=account,
        name="Phase 6 Historical Portfolio",
        holdings=(("P6BND", 0.4), ("P6AAPL", 0.6)),
    )
    rows = (
        ("P6AAPL", date(2020, 1, 31), 999.0, 900),
        ("P6AAPL", date(2020, 2, 3), 100.0, 1_001),
        ("P6AAPL", date(2020, 2, 4), 50.0, 1_002),
        ("P6AAPL", date(2020, 2, 5), 80.0, 1_003),
        ("P6AAPL", date(2020, 2, 6), 90.0, 1_004),
        ("P6AAPL", date(2020, 2, 7), 100.0, 1_005),
        ("P6AAPL", date(2020, 5, 1), 999.0, 1_006),
        ("P6BND", date(2020, 2, 3), 100.0, None),
        ("P6BND", date(2020, 2, 5), 100.0, None),
        ("P6BND", date(2020, 2, 6), 80.0, None),
        ("P6BND", date(2020, 2, 7), 100.0, None),
        ("P6BND", date(2020, 2, 10), 123.0, None),
    )
    _store_market_data(session_factory, rows)

    with session_factory() as fresh_session:
        persisted_user = fresh_session.get(User, account.id)
        persisted_portfolio = PortfolioRepository(
            fresh_session
        ).get_with_holdings(portfolio_id)
        assert persisted_user is not None
        assert persisted_user.email == "phase6-owner@example.com"
        assert persisted_user.password_hash is not None
        assert persisted_user.password_hash != account.password
        assert verify_password(account.password, persisted_user.password_hash)
        assert persisted_portfolio is not None
        assert persisted_portfolio.user_id == account.id
        assert [
            (holding.symbol, holding.position, holding.weight)
            for holding in persisted_portfolio.holdings
        ] == [
            ("P6BND", 0, Decimal("0.400000000000000000")),
            ("P6AAPL", 1, Decimal("0.600000000000000000")),
        ]

    state_before = _persistence_state(
        session_factory,
        postgres_engine,
        portfolio_id,
    )
    assert state_before.analysis_count == 0
    assert "simulations" not in state_before.table_names
    assert "simulation_history" not in state_before.table_names

    response = live_client.post(
        _simulation_path(portfolio_id),
        headers=account.headers,
        json={"scenario_id": SCENARIO_ID},
    )
    assert response.status_code == 200
    result = HistoricalScenarioSimulationResponse.model_validate(response.json())
    scenario = get_historical_scenario(SCENARIO_ID)
    assert scenario is not None
    assert result.portfolio_id == portfolio_id
    assert result.portfolio_name == "Phase 6 Historical Portfolio"
    assert result.scenario.id == scenario.id
    assert result.scenario.requested_start_date == scenario.requested_start_date
    assert result.scenario.requested_end_date == scenario.requested_end_date
    assert result.metadata.effective_start_date == COMMON_DATES[0]
    assert result.metadata.effective_end_date == COMMON_DATES[-1]
    assert result.metadata.price_observation_count == len(COMMON_DATES)
    assert result.metadata.return_observation_count == len(COMMON_DATES) - 1
    assert [point.date for point in result.trajectory] == list(COMMON_DATES)
    assert len(result.trajectory) == result.metadata.price_observation_count
    assert result.metrics.normalized_starting_value == 1.0

    expected_prices = pd.DataFrame(
        [
            [100.0, 100.0],
            [100.0, 80.0],
            [80.0, 90.0],
            [100.0, 100.0],
        ],
        index=pd.DatetimeIndex(COMMON_DATES),
        columns=("P6BND", "P6AAPL"),
        dtype=float,
    )
    expected = simulate_historical_scenario(
        expected_prices,
        {"P6BND": 0.4, "P6AAPL": 0.6},
    )
    assert result.metrics.normalized_ending_value == pytest.approx(
        expected.normalized_ending_value
    )
    assert result.metrics.cumulative_return == pytest.approx(
        expected.cumulative_return
    )
    assert result.metrics.annualized_volatility == pytest.approx(
        expected.annualized_volatility
    )
    if expected.sharpe_ratio is None:
        assert result.metrics.sharpe_ratio is None
    else:
        assert result.metrics.sharpe_ratio is not None
        assert math.isfinite(result.metrics.sharpe_ratio)
        assert result.metrics.sharpe_ratio == pytest.approx(expected.sharpe_ratio)
    assert result.metrics.maximum_drawdown.max_drawdown == pytest.approx(
        expected.maximum_drawdown.max_drawdown
    )
    assert result.metrics.maximum_drawdown.max_drawdown < 0
    assert result.metrics.maximum_drawdown.peak_date == (
        None
        if expected.maximum_drawdown.peak_date is None
        else expected.maximum_drawdown.peak_date.date()
    )
    assert result.metrics.maximum_drawdown.trough_date == (
        None
        if expected.maximum_drawdown.trough_date is None
        else expected.maximum_drawdown.trough_date.date()
    )
    assert [point.normalized_value for point in result.trajectory] == pytest.approx(
        [point.normalized_value for point in expected.trajectory]
    )

    state_after = _persistence_state(
        session_factory,
        postgres_engine,
        portfolio_id,
    )
    assert state_after == state_before


def test_live_missing_data_and_insufficient_common_observations(
    live_client: TestClient,
    session_factory: sessionmaker[Session],
) -> None:
    account = _register_and_login(
        live_client,
        email="phase6-data-errors@example.com",
    )
    missing_portfolio_id = _create_portfolio(
        live_client,
        account=account,
        name="Phase 6 Missing Data",
        holdings=(
            ("P6PRESENT", 0.5),
            ("P6MISSB", 0.3),
            ("P6MISSA", 0.2),
        ),
    )
    insufficient_portfolio_id = _create_portfolio(
        live_client,
        account=account,
        name="Phase 6 Insufficient Common Dates",
        holdings=(("P6SHORTA", 0.5), ("P6SHORTB", 0.5)),
    )
    _store_market_data(
        session_factory,
        (
            ("P6PRESENT", date(2020, 2, 3), 100.0, None),
            ("P6SHORTA", date(2020, 2, 3), 100.0, None),
            ("P6SHORTA", date(2020, 2, 4), 101.0, None),
            ("P6SHORTA", date(2020, 2, 5), 102.0, None),
            ("P6SHORTB", date(2020, 2, 3), 50.0, None),
            ("P6SHORTB", date(2020, 2, 5), 51.0, None),
        ),
    )

    missing_response = live_client.post(
        _simulation_path(missing_portfolio_id),
        headers=account.headers,
        json={"scenario_id": SCENARIO_ID},
    )
    assert missing_response.status_code == 422
    assert missing_response.json() == {
        "detail": (
            "market data is unavailable for requested symbols: "
            "P6MISSB, P6MISSA"
        )
    }

    insufficient_response = live_client.post(
        _simulation_path(insufficient_portfolio_id),
        headers=account.headers,
        json={"scenario_id": SCENARIO_ID},
    )
    assert insufficient_response.status_code == 422
    assert insufficient_response.json() == {
        "detail": (
            "prices must contain at least three rows for historical simulation"
        )
    }


def test_live_unknown_scenario_returns_not_found(
    live_client: TestClient,
) -> None:
    account = _register_and_login(
        live_client,
        email="phase6-unknown-scenario@example.com",
    )
    portfolio_id = _create_portfolio(
        live_client,
        account=account,
        name="Phase 6 Unknown Scenario",
        holdings=(("P6UNKNOWN", 1.0),),
    )

    response = live_client.post(
        _simulation_path(portfolio_id),
        headers=account.headers,
        json={"scenario_id": "syntactically-valid-unknown-scenario"},
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "Historical scenario not found"}


def test_live_two_user_ownership_isolation_returns_private_not_found(
    live_client: TestClient,
) -> None:
    owner = _register_and_login(
        live_client,
        email="phase6-owner-a@example.com",
    )
    other_user = _register_and_login(
        live_client,
        email="phase6-owner-b@example.com",
    )
    owner_portfolio_id = _create_portfolio(
        live_client,
        account=owner,
        name="Phase 6 User A Portfolio",
        holdings=(("P6PRIVATE", 1.0),),
    )

    response = live_client.post(
        _simulation_path(owner_portfolio_id),
        headers=other_user.headers,
        json={"scenario_id": SCENARIO_ID},
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "Portfolio not found"}
