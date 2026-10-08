"""Guarded local PostgreSQL acceptance in a disposable, UUID-named schema.

Never migrates public, changes existing observations, or calls a live provider.
"""

from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
import importlib
import os
import re
from unittest.mock import Mock
from uuid import uuid4

from alembic.migration import MigrationContext
from alembic.operations import Operations
import pandas as pd
import pytest
from sqlalchemy import create_engine, func, inspect, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from backend.app.core.instruments import MARKET_UPDATE_SYMBOLS
from backend.app.data_pipeline.updater import MarketDataUpdateResult
from backend.app.database.models import MarketData, MarketDataRefreshState
from backend.app.database.repositories.market_data_refresh_repository import MarketDataRefreshRepository
import backend.app.scheduler.market_data_lock as locks
from backend.app.scheduler.market_data_worker import MarketDataWorker
import backend.app.services.market_data_refresh_service as refresh
from backend.app.services.market_data_status_service import MarketDataStatusService


@pytest.fixture
def database(monkeypatch, tmp_path):
    raw = os.getenv("AURA_TEST_DATABASE_URL")
    if not raw:
        pytest.skip("AURA_TEST_DATABASE_URL is not configured")
    url = make_url(raw)
    if url.drivername != "postgresql+psycopg" or url.host not in {"localhost", "127.0.0.1", "::1"} or not (
        url.database == "aura_test" or (url.database or "").startswith("aura_test_")):
        pytest.fail("Refresh acceptance requires an explicitly selected local aura_test database", pytrace=False)
    schema = f"aura_refresh_{uuid4().hex}"
    assert re.fullmatch(r"aura_refresh_[0-9a-f]{32}", schema)
    control = create_engine(url, poolclass=NullPool, connect_args={"connect_timeout": 5})
    engine = create_engine(url, poolclass=NullPool,
        connect_args={"connect_timeout": 5, "options": f"-c search_path={schema},pg_catalog"})
    with control.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    try:
        with engine.begin() as connection:
            revision = importlib.import_module("backend.alembic.versions.d6e8f0a2b4c6_market_data_refresh_state")
            with Operations.context(MigrationContext.configure(connection)):
                revision.upgrade()
            MarketData.__table__.create(connection)
        monkeypatch.setattr(locks, "create_database_engine", lambda *args, **kwargs: engine)
        monkeypatch.setattr(locks.settings, "database_url", raw)
        monkeypatch.setattr(locks.settings, "market_data_worker_database_url", None)
        monkeypatch.setattr(refresh.settings, "market_data_refresh_max_attempts", 1)
        # Do not contend with any application worker using the same local DB.
        monkeypatch.setattr(refresh, "REFRESH_LOCK_KEY", uuid4().int % (2 ** 62))
        cutoff = datetime.now(UTC).date() - timedelta(days=1)
        frame = pd.DataFrame({"date": [pd.Timestamp(cutoff)] * len(MARKET_UPDATE_SYMBOLS),
            "symbol": list(MARKET_UPDATE_SYMBOLS), "adjusted_close": [100.0] * len(MARKET_UPDATE_SYMBOLS),
            "volume": [1000] * len(MARKET_UPDATE_SYMBOLS), "source": ["refresh-acceptance"] * len(MARKET_UPDATE_SYMBOLS)})
        result = MarketDataUpdateResult(tmp_path / "raw.csv", tmp_path / "clean.csv", len(frame),
            MARKET_UPDATE_SYMBOLS, (), "2010-01-01", str(cutoff), str(cutoff), str(cutoff))
        pipeline = Mock(return_value=(result, frame))
        monkeypatch.setattr(refresh, "_update_market_data_with_frame", pipeline)
        yield engine, pipeline, result, frame
    finally:
        engine.dispose()
        # Exact fixture-owned schema only; never drop a pre-existing/public schema.
        assert re.fullmatch(r"aura_refresh_[0-9a-f]{32}", schema)
        with control.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        control.dispose()


