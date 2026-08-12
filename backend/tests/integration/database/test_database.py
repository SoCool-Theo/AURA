"""Live PostgreSQL verification for Aura's database foundation."""

from collections.abc import Iterator
from datetime import date
from decimal import Decimal
import os
from pathlib import Path
from typing import Any
from uuid import UUID

from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
import pytest
import sqlalchemy as sa
from sqlalchemy import inspect, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from backend.app.core.config import settings
from backend.app.database.connection import create_database_engine
from backend.app.database.models import (
    Analysis,
    Holding,
    MarketData,
    Portfolio,
    User,
)
from backend.app.database.repositories import (
    AnalysisRepository,
    MarketDataRepository,
    PortfolioRepository,
)


BACKEND_ROOT = Path(__file__).resolve().parents[3]
ALEMBIC_CONFIG_PATH = BACKEND_ROOT / "alembic.ini"
APPLICATION_TABLES = {
    "analyses",
    "holdings",
    "market_data",
    "portfolios",
    "users",
}


def _test_database_url() -> str:
    raw_url = os.getenv("AURA_TEST_DATABASE_URL")
    if not raw_url:
        pytest.skip("AURA_TEST_DATABASE_URL is not configured")

    url = make_url(raw_url)
    database_name = url.database or ""
    if url.drivername != "postgresql+psycopg":
        pytest.fail(
            "AURA_TEST_DATABASE_URL must use postgresql+psycopg",
            pytrace=False,
        )
    if not (
        database_name == "aura_test"
        or database_name.startswith("aura_test_")
    ):
        pytest.fail(
            "AURA_TEST_DATABASE_URL must target aura_test or aura_test_*",
            pytrace=False,
        )
    return raw_url


def _alembic_config() -> Config:
    return Config(ALEMBIC_CONFIG_PATH)


@pytest.fixture(scope="session")
def postgres_engine() -> Iterator[Engine]:
    raw_url = _test_database_url()
    engine = create_database_engine(raw_url)
    original_database_url = settings.database_url
    upgraded = False
    initial_tables: set[str] = set()

    try:
        with engine.connect() as connection:
            inspector = inspect(connection)
            initial_tables = set(inspector.get_table_names(schema="public"))
            unexpected_tables = initial_tables - {"alembic_version"}
            if unexpected_tables:
                pytest.fail(
                    "isolated test database contains unexpected public "
                    f"tables: {sorted(unexpected_tables)}",
                    pytrace=False,
                )
            if "alembic_version" in initial_tables:
                revision_count = connection.scalar(
                    sa.text("SELECT count(*) FROM alembic_version")
                )
                if revision_count != 0:
                    pytest.fail(
                        "isolated test database is not at Alembic base",
                        pytrace=False,
                    )

        settings.database_url = raw_url  # type: ignore[assignment]
        command.upgrade(_alembic_config(), "head")
        upgraded = True
        yield engine
    finally:
        try:
            if upgraded:
                command.downgrade(_alembic_config(), "base")
                with engine.connect() as connection:
                    final_tables = set(
                        inspect(connection).get_table_names(schema="public")
                    )
                remaining_application_tables = final_tables & APPLICATION_TABLES
                if remaining_application_tables:
                    raise AssertionError(
                        "Alembic downgrade left application tables: "
                        f"{sorted(remaining_application_tables)}"
                    )
                if not initial_tables.issubset(final_tables):
                    raise AssertionError(
                        "Alembic downgrade removed a pre-existing table"
                    )
        finally:
            settings.database_url = original_database_url
            engine.dispose()


@pytest.fixture
def session_factory(
    postgres_engine: Engine,
) -> sessionmaker[Session]:
    return sessionmaker(
        bind=postgres_engine,
        class_=Session,
        autoflush=False,
        expire_on_commit=False,
    )


@pytest.fixture(autouse=True)
def clean_application_rows(postgres_engine: Engine) -> Iterator[None]:
    yield
    with postgres_engine.begin() as connection:
        connection.execute(
            sa.text(
                "TRUNCATE TABLE analyses, holdings, portfolios, users, "
                "market_data CASCADE"
            )
        )


def _create_user(session: Session) -> User:
    user = User()
    session.add(user)
    session.flush()
    return user


def _column_map(inspector: sa.Inspector, table: str) -> dict[str, Any]:
    return {
        column["name"]: column
        for column in inspector.get_columns(table, schema="public")
    }


