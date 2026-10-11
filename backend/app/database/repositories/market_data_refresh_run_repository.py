"""Caller-owned run bookkeeping; all mutations require the shared refresh lock."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select, text, update
from sqlalchemy.orm import Session

from ..models.market_data_refresh_run import MarketDataRefreshRun
from ...scheduler.market_data_lock import REFRESH_LOCK_KEY, MarketDataRefreshBusyError


class MarketDataRefreshRunRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def lock_requests(self) -> None:
        if self.session.get_bind().dialect.name == "postgresql":
            if not self.session.scalar(text("SELECT pg_try_advisory_xact_lock(:key)"), {"key": REFRESH_LOCK_KEY}):
                raise MarketDataRefreshBusyError()

    def get(self, run_id: UUID) -> MarketDataRefreshRun | None:
        return self.session.get(MarketDataRefreshRun, run_id, populate_existing=True)

    def pending(self) -> MarketDataRefreshRun | None:
        return self.session.scalars(select(MarketDataRefreshRun).where(
            MarketDataRefreshRun.trigger == "ADMIN", MarketDataRefreshRun.status == "queued"
        ).order_by(MarketDataRefreshRun.requested_at, MarketDataRefreshRun.id).limit(1)).first()

    def recover_interrupted(self, now: datetime) -> int:
        # Called only after acquiring the session refresh lock. A running row at
        # this point belongs to an interrupted process, never a healthy writer.
        result = self.session.execute(update(MarketDataRefreshRun).where(MarketDataRefreshRun.status == "running").values(
            status="failed", finished_at=now, error_code="lock_lost"))
        return result.rowcount

    def create(self, **values: object) -> MarketDataRefreshRun:
        row = MarketDataRefreshRun(**values)
        self.session.add(row)
        self.session.flush()
        return row

    def save(self, run_id: UUID, **values: object) -> None:
        self.session.execute(update(MarketDataRefreshRun).where(MarketDataRefreshRun.id == run_id).values(**values))
        self.session.flush()

    def list(self, *, limit: int, offset: int) -> tuple[list[MarketDataRefreshRun], int]:
        total = self.session.scalar(select(func.count()).select_from(MarketDataRefreshRun)) or 0
        rows = self.session.scalars(select(MarketDataRefreshRun).order_by(
            MarketDataRefreshRun.requested_at.desc(), MarketDataRefreshRun.id.desc()).limit(limit).offset(offset)).all()
        return list(rows), total
