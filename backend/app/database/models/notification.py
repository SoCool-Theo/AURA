"""Account-owned in-app notifications; no external delivery or financial data."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from ..base import Base


class NotificationPreferences(Base):
    __tablename__ = "notification_preferences"

    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    analysis_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    simulation_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        CheckConstraint("(kind = 'analysis' AND report_id IS NOT NULL AND simulation_id IS NULL) OR (kind = 'simulation' AND simulation_id IS NOT NULL AND report_id IS NULL)", name="ck_notifications_target"),
        UniqueConstraint("report_id", name="uq_notifications_report"),
        UniqueConstraint("simulation_id", name="uq_notifications_simulation"),
        Index("ix_notifications_user_created_at", "user_id", "created_at", "id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    portfolio_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False)
    report_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("analyses.id", ondelete="CASCADE"), nullable=True)
    simulation_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("simulations.id", ondelete="CASCADE"), nullable=True)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