def test_live_migration_schema_types_and_revision(
    postgres_engine: Engine,
) -> None:
    with postgres_engine.connect() as connection:
        inspector = inspect(connection)
        assert APPLICATION_TABLES.issubset(
            inspector.get_table_names(schema="public")
        )

        holding_columns = _column_map(inspector, "holdings")
        market_columns = _column_map(inspector, "market_data")
        analysis_columns = _column_map(inspector, "analyses")
        user_columns = _column_map(inspector, "users")

        assert isinstance(user_columns["id"]["type"], postgresql.UUID)
        assert isinstance(holding_columns["weight"]["type"], sa.Numeric)
        assert holding_columns["weight"]["type"].precision == 20
        assert holding_columns["weight"]["type"].scale == 18
        assert isinstance(market_columns["adjusted_close"]["type"], sa.Numeric)
        assert market_columns["adjusted_close"]["type"].precision == 28
        assert market_columns["adjusted_close"]["type"].scale == 12
        assert isinstance(market_columns["volume"]["type"], sa.BigInteger)
        assert market_columns["volume"]["nullable"] is True
        assert isinstance(
            analysis_columns["result_snapshot"]["type"],
            postgresql.JSONB,
        )
        assert isinstance(user_columns["created_at"]["type"], sa.DateTime)
        assert user_columns["created_at"]["type"].timezone is True

        migration_revision = MigrationContext.configure(
            connection
        ).get_current_revision()

    script = ScriptDirectory.from_config(_alembic_config())
    assert migration_revision == script.get_current_head()
    assert len(list(script.walk_revisions())) == 1


