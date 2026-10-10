"""Insert and query audit history within a caller-owned transaction."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select, true
from sqlalchemy.orm import Session, aliased

from ..models.audit_log import AuditLog


class AuditLogRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def record(
        self,
        *,
        actor_kind: str,
        actor_user_id: UUID | None,
        action: str,
        target_type: str,
        target_id: UUID,
        details: dict[str, str],
    ) -> AuditLog:
        row = AuditLog(
            actor_kind=actor_kind,
            actor_user_id=actor_user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            details=dict(details),
        )
        self._session.add(row)
        self._session.flush()
        return row

    def list(
        self,
        *,
        limit: int,
        offset: int,
        action: str | None = None,
        actor_kind: str | None = None,
        actor_user_id: UUID | None = None,
        target_type: str | None = None,
        target_id: UUID | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> tuple[list[AuditLog], int]:
        conditions = []
        filters = {
            "action": action,
            "actor_kind": actor_kind,
            "actor_user_id": actor_user_id,
            "target_type": target_type,
            "target_id": target_id,
        }
        for field, value in filters.items():
            if value is not None:
                conditions.append(getattr(AuditLog, field) == value)
        if created_from is not None:
            conditions.append(AuditLog.created_at >= created_from)
        if created_to is not None:
            conditions.append(AuditLog.created_at <= created_to)

        # One statement keeps total and page consistent under READ COMMITTED,
        # including an empty page when offset exceeds the matching count.
        matching = select(AuditLog).where(*conditions).cte("matching_audit_logs")
        page = (
            select(matching)
            .order_by(matching.c.created_at.desc(), matching.c.id.desc())
            .offset(offset)
            .limit(limit)
            .cte("audit_page")
        )
        totals = (
            select(func.count().label("total"))
            .select_from(matching)
            .cte("audit_total")
        )
        event = aliased(AuditLog, page)
        statement = (
            select(event, totals.c.total)
            .select_from(totals.outerjoin(page, true()))
            .order_by(page.c.created_at.desc(), page.c.id.desc())
        )
        results = self._session.execute(statement).all()
        return [row for row, _ in results if row is not None], results[0][1]
