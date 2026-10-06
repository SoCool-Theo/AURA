"""Singleton operational state, separate from market observations and snapshots."""

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base


class MarketDataRefreshState(Base):
    __tablename__ = "market_data_refresh_state"
    __table_args__ = (
        CheckConstraint("id = 1", name="ck_market_refresh_singleton"),
        CheckConstraint("status IN ('never', 'running', 'success', 'partial', 'failed')", name="ck_market_refresh_status"),
        CheckConstraint("attempt_count >= 0 AND stored_count >= 0", name="ck_market_refresh_counts"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="never")
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_complete_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_complete_slot: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    stored_count: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0")
    updated_symbols: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default="[]")
    failed_symbols: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default="[]")
    error_code: Mapped[str | None] = mapped_column(Text)
    worker_running: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    worker_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