def test_real_migration_and_status_price_commit_then_restart_skip(database):
    engine, pipeline, result, frame = database
    with engine.connect() as connection:
        assert set(inspect(connection).get_table_names()) == {"market_data", "market_data_refresh_state"}
    refresh.run_market_data_refresh()
    with Session(engine) as session:
        state = session.get(MarketDataRefreshState, 1)
        assert state.status == "success"
        assert state.last_complete_at is not None
        assert state.stored_count == 18
        assert session.scalar(select(func.count()).select_from(MarketData)) == 18
        status = MarketDataStatusService(session).get()
        assert status.data_status == "current"
        assert status.worker_status == "unknown"
    assert refresh.run_market_data_refresh(only_if_due=True) is None
    pipeline.assert_called_once()


def test_actual_session_lock_blocks_other_process_and_releases_after_exception(database):
    engine, pipeline, result, frame = database
    with pytest.raises(ValueError, match="fixture interruption"):
        with locks.market_data_lease(refresh.REFRESH_LOCK_KEY) as lease:
            lease.verify()  # Committing does not release a session lock.
            with pytest.raises(locks.MarketDataRefreshBusyError):
                refresh.run_market_data_refresh()
            pipeline.assert_not_called()
            raise ValueError("fixture interruption")
    refresh.run_market_data_refresh()
    pipeline.assert_called_once()


def test_actual_rollback_keeps_prices_unchanged_and_records_safe_failure(database, monkeypatch):
    engine, pipeline, result, frame = database
    original_store = refresh.MarketDataService.store

    def failed_store(self, data):
        original_store(self, data)
        raise ValueError("private transaction failure")

    monkeypatch.setattr(refresh.MarketDataService, "store", failed_store)
    with pytest.raises(refresh.MarketDataRefreshError, match="validation_failed"):
        refresh.run_market_data_refresh()
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(MarketData)) == 0
        state = session.get(MarketDataRefreshState, 1)
        assert state.status == "failed"
        assert state.last_complete_at is None
        assert state.error_code == "validation_failed"


def test_partial_fetch_preserves_old_symbols_and_last_complete_marker(database):
    from dataclasses import replace
    engine, pipeline, result, frame = database
    refresh.run_market_data_refresh()
    with Session(engine) as session:
        complete = session.get(MarketDataRefreshState, 1).last_complete_at
    partial = frame.iloc[:1].copy()
    partial["adjusted_close"] = 120.0
    pipeline.return_value = replace(result, symbols=("AAPL",), failed_symbols=("MSFT",)), partial
    refresh.run_market_data_refresh()
    with Session(engine) as session:
        state = session.get(MarketDataRefreshState, 1)
        assert state.status == "partial"
        assert "MSFT" in state.failed_symbols
        assert state.last_complete_at == complete
        assert session.scalar(select(func.count()).select_from(MarketData)) == 18
        assert float(session.get(MarketData, ("AAPL", frame.iloc[0]["date"].date())).adjusted_close) == 120.0
        assert float(session.get(MarketData, ("MSFT", frame.iloc[0]["date"].date())).adjusted_close) == 100.0


def test_worker_heartbeat_is_independent_and_clean_stop_reports_offline(database):
    engine, pipeline, result, frame = database
    with locks.market_data_lease(uuid4().int % (2 ** 62)) as lease:
        worker = MarketDataWorker(lease)
        worker.heartbeat()
        with Session(engine) as session:
            assert MarketDataStatusService(session).get().worker_status == "online"
        worker.stop()
        with Session(engine) as session:
            assert MarketDataStatusService(session).get().worker_status == "offline"
    pipeline.assert_not_called()


def test_lost_physical_lock_connection_aborts_before_prices_and_restart_recovers(database, monkeypatch):
    engine, pipeline, result, frame = database
    original_lease = refresh.market_data_lease
    active = []

    @contextmanager
    def capture(key):
        with original_lease(key) as lease:
            active.append(lease)
            yield lease

    monkeypatch.setattr(refresh, "market_data_lease", capture)

    def disconnect(**kwargs):
        with engine.begin() as connection:
            assert connection.scalar(text("SELECT pg_terminate_backend(:pid)"), {"pid": active[-1].backend_pid})
        return result, frame

    pipeline.side_effect = disconnect
    with pytest.raises(refresh.MarketDataRefreshError, match="lock_lost"):
        refresh.run_market_data_refresh()
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(MarketData)) == 0
    pipeline.side_effect = None
    refresh.run_market_data_refresh(only_if_due=True)
    with Session(engine) as session:
        assert session.get(MarketDataRefreshState, 1).status == "success"
