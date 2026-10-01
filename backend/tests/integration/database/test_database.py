"""Live PostgreSQL verification for Aura's database foundation."""

from collections.abc import Iterator
from datetime import date
from decimal import Decimal
import math
import os
from pathlib import Path
from typing import Any
from unittest.mock import patch
from uuid import UUID, uuid4

from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
import pandas as pd
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
    UserRepository,
)
from backend.app.schemas import (
    PortfolioAnalysisRequest,
    PortfolioAnalysisResponse,
)
from backend.app.services.analysis_service import AnalysisService
from backend.app.services.market_data_service import MarketDataService
import backend.scripts.seed_historical_data as seed_script
import backend.scripts.update_market_data as update_script


BACKEND_ROOT = Path(__file__).resolve().parents[3]
ALEMBIC_CONFIG_PATH = BACKEND_ROOT / "alembic.ini"
APPLICATION_TABLES = {
    "analyses",
    "simulations",
    "holdings",
    "market_data",
    "portfolios",
    "users",
    "watchlist_items",
}
INITIAL_REVISION = "9f4c2a7b1d3e"
LEGACY_MIGRATION_USER_ID = UUID("00000000-0000-0000-0000-000000000001")


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
        command.upgrade(_alembic_config(), INITIAL_REVISION)
        upgraded = True
        with engine.begin() as connection:
            connection.execute(
                sa.text("INSERT INTO users (id) VALUES (:user_id)"),
                {"user_id": LEGACY_MIGRATION_USER_ID},
            )

        command.upgrade(_alembic_config(), "head")
        with engine.connect() as connection:
            migrated_credentials = connection.execute(
                sa.text(
                    "SELECT email, password_hash FROM users WHERE id = :user_id"
                ),
                {"user_id": LEGACY_MIGRATION_USER_ID},
            ).one()
        if migrated_credentials != (None, None):
            raise AssertionError(
                "authentication migration changed legacy User credentials"
            )
        with engine.begin() as connection:
            connection.execute(
                sa.text("DELETE FROM users WHERE id = :user_id"),
                {"user_id": LEGACY_MIGRATION_USER_ID},
            )
        yield engine
    finally:
        try:
            if upgraded:
                try:
                    command.downgrade(
                        _alembic_config(),
                        INITIAL_REVISION,
                    )
                    with engine.connect() as connection:
                        initial_user_columns = set(
                            _column_map(
                                inspect(connection),
                                "users",
                            )
                        )
                    if initial_user_columns != {
                        "id",
                        "created_at",
                        "updated_at",
                    }:
                        raise AssertionError(
                            "authentication downgrade did not restore the "
                            "initial users table"
                        )
                finally:
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
                "TRUNCATE TABLE simulations, analyses, holdings, portfolios, users, "
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


def _canonical_market_data(
    rows: list[tuple[str, str, float, int | None, str]],
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
            "source": pd.Series([row[4] for row in rows], dtype="string"),
        }
    )


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
        assert isinstance(user_columns["email"]["type"], sa.Text)
        assert user_columns["email"]["nullable"] is True
        assert isinstance(user_columns["password_hash"]["type"], sa.Text)
        assert user_columns["password_hash"]["nullable"] is True
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
        user_unique_constraints = {
            constraint["name"]: tuple(constraint["column_names"])
            for constraint in inspector.get_unique_constraints(
                "users",
                schema="public",
            )
        }
        assert user_unique_constraints["uq_users_email"] == ("email",)
        user_check_constraints = {
            constraint["name"]: constraint["sqltext"]
            for constraint in inspector.get_check_constraints(
                "users",
                schema="public",
            )
        }
        assert "ck_users_credentials_complete" in user_check_constraints

        migration_revision = MigrationContext.configure(
            connection
        ).get_current_revision()

    script = ScriptDirectory.from_config(_alembic_config())
    assert migration_revision == script.get_current_head()
    assert len(list(script.walk_revisions())) == 3


