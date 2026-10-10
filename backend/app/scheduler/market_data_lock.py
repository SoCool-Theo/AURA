"""Session advisory locks held on dedicated, non-pooled PostgreSQL connections."""

from contextlib import contextmanager
from collections.abc import Iterator
from threading import RLock

from sqlalchemy import Connection, text
from sqlalchemy.engine import make_url

from ..core.config import settings
from ..database.connection import create_database_engine

REFRESH_LOCK_KEY = 0x4155524101
WORKER_LOCK_KEY = 0x4155524102


class MarketDataRefreshBusyError(RuntimeError):
    def __init__(self) -> None:
        super().__init__("Another market-data process already holds the lock.")


class MarketDataLockLostError(RuntimeError):
    def __init__(self) -> None:
        super().__init__("Market-data lock connection was lost; update aborted.")


class MarketDataLease:
    def __init__(self, connection: Connection, backend_pid: int) -> None:
        self.connection = connection
        self.backend_pid = backend_pid
        self.mutex = RLock()

    def verify(self) -> None:
        if self.connection.closed or self.connection.invalidated:
            raise MarketDataLockLostError()
        if self.connection.scalar(text("SELECT pg_backend_pid()")) != self.backend_pid:
            raise MarketDataLockLostError()
        self.connection.commit()


@contextmanager
def market_data_lease(key: int) -> Iterator[MarketDataLease]:
    # Never return a session-level advisory lock to a shared connection pool.
    url = settings.market_data_worker_database_url or settings.database_url
    if url is not None:
        parsed = make_url(str(url))
        if (parsed.host or "").endswith("pooler.supabase.com") and parsed.port == 6543:
            raise RuntimeError("Market-data worker requires a direct or session-pooled database connection.")
    engine = create_database_engine(url, isolated=True)
    try:
        with engine.connect() as connection:
            connection.execute(text("SET statement_timeout = '30s'"))
            acquired = connection.scalar(text("SELECT pg_try_advisory_lock(:key)"), {"key": key})
            backend_pid = connection.scalar(text("SELECT pg_backend_pid()"))
            connection.commit()
            if not acquired:
                raise MarketDataRefreshBusyError()
            lease = MarketDataLease(connection, backend_pid)
            try:
                yield lease
            finally:
                # Release explicitly for supported session poolers too. Verify
                # the original session first; never reconnect just to unlock.
                with lease.mutex:
                    if not connection.closed and not connection.invalidated:
                        try:
                            connection.rollback()
                            lease.verify()
                            connection.scalar(text("SELECT pg_advisory_unlock(:key)"), {"key": key})
                            connection.commit()
                        except Exception:
                            connection.invalidate()
                # NullPool also closes the dedicated physical connection;
                # a dead session cannot be returned to our shared API pool.
    finally:
        engine.dispose()
