"""Administrative event history, retained independently of account deletion."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, CheckConstraint, DateTime, Index, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from ..base import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        CheckConstraint(
            "(actor_kind = 'OPERATOR' AND actor_user_id IS NULL) OR "
            "(actor_kind = 'ADMIN' AND actor_user_id IS NOT NULL)",
            name="ck_audit_logs_actor",
        ),
        CheckConstraint("length(action) BETWEEN 1 AND 64", name="ck_audit_logs_action"),
        CheckConstraint(
            "length(target_type) BETWEEN 1 AND 64", name="ck_audit_logs_target_type"
        ),
        Index("ix_audit_logs_created_at", "created_at", "id"),
        Index("ix_audit_logs_actor_created_at", "actor_user_id", "created_at", "id"),
        Index("ix_audit_logs_target_created_at", "target_type", "target_id", "created_at", "id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    # UUID snapshots intentionally have no cascading FKs: deleted users must not
    # erase event history, and operator actions have no authenticated user actor.
    actor_kind: Mapped[str] = mapped_column(Text, nullable=False)
    actor_user_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    target_type: Mapped[str] = mapped_column(Text, nullable=False)
    target_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    details: Mapped[dict[str, str]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
