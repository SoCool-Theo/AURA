from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from pydantic import ValidationError
import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session

from backend.app.database.repositories.ai_monitoring_repository import AIMonitoringRepository
from backend.app.schemas.ai_monitoring import AIRequestsQuery
import backend.app.services.ai_monitoring_service as module


@pytest.mark.parametrize("values", [
    {"limit": 0}, {"limit": 101}, {"offset": -1}, {"offset": 10001},
    {"outcome": "arbitrary"}, {"error_code": "private arbitrary text"},
    {"created_from": datetime(2026, 10, 11, tzinfo=UTC), "created_to": datetime(2026, 10, 10, tzinfo=UTC)},
])
def test_internal_queries_revalidated_before_database(values):
    with patch.object(module, "AIMonitoringRepository") as repository:
        with pytest.raises(ValidationError):
            module.AIMonitoringService(MagicMock(spec=Session)).list(AIRequestsQuery.model_construct(**values))
    repository.return_value.list.assert_not_called()


def test_postgresql_list_binds_filters_and_retains_total_on_empty_page():
    session = MagicMock(spec=Session)
    session.execute.return_value.all.return_value = [(None, 2)]
    rows, total = AIMonitoringRepository(session).list(limit=1, offset=10000, outcome="ERROR", error_code="PROVIDER_TIMEOUT")
    assert rows == [] and total == 2
    compiled = session.execute.call_args.args[0].compile(dialect=postgresql.dialect())
    assert "LEFT OUTER JOIN ai_requests_page ON true" in str(compiled)
    assert {"ERROR", "PROVIDER_TIMEOUT"}.issubset(set(compiled.params.values()))
    for secret_field in ["password_hash", "portfolio_id", "message", "answer", "history", "user_id"]:
        assert secret_field not in str(compiled)
    session.execute.assert_called_once()


def test_postgresql_summary_counts_only_metadata_without_loading_logs_or_context():
    session = MagicMock(spec=Session)
    AIMonitoringRepository(session).summary(created_from=datetime(2026, 10, 10, tzinfo=UTC))
    sql = str(session.execute.call_args.args[0].compile(dialect=postgresql.dialect()))
    assert "avg(ai_request_logs.duration_ms)" in sql
    assert "ai_request_logs.created_at >=" in sql
    assert "JOIN" not in sql and "users" not in sql
    session.execute.assert_called_once()
    session.commit.assert_not_called()
    session.flush.assert_not_called()
