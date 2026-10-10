"""Caller-owned inserts and single-statement monitoring page/aggregate reads."""

from sqlalchemy import func, select, true
from sqlalchemy.orm import Session, aliased

from ..models.ai_request_log import AIRequestLog


class AIMonitoringRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def record(self, **values) -> AIRequestLog:
        row = AIRequestLog(**values)
        self._session.add(row)
        self._session.flush()
        return row

    @staticmethod
    def _conditions(*, created_from=None, created_to=None, **filters):
        conditions = [getattr(AIRequestLog, key) == value for key, value in filters.items() if value is not None]
        if created_from is not None:
            conditions.append(AIRequestLog.created_at >= created_from)
        if created_to is not None:
            conditions.append(AIRequestLog.created_at <= created_to)
        return conditions

    def list(self, *, limit, offset, **filters):
        matching = select(AIRequestLog).where(*self._conditions(**filters)).cte("matching_ai_requests")
        page = select(matching).order_by(matching.c.created_at.desc(), matching.c.id.desc()).limit(limit).offset(offset).cte("ai_requests_page")
        total = select(func.count().label("total")).select_from(matching).cte("ai_requests_total")
        event = aliased(AIRequestLog, page)
        rows = self._session.execute(select(event, total.c.total).select_from(
            total.outerjoin(page, true()),
        ).order_by(page.c.created_at.desc(), page.c.id.desc())).all()
        return [row for row, _ in rows if row is not None], rows[0][1]

    def summary(self, *, created_from=None, created_to=None):
        statement = select(
            func.count().label("total"),
            func.count().filter(AIRequestLog.outcome == "COMPLETED").label("completed"),
            func.count().filter(AIRequestLog.outcome == "REFUSED").label("refused"),
            func.count().filter(AIRequestLog.outcome == "ERROR").label("errors"),
            func.count().filter(AIRequestLog.provider_called.is_(True)).label("provider_calls"),
            func.count().filter(AIRequestLog.refusal_stage == "INPUT").label("input_refusals"),
            func.count().filter(AIRequestLog.refusal_stage == "OUTPUT").label("output_refusals"),
            func.avg(AIRequestLog.duration_ms).label("average_duration_ms"),
            func.min(AIRequestLog.created_at).label("first_recorded_at"),
            func.max(AIRequestLog.created_at).label("last_recorded_at"),
        ).where(*self._conditions(created_from=created_from, created_to=created_to))
        return self._session.execute(statement).mappings().one()
