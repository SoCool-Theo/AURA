"""Guarded live PostgreSQL verification for the scheduled update path."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
import logging
import os
from pathlib import Path
from unittest.mock import patch

from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
import pandas as pd
import pytest
from sqlalchemy import Engine, delete, func, inspect, select, text, tuple_
from sqlalchemy.engine import make_url

from backend.app.core.config import settings
from backend.app.data_pipeline.updater import MarketDataUpdateResult
from backend.app.database.connection import create_database_engine
from backend.app.database.models import MarketData
from backend.app.database.repositories import MarketDataRepository
import backend.app.scheduler.market_data_job as job_module
from backend.app.services import market_data_update_service as update_service


BACKEND_ROOT = Path(__file__).resolve().parents[3]
ALEMBIC_CONFIG_PATH = BACKEND_ROOT / "alembic.ini"
APPLICATION_TABLES = {
    "alembic_version",
    "analyses",
    "holdings",
    "market_data",
    "portfolios",
    "simulations",
    "users",
}
SOURCE = "phase-6-scheduler-live"
E2E_SYMBOL = "AURA_P6_SCHED_E2E"
PARTIAL_SYMBOL = "AURA_P6_SCHED_PARTIAL"
ROLLBACK_SYMBOL = "AURA_P6_SCHED_ROLLBACK"
FAILED_SYMBOL = "AURA_P6_SCHED_UNAVAILABLE"
E2E_DATES = (date(2099, 1, 5), date(2099, 1, 6))
PARTIAL_DATE = date(2099, 2, 5)
ROLLBACK_DATE = date(2099, 3, 5)
TEST_IDENTITIES = frozenset(
    {
        (E2E_SYMBOL, E2E_DATES[0]),
        (E2E_SYMBOL, E2E_DATES[1]),
        (PARTIAL_SYMBOL, PARTIAL_DATE),
        (ROLLBACK_SYMBOL, ROLLBACK_DATE),
    }
)
TEST_SYMBOLS = frozenset(symbol for symbol, _ in TEST_IDENTITIES)


@dataclass(frozen=True, slots=True)
class UnrelatedMarketDataBaseline:
    row_count: int
    sentinel: tuple[object, ...] | None


class ControlledRollbackError(RuntimeError):
    """Test-only failure raised after a real repository mutation."""


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


def _test_identity_filter():
    return tuple_(MarketData.symbol, MarketData.date).in_(TEST_IDENTITIES)


def _unrelated_baseline(engine: Engine) -> UnrelatedMarketDataBaseline:
    with engine.connect() as connection:
        row_count = int(
            connection.scalar(
                select(func.count())
                .select_from(MarketData)
                .where(~MarketData.symbol.in_(TEST_SYMBOLS))
            )
            or 0
        )
        sentinel = connection.execute(
            select(
                MarketData.symbol,
                MarketData.date,
                MarketData.adjusted_close,
                MarketData.volume,
                MarketData.source,
            )
            .where(~MarketData.symbol.in_(TEST_SYMBOLS))
            .order_by(MarketData.symbol, MarketData.date)
            .limit(1)
        ).one_or_none()
    return UnrelatedMarketDataBaseline(
        row_count=row_count,
        sentinel=None if sentinel is None else tuple(sentinel),
    )


@pytest.fixture(scope="module")
def postgres_engine() -> Iterator[Engine]:
    raw_url = _test_database_url()
    expected_database = make_url(raw_url).database
    engine = create_database_engine(raw_url)
    original_database_url = settings.database_url

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

        if actual_database != expected_database or actual_schema != "public":
            pytest.fail(
                "AURA_TEST_DATABASE_URL did not resolve to the expected "
                "database and public schema",
                pytrace=False,
            )
        if table_names != APPLICATION_TABLES:
            pytest.fail(
                "Guarded test database must contain exactly the current Aura "
                f"application schema; found tables: {sorted(table_names)}",
                pytrace=False,
            )
        expected_head = ScriptDirectory.from_config(
            Config(str(ALEMBIC_CONFIG_PATH))
        ).get_current_head()
        if current_revision != expected_head:
            pytest.fail(
                "Guarded test database must already be at Alembic head",
                pytrace=False,
            )

        settings.database_url = raw_url  # type: ignore[assignment]
        yield engine
    finally:
        settings.database_url = original_database_url
        engine.dispose()


@pytest.fixture(autouse=True)
def protect_database_state(postgres_engine: Engine) -> Iterator[None]:
    with postgres_engine.connect() as connection:
        existing_test_rows = int(
            connection.scalar(
                select(func.count())
                .select_from(MarketData)
                .where(MarketData.symbol.in_(TEST_SYMBOLS))
            )
            or 0
        )
    if existing_test_rows:
        pytest.fail(
            "Dedicated Phase 6 scheduler-test identities already exist; "
            "refusing to overwrite them",
            pytrace=False,
        )
    unrelated_before = _unrelated_baseline(postgres_engine)

    try:
        yield
    finally:
        with postgres_engine.begin() as connection:
            connection.execute(
                delete(MarketData).where(_test_identity_filter())
            )
        with postgres_engine.connect() as connection:
            remaining_test_rows = int(
                connection.scalar(
                    select(func.count())
                    .select_from(MarketData)
                    .where(_test_identity_filter())
                )
                or 0
            )
        assert remaining_test_rows == 0
        assert _unrelated_baseline(postgres_engine) == unrelated_before


def _canonical_data(
    rows: Sequence[tuple[str, date, float, int | None, str]],
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


def _pipeline_handoff(
    data: pd.DataFrame,
    *,
    failed_symbols: tuple[str, ...] = (),
) -> tuple[MarketDataUpdateResult, pd.DataFrame]:
    dates = pd.to_datetime(data["date"])
    symbols = tuple(data["symbol"].drop_duplicates().tolist())
    return (
        MarketDataUpdateResult(
            raw_path=Path("phase-6-synthetic-raw-not-written.csv"),
            processed_path=Path("phase-6-synthetic-processed-not-written.csv"),
            row_count=len(data),
            symbols=symbols,
            failed_symbols=failed_symbols,
            requested_start_date=dates.min().date().isoformat(),
            requested_end_date=dates.max().date().isoformat(),
            actual_start_date=dates.min().date().isoformat(),
            actual_end_date=dates.max().date().isoformat(),
        ),
        data,
    )


def _rows_for_symbol(engine: Engine, symbol: str) -> list[MarketData]:
    with update_service.create_session_factory(engine)() as fresh_session:
        return list(
            fresh_session.scalars(
                select(MarketData)
                .where(MarketData.symbol == symbol)
                .order_by(MarketData.date)
            ).all()
        )


def test_live_scheduled_job_persists_through_real_postgresql(
    postgres_engine: Engine,
) -> None:
    data = _canonical_data(
        [
            (E2E_SYMBOL, E2E_DATES[0], 101.25, 1_001, SOURCE),
            (E2E_SYMBOL, E2E_DATES[1], 102.5, None, SOURCE),
        ]
    )
    assert (
        job_module.update_market_data_and_persist
        is update_service.update_market_data_and_persist
    )

    with patch.object(
        update_service,
        "_update_market_data_with_frame",
        return_value=_pipeline_handoff(data),
    ) as pipeline_handoff:
        result = job_module.run_scheduled_market_data_update()

    assert result is None
    pipeline_handoff.assert_called_once()
    rows = _rows_for_symbol(postgres_engine, E2E_SYMBOL)
    assert [row.date for row in rows] == list(E2E_DATES)
    assert [row.adjusted_close for row in rows] == [
        Decimal("101.250000000000"),
        Decimal("102.500000000000"),
    ]
    assert [row.volume for row in rows] == [1_001, None]
    assert [row.source for row in rows] == [SOURCE, SOURCE]


def test_live_scheduled_job_repeat_upsert_updates_without_duplicates(
    postgres_engine: Engine,
) -> None:
    initial = _canonical_data(
        [(E2E_SYMBOL, E2E_DATES[0], 201.0, 2_001, SOURCE)]
    )
    updated_source = f"{SOURCE}-updated"
    updated = _canonical_data(
        [(E2E_SYMBOL, E2E_DATES[0], 209.75, 2_099, updated_source)]
    )

    with patch.object(
        update_service,
        "_update_market_data_with_frame",
        side_effect=[
            _pipeline_handoff(initial),
            _pipeline_handoff(updated),
        ],
    ) as pipeline_handoff:
        job_module.run_scheduled_market_data_update()
        first_rows = _rows_for_symbol(postgres_engine, E2E_SYMBOL)
        job_module.run_scheduled_market_data_update()

    assert len(first_rows) == 1
    assert first_rows[0].adjusted_close == Decimal("201.000000000000")
    assert pipeline_handoff.call_count == 2
    rows = _rows_for_symbol(postgres_engine, E2E_SYMBOL)
    assert len(rows) == 1
    assert rows[0].date == E2E_DATES[0]
    assert rows[0].adjusted_close == Decimal("209.750000000000")
    assert rows[0].volume == 2_099
    assert rows[0].source == updated_source


def test_live_partial_provider_result_persists_available_rows(
    postgres_engine: Engine,
    caplog: pytest.LogCaptureFixture,
) -> None:
    data = _canonical_data(
        [(PARTIAL_SYMBOL, PARTIAL_DATE, 301.5, 3_001, SOURCE)]
    )

    with (
        patch.object(
            update_service,
            "_update_market_data_with_frame",
            return_value=_pipeline_handoff(
                data,
                failed_symbols=(FAILED_SYMBOL,),
            ),
        ),
        caplog.at_level(logging.WARNING, logger=job_module.__name__),
    ):
        result = job_module.run_scheduled_market_data_update()

    assert result is None
    rows = _rows_for_symbol(postgres_engine, PARTIAL_SYMBOL)
    assert len(rows) == 1
    assert rows[0].adjusted_close == Decimal("301.500000000000")
    assert rows[0].volume == 3_001
    assert FAILED_SYMBOL in caplog.text


def test_live_scheduled_failure_rolls_back_and_preserves_exception(
    postgres_engine: Engine,
) -> None:
    data = _canonical_data(
        [(ROLLBACK_SYMBOL, ROLLBACK_DATE, 401.25, 4_001, SOURCE)]
    )
    failure = ControlledRollbackError("controlled scheduler rollback")
    mutation_executed = False
    original_upsert = MarketDataRepository.upsert_many

    def upsert_then_fail(
        repository: MarketDataRepository,
        records,
    ) -> int:
        nonlocal mutation_executed
        stored_count = original_upsert(repository, records)
        assert stored_count == len(records) == 1
        mutation_executed = True
        raise failure

    with (
        patch.object(
            update_service,
            "_update_market_data_with_frame",
            return_value=_pipeline_handoff(data),
        ),
        patch.object(
            MarketDataRepository,
            "upsert_many",
            autospec=True,
            side_effect=upsert_then_fail,
        ),
        pytest.raises(ControlledRollbackError) as raised,
    ):
        job_module.run_scheduled_market_data_update()

    assert mutation_executed
    assert raised.value is failure
    assert _rows_for_symbol(postgres_engine, ROLLBACK_SYMBOL) == []
