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
from app.database.models import Analysis, MarketData, Portfolio, Simulation, User
from app.database.repositories import PortfolioRepository
from app.main import app
from app.scenarios.definitions import (
    HISTORICAL_SCENARIOS,
    get_historical_scenario,
)
from app.scenarios.simulator import (
    HistoricalSimulationResult,
    simulate_allocation_change,
    simulate_historical_scenario,
)
from app.schemas.simulation import (
    AllocationSimulationResponse,
    AllocationSimulationResult,
    CombinedSimulationResponse,
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
    "simulations",
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
ALLOCATION_START_DATE = date(2064, 1, 1)
ALLOCATION_END_DATE = date(2064, 1, 8)
ALLOCATION_COMMON_DATES = (
    date(2064, 1, 2),
    date(2064, 1, 4),
    date(2064, 1, 6),
    date(2064, 1, 7),
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
    simulation_count: int
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
                "TRUNCATE TABLE simulations, analyses, holdings, portfolios, users, "
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
        simulation_count = int(
            session.scalar(select(func.count()).select_from(Simulation)) or 0
        )

    return PersistenceState(
        portfolio=portfolio_state,
        holdings=holding_state,
        market_data=market_state,
        analysis_count=analysis_count,
        simulation_count=simulation_count,
        table_names=frozenset(_table_names(postgres_engine)),
    )


def _simulation_path(portfolio_id: UUID) -> str:
    return (
        f"/api/portfolios/{portfolio_id}"
        "/simulations/historical-scenarios"
    )


def _allocation_simulation_path(portfolio_id: UUID) -> str:
    return f"/api/portfolios/{portfolio_id}/simulations/allocations"


def _combined_simulation_path(portfolio_id: UUID) -> str:
    return f"/api/portfolios/{portfolio_id}/simulations/combined"


def _allocation_request(
    holdings: Sequence[tuple[str, float]],
) -> dict[str, object]:
    return {
        "start_date": ALLOCATION_START_DATE.isoformat(),
        "end_date": ALLOCATION_END_DATE.isoformat(),
        "modified_allocation": [
            {"symbol": symbol, "weight": weight}
            for symbol, weight in holdings
        ],
    }


def _combined_request(
    holdings: Sequence[tuple[str, float]],
    *,
    scenario_id: str = SCENARIO_ID,
) -> dict[str, object]:
    return {
        "scenario_id": scenario_id,
        "modified_allocation": [
            {"symbol": symbol, "weight": weight}
            for symbol, weight in holdings
        ],
    }


def _assert_allocation_result_matches(
    actual: AllocationSimulationResult,
    expected: HistoricalSimulationResult,
) -> None:
    assert actual.metrics.normalized_starting_value == pytest.approx(
        expected.normalized_starting_value
    )
    assert actual.metrics.normalized_ending_value == pytest.approx(
        expected.normalized_ending_value
    )
    assert actual.metrics.cumulative_return == pytest.approx(
        expected.cumulative_return
    )
    assert actual.metrics.annualized_volatility == pytest.approx(
        expected.annualized_volatility
    )
    if expected.sharpe_ratio is None:
        assert actual.metrics.sharpe_ratio is None
    else:
        assert actual.metrics.sharpe_ratio == pytest.approx(
            expected.sharpe_ratio
        )
    assert actual.metrics.maximum_drawdown.max_drawdown == pytest.approx(
        expected.maximum_drawdown.max_drawdown
    )
    assert actual.metrics.maximum_drawdown.peak_date == (
        None
        if expected.maximum_drawdown.peak_date is None
        else expected.maximum_drawdown.peak_date.date()
    )
    assert actual.metrics.maximum_drawdown.trough_date == (
        None
        if expected.maximum_drawdown.trough_date is None
        else expected.maximum_drawdown.trough_date.date()
    )
    assert [point.date for point in actual.trajectory] == [
        point.date.date() for point in expected.trajectory
    ]
    assert [point.normalized_value for point in actual.trajectory] == (
        pytest.approx(
            [point.normalized_value for point in expected.trajectory]
        )
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
    assert state_before.simulation_count == 0
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


def test_live_allocation_simulation_canonicalizes_order_and_is_read_only(
    live_client: TestClient,
    session_factory: sessionmaker[Session],
    postgres_engine: Engine,
) -> None:
    account = _register_and_login(
        live_client,
        email="phase6-allocation-owner@example.com",
    )
    portfolio_id = _create_portfolio(
        live_client,
        account=account,
        name="Phase 6 Allocation Portfolio",
        holdings=(("AAPL", 0.5), ("BND", 0.3), ("GLD", 0.2)),
    )
    _store_market_data(
        session_factory,
        (
            ("AAPL", date(2064, 1, 1), 98.0, 1_001),
            ("AAPL", date(2064, 1, 2), 100.0, 1_002),
            ("AAPL", date(2064, 1, 3), 102.0, 1_003),
            ("AAPL", date(2064, 1, 4), 104.0, 1_004),
            ("AAPL", date(2064, 1, 6), 103.0, 1_006),
            ("AAPL", date(2064, 1, 7), 108.0, 1_007),
            ("AAPL", date(2064, 1, 8), 109.0, 1_008),
            ("BND", date(2064, 1, 2), 100.0, None),
            ("BND", date(2064, 1, 3), 100.5, None),
            ("BND", date(2064, 1, 4), 99.0, None),
            ("BND", date(2064, 1, 5), 100.0, None),
            ("BND", date(2064, 1, 6), 101.0, None),
            ("BND", date(2064, 1, 7), 102.0, None),
            ("GLD", date(2064, 1, 2), 50.0, 2_002),
            ("GLD", date(2064, 1, 4), 52.0, 2_004),
            ("GLD", date(2064, 1, 6), 51.0, 2_006),
            ("GLD", date(2064, 1, 7), 54.0, 2_007),
        ),
    )
    state_before = _persistence_state(
        session_factory,
        postgres_engine,
        portfolio_id,
    )
    assert state_before.analysis_count == 0
    assert state_before.simulation_count == 0
    assert "simulation_history" not in state_before.table_names

    response = live_client.post(
        _allocation_simulation_path(portfolio_id),
        headers=account.headers,
        json=_allocation_request(
            (("GLD", 0.0), ("AAPL", 0.7), ("BND", 0.3))
        ),
    )

    assert response.status_code == 200
    result = AllocationSimulationResponse.model_validate(response.json())
    assert result.portfolio_id == portfolio_id
    assert result.portfolio_name == "Phase 6 Allocation Portfolio"
    assert result.start_date == ALLOCATION_START_DATE
    assert result.end_date == ALLOCATION_END_DATE
    assert result.metadata.effective_start_date == ALLOCATION_COMMON_DATES[0]
    assert result.metadata.effective_end_date == ALLOCATION_COMMON_DATES[-1]
    assert result.metadata.price_observation_count == len(
        ALLOCATION_COMMON_DATES
    )
    assert result.metadata.return_observation_count == (
        len(ALLOCATION_COMMON_DATES) - 1
    )

    assert [item.symbol for item in result.original.allocation] == [
        "AAPL",
        "BND",
        "GLD",
    ]
    assert [float(item.weight) for item in result.original.allocation] == (
        pytest.approx([0.5, 0.3, 0.2])
    )
    assert [item.symbol for item in result.modified.allocation] == [
        "AAPL",
        "BND",
        "GLD",
    ]
    assert [float(item.weight) for item in result.modified.allocation] == (
        pytest.approx([0.7, 0.3, 0.0])
    )
    assert result.modified.allocation[-1].symbol == "GLD"
    assert result.modified.allocation[-1].weight == 0

    expected_prices = pd.DataFrame(
        [
            [100.0, 100.0, 50.0],
            [104.0, 99.0, 52.0],
            [103.0, 101.0, 51.0],
            [108.0, 102.0, 54.0],
        ],
        index=pd.DatetimeIndex(ALLOCATION_COMMON_DATES),
        columns=("AAPL", "BND", "GLD"),
        dtype=float,
    )
    expected = simulate_allocation_change(
        expected_prices,
        {"AAPL": 0.5, "BND": 0.3, "GLD": 0.2},
        {"AAPL": 0.7, "BND": 0.3, "GLD": 0.0},
    )
    _assert_allocation_result_matches(result.original, expected.original)
    _assert_allocation_result_matches(result.modified, expected.modified)
    assert result.comparison.normalized_ending_value_delta == pytest.approx(
        expected.normalized_ending_value_delta
    )
    assert result.comparison.cumulative_return_delta == pytest.approx(
        expected.cumulative_return_delta
    )
    assert result.comparison.annualized_volatility_delta == pytest.approx(
        expected.annualized_volatility_delta
    )
    if expected.sharpe_ratio_delta is None:
        assert result.comparison.sharpe_ratio_delta is None
    else:
        assert result.comparison.sharpe_ratio_delta == pytest.approx(
            expected.sharpe_ratio_delta
        )
    assert result.comparison.maximum_drawdown_delta == pytest.approx(
        expected.maximum_drawdown_delta
    )
    assert [point.date for point in result.original.trajectory] == list(
        ALLOCATION_COMMON_DATES
    )
    assert [point.date for point in result.modified.trajectory] == list(
        ALLOCATION_COMMON_DATES
    )

    state_after = _persistence_state(
        session_factory,
        postgres_engine,
        portfolio_id,
    )
    assert state_after == state_before
    assert [(row[2], row[4], row[3]) for row in state_after.holdings] == [
        ("AAPL", 0, Decimal("0.500000000000000000")),
        ("BND", 1, Decimal("0.300000000000000000")),
        ("GLD", 2, Decimal("0.200000000000000000")),
    ]
    assert len([row for row in state_after.market_data if row[0] == "GLD"]) == 4


def test_live_allocation_authentication_and_ownership_are_private(
    live_client: TestClient,
    session_factory: sessionmaker[Session],
    postgres_engine: Engine,
) -> None:
    owner = _register_and_login(
        live_client,
        email="phase6-allocation-private-owner@example.com",
    )
    other_user = _register_and_login(
        live_client,
        email="phase6-allocation-private-other@example.com",
    )
    portfolio_id = _create_portfolio(
        live_client,
        account=owner,
        name="Phase 6 Private Allocation Portfolio",
        holdings=(("AAPL", 0.5), ("BND", 0.3), ("GLD", 0.2)),
    )
    state_before = _persistence_state(
        session_factory,
        postgres_engine,
        portfolio_id,
    )
    request = _allocation_request(
        (("AAPL", 0.5), ("BND", 0.3), ("GLD", 0.2))
    )

    unauthenticated = live_client.post(
        _allocation_simulation_path(portfolio_id),
        headers={"X-User-ID": str(owner.id)},
        json=request,
    )
    assert unauthenticated.status_code == 401
    assert unauthenticated.json() == {
        "detail": "Invalid or missing authentication credentials"
    }

    wrong_owner = live_client.post(
        _allocation_simulation_path(portfolio_id),
        headers=other_user.headers,
        json=request,
    )
    assert wrong_owner.status_code == 404
    assert wrong_owner.json() == {"detail": "Portfolio not found"}

    state_after = _persistence_state(
        session_factory,
        postgres_engine,
        portfolio_id,
    )
    assert state_after == state_before


def test_live_allocation_symbol_mismatch_is_unprocessable_and_read_only(
    live_client: TestClient,
    session_factory: sessionmaker[Session],
    postgres_engine: Engine,
) -> None:
    account = _register_and_login(
        live_client,
        email="phase6-allocation-symbols@example.com",
    )
    portfolio_id = _create_portfolio(
        live_client,
        account=account,
        name="Phase 6 Allocation Symbol Mismatch",
        holdings=(("AAPL", 0.5), ("BND", 0.3), ("GLD", 0.2)),
    )
    state_before = _persistence_state(
        session_factory,
        postgres_engine,
        portfolio_id,
    )

    response = live_client.post(
        _allocation_simulation_path(portfolio_id),
        headers=account.headers,
        json=_allocation_request(
            (("MSFT", 0.2), ("AAPL", 0.5), ("BND", 0.3))
        ),
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": (
            "modified allocation symbols must exactly match saved "
            "portfolio symbols"
        )
    }
    assert "traceback" not in response.text.casefold()
    state_after = _persistence_state(
        session_factory,
        postgres_engine,
        portfolio_id,
    )
    assert state_after == state_before


def test_live_allocation_data_failures_are_unprocessable_and_read_only(
    live_client: TestClient,
    session_factory: sessionmaker[Session],
    postgres_engine: Engine,
) -> None:
    account = _register_and_login(
        live_client,
        email="phase6-allocation-data-errors@example.com",
    )
    missing_portfolio_id = _create_portfolio(
        live_client,
        account=account,
        name="Phase 6 Allocation Missing Data",
        holdings=(("MISSA", 0.5), ("MISSB", 0.5)),
    )
    insufficient_portfolio_id = _create_portfolio(
        live_client,
        account=account,
        name="Phase 6 Allocation Insufficient Data",
        holdings=(("SHORTA", 0.5), ("SHORTB", 0.5)),
    )
    _store_market_data(
        session_factory,
        (
            ("MISSA", date(2064, 1, 2), 100.0, None),
            ("SHORTA", date(2064, 1, 2), 100.0, None),
            ("SHORTA", date(2064, 1, 3), 101.0, None),
            ("SHORTA", date(2064, 1, 4), 102.0, None),
            ("SHORTB", date(2064, 1, 2), 50.0, None),
            ("SHORTB", date(2064, 1, 4), 51.0, None),
            ("SHORTB", date(2064, 1, 5), 52.0, None),
        ),
    )
    missing_before = _persistence_state(
        session_factory,
        postgres_engine,
        missing_portfolio_id,
    )
    insufficient_before = _persistence_state(
        session_factory,
        postgres_engine,
        insufficient_portfolio_id,
    )

    missing_response = live_client.post(
        _allocation_simulation_path(missing_portfolio_id),
        headers=account.headers,
        json=_allocation_request((("MISSA", 0.5), ("MISSB", 0.5))),
    )
    assert missing_response.status_code == 422
    assert missing_response.json() == {
        "detail": "market data is unavailable for requested symbols: MISSB"
    }

    insufficient_response = live_client.post(
        _allocation_simulation_path(insufficient_portfolio_id),
        headers=account.headers,
        json=_allocation_request((("SHORTA", 0.5), ("SHORTB", 0.5))),
    )
    assert insufficient_response.status_code == 422
    assert insufficient_response.json() == {
        "detail": (
            "prices must contain at least three rows for historical simulation"
        )
    }

    missing_after = _persistence_state(
        session_factory,
        postgres_engine,
        missing_portfolio_id,
    )
    insufficient_after = _persistence_state(
        session_factory,
        postgres_engine,
        insufficient_portfolio_id,
    )
    assert missing_after == missing_before
    assert insufficient_after == insufficient_before
    assert missing_after.analysis_count == 0
    assert missing_after.simulation_count == 0
    assert "simulation_history" not in missing_after.table_names


def test_live_combined_simulation_uses_one_aligned_period_and_is_read_only(
    live_client: TestClient,
    session_factory: sessionmaker[Session],
    postgres_engine: Engine,
) -> None:
    account = _register_and_login(
        live_client,
        email="combined-live-owner@example.com",
    )
    portfolio_id = _create_portfolio(
        live_client,
        account=account,
        name="Combined Live Portfolio",
        holdings=(
            ("CBAAPL", 0.5),
            ("CBBND", 0.3),
            ("CBGLD", 0.2),
        ),
    )
    _store_market_data(
        session_factory,
        (
            ("CBAAPL", date(2020, 1, 31), 99.0, 900),
            ("CBAAPL", date(2020, 2, 3), 100.0, 1_003),
            ("CBAAPL", date(2020, 2, 4), 70.0, 1_004),
            ("CBAAPL", date(2020, 2, 5), 80.0, 1_005),
            ("CBAAPL", date(2020, 2, 6), 90.0, 1_006),
            ("CBAAPL", date(2020, 2, 7), 100.0, 1_007),
            ("CBAAPL", date(2020, 5, 1), 101.0, 1_501),
            ("CBBND", date(2020, 1, 31), 100.0, None),
            ("CBBND", date(2020, 2, 3), 100.0, None),
            ("CBBND", date(2020, 2, 5), 100.0, None),
            ("CBBND", date(2020, 2, 6), 100.0, None),
            ("CBBND", date(2020, 2, 7), 100.0, None),
            ("CBBND", date(2020, 2, 10), 100.0, None),
            ("CBBND", date(2020, 5, 1), 100.0, None),
            ("CBGLD", date(2020, 1, 31), 49.0, 2_031),
            ("CBGLD", date(2020, 2, 3), 50.0, 2_003),
            ("CBGLD", date(2020, 2, 5), 52.0, 2_005),
            ("CBGLD", date(2020, 2, 6), 51.0, 2_006),
            ("CBGLD", date(2020, 2, 7), 54.0, 2_007),
            ("CBGLD", date(2020, 5, 1), 55.0, 2_501),
        ),
    )
    state_before = _persistence_state(
        session_factory,
        postgres_engine,
        portfolio_id,
    )
    scenario = get_historical_scenario(SCENARIO_ID)
    assert scenario is not None

    request = _combined_request(
        (("CBGLD", 0.0), ("CBBND", 1.0), ("CBAAPL", 0.0))
    )
    response = live_client.post(
        _combined_simulation_path(portfolio_id),
        headers=account.headers,
        json=request,
    )

    assert response.status_code == 200
    assert request == {
        "scenario_id": SCENARIO_ID,
        "modified_allocation": [
            {"symbol": "CBGLD", "weight": 0.0},
            {"symbol": "CBBND", "weight": 1.0},
            {"symbol": "CBAAPL", "weight": 0.0},
        ],
    }
    result = CombinedSimulationResponse.model_validate(response.json())
    assert result.portfolio_id == portfolio_id
    assert result.portfolio_name == "Combined Live Portfolio"
    assert result.scenario.id == scenario.id
    assert result.scenario.display_name == scenario.display_name
    assert result.scenario.description == scenario.description
    assert (
        result.scenario.requested_start_date
        == scenario.requested_start_date
    )
    assert result.scenario.requested_end_date == scenario.requested_end_date
    assert result.metadata.effective_start_date == COMMON_DATES[0]
    assert result.metadata.effective_end_date == COMMON_DATES[-1]
    assert result.metadata.price_observation_count == len(COMMON_DATES)
    assert result.metadata.return_observation_count == len(COMMON_DATES) - 1

    assert [item.symbol for item in result.original.allocation] == [
        "CBAAPL",
        "CBBND",
        "CBGLD",
    ]
    assert [float(item.weight) for item in result.original.allocation] == (
        pytest.approx([0.5, 0.3, 0.2])
    )
    assert [item.symbol for item in result.modified.allocation] == [
        "CBAAPL",
        "CBBND",
        "CBGLD",
    ]
    assert [float(item.weight) for item in result.modified.allocation] == (
        pytest.approx([0.0, 1.0, 0.0])
    )
    assert result.modified.allocation[0].weight == 0
    assert result.modified.allocation[2].weight == 0

    expected_prices = pd.DataFrame(
        [
            [100.0, 100.0, 50.0],
            [80.0, 100.0, 52.0],
            [90.0, 100.0, 51.0],
            [100.0, 100.0, 54.0],
        ],
        index=pd.DatetimeIndex(COMMON_DATES),
        columns=("CBAAPL", "CBBND", "CBGLD"),
        dtype=float,
    )
    expected = simulate_allocation_change(
        expected_prices,
        {"CBAAPL": 0.5, "CBBND": 0.3, "CBGLD": 0.2},
        {"CBAAPL": 0.0, "CBBND": 1.0, "CBGLD": 0.0},
    )
    _assert_allocation_result_matches(result.original, expected.original)
    _assert_allocation_result_matches(result.modified, expected.modified)
    assert result.comparison.normalized_ending_value_delta == pytest.approx(
        expected.normalized_ending_value_delta
    )
    assert result.comparison.cumulative_return_delta == pytest.approx(
        expected.cumulative_return_delta
    )
    assert result.comparison.annualized_volatility_delta == pytest.approx(
        expected.annualized_volatility_delta
    )
    assert expected.sharpe_ratio_delta is None
    assert result.modified.metrics.sharpe_ratio is None
    assert result.comparison.sharpe_ratio_delta is None
    assert result.comparison.maximum_drawdown_delta == pytest.approx(
        expected.maximum_drawdown_delta
    )
    original_dates = [point.date for point in result.original.trajectory]
    modified_dates = [point.date for point in result.modified.trajectory]
    assert original_dates == modified_dates == list(COMMON_DATES)
    assert result.original.trajectory[0].normalized_value == 1.0
    assert result.modified.trajectory[0].normalized_value == 1.0

    state_after = _persistence_state(
        session_factory,
        postgres_engine,
        portfolio_id,
    )
    assert state_after == state_before
    assert state_after.analysis_count == 0
    assert state_after.simulation_count == 0
    assert "simulation_history" not in state_after.table_names
    assert [(row[2], row[4], row[3]) for row in state_after.holdings] == [
        ("CBAAPL", 0, Decimal("0.500000000000000000")),
        ("CBBND", 1, Decimal("0.300000000000000000")),
        ("CBGLD", 2, Decimal("0.200000000000000000")),
    ]
    assert len(
        [row for row in state_after.market_data if row[0] == "CBGLD"]
    ) == 6


def test_live_combined_authentication_and_ownership_are_private(
    live_client: TestClient,
    session_factory: sessionmaker[Session],
    postgres_engine: Engine,
) -> None:
    owner = _register_and_login(
        live_client,
        email="combined-live-private-owner@example.com",
    )
    other_user = _register_and_login(
        live_client,
        email="combined-live-private-other@example.com",
    )
    portfolio_id = _create_portfolio(
        live_client,
        account=owner,
        name="Combined Private Portfolio",
        holdings=(("CBPRIVATE", 1.0),),
    )
    state_before = _persistence_state(
        session_factory,
        postgres_engine,
        portfolio_id,
    )
    request = _combined_request((("CBPRIVATE", 1.0),))

    for headers in (
        {},
        {"Authorization": "Bearer not-a-valid-token"},
        {"X-User-ID": str(owner.id)},
    ):
        unauthenticated = live_client.post(
            _combined_simulation_path(portfolio_id),
            headers=headers,
            json=request,
        )
        assert unauthenticated.status_code == 401
        assert unauthenticated.json() == {
            "detail": "Invalid or missing authentication credentials"
        }

    wrong_owner = live_client.post(
        _combined_simulation_path(portfolio_id),
        headers=other_user.headers,
        json=request,
    )
    assert wrong_owner.status_code == 404
    assert wrong_owner.json() == {"detail": "Portfolio not found"}

    missing = live_client.post(
        _combined_simulation_path(uuid4()),
        headers=other_user.headers,
        json=request,
    )
    assert missing.status_code == wrong_owner.status_code
    assert missing.json() == wrong_owner.json()

    state_after = _persistence_state(
        session_factory,
        postgres_engine,
        portfolio_id,
    )
    assert state_after == state_before


def test_live_combined_unknown_scenario_is_not_found_and_read_only(
    live_client: TestClient,
    session_factory: sessionmaker[Session],
    postgres_engine: Engine,
) -> None:
    account = _register_and_login(
        live_client,
        email="combined-live-unknown-scenario@example.com",
    )
    portfolio_id = _create_portfolio(
        live_client,
        account=account,
        name="Combined Unknown Scenario Portfolio",
        holdings=(("CBUNKNOWN", 1.0),),
    )
    state_before = _persistence_state(
        session_factory,
        postgres_engine,
        portfolio_id,
    )

    response = live_client.post(
        _combined_simulation_path(portfolio_id),
        headers=account.headers,
        json=_combined_request(
            (("CBUNKNOWN", 1.0),),
            scenario_id="not-a-real-scenario",
        ),
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Historical scenario not found"}
    assert "traceback" not in response.text.casefold()
    assert "select " not in response.text.casefold()
    state_after = _persistence_state(
        session_factory,
        postgres_engine,
        portfolio_id,
    )
    assert state_after == state_before


def test_live_combined_data_failures_are_unprocessable_and_read_only(
    live_client: TestClient,
    session_factory: sessionmaker[Session],
    postgres_engine: Engine,
) -> None:
    account = _register_and_login(
        live_client,
        email="combined-live-data-errors@example.com",
    )
    missing_portfolio_id = _create_portfolio(
        live_client,
        account=account,
        name="Combined Missing Data Portfolio",
        holdings=(("CBMISSA", 0.5), ("CBMISSZERO", 0.5)),
    )
    insufficient_portfolio_id = _create_portfolio(
        live_client,
        account=account,
        name="Combined Insufficient Data Portfolio",
        holdings=(("CBSHORTA", 0.5), ("CBSHORTB", 0.5)),
    )
    _store_market_data(
        session_factory,
        (
            ("CBMISSA", date(2020, 2, 3), 100.0, None),
            ("CBMISSA", date(2020, 2, 5), 101.0, None),
            ("CBMISSA", date(2020, 2, 6), 102.0, None),
            ("CBSHORTA", date(2020, 2, 3), 100.0, None),
            ("CBSHORTA", date(2020, 2, 4), 101.0, None),
            ("CBSHORTA", date(2020, 2, 5), 102.0, None),
            ("CBSHORTB", date(2020, 2, 3), 50.0, None),
            ("CBSHORTB", date(2020, 2, 5), 51.0, None),
            ("CBSHORTB", date(2020, 2, 6), 52.0, None),
        ),
    )
    missing_before = _persistence_state(
        session_factory,
        postgres_engine,
        missing_portfolio_id,
    )
    insufficient_before = _persistence_state(
        session_factory,
        postgres_engine,
        insufficient_portfolio_id,
    )

    missing_response = live_client.post(
        _combined_simulation_path(missing_portfolio_id),
        headers=account.headers,
        json=_combined_request(
            (("CBMISSZERO", 0.0), ("CBMISSA", 1.0))
        ),
    )
    assert missing_response.status_code == 422
    assert missing_response.json() == {
        "detail": (
            "market data is unavailable for requested symbols: CBMISSZERO"
        )
    }
    assert "traceback" not in missing_response.text.casefold()
    assert "select " not in missing_response.text.casefold()

    insufficient_response = live_client.post(
        _combined_simulation_path(insufficient_portfolio_id),
        headers=account.headers,
        json=_combined_request(
            (("CBSHORTB", 0.5), ("CBSHORTA", 0.5))
        ),
    )
    assert insufficient_response.status_code == 422
    assert insufficient_response.json() == {
        "detail": (
            "prices must contain at least three rows for historical simulation"
        )
    }
    assert "traceback" not in insufficient_response.text.casefold()
    assert "select " not in insufficient_response.text.casefold()

    missing_after = _persistence_state(
        session_factory,
        postgres_engine,
        missing_portfolio_id,
    )
    insufficient_after = _persistence_state(
        session_factory,
        postgres_engine,
        insufficient_portfolio_id,
    )
    assert missing_after == missing_before
    assert insufficient_after == insufficient_before
    assert missing_after.analysis_count == 0
    assert missing_after.simulation_count == 0
    assert "simulation_history" not in missing_after.table_names
