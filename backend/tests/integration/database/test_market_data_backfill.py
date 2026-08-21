"""Live PostgreSQL verification for historical backfill orchestration."""

from collections.abc import Iterator
from datetime import date
from decimal import Decimal
import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
import pandas as pd
import pytest
import sqlalchemy as sa
from sqlalchemy import inspect, select
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session, sessionmaker

from backend.app.core.config import settings
from backend.app.database.connection import create_database_engine
from backend.app.database.models import MarketData
from backend.app.services.market_data_backfill_service import (
    MarketDataBackfillService,
)
from backend.app.services.market_data_service import MarketDataService


BACKEND_ROOT = Path(__file__).resolve().parents[3]
ALEMBIC_CONFIG_PATH = BACKEND_ROOT / "alembic.ini"
CURRENT_REVISION = "7c1e2f4a6b90"
APPLICATION_TABLES = {
    "users",
    "portfolios",
    "holdings",
    "market_data",
    "analyses",
    "simulations",
}


class StaticProvider:
    source_name = "phase-3-live"

    def __init__(
        self,
        data: pd.DataFrame,
        *,
        failed_symbols: tuple[str, ...] = (),
    ) -> None:
        self._data = data
        self._failed_symbols = failed_symbols

    def fetch_historical_prices(
        self,
        symbols,
        start_date,
        end_date,
    ) -> pd.DataFrame:
        data = self._data.copy(deep=True)
        data.attrs["failed_symbols"] = self._failed_symbols
        return data


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
    if database_name != "aura_test" and not database_name.startswith(
        "aura_test_"
    ):
        pytest.fail(
            "AURA_TEST_DATABASE_URL must target aura_test or aura_test_*",
            pytrace=False,
        )
    return raw_url


def _alembic_config() -> Config:
    return Config(ALEMBIC_CONFIG_PATH)


@pytest.fixture(scope="module")
def postgres_engine() -> Iterator[Engine]:
    raw_url = _test_database_url()
    engine = create_database_engine(raw_url)
    original_database_url = settings.database_url
    owns_schema = False

    try:
        with engine.connect() as connection:
            initial_tables = set(
                inspect(connection).get_table_names(schema="public")
            )
            unexpected = initial_tables - APPLICATION_TABLES - {
                "alembic_version"
            }
            if unexpected:
                pytest.fail(
                    "isolated test database contains unexpected public "
                    f"tables: {sorted(unexpected)}",
                    pytrace=False,
                )
            revision = MigrationContext.configure(
                connection
            ).get_current_revision()

        existing_tables = initial_tables & APPLICATION_TABLES
        if existing_tables:
            if existing_tables != APPLICATION_TABLES:
                pytest.fail(
                    "isolated test database has an incomplete application "
                    "schema",
                    pytrace=False,
                )
            if revision != CURRENT_REVISION:
                pytest.fail(
                    "isolated test database migrations are not current",
                    pytrace=False,
                )
            with engine.connect() as connection:
                populated = {
                    table: int(
                        connection.scalar(
                            sa.text(f'SELECT COUNT(*) FROM "{table}"')
                        )
                        or 0
                    )
                    for table in APPLICATION_TABLES
                }
            if any(populated.values()):
                pytest.fail(
                    "isolated test database contains application rows",
                    pytrace=False,
                )
        elif revision is not None:
            pytest.fail(
                "isolated test database is not at Alembic base",
                pytrace=False,
            )

        settings.database_url = raw_url  # type: ignore[assignment]
        if not existing_tables:
            command.upgrade(_alembic_config(), "head")
            owns_schema = True
        yield engine
    finally:
        try:
            if owns_schema:
                command.downgrade(_alembic_config(), "base")
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
def clean_rows(postgres_engine: Engine) -> Iterator[None]:
    yield
    with postgres_engine.begin() as connection:
        connection.execute(
            sa.text(
                "TRUNCATE TABLE simulations, analyses, holdings, portfolios, "
                "users, market_data CASCADE"
            )
        )


def _raw_data(
    rows: list[tuple[str, str, float, int | None, str]],
) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Date": [row[1] for row in rows],
            "Adj Close": [row[2] for row in rows],
            "Volume": [row[3] for row in rows],
            "symbol": [row[0] for row in rows],
            "source": [row[4] for row in rows],
        }
    )


def _canonical_data(
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
            "volume": pd.Series(
                [row[3] for row in rows],
                dtype="Int64",
            ),
            "source": pd.Series([row[4] for row in rows], dtype="string"),
        }
    )


