"""Live verification of catalogue scenarios against preserved market data."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
import os
from pathlib import Path
import sys
from uuid import UUID, uuid4


BACKEND_ROOT = Path(__file__).resolve().parents[3]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from fastapi.testclient import TestClient
import pandas as pd
import pytest
from pydantic import SecretStr
from sqlalchemy import Engine, delete, func, inspect, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.api.dependencies import get_database_session
from app.core.config import settings as app_settings
from app.database.connection import session_scope
from app.database.models import MarketData, Simulation, User
from app.database.repositories import PortfolioRepository
from app.main import app
from app.scenarios.definitions import get_historical_scenario
from app.scenarios.simulator import (
    HistoricalSimulationResult,
    simulate_historical_scenario,
)
from app.schemas.simulation import HistoricalScenarioSimulationResponse
from app.schemas.simulation_history import (
    SimulationHistoryDetailResponse,
    SimulationHistoryListResponse,
)
from app.services.analysis_service import _build_price_frame
from app.services.market_data_service import MarketDataService
from app.services.simulation_history_mapper import (
    HISTORICAL_SCENARIO_SIMULATION_RESPONSE_SCHEMA_VERSION,
)
from backend.app.database.connection import create_database_engine


ALEMBIC_CONFIG_PATH = BACKEND_ROOT / "alembic.ini"
APPLICATION_TABLES = {
    "analyses",
    "holdings",
    "market_data",
    "portfolios",
    "simulations",
    "users",
}
JWT_SECRET = "phase-5-catalog-live-postgresql-secret"
PASSWORD = "Phase5-catalog-live-password!"
SUCCESS_HOLDINGS = (("AAPL", 0.6), ("MSFT", 0.4))


@dataclass(frozen=True)
class AuthenticatedAccount:
    id: UUID
    headers: dict[str, str]


def _test_database_url() -> str:
    raw_url = os.getenv("AURA_TEST_DATABASE_URL")
    if not raw_url:
        pytest.fail(
            "AURA_TEST_DATABASE_URL is required for live PostgreSQL tests",
            pytrace=False,
        )

    url = make_url(raw_url)
    database_name = url.database or ""
    if url.drivername != "postgresql+psycopg":
        pytest.fail(
            "AURA_TEST_DATABASE_URL must use postgresql+psycopg",
            pytrace=False,
        )
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


def _market_data_fingerprint(engine: Engine) -> tuple[object, ...]:
    with engine.connect() as connection:
        row = connection.execute(
            text(
                """
                SELECT
                    COUNT(*),
                    MIN(date),
                    MAX(date),
                    MD5(
                        STRING_AGG(
                            MD5(
                                CONCAT_WS(
                                    '|',
                                    symbol,
                                    date::text,
                                    adjusted_close::text,
                                    COALESCE(volume::text, '<null>'),
                                    source
                                )
                            ),
                            '' ORDER BY symbol, date
                        )
                    )
                FROM market_data
                """
            )
        ).one()
    return tuple(row)


@pytest.fixture(scope="module")
def test_user_ids() -> set[UUID]:
    return set()


@pytest.fixture(scope="module")
def postgres_engine(test_user_ids: set[UUID]) -> Iterator[Engine]:
    raw_url = _test_database_url()
    expected_database = make_url(raw_url).database
    engine = create_database_engine(raw_url)
    initial_fingerprint: tuple[object, ...] | None = None

    try:
        with engine.connect() as connection:
            actual_database = connection.scalar(text("SELECT current_database()"))
            actual_schema = connection.scalar(text("SELECT current_schema()"))
            table_names = set(
                inspect(connection).get_table_names(schema="public")
            )
            current_revision = MigrationContext.configure(
                connection
            ).get_current_revision()

        assert actual_database == expected_database
        assert actual_schema == "public"
        expected_tables = APPLICATION_TABLES | {"alembic_version"}
        if table_names != expected_tables:
            pytest.fail(
                "Guarded test database must contain the complete current "
                "application schema before preserved-market-data verification; "
                f"found tables: {sorted(table_names)}",
                pytrace=False,
            )
        expected_head = ScriptDirectory.from_config(
            _alembic_config()
        ).get_current_head()
        assert current_revision == expected_head

        initial_fingerprint = _market_data_fingerprint(engine)
        assert int(initial_fingerprint[0]) > 0
        assert initial_fingerprint[1] is not None
        assert initial_fingerprint[2] is not None
        assert initial_fingerprint[3] is not None
        yield engine
    finally:
        try:
            if test_user_ids:
                with engine.begin() as connection:
                    connection.execute(
                        delete(User).where(User.id.in_(test_user_ids))
                    )
                test_user_ids.clear()
            if initial_fingerprint is not None:
                assert _market_data_fingerprint(engine) == initial_fingerprint
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
def cleanup_test_users(
    session_factory: sessionmaker[Session],
    test_user_ids: set[UUID],
) -> Iterator[None]:
    existing_ids = set(test_user_ids)
    try:
        yield
    finally:
        created_ids = test_user_ids - existing_ids
        if created_ids:
            with session_factory.begin() as session:
                session.execute(delete(User).where(User.id.in_(created_ids)))
            test_user_ids.difference_update(created_ids)


def _register_and_login(
    client: TestClient,
    test_user_ids: set[UUID],
) -> AuthenticatedAccount:
    email = f"phase5-catalog-{uuid4()}@example.com"
    registration = client.post(
        "/api/auth/register",
        json={"email": email, "password": PASSWORD},
    )
    assert registration.status_code == 201
    user_id = UUID(registration.json()["id"])
    test_user_ids.add(user_id)

    login = client.post(
        "/api/auth/login",
        json={"email": email, "password": PASSWORD},
    )
    assert login.status_code == 200
    return AuthenticatedAccount(
        id=user_id,
        headers={
            "Authorization": f"Bearer {login.json()['access_token']}"
        },
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
    return portfolio_id


def _aligned_prices(
    session_factory: sessionmaker[Session],
    *,
    symbols: Sequence[str],
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    with session_factory() as session:
        records = MarketDataService(session).get_range(
            symbols,
            start_date,
            end_date,
        )
    prices = _build_price_frame(records, symbols)
    assert list(prices.columns) == list(symbols)
    assert len(prices.index) >= 3
    assert not prices.isna().any().any()
    return prices


def _simulation_path(portfolio_id: UUID) -> str:
    return (
        f"/api/portfolios/{portfolio_id}"
        "/simulations/historical-scenarios"
    )


def _history_path(portfolio_id: UUID) -> str:
    return f"/api/portfolios/{portfolio_id}/simulations"


def _history_detail_path(portfolio_id: UUID, simulation_id: UUID) -> str:
    return f"{_history_path(portfolio_id)}/{simulation_id}"


def _assert_result_matches_expected(
    actual: HistoricalScenarioSimulationResponse,
    expected: HistoricalSimulationResult,
) -> None:
    assert actual.metrics.normalized_starting_value == 1.0
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


@pytest.mark.parametrize(
    (
        "scenario_id",
        "requested_start",
        "requested_end",
        "expect_later_effective_start",
    ),
    [
        (
            "dot-com-bust-2000-2002",
            date(2000, 3, 10),
            date(2002, 10, 9),
            False,
        ),
        (
            "global-financial-crisis-2007-2009",
            date(2007, 10, 9),
            date(2009, 3, 9),
            False,
        ),
        (
            "covid-19-shock-2020",
            date(2020, 2, 1),
            date(2020, 4, 30),
            True,
        ),
    ],
)
def test_live_catalogue_scenario_uses_preserved_prices_and_round_trips_history(
    live_client: TestClient,
    session_factory: sessionmaker[Session],
    postgres_engine: Engine,
    test_user_ids: set[UUID],
    scenario_id: str,
    requested_start: date,
    requested_end: date,
    expect_later_effective_start: bool,
) -> None:
    scenario = get_historical_scenario(scenario_id)
    assert scenario is not None
    assert scenario.requested_start_date == requested_start
    assert scenario.requested_end_date == requested_end

    symbols = [symbol for symbol, _ in SUCCESS_HOLDINGS]
    weights = dict(SUCCESS_HOLDINGS)
    prices = _aligned_prices(
        session_factory,
        symbols=symbols,
        start_date=requested_start,
        end_date=requested_end,
    )
    market_data_before = _market_data_fingerprint(postgres_engine)
    account = _register_and_login(live_client, test_user_ids)
    portfolio_id = _create_portfolio(
        live_client,
        account=account,
        name=f"Phase 5 {scenario.display_name}",
        holdings=SUCCESS_HOLDINGS,
    )

    response = live_client.post(
        _simulation_path(portfolio_id),
        headers=account.headers,
        json={"scenario_id": scenario_id},
    )

    assert response.status_code == 200
    result = HistoricalScenarioSimulationResponse.model_validate(response.json())
    assert result.portfolio_id == portfolio_id
    assert result.scenario.id == scenario_id
    assert result.scenario.requested_start_date == requested_start
    assert result.scenario.requested_end_date == requested_end
    assert result.metadata.effective_start_date == prices.index[0].date()
    assert result.metadata.effective_end_date == prices.index[-1].date()
    assert requested_start <= result.metadata.effective_start_date
    assert result.metadata.effective_end_date <= requested_end
    assert result.metadata.price_observation_count == len(prices.index)
    assert result.metadata.price_observation_count >= 3
    assert result.metadata.return_observation_count == len(prices.index) - 1
    assert result.trajectory[0].normalized_value == 1.0
    if expect_later_effective_start:
        assert result.metadata.effective_start_date > requested_start

    expected = simulate_historical_scenario(prices, weights)
    _assert_result_matches_expected(result, expected)

    with session_factory() as fresh_session:
        persisted_portfolio = PortfolioRepository(
            fresh_session
        ).get_with_holdings(portfolio_id)
        records = fresh_session.scalars(
            select(Simulation).where(Simulation.portfolio_id == portfolio_id)
        ).all()
    assert persisted_portfolio is not None
    assert [
        (holding.symbol, holding.position, holding.weight)
        for holding in persisted_portfolio.holdings
    ] == [
        ("AAPL", 0, Decimal("0.600000000000000000")),
        ("MSFT", 1, Decimal("0.400000000000000000")),
    ]
    assert len(records) == 1
    record = records[0]
    assert record.scenario_id == scenario_id
    assert record.requested_start_date == requested_start
    assert record.requested_end_date == requested_end
    assert record.schema_version == (
        HISTORICAL_SCENARIO_SIMULATION_RESPONSE_SCHEMA_VERSION
    )
    assert record.result_snapshot == result.model_dump(mode="json")

    history_response = live_client.get(
        _history_path(portfolio_id),
        headers=account.headers,
    )
    assert history_response.status_code == 200
    history = SimulationHistoryListResponse.model_validate(
        history_response.json()
    )
    assert [item.id for item in history.simulations] == [record.id]

    detail_response = live_client.get(
        _history_detail_path(portfolio_id, record.id),
        headers=account.headers,
    )
    assert detail_response.status_code == 200
    detail = SimulationHistoryDetailResponse.model_validate(
        detail_response.json()
    )
    assert detail.result == result
    assert _market_data_fingerprint(postgres_engine) == market_data_before


def test_live_old_scenario_late_asset_returns_422_without_history(
    live_client: TestClient,
    session_factory: sessionmaker[Session],
    postgres_engine: Engine,
    test_user_ids: set[UUID],
) -> None:
    scenario_id = "global-financial-crisis-2007-2009"
    requested_start = date(2007, 10, 9)
    requested_end = date(2009, 3, 9)
    _aligned_prices(
        session_factory,
        symbols=["AAPL"],
        start_date=requested_start,
        end_date=requested_end,
    )
    with session_factory() as session:
        eth_first_date = session.scalar(
            select(func.min(MarketData.date)).where(
                MarketData.symbol == "ETH-USD"
            )
        )
        eth_old_row_count = int(
            session.scalar(
                select(func.count())
                .select_from(MarketData)
                .where(
                    MarketData.symbol == "ETH-USD",
                    MarketData.date >= requested_start,
                    MarketData.date <= requested_end,
                )
            )
            or 0
        )
    assert eth_first_date is not None
    assert eth_first_date > requested_end
    assert eth_old_row_count == 0

    market_data_before = _market_data_fingerprint(postgres_engine)
    account = _register_and_login(live_client, test_user_ids)
    portfolio_id = _create_portfolio(
        live_client,
        account=account,
        name="Phase 5 Expected Coverage Failure",
        holdings=(("AAPL", 0.5), ("ETH-USD", 0.5)),
    )

    response = live_client.post(
        _simulation_path(portfolio_id),
        headers=account.headers,
        json={"scenario_id": scenario_id},
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": "market data is unavailable for requested symbols: ETH-USD"
    }
    with session_factory() as fresh_session:
        simulation_count = int(
            fresh_session.scalar(
                select(func.count())
                .select_from(Simulation)
                .where(Simulation.portfolio_id == portfolio_id)
            )
            or 0
        )
        persisted_portfolio = PortfolioRepository(
            fresh_session
        ).get_with_holdings(portfolio_id)
    assert simulation_count == 0
    assert persisted_portfolio is not None
    assert [holding.symbol for holding in persisted_portfolio.holdings] == [
        "AAPL",
        "ETH-USD",
    ]

    history_response = live_client.get(
        _history_path(portfolio_id),
        headers=account.headers,
    )
    assert history_response.status_code == 200
    history = SimulationHistoryListResponse.model_validate(
        history_response.json()
    )
    assert history.simulations == []
    assert _market_data_fingerprint(postgres_engine) == market_data_before
