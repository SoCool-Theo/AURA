"""Synthetic provider acceptance; called only inside the guarded PG fixture."""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Barrier, Event, Thread
from unittest.mock import patch
from uuid import UUID, uuid4

import pandas as pd
from sqlalchemy import select

from app.database.models import MarketData, MarketDataRefreshRun
from app.database.repositories.market_data_refresh_repository import MarketDataRefreshRepository
import app.database.repositories.market_data_refresh_run_repository as requests
import app.services.market_data_refresh_service as refresh
from app.scheduler.market_data_lock import market_data_lease
from app.scheduler.market_data_worker import MarketDataWorker


class SyntheticDailyProvider:
    source_name = "synthetic-admin-refresh"
    omitted = ()
    price = 100.0

    def fetch_historical_prices(self, symbols, start_date, end_date):
        selected = [symbol for symbol in symbols if symbol not in self.omitted]
        return pd.DataFrame({"date": [str(end_date)] * len(selected), "symbol": selected,
            "adjusted_close": [123.45678901 if symbol == "AAPL" else self.price for symbol in selected],
            "volume": [1000] * len(selected), "source": [self.source_name] * len(selected)})


def check_manual_refresh(client, factory, admin, customer):
    random_key = uuid4().int % (2 ** 62)
    with TemporaryDirectory(prefix="aura-manual-refresh-") as folder, patch.object(refresh, "REFRESH_LOCK_KEY", random_key), patch.object(requests, "REFRESH_LOCK_KEY", random_key), patch.object(refresh.settings, "market_data_refresh_max_attempts", 1):
        raw, clean = Path(folder)/"raw.csv", Path(folder)/"clean.csv"
        provider = SyntheticDailyProvider()
        def execute():
            return refresh.run_market_data_refresh(queued_only=True, provider=provider, raw_path=raw, processed_path=clean)
        def request(run_id=None, headers=admin):
            return client.post("/api/admin/market-data/refresh", headers=headers, json={"request_id": str(run_id or uuid4())})
        assert request(headers=customer).status_code == 403
        assert request().status_code == 409  # No worker heartbeat.
        with factory() as session:
            MarketDataRefreshRepository(session).save(worker_running=True, worker_heartbeat_at=datetime.now(UTC))
            session.commit()
        barrier = Barrier(2)
        def concurrent_request(_):
            barrier.wait(timeout=10)
            return request()
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(concurrent_request, range(2)))
        assert sorted(response.status_code for response in responses) == [202, 409]
        accepted = next(response.json() for response in responses if response.status_code == 202)
        assert request(UUID(accepted["id"])).json() == accepted
        with market_data_lease(random_key):
            assert request().status_code == 409
            # Replaying an accepted ID remains safe while the execution lock is held.
            assert request(UUID(accepted["id"])).json() == accepted
        assert execute().stored_count == 18
        with factory() as session:
            run = session.get(MarketDataRefreshRun, UUID(accepted["id"]))
            assert run.status == "success" and run.attempt_count == 1 and run.finished_at
            preserved_fx = session.get(MarketData, ("THB=X", datetime.now(UTC).date()-timedelta(days=1))).adjusted_close
        assert execute() is None  # Empty polling makes no new history row.
        assert request(UUID(accepted["id"])).json()["status"] == "success"
        assert request().status_code == 202
        provider.omitted = ("THB=X",)
        execute()
        with factory() as session:
            partial = session.scalars(select(MarketDataRefreshRun).order_by(MarketDataRefreshRun.requested_at.desc())).first()
            assert partial.status == "partial" and partial.failed_symbols == ["THB=X"]
            assert session.get(MarketData, ("THB=X", datetime.now(UTC).date()-timedelta(days=1))).adjusted_close == preserved_fx
        provider.omitted = ()
        failed_id = uuid4()
        assert request(failed_id).status_code == 202
        with factory() as session:
            prices_before = session.execute(select(MarketData.symbol, MarketData.date, MarketData.adjusted_close, MarketData.source).order_by(MarketData.symbol, MarketData.date)).all()
        provider.price = 999.0
        original_store = refresh.MarketDataService.store
        def fail_after_store(self, frame):
            original_store(self, frame)
            raise ValueError("synthetic rollback; private details must not escape")
        with patch.object(refresh.MarketDataService, "store", fail_after_store):
            try:
                execute()
            except refresh.MarketDataRefreshError as error:
                assert error.code == "validation_failed"
            else:
                raise AssertionError("Storage failure was reported as success")
        with factory() as session:
            assert session.execute(select(MarketData.symbol, MarketData.date, MarketData.adjusted_close, MarketData.source).order_by(MarketData.symbol, MarketData.date)).all() == prices_before
            assert session.get(MarketDataRefreshRun, failed_id).status == "failed"
            assert session.get(MarketDataRefreshRun, failed_id).stored_count == 0
            interrupted = uuid4()
            session.add(MarketDataRefreshRun(id=interrupted, trigger="OPERATOR", status="running", started_at=datetime.now(UTC)))
            session.commit()
        assert execute() is None
        with factory() as session:
            assert session.get(MarketDataRefreshRun, interrupted).error_code == "lock_lost"
            assert MarketDataRefreshRepository(session).get().status == "failed"
            MarketDataRefreshRepository(session).save(worker_running=False)
            session.commit()
        assert request().status_code == 409
        history = client.get("/api/admin/market-data/refresh-runs", headers=admin).json()
        assert history["total"] == 4
        audit = client.get("/api/admin/audit-logs", headers=admin, params={"action": "MARKET_REFRESH_REQUESTED"}).json()
        assert audit["total"] == 3 and all(event["target_type"] == "MARKET_REFRESH" for event in audit["items"])
        print("PASS PostgreSQL manual refresh: concurrent request/replay, shared locks, actual synthetic pipeline/storage, partial preservation, rollback, interrupted recovery and audit history", flush=True)


class SyntheticRefreshPreview:
    """Fixture-only consumer; no daily/catch-up scheduler or real provider."""
    def __init__(self):
        self.stop = Event()
        self.folder = TemporaryDirectory(prefix="aura-refresh-preview-")
        self.key = uuid4().int % (2 ** 62)
        self.patches = [patch.object(refresh, "REFRESH_LOCK_KEY", self.key), patch.object(requests, "REFRESH_LOCK_KEY", self.key), patch.object(refresh.settings, "market_data_refresh_max_attempts", 1)]
        for item in self.patches: item.start()
        self.ready = Event()
        self.thread = Thread(target=self.run, daemon=True)
        self.thread.start()
        if not self.ready.wait(timeout=10):
            self.close()
            raise RuntimeError("Synthetic preview consumer failed to start")

    def run(self):
        with market_data_lease(uuid4().int % (2 ** 62)) as lease:
            worker = MarketDataWorker(lease)
            try:
                worker.heartbeat(); self.ready.set()
                while not self.stop.wait(2):
                    worker.heartbeat()
                    refresh.run_market_data_refresh(queued_only=True, provider=SyntheticDailyProvider(),
                        raw_path=Path(self.folder.name)/"raw.csv", processed_path=Path(self.folder.name)/"clean.csv")
            finally:
                worker.stop()

    def close(self):
        self.stop.set(); self.thread.join(timeout=30)
        if self.thread.is_alive(): raise RuntimeError("Synthetic refresh consumer has not stopped")
        for item in reversed(self.patches): item.stop()
        self.folder.cleanup()