def test_backfill_preserves_existing_newer_rows(
    session_factory: sessionmaker[Session],
) -> None:
    newer = _canonical_data(
        [("P3OLDER", "2026-01-05", 105.0, 1_005, "existing")]
    )
    with session_factory() as session:
        MarketDataService(session).store(newer)
        session.commit()

    provider = StaticProvider(
        _raw_data(
            [
                ("P3OLDER", "2000-01-03", 10.0, 100, "backfill"),
                ("P3OLDER", "2000-01-04", 11.0, 101, "backfill"),
            ]
        )
    )
    with session_factory() as session:
        MarketDataBackfillService(session).run(
            ["P3OLDER"],
            "2000-01-01",
            "2000-01-31",
            provider=provider,
        )
        session.commit()

    with session_factory() as session:
        rows = list(
            session.scalars(
                select(MarketData)
                .where(MarketData.symbol == "P3OLDER")
                .order_by(MarketData.date)
            ).all()
        )

    assert [row.date for row in rows] == [
        date(2000, 1, 3),
        date(2000, 1, 4),
        date(2026, 1, 5),
    ]
    assert rows[-1].adjusted_close == Decimal("105.000000000000")
    assert rows[-1].source == "existing"


def test_backfill_updates_one_overlapping_database_identity(
    session_factory: sessionmaker[Session],
) -> None:
    existing = _canonical_data(
        [("P3OVERLAP", "2001-01-03", 10.0, 100, "existing")]
    )
    with session_factory() as session:
        MarketDataService(session).store(existing)
        session.commit()

    provider = StaticProvider(
        _raw_data(
            [("P3OVERLAP", "2001-01-03", 12.5, None, "backfill")]
        )
    )
    with session_factory() as session:
        MarketDataBackfillService(session).run(
            ["P3OVERLAP"],
            "2001-01-01",
            "2001-01-31",
            provider=provider,
        )
        session.commit()

    with session_factory() as session:
        rows = list(
            session.scalars(
                select(MarketData).where(
                    MarketData.symbol == "P3OVERLAP"
                )
            ).all()
        )

    assert len(rows) == 1
    assert rows[0].adjusted_close == Decimal("12.500000000000")
    assert rows[0].volume is None
    assert rows[0].source == "backfill"


def test_backfill_rerun_does_not_create_duplicate_identities(
    session_factory: sessionmaker[Session],
) -> None:
    provider = StaticProvider(
        _raw_data(
            [
                ("P3RERUN", "2002-01-02", 20.0, 200, "backfill"),
                ("P3RERUN", "2002-01-03", 21.0, 201, "backfill"),
            ]
        )
    )
    for _ in range(2):
        with session_factory() as session:
            MarketDataBackfillService(session).run(
                ["P3RERUN"],
                "2002-01-01",
                "2002-01-31",
                provider=provider,
            )
            session.commit()

    with session_factory() as session:
        count = session.scalar(
            select(sa.func.count()).select_from(MarketData).where(
                MarketData.symbol == "P3RERUN"
            )
        )

    assert count == 2


def test_backfill_reuses_large_existing_storage_batches(
    session_factory: sessionmaker[Session],
) -> None:
    row_count = 1_001
    dates = pd.date_range("2003-01-01", periods=row_count)
    provider = StaticProvider(
        _raw_data(
            [
                (
                    "P3BATCH",
                    observation_date.date().isoformat(),
                    float(index + 1),
                    index,
                    "backfill",
                )
                for index, observation_date in enumerate(dates)
            ]
        )
    )

    with session_factory() as session:
        result = MarketDataBackfillService(session).run(
            ["P3BATCH"],
            dates[0].date(),
            dates[-1].date(),
            provider=provider,
        )
        assert result.row_count == row_count
        assert result.stored_count == row_count
        session.commit()

    with session_factory() as session:
        count = session.scalar(
            select(sa.func.count()).select_from(MarketData).where(
                MarketData.symbol == "P3BATCH"
            )
        )

    assert count == row_count


def test_failed_coverage_persists_no_rows(
    session_factory: sessionmaker[Session],
) -> None:
    provider = StaticProvider(
        _raw_data(
            [("P3VALID", "2004-01-02", 40.0, 400, "backfill")]
        ),
        failed_symbols=("P3FAILED",),
    )
    with session_factory() as session:
        with pytest.raises(ValueError, match="P3FAILED"):
            MarketDataBackfillService(session).run(
                ["P3VALID", "P3FAILED"],
                "2004-01-01",
                "2004-01-31",
                provider=provider,
            )
        session.commit()

    with session_factory() as session:
        count = session.scalar(
            select(sa.func.count()).select_from(MarketData).where(
                MarketData.symbol.in_(["P3VALID", "P3FAILED"])
            )
        )

    assert count == 0


def test_caller_rollback_removes_successful_backfill(
    session_factory: sessionmaker[Session],
) -> None:
    provider = StaticProvider(
        _raw_data(
            [("P3ROLLBACK", "2005-01-03", 50.0, 500, "backfill")]
        )
    )
    with session_factory() as session:
        MarketDataBackfillService(session).run(
            ["P3ROLLBACK"],
            "2005-01-01",
            "2005-01-31",
            provider=provider,
        )
        assert session.in_transaction()
        session.rollback()

    with session_factory() as session:
        count = session.scalar(
            select(sa.func.count()).select_from(MarketData).where(
                MarketData.symbol == "P3ROLLBACK"
            )
        )

    assert count == 0
