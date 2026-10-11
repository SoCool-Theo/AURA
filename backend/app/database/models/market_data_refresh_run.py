"""Durable refresh requests and run history, separate from financial records."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, BigInteger, CheckConstraint, DateTime, Index, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from ..base import Base


class MarketDataRefreshRun(Base):
    __tablename__ = "market_data_refresh_runs"
    __table_args__ = (
        CheckConstraint("trigger IN ('ADMIN', 'SCHEDULED', 'CATCH_UP', 'OPERATOR')", name="ck_market_runs_trigger"),
        CheckConstraint("status IN ('queued', 'running', 'success', 'partial', 'failed')", name="ck_market_runs_status"),
        CheckConstraint("attempt_count >= 0 AND stored_count >= 0", name="ck_market_runs_counts"),
        CheckConstraint("(trigger = 'ADMIN' AND requested_by IS NOT NULL) OR (trigger != 'ADMIN' AND requested_by IS NULL)", name="ck_market_runs_actor"),
        Index("ix_market_runs_requested_at", "requested_at", "id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    trigger: Mapped[str] = mapped_column(Text, nullable=False)
    requested_by: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    status: Mapped[str] = mapped_column(Text, nullable=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    stored_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, server_default="0")
    updated_symbols: Mapped[list[str]] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=False, default=list, server_default="[]")
    failed_symbols: Mapped[list[str]] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=False, default=list, server_default="[]")
    error_code: Mapped[str | None] = mapped_column(Text)
