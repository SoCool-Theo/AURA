"""Health aggregation, failure precedence, real timing, and PostgreSQL probe SQL."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

from pydantic import ValidationError
import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.database.repositories.admin_system_health_repository import AdminSystemHealthRepository
from backend.app.schemas.market_data_status import MarketDataStatusResponse
import backend.app.services.admin_system_health_service as module


NOW = datetime(2026, 10, 10, 9, tzinfo=UTC)


def market_status(*, worker="online", data="current", run="success"):
    return MarketDataStatusResponse(
        checked_at=NOW, update_time_utc="02:00", next_scheduled_at=NOW + timedelta(days=1),
        worker_status=worker, worker_last_seen_at=NOW - timedelta(seconds=60),
        last_run_status=run, last_attempt_at=NOW - timedelta(hours=1),
        last_finished_at=None if run == "running" else NOW - timedelta(minutes=50),
        last_complete_at=NOW - timedelta(minutes=50), attempt_count=1, stored_count=18,
        updated_symbols=[], failed_symbols=[], error_code=None, data_status=data, observations=[],
    )


@pytest.mark.parametrize("worker,data,run,expected", [
    ("online", "current", "success", "healthy"),
    ("offline", "current", "success", "degraded"),
    ("unknown", "current", "success", "unknown"),
    ("online", "stale", "success", "degraded"),
    ("online", "missing", "success", "degraded"),
    ("online", "current", "partial", "degraded"),
    ("online", "current", "failed", "degraded"),
    ("online", "current", "running", "unknown"),
    ("online", "current", "never", "unknown"),
    ("unknown", "stale", "never", "degraded"),
    ("unknown", "current", "failed", "degraded"),
    ("offline", "current", "running", "degraded"),
])
def test_aggregate_preserves_independent_worker_data_and_refresh_evidence(worker, data, run, expected):
    state = market_status(worker=worker, data=data, run=run)
    with (
        patch.object(module, "AdminSystemHealthRepository") as repository,
        patch.object(module, "MarketDataStatusService") as market,
        patch.object(module, "perf_counter", side_effect=[100.0, 100.012345]),
    ):
        repository.return_value.database_responds.return_value = True
        market.return_value.get.return_value = state
        result = module.AdminSystemHealthService(MagicMock(spec=Session)).get()
    assert result.status == expected and result.coverage == "partial"
    checks = {check.component: check for check in result.checks}
    assert len(checks) == len(result.checks) == 8
    assert checks["database"].status == "healthy" and checks["database"].latency_ms == 12.345
    assert checks["market_data_worker"].reason == f"worker_{worker}"
    assert checks["market_data"].reason == f"observations_{data}"
    assert checks["market_data_refresh"].reason == ("refresh_never_run" if run == "never" else f"refresh_{run}")
    assert all(checks[name].status == "not_checked" for name in ["market_data_provider", "analytics"])
    assert all(check.latency_ms is None for check in result.checks if check.component != "database")
    assert result.market_data == state
    market.return_value.get.assert_called_once_with(now=result.checked_at)


@pytest.mark.parametrize("failure", [False, SQLAlchemyError("postgresql://user:private-password@example.invalid/database")])
def test_database_failure_stops_further_reads_and_never_leaks_exception(failure):
    session = MagicMock(spec=Session)
    with patch.object(module, "AdminSystemHealthRepository") as repository, patch.object(module, "MarketDataStatusService") as market:
        if isinstance(failure, Exception):
            repository.return_value.database_responds.side_effect = failure
        else:
            repository.return_value.database_responds.return_value = failure
        result = module.AdminSystemHealthService(session).get()
    assert result.status == "unavailable" and result.market_data is None
    checks = {check.component: check for check in result.checks}
    assert checks["database"].status == "unavailable" and checks["database"].reason == "database_query_failed"
    for name in ["market_data_worker", "market_data", "market_data_refresh"]:
        assert checks[name].status == "unknown" and checks[name].reason == "database_unavailable"
    assert "private-password" not in result.model_dump_json()
    market.assert_not_called()
    session.commit.assert_not_called()
    session.rollback.assert_not_called()
    session.close.assert_not_called()


@pytest.mark.parametrize("failure", [SQLAlchemyError("private database connection"), ValidationError.from_exception_data("Synthetic", [])])
def test_market_status_failure_preserves_successful_ping_and_marks_degraded(failure):
    with patch.object(module, "AdminSystemHealthRepository") as repository, patch.object(module, "MarketDataStatusService") as market:
        repository.return_value.database_responds.return_value = True
        market.return_value.get.side_effect = failure
        result = module.AdminSystemHealthService(MagicMock(spec=Session)).get()
    assert result.status == "degraded" and result.market_data is None
    checks = {check.component: check for check in result.checks}
    assert checks["database"].status == "healthy"
    assert all(checks[name].status == "unavailable" and checks[name].reason == "market_status_unavailable"
               for name in ["market_data_worker", "market_data", "market_data_refresh"])
    assert "private database" not in result.model_dump_json()


@pytest.mark.parametrize("dialect,expected_sql", [
    ("postgresql", ["SET LOCAL statement_timeout = '2000ms'", "SELECT 1"]),
    ("sqlite", ["SELECT 1"]),
])
def test_probe_uses_transaction_local_postgresql_timeout_and_no_persistent_setting(dialect, expected_sql):
    session = MagicMock(spec=Session)
    session.get_bind.return_value.dialect.name = dialect
    session.execute.return_value.scalar_one.return_value = 1
    assert AdminSystemHealthRepository(session).database_responds() is True
    assert [str(call.args[0]) for call in session.execute.call_args_list] == expected_sql
    session.execute.return_value.scalar_one.assert_called_once()
    session.commit.assert_not_called()
    session.flush.assert_not_called()
    session.rollback.assert_not_called()
    session.close.assert_not_called()


def test_probe_checks_scalar_instead_of_treating_any_execution_as_success():
    session = MagicMock(spec=Session)
    session.get_bind.return_value.dialect.name = "postgresql"
    session.execute.return_value.scalar_one.return_value = 0
    assert AdminSystemHealthRepository(session).database_responds() is False
