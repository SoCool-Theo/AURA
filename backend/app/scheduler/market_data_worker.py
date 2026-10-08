"""One worker leader with serialized heartbeat access to its dedicated lease."""

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from ..database.repositories.market_data_refresh_repository import MarketDataRefreshRepository
from ..services.market_data_refresh_service import MarketDataRefreshError
from .market_data_lock import MarketDataLease


class MarketDataWorker:
    def __init__(self, lease: MarketDataLease) -> None:
        self.lease = lease

    def heartbeat(self) -> None:
        try:
            with self.lease.mutex:
                self.lease.verify()
                with Session(bind=self.lease.connection) as session:
                    MarketDataRefreshRepository(session).save(worker_running=True, worker_heartbeat_at=datetime.now(UTC))
                    session.commit()
        except Exception:
            raise MarketDataRefreshError("database_unavailable") from None

    def stop(self) -> None:
        with self.lease.mutex:
            self.lease.verify()
            with Session(bind=self.lease.connection) as session:
                MarketDataRefreshRepository(session).save(worker_running=False)
                session.commit()