def test_portfolio_repository_commit_round_trip_and_caller_rollback(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        user = _create_user(session)
        repository = PortfolioRepository(session)
        portfolio = repository.create(user_id=user.id, name="Core")
        repository.replace_holdings(
            portfolio.id,
            [
                ("AAPL", Decimal("0.600000000000000000")),
                ("MSFT", Decimal("0.400000000000000000")),
            ],
        )
        portfolio_id = portfolio.id

        with session_factory() as uncommitted_reader:
            assert uncommitted_reader.get(Portfolio, portfolio_id) is None

        session.commit()

    with session_factory() as session:
        loaded = PortfolioRepository(session).get_with_holdings(portfolio_id)
        assert loaded is not None
        assert isinstance(loaded.id, UUID)
        assert [(item.symbol, item.position) for item in loaded.holdings] == [
            ("AAPL", 0),
            ("MSFT", 1),
        ]
        assert [item.weight for item in loaded.holdings] == [
            Decimal("0.600000000000000000"),
            Decimal("0.400000000000000000"),
        ]

    with session_factory() as session:
        user = _create_user(session)
        rolled_back = PortfolioRepository(session).create(
            user_id=user.id,
            name="Rollback",
        )
        rolled_back_id = rolled_back.id
        session.rollback()

    with session_factory() as session:
        assert session.get(Portfolio, rolled_back_id) is None


def test_market_data_postgresql_upsert_and_range_round_trip(
    session_factory: sessionmaker[Session],
) -> None:
    first_date = date(2026, 1, 2)
    last_date = date(2026, 1, 3)
    with session_factory() as session:
        repository = MarketDataRepository(session)
        repository.upsert_many(
            [
                {
                    "symbol": "AAPL",
                    "date": first_date,
                    "adjusted_close": Decimal("101.123456789012"),
                    "volume": 1_000,
                    "source": "provider-a",
                },
                {
                    "symbol": "MSFT",
                    "date": last_date,
                    "adjusted_close": Decimal("400.000000000001"),
                    "volume": 2_000,
                    "source": "provider-a",
                },
            ]
        )
        session.commit()

    with session_factory() as session:
        MarketDataRepository(session).upsert_many(
            [
                {
                    "symbol": "AAPL",
                    "date": first_date,
                    "adjusted_close": Decimal("102.987654321098"),
                    "volume": None,
                    "source": "provider-b",
                }
            ]
        )
        session.commit()

    with session_factory() as session:
        repository = MarketDataRepository(session)
        rows = repository.get_range(
            ["MSFT", "AAPL"],
            first_date,
            last_date,
        )
        assert [(row.symbol, row.date) for row in rows] == [
            ("AAPL", first_date),
            ("MSFT", last_date),
        ]
        assert rows[0].adjusted_close == Decimal("102.987654321098")
        assert rows[0].volume is None
        assert rows[0].source == "provider-b"
        assert session.scalar(
            select(sa.func.count()).select_from(MarketData).where(
                MarketData.symbol == "AAPL",
                MarketData.date == first_date,
            )
        ) == 1


def test_analysis_jsonb_round_trip_and_database_cascades(
    session_factory: sessionmaker[Session],
) -> None:
    snapshot = {
        "maximum_drawdown": -0.25,
        "sharpe_ratio": None,
        "nested": {"classification": "high"},
        "ordered_assets": ["AAPL", "MSFT"],
    }
    with session_factory() as session:
        user = _create_user(session)
        portfolio = PortfolioRepository(session).create(
            user_id=user.id,
            name="Cascade",
        )
        PortfolioRepository(session).replace_holdings(
            portfolio.id,
            [("AAPL", Decimal("1.000000000000000000"))],
        )
        analysis = AnalysisRepository(session).save_snapshot(
            portfolio_id=portfolio.id,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            schema_version="1.0",
            result_snapshot=snapshot,
        )
        portfolio_id = portfolio.id
        analysis_id = analysis.id
        session.commit()

    with session_factory() as session:
        loaded = AnalysisRepository(session).get_by_id(analysis_id)
        assert loaded is not None
        assert loaded.result_snapshot == snapshot

    with session_factory.begin() as session:
        session.execute(
            sa.delete(Portfolio).where(Portfolio.id == portfolio_id)
        )

    with session_factory() as session:
        assert session.scalar(
            select(sa.func.count()).select_from(Holding).where(
                Holding.portfolio_id == portfolio_id
            )
        ) == 0
        assert session.scalar(
            select(sa.func.count()).select_from(Analysis).where(
                Analysis.portfolio_id == portfolio_id
            )
        ) == 0

        cascade_user = _create_user(session)
        cascade_portfolio = PortfolioRepository(session).create(
            user_id=cascade_user.id,
            name="User cascade",
        )
        cascade_user_id = cascade_user.id
        cascade_portfolio_id = cascade_portfolio.id
        session.commit()

    with session_factory.begin() as session:
        session.execute(sa.delete(User).where(User.id == cascade_user_id))

    with session_factory() as session:
        assert session.get(Portfolio, cascade_portfolio_id) is None


def test_representative_postgresql_constraints(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        user = _create_user(session)
        portfolio = PortfolioRepository(session).create(
            user_id=user.id,
            name="Constraints",
        )
        portfolio_id = portfolio.id
        session.commit()

    with session_factory() as session:
        session.add(
            Holding(
                portfolio_id=portfolio_id,
                symbol="INVALID",
                weight=Decimal("1.100000000000000000"),
                position=0,
            )
        )
        with pytest.raises(IntegrityError) as raised:
            session.flush()
        assert raised.value.orig.diag.constraint_name == (
            "ck_holdings_weight_range"
        )
        session.rollback()

    with session_factory() as session:
        session.add_all(
            [
                Holding(
                    portfolio_id=portfolio_id,
                    symbol="AAPL",
                    weight=Decimal("0.500000000000000000"),
                    position=0,
                ),
                Holding(
                    portfolio_id=portfolio_id,
                    symbol="AAPL",
                    weight=Decimal("0.500000000000000000"),
                    position=1,
                ),
            ]
        )
        with pytest.raises(IntegrityError) as raised:
            session.flush()
        assert raised.value.orig.diag.constraint_name == (
            "uq_holdings_portfolio_symbol"
        )
        session.rollback()

    with session_factory() as session:
        session.add(
            Analysis(
                portfolio_id=portfolio_id,
                start_date=date(2026, 2, 1),
                end_date=date(2026, 1, 1),
                schema_version="1.0",
                result_snapshot={},
            )
        )
        with pytest.raises(IntegrityError) as raised:
            session.flush()
        assert raised.value.orig.diag.constraint_name == (
            "ck_analyses_date_order"
        )
        session.rollback()

    with session_factory() as session:
        session.add_all(
            [
                MarketData(
                    symbol="AAPL",
                    date=date(2026, 1, 2),
                    adjusted_close=Decimal("100.000000000000"),
                    volume=1,
                    source="direct",
                ),
                MarketData(
                    symbol="AAPL",
                    date=date(2026, 1, 2),
                    adjusted_close=Decimal("101.000000000000"),
                    volume=2,
                    source="direct",
                ),
            ]
        )
        with pytest.raises(IntegrityError) as raised:
            session.flush()
        assert raised.value.orig.diag.constraint_name == "market_data_pkey"
        session.rollback()
