"""Synthetic persistence checks; no application database is used."""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

from alembic.config import Config
from alembic.script import ScriptDirectory
import pytest
from sqlalchemy import CheckConstraint, create_engine, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.database.connection import session_scope
from backend.app.database.models import AuditLog, User
from backend.app.database.repositories.audit_log_repository import AuditLogRepository
from backend.app.schemas.audit_log import AuditEventCreate, AuditLogQuery, AuditRoleChangeDetails
from backend.app.services.admin_access_service import AdminAccessService
from backend.app.services.audit_log_service import AuditLogService


@pytest.fixture
def audit_session() -> Iterator[Session]:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    User.__table__.create(engine)
    AuditLog.__table__.create(engine)
    try:
        with Session(engine) as session:
            yield session
    finally:
        engine.dispose()


def event(target_id: UUID | None = None) -> AuditEventCreate:
    return AuditEventCreate(
        actor_kind="OPERATOR", action="ADMIN_BOOTSTRAPPED", target_type="USER",
        target_id=target_id or uuid4(),
        details=AuditRoleChangeDetails(previous_role="CUSTOMER", new_role="ADMIN"),
    )


def test_record_is_caller_owned_and_rollback_removes_event(audit_session: Session) -> None:
    row = AuditLogService(audit_session).record(event())
    assert row.id is not None and row.created_at is not None
    assert row.details == {"previous_role": "CUSTOMER", "new_role": "ADMIN"}
    assert audit_session.scalar(select(func.count()).select_from(AuditLog)) == 1
    audit_session.rollback()
    assert audit_session.scalar(select(func.count()).select_from(AuditLog)) == 0


def test_record_flushes_without_commit_or_session_cleanup() -> None:
    session = MagicMock(spec=Session)
    payload = event().model_dump(mode="python")
    result = AuditLogRepository(session).record(**payload)
    session.add.assert_called_once_with(result)
    session.flush.assert_called_once_with()
    session.commit.assert_not_called()
    session.rollback.assert_not_called()
    session.close.assert_not_called()


def test_page_order_total_empty_page_and_committed_history(audit_session: Session) -> None:
    day = datetime(2026, 10, 10, tzinfo=UTC)
    service = AuditLogService(audit_session)
    rows = [service.record(event()) for _ in range(3)]
    # Insert order differs from tie-breaking ID order; newest time comes first.
    for index, row in enumerate(rows):
        row.id = UUID(int=index + 1)
        row.created_at = day + timedelta(days=1 if index == 0 else 0)
    audit_session.commit()
    audit_session.expire_all()
    page = service.list(AuditLogQuery(limit=1, offset=1))
    assert [item.id for item in page.items] == [UUID(int=3)]
    assert (page.total, page.limit, page.offset) == (3, 1, 1)
    assert page.items[0].created_at.utcoffset() == timedelta(0)
    all_rows = service.list(AuditLogQuery())
    assert [item.id for item in all_rows.items] == [UUID(int=1), UUID(int=3), UUID(int=2)]
    empty = service.list(AuditLogQuery(offset=3))
    assert empty.items == [] and empty.total == 3


def test_filters_combine_and_dates_are_inclusive(audit_session: Session) -> None:
    day = datetime(2026, 10, 10, tzinfo=UTC)
    target = uuid4()
    for target_id, timestamp in [
        (target, day - timedelta(seconds=1)), (target, day),
        (target, day + timedelta(seconds=1)), (uuid4(), day),
    ]:
        row = AuditLogService(audit_session).record(event(target_id))
        row.created_at = timestamp
    audit_session.commit()
    query = AuditLogQuery(
        action="ADMIN_BOOTSTRAPPED", actor_kind="OPERATOR", target_type="USER",
        target_id=target, created_from=day, created_to=day,
    )
    page = AuditLogService(audit_session).list(query)
    assert page.total == 1 and len(page.items) == 1
    assert page.items[0].target_id == target
    for filter_values in [{"actor_kind": "ADMIN"}, {"actor_user_id": uuid4()}, {"target_id": uuid4()}]:
        page = AuditLogService(audit_session).list(AuditLogQuery(**filter_values))
        assert page.total == 0 and page.items == []