def test_user_credentials_and_legacy_users_persist_together(
    session_factory: sessionmaker[Session],
) -> None:
    explicit_id = uuid4()
    with session_factory.begin() as session:
        generated_legacy = User()
        explicit_legacy = User(id=explicit_id)
        credential_user = User(
            email="canonical@example.com",
            password_hash="$argon2id$persisted-test-hash",
        )
        session.add_all(
            [generated_legacy, explicit_legacy, credential_user]
        )
        session.flush()
        generated_legacy_id = generated_legacy.id
        credential_user_id = credential_user.id

    with session_factory() as session:
        generated_loaded = session.get(User, generated_legacy_id)
        explicit_loaded = session.get(User, explicit_id)
        credential_loaded = session.get(User, credential_user_id)

        assert generated_loaded is not None
        assert generated_loaded.email is None
        assert generated_loaded.password_hash is None
        assert generated_loaded.created_at.tzinfo is not None
        assert generated_loaded.updated_at.tzinfo is not None
        assert explicit_loaded is not None
        assert explicit_loaded.email is None
        assert explicit_loaded.password_hash is None
        assert credential_loaded is not None
        assert credential_loaded.email == "canonical@example.com"
        assert credential_loaded.password_hash == (
            "$argon2id$persisted-test-hash"
        )


