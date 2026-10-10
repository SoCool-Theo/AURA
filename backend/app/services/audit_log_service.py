"""Typed, allowlisted audit recording and read-only query mapping."""

from datetime import UTC

from sqlalchemy.orm import Session

from ..database.models.audit_log import AuditLog
from ..database.repositories.audit_log_repository import AuditLogRepository
from ..schemas.audit_log import (
    AuditEventCreate,
    AuditLogListResponse,
    AuditLogQuery,
    AuditLogResponse,
)


class AuditLogService:
    def __init__(self, session: Session) -> None:
        self._repository = AuditLogRepository(session)

    def record(self, event: AuditEventCreate) -> AuditLog:
        # Revalidate even constructed models before persistence. New action kinds
        # must deliberately extend the typed allowlist rather than accept payloads.
        validated = AuditEventCreate.model_validate(event.model_dump())
        return self._repository.record(**validated.model_dump(mode="python"))

    def list(self, query: AuditLogQuery) -> AuditLogListResponse:
        validated = AuditLogQuery.model_validate(query.model_dump())
        rows, total = self._repository.list(**validated.model_dump(mode="python"))
        items: list[AuditLogResponse] = []
        for row in rows:
            timestamp = row.created_at
            if timestamp.tzinfo is None:
                # SQLite verification loses timezone metadata; database timestamps
                # are UTC, and production PostgreSQL returns aware timestamps.
                timestamp = timestamp.replace(tzinfo=UTC)
            items.append(
                AuditLogResponse(
                    id=row.id,
                    actor_kind=row.actor_kind,
                    actor_user_id=row.actor_user_id,
                    action=row.action,
                    target_type=row.target_type,
                    target_id=row.target_id,
                    details=row.details,
                    created_at=timestamp.astimezone(UTC),
                )
            )
        return AuditLogListResponse(
            items=items, total=total, limit=validated.limit, offset=validated.offset
        )