def test_audit_history_survives_deletion_of_target_account(audit_session: Session) -> None:
    user = User(email="synthetic@example.com", password_hash="encoded")
    audit_session.add(user)
    audit_session.flush()
    user_id = user.id
    AuditLogService(audit_session).record(event(user_id))
    audit_session.commit()
    audit_session.delete(user)
    audit_session.commit()
    page = AuditLogService(audit_session).list(AuditLogQuery(target_id=user_id))
    assert page.total == 1 and page.items[0].target_id == user_id
    assert not AuditLog.__table__.foreign_keys


@pytest.mark.parametrize("actor_kind,actor_id", [
    ("OPERATOR", uuid4()), ("ADMIN", None), ("CUSTOMER", uuid4()),
])
def test_database_checks_actor_consistency(audit_session: Session, actor_kind, actor_id) -> None:
    payload = event().model_dump(mode="python")
    payload.update(actor_kind=actor_kind, actor_user_id=actor_id)
    audit_session.add(AuditLog(**payload))
    with pytest.raises(IntegrityError):
        audit_session.flush()


def test_bootstrap_role_and_event_commit_together_without_duplicate(audit_session: Session) -> None:
    user = User(email="synthetic@example.com", password_hash="encoded")
    audit_session.add(user)
    audit_session.commit()
    service = AdminAccessService(audit_session)
    # The PostgreSQL-only lock is mocked; role/event SQL is real SQLite SQL.
    with patch.object(service._repository, "lock_admin_bootstrap"):
        service.bootstrap_first_admin(user.id)
        audit_session.commit()
        service.bootstrap_first_admin(user.id)
        audit_session.commit()
    audit_session.expire_all()
    assert user.role == "ADMIN"
    page = AuditLogService(audit_session).list(AuditLogQuery())
    assert page.total == 1
    assert page.items[0].target_id == user.id
    assert page.items[0].actor_kind == "OPERATOR" and page.items[0].actor_user_id is None


def test_audit_failure_rolls_back_role_and_inserted_event(audit_session: Session) -> None:
    user = User(email="synthetic@example.com", password_hash="encoded")
    audit_session.add(user)
    audit_session.commit()
    user_id = user.id
    service = AdminAccessService(audit_session)
    original_record = service._audit.record

    def fail_after_insert(payload):
        original_record(payload)
        raise RuntimeError("synthetic audit failure")

    with (
        patch.object(service._repository, "lock_admin_bootstrap"),
        patch.object(service._audit, "record", side_effect=fail_after_insert),
        pytest.raises(RuntimeError, match="synthetic audit failure"),
        session_scope(lambda: audit_session),
    ):
        service.bootstrap_first_admin(user_id)
        audit_session.commit()
    assert audit_session.get(User, user_id).role == "CUSTOMER"
    assert audit_session.scalar(select(func.count()).select_from(AuditLog)) == 0


def test_audit_migration_matches_model_and_downgrade_is_scoped() -> None:
    script = ScriptDirectory.from_config(Config("backend/alembic.ini"))
    revision = script.get_revision("f8a0b2c4d6e9").module
    assert revision.down_revision == "e7f9a1b3c5d8"
    with patch.object(revision.op, "create_table") as create, patch.object(revision.op, "create_index") as indexes:
        revision.upgrade()
    assert create.call_args.args[0] == "audit_logs"
    model_checks = {c.name: str(c.sqltext) for c in AuditLog.__table__.constraints if isinstance(c, CheckConstraint)}
    migration_checks = {c.name: str(c.sqltext) for c in create.call_args.args[1:] if isinstance(c, CheckConstraint)}
    assert migration_checks == model_checks
    assert {call.args[0] for call in indexes.call_args_list} == {index.name for index in AuditLog.__table__.indexes}
    with patch.object(revision.op, "drop_index") as drop_index, patch.object(revision.op, "drop_table") as drop_table:
        revision.downgrade()
    drop_table.assert_called_once_with("audit_logs")
    assert len(drop_index.call_args_list) == 3