def test_user_repository_live_round_trip_and_legacy_compatibility(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        legacy_user = User()
        session.add(legacy_user)
        session.flush()

        repository = UserRepository(session)
        credential_user = repository.create(
            email="repository@example.com",
            password_hash="$argon2id$repository-test-hash",
        )
        credential_user_id = credential_user.id
        legacy_user_id = legacy_user.id

        with session_factory() as uncommitted_reader:
            assert uncommitted_reader.get(User, credential_user_id) is None

        session.commit()

    with session_factory() as session:
        repository = UserRepository(session)
        credential_loaded = repository.get_by_email(
            "repository@example.com"
        )
        legacy_loaded = session.get(User, legacy_user_id)

        assert credential_loaded is not None
        assert credential_loaded.id == credential_user_id
        assert credential_loaded.password_hash == (
            "$argon2id$repository-test-hash"
        )
        assert repository.get_by_email("REPOSITORY@EXAMPLE.COM") is None
        assert legacy_loaded is not None
        assert legacy_loaded.email is None
        assert legacy_loaded.password_hash is None


def test_duplicate_non_null_user_email_violates_unique_constraint(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory.begin() as session:
        session.add(
            User(
                email="duplicate@example.com",
                password_hash="$argon2id$first-test-hash",
            )
        )

    with session_factory() as session:
        session.add(
            User(
                email="duplicate@example.com",
                password_hash="$argon2id$second-test-hash",
            )
        )
        with pytest.raises(IntegrityError) as raised:
            session.flush()
        assert raised.value.orig.diag.constraint_name == "uq_users_email"
        session.rollback()


@pytest.mark.parametrize(
    ("email", "password_hash"),
    [
        ("incomplete@example.com", None),
        (None, "$argon2id$orphaned-test-hash"),
    ],
)
def test_incomplete_user_credentials_violate_pair_constraint(
    session_factory: sessionmaker[Session],
    email: str | None,
    password_hash: str | None,
) -> None:
    with session_factory() as session:
        session.add(User(email=email, password_hash=password_hash))
        with pytest.raises(IntegrityError) as raised:
            session.flush()
        assert raised.value.orig.diag.constraint_name == (
            "ck_users_credentials_complete"
        )
        session.rollback()


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


def test_market_data_service_live_round_trip_is_inclusive_and_ordered(
    session_factory: sessionmaker[Session],
) -> None:
    start_date = date(2040, 1, 2)
    end_date = date(2040, 1, 4)
    data = _canonical_market_data(
        [
            ("P7B", "2040-01-02", 200.25, 20, "phase-7-live"),
            ("P7B", "2040-01-04", 201.25, 21, "phase-7-live"),
            ("P7A", "2040-01-02", 1.2345678901235, None, "phase-7-live"),
            ("P7A", "2040-01-04", 101.125, 10, "phase-7-live"),
        ]
    )

    with session_factory() as session:
        assert MarketDataService(session).store(data) == 4
        session.commit()

    with session_factory() as session:
        rows = MarketDataService(session).get_range(
            ["P7B", "P7A"],
            start_date,
            end_date,
        )

    assert [
        (
            row.symbol,
            row.date,
            row.adjusted_close,
            row.volume,
            row.source,
        )
        for row in rows
    ] == [
        (
            "P7A",
            start_date,
            Decimal("1.234567890124"),
            None,
            "phase-7-live",
        ),
        (
            "P7A",
            end_date,
            Decimal("101.125000000000"),
            10,
            "phase-7-live",
        ),
        (
            "P7B",
            start_date,
            Decimal("200.250000000000"),
            20,
            "phase-7-live",
        ),
        (
            "P7B",
            end_date,
            Decimal("201.250000000000"),
            21,
            "phase-7-live",
        ),
    ]


def test_market_data_service_live_repeat_upsert_updates_existing_row(
    session_factory: sessionmaker[Session],
) -> None:
    observation_date = date(2040, 2, 1)
    initial = _canonical_market_data(
        [("P7UPSERT", "2040-02-01", 10.0, 100, "phase-7-initial")]
    )
    updated = _canonical_market_data(
        [("P7UPSERT", "2040-02-01", 11.5, None, "phase-7-updated")]
    )

    with session_factory() as session:
        assert MarketDataService(session).store(initial) == 1
        session.commit()

    with session_factory() as session:
        assert MarketDataService(session).store(updated) == 1
        session.commit()

    with session_factory() as session:
        rows = MarketDataService(session).get_range(
            ["P7UPSERT"],
            observation_date,
            observation_date,
        )
        identity_count = session.scalar(
            select(sa.func.count()).select_from(MarketData).where(
                MarketData.symbol == "P7UPSERT",
                MarketData.date == observation_date,
            )
        )

    assert identity_count == 1
    assert len(rows) == 1
    assert rows[0].adjusted_close == Decimal("11.500000000000")
    assert rows[0].volume is None
    assert rows[0].source == "phase-7-updated"


def test_market_data_service_live_batches_more_than_one_thousand_rows(
    session_factory: sessionmaker[Session],
) -> None:
    row_count = 1_001
    dates = pd.date_range("2041-01-01", periods=row_count)
    data = pd.DataFrame(
        {
            "date": dates,
            "symbol": pd.Series(["P7BATCH"] * row_count, dtype="string"),
            "adjusted_close": pd.Series(
                [float(index + 1) for index in range(row_count)],
                dtype="float64",
            ),
            "volume": pd.Series(range(row_count), dtype="Int64"),
            "source": pd.Series(
                ["phase-7-batch"] * row_count,
                dtype="string",
            ),
        }
    )

    with session_factory() as session:
        assert MarketDataService(session).store(data) == row_count
        session.commit()

    with session_factory() as session:
        rows = MarketDataService(session).get_range(
            ["P7BATCH"],
            dates[0].date(),
            dates[-1].date(),
        )
        persisted_count = session.scalar(
            select(sa.func.count()).select_from(MarketData).where(
                MarketData.symbol == "P7BATCH"
            )
        )

    assert persisted_count == row_count
    assert len(rows) == row_count
    assert rows[0].date == dates[0].date()
    assert rows[-1].date == dates[-1].date()


def test_market_data_service_live_caller_rollback_removes_all_rows(
    session_factory: sessionmaker[Session],
) -> None:
    start_date = date(2044, 1, 2)
    end_date = date(2044, 1, 3)
    data = _canonical_market_data(
        [
            ("P7ROLLBACK", "2044-01-02", 50.0, 500, "phase-7-rollback"),
            ("P7ROLLBACK", "2044-01-03", 51.0, 501, "phase-7-rollback"),
        ]
    )

    with session_factory() as session:
        assert MarketDataService(session).store(data) == 2
        assert len(
            MarketDataService(session).get_range(
                ["P7ROLLBACK"],
                start_date,
                end_date,
            )
        ) == 2
        session.rollback()

    with session_factory() as session:
        assert MarketDataService(session).get_range(
            ["P7ROLLBACK"],
            start_date,
            end_date,
        ) == []


def test_analysis_service_live_real_multi_asset_workflow(
    session_factory: sessionmaker[Session],
) -> None:
    requested_symbols = ["P5BND", "P5AAPL"]
    start_date = date(2060, 1, 2)
    end_date = date(2060, 1, 7)
    data = _canonical_market_data(
        [
            ("P5AAPL", "2060-01-01", 197.0, 1_000, "phase-5-live"),
            ("P5AAPL", "2060-01-02", 200.0, 1_001, "phase-5-live"),
            ("P5AAPL", "2060-01-03", 198.0, 1_002, "phase-5-live"),
            ("P5AAPL", "2060-01-05", 204.0, 1_003, "phase-5-live"),
            ("P5AAPL", "2060-01-06", 202.0, 1_004, "phase-5-live"),
            ("P5AAPL", "2060-01-07", 208.0, 1_005, "phase-5-live"),
            ("P5AAPL", "2060-01-08", 210.0, 1_006, "phase-5-live"),
            ("P5BND", "2060-01-01", 99.0, None, "phase-5-live"),
            ("P5BND", "2060-01-02", 100.0, None, "phase-5-live"),
            ("P5BND", "2060-01-03", 101.0, None, "phase-5-live"),
            ("P5BND", "2060-01-04", 150.0, None, "phase-5-live"),
            ("P5BND", "2060-01-05", 99.0, None, "phase-5-live"),
            ("P5BND", "2060-01-06", 103.0, None, "phase-5-live"),
            ("P5BND", "2060-01-07", 102.0, None, "phase-5-live"),
            ("P5BND", "2060-01-08", 104.0, None, "phase-5-live"),
        ]
    )
    request = PortfolioAnalysisRequest.model_validate(
        {
            "portfolio_name": "Live Integration Portfolio",
            "holdings": [
                {"symbol": "P5BND", "weight": 0.45},
                {"symbol": "P5AAPL", "weight": 0.55},
            ],
            "start_date": start_date,
            "end_date": end_date,
        }
    )

    with session_factory() as session:
        assert MarketDataService(session).store(data) == 15
        assert session.in_transaction()

        response = AnalysisService(session).analyze(request)

        assert session.in_transaction()
        assert isinstance(response, PortfolioAnalysisResponse)
        assert response.portfolio_name == "Live Integration Portfolio"
        assert response.start_date == start_date
        assert response.end_date == end_date
        assert response.metadata.analysis_start == start_date
        assert response.metadata.analysis_end == end_date
        assert response.metadata.price_observation_count == 5
        assert response.metadata.return_observation_count == 4
        assert response.metadata.asset_count == 2
        assert [metric.symbol for metric in response.asset_metrics] == (
            requested_symbols
        )
        assert response.correlation_matrix.symbols == requested_symbols
        assert [
            (pair.asset_a, pair.asset_b)
            for pair in response.correlation_pairs
        ] == [("P5BND", "P5AAPL")]
        assert len(response.portfolio_returns) == 4
        assert all(
            math.isfinite(value)
            for value in (
                response.portfolio_metrics.cumulative_return,
                response.portfolio_metrics.annualized_return,
                response.portfolio_metrics.annualized_volatility,
                response.portfolio_metrics.sharpe_ratio,
            )
        )
        assert PortfolioAnalysisResponse.model_validate(
            response.model_dump()
        ) == response
        assert session.scalar(
            select(sa.func.count()).select_from(Analysis)
        ) == 0

        with session_factory() as uncommitted_reader:
            assert uncommitted_reader.scalar(
                select(sa.func.count())
                .select_from(MarketData)
                .where(MarketData.symbol.in_(requested_symbols))
            ) == 0
            assert uncommitted_reader.scalar(
                select(sa.func.count()).select_from(Analysis)
            ) == 0

        session.rollback()
        assert not session.in_transaction()

    with session_factory() as rolled_back_reader:
        assert rolled_back_reader.scalar(
            select(sa.func.count())
            .select_from(MarketData)
            .where(MarketData.symbol.in_(requested_symbols))
        ) == 0


def test_analysis_service_live_missing_symbols_preserve_request_order(
    session_factory: sessionmaker[Session],
) -> None:
    data = _canonical_market_data(
        [
            ("P5PRESENT", "2061-01-02", 100.0, 100, "phase-5-live"),
            ("P5PRESENT", "2061-01-03", 102.0, 101, "phase-5-live"),
            ("P5PRESENT", "2061-01-04", 101.0, 102, "phase-5-live"),
        ]
    )
    request = PortfolioAnalysisRequest.model_validate(
        {
            "portfolio_name": "Missing Symbols",
            "holdings": [
                {"symbol": "P5MISSB", "weight": 0.2},
                {"symbol": "P5PRESENT", "weight": 0.5},
                {"symbol": "P5MISSA", "weight": 0.3},
            ],
            "start_date": "2061-01-02",
            "end_date": "2061-01-04",
        }
    )

    with session_factory() as session:
        assert MarketDataService(session).store(data) == 3

        with pytest.raises(ValueError) as raised:
            AnalysisService(session).analyze(request)

        assert str(raised.value) == (
            "market data is unavailable for requested symbols: "
            "P5MISSB, P5MISSA"
        )
        assert session.in_transaction()
        assert session.scalar(
            select(sa.func.count()).select_from(Analysis)
        ) == 0

        with session_factory() as uncommitted_reader:
            assert uncommitted_reader.scalar(
                select(sa.func.count())
                .select_from(MarketData)
                .where(MarketData.symbol == "P5PRESENT")
            ) == 0

        session.rollback()


def test_seed_workflow_live_repeat_upsert_and_existing_row_update(
    tmp_path: Path,
    postgres_engine: Engine,
    session_factory: sessionmaker[Session],
) -> None:
    input_path = tmp_path / "phase_8_processed.csv"
    input_data = pd.DataFrame(
        {
            "date": ["2050-01-02", "2050-01-03"],
            "symbol": ["P8SEEDA", "P8SEEDB"],
            "adjusted_close": [123.125, 200.5],
            "volume": [None, 2_000],
            "source": ["phase-8-seed", "phase-8-seed"],
        }
    )
    input_data.to_csv(input_path, index=False)

    with patch.object(
        seed_script,
        "create_database_engine",
        return_value=postgres_engine,
    ) as create_engine:
        assert seed_script.seed_historical_data(input_path) == 2
        assert seed_script.seed_historical_data(input_path) == 2

        with session_factory() as session:
            repeated_rows = list(
                session.scalars(
                    select(MarketData)
                    .where(MarketData.symbol.in_(["P8SEEDA", "P8SEEDB"]))
                    .order_by(MarketData.symbol, MarketData.date)
                ).all()
            )

        assert len(repeated_rows) == 2
        assert [
            (
                row.symbol,
                row.date,
                row.adjusted_close,
                row.volume,
                row.source,
            )
            for row in repeated_rows
        ] == [
            (
                "P8SEEDA",
                date(2050, 1, 2),
                Decimal("123.125000000000"),
                None,
                "phase-8-seed",
            ),
            (
                "P8SEEDB",
                date(2050, 1, 3),
                Decimal("200.500000000000"),
                2_000,
                "phase-8-seed",
            ),
        ]

        input_data.loc[0, "adjusted_close"] = 124.75
        input_data.loc[0, "volume"] = 777
        input_data.loc[0, "source"] = "phase-8-seed-updated"
        input_data.to_csv(input_path, index=False)

        assert seed_script.seed_historical_data(input_path) == 2

    assert create_engine.call_count == 3

    with session_factory() as session:
        updated_rows = list(
            session.scalars(
                select(MarketData)
                .where(MarketData.symbol.in_(["P8SEEDA", "P8SEEDB"]))
                .order_by(MarketData.symbol, MarketData.date)
            ).all()
        )

    assert len(updated_rows) == 2
    assert updated_rows[0].adjusted_close == Decimal("124.750000000000")
    assert updated_rows[0].volume == 777
    assert updated_rows[0].source == "phase-8-seed-updated"


def test_updater_persist_database_workflow_commits_live_canonical_frame(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    postgres_engine: Engine,
    session_factory: sessionmaker[Session],
) -> None:
    data = _canonical_market_data(
        [
            ("P8UPDA", "2051-01-02", 300.125, None, "phase-8-update"),
            (
                "P8UPDB",
                "2051-01-03",
                400.123456789012,
                4_000,
                "phase-8-update",
            ),
        ]
    )
    result = update_script.MarketDataUpdateResult(
        raw_path=tmp_path / "unused_raw.csv",
        processed_path=tmp_path / "unused_processed.csv",
        row_count=2,
        symbols=("P8UPDA", "P8UPDB"),
        failed_symbols=(),
        requested_start_date="2051-01-02",
        requested_end_date="2051-01-03",
        actual_start_date="2051-01-02",
        actual_end_date="2051-01-03",
    )

    with (
        patch.object(
            update_script,
            "_update_market_data_with_frame",
            return_value=(result, data),
        ) as update_handoff,
        patch.object(
            update_script,
            "create_database_engine",
            return_value=postgres_engine,
        ),
    ):
        update_script.main(
            [
                "--symbols",
                "P8UPDA",
                "P8UPDB",
                "--start-date",
                "2051-01-02",
                "--end-date",
                "2051-01-03",
                "--persist-database",
            ]
        )

    update_handoff.assert_called_once_with(
        symbols=["P8UPDA", "P8UPDB"],
        start_date="2051-01-02",
        end_date="2051-01-03",
    )
    assert "Database rows stored: 2" in capsys.readouterr().out
    assert not result.raw_path.exists()
    assert not result.processed_path.exists()

    with session_factory() as session:
        rows = list(
            session.scalars(
                select(MarketData)
                .where(MarketData.symbol.in_(["P8UPDA", "P8UPDB"]))
                .order_by(MarketData.symbol, MarketData.date)
            ).all()
        )

    assert [
        (
            row.symbol,
            row.date,
            row.adjusted_close,
            row.volume,
            row.source,
        )
        for row in rows
    ] == [
        (
            "P8UPDA",
            date(2051, 1, 2),
            Decimal("300.125000000000"),
            None,
            "phase-8-update",
        ),
        (
            "P8UPDB",
            date(2051, 1, 3),
            Decimal("400.123456789012"),
            4_000,
            "phase-8-update",
        ),
    ]


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
