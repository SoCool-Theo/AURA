"""Synthetic storage, constraints, retention, and allowlisted monitoring contracts."""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch
from uuid import UUID

from alembic.config import Config
from alembic.script import ScriptDirectory
from pydantic import ValidationError
import pytest
from sqlalchemy import CheckConstraint, create_engine, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.database.models import AIRequestLog
from backend.app.database.repositories.ai_monitoring_repository import AIMonitoringRepository
from backend.app.schemas.ai_monitoring import AIRequestEvent, AIRequestsQuery, AIMonitoringTimeQuery
from backend.app.services.ai_monitoring_service import AIMonitoringService


NOW = datetime(2026, 10, 10, tzinfo=UTC)


def event(**changes):
    return AIRequestEvent(**{
        "started_at": NOW, "duration_ms": 10.0, "outcome": "COMPLETED", "http_status": 200,
        "provider_kind": "custom", "provider_called": True, "has_portfolio_source": True, **changes,
    })


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    AIRequestLog.__table__.create(engine)
    try:
        with Session(engine, autoflush=False) as connection:
            yield connection
    finally:
        engine.dispose()


def test_recording_is_caller_owned_and_rollback_removes_insert(session):
    row = AIMonitoringService(session).record(event())
    assert row.id is not None and row.created_at is not None
    assert session.scalar(select(func.count()).select_from(AIRequestLog)) == 1
    session.rollback()
    assert session.scalar(select(func.count()).select_from(AIRequestLog)) == 0


def test_repository_never_commits_rolls_back_or_closes_caller():
    session = MagicMock(spec=Session)
    AIMonitoringService(session).record(event())
    session.add.assert_called_once()
    session.flush.assert_called_once_with()
    session.commit.assert_not_called()
    session.rollback.assert_not_called()
    session.close.assert_not_called()


@pytest.mark.parametrize("changes", [
    {"duration_ms": -1}, {"duration_ms": float("nan")}, {"duration_ms": float("inf")},
    {"outcome": "arbitrary"}, {"provider_kind": "http://secret.invalid"}, {"http_status": 201},
    {"error_code": "private arbitrary text"}, {"guardrail_reason": "private arbitrary text"},
    {"limitation_count": 11}, {"started_at": NOW.replace(tzinfo=None)},
    {"outcome": "REFUSED"}, {"provider_called": False},
    {"outcome": "REFUSED", "refusal_stage": "INPUT", "guardrail_reason": "investment_advice", "has_portfolio_source": False},
    {"outcome": "ERROR", "http_status": 503},
    {"outcome": "ERROR", "http_status": 503, "error_code": "PROVIDER_TIMEOUT"},
])
def test_invalid_or_inconsistent_metadata_rejected_before_persistence(changes):
    payload = event().model_dump()
    payload.update(changes)
    constructed = AIRequestEvent.model_construct(**payload)
    with patch("backend.app.services.ai_monitoring_service.AIMonitoringRepository") as repository:
        with pytest.raises(ValidationError):
            AIMonitoringService(MagicMock(spec=Session)).record(constructed)
    repository.return_value.record.assert_not_called()


@pytest.mark.parametrize("field", ["message", "answer", "history", "user_id", "portfolio_id", "model", "api_key", "details"])
def test_no_freeform_or_identity_fields_can_be_added_to_event(field):
    values = event().model_dump()
    values[field] = "PRIVATE_CONTENT"
    with pytest.raises(ValidationError):
        AIRequestEvent(**values)
    assert field not in AIRequestLog.__table__.columns


def test_stable_pages_inclusive_utc_time_filter_and_summary_agree(session):
    service = AIMonitoringService(session)
    rows = [service.record(event(duration_ms=value)) for value in [10, 20, 30, 40]]
    for index, row in enumerate(rows):
        row.id = UUID(int=index + 1)
        row.created_at = NOW + timedelta(seconds=1 if index == 0 else 0)
    session.commit()
    page = service.list(AIRequestsQuery(limit=2, offset=1))
    assert [item.id for item in page.items] == [UUID(int=4), UUID(int=3)]
    assert page.total == 4 and all(item.created_at.tzinfo == UTC for item in page.items)
    # +07:00 is normalized to the same UTC midnight, including both bounds.
    start = datetime.fromisoformat("2026-10-10T07:00:00+07:00")
    query = AIMonitoringTimeQuery(created_from=start, created_to=NOW)
    summary = service.summary(query)
    assert summary.total == summary.completed == 3
    assert summary.average_duration_ms == 30
    assert summary.first_recorded_at == summary.last_recorded_at == NOW
    filtered = service.list(AIRequestsQuery(created_from=start, created_to=NOW, offset=10000))
    assert filtered.items == [] and filtered.total == 3
    empty = service.summary(AIMonitoringTimeQuery(created_to=NOW - timedelta(seconds=1)))
    assert empty.total == 0 and empty.average_duration_ms is empty.first_recorded_at is empty.last_recorded_at is None


@pytest.mark.parametrize("changes", [
    {"outcome": "unknown"}, {"provider_kind": "secret"}, {"duration_ms": -1}, {"http_status": 503},
    {"outcome": "REFUSED", "refusal_stage": None, "guardrail_reason": "investment_advice", "has_portfolio_source": False},
    {"outcome": "REFUSED", "refusal_stage": "INPUT", "guardrail_reason": "investment_advice", "has_portfolio_source": False},
])
def test_database_constraints_reject_invalid_rows_without_schema_validation(session, changes):
    values = event().model_dump()
    values.update(changes)
    session.add(AIRequestLog(**values))
    with pytest.raises(IntegrityError):
        session.flush()


def test_log_has_no_account_resource_reference_or_conversation_json():
    assert not AIRequestLog.__table__.foreign_keys
    assert set(AIRequestLog.__table__.columns.keys()) == {
        "id", "started_at", "duration_ms", "outcome", "http_status", "provider_kind", "provider_called",
        "refusal_stage", "guardrail_reason", "error_code", "has_portfolio_source", "has_report_source",
        "has_simulation_source", "limitation_count", "created_at",
    }


def test_ai_migration_matches_model_checks_and_scoped_downgrade():
    script = ScriptDirectory.from_config(Config("backend/alembic.ini"))
    migration = script.get_revision("a9b1c3d5e7f0").module
    assert migration.down_revision == "f8a0b2c4d6e9"
    with patch.object(migration.op, "create_table") as create, patch.object(migration.op, "create_index") as index:
        migration.upgrade()
    assert create.call_args.args[0] == "ai_request_logs"
    actual = {item.name: str(item.sqltext) for item in create.call_args.args[1:] if isinstance(item, CheckConstraint)}
    expected = {item.name: str(item.sqltext) for item in AIRequestLog.__table__.constraints if isinstance(item, CheckConstraint)}
    assert actual == expected
    assert {call.args[0] for call in index.call_args_list} == {item.name for item in AIRequestLog.__table__.indexes}
    with patch.object(migration.op, "drop_table") as drop_table, patch.object(migration.op, "drop_index") as drop_index:
        migration.downgrade()
    drop_table.assert_called_once_with("ai_request_logs")
    assert drop_index.call_count == 2
