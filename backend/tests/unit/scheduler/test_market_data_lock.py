from unittest.mock import MagicMock, Mock

import pytest

import backend.app.scheduler.market_data_lock as locks


@pytest.fixture
def harness(monkeypatch):
    engine, connection = MagicMock(), MagicMock(closed=False, invalidated=False)
    engine.connect.return_value.__enter__.return_value = connection
    connection.scalar.side_effect = [True, 42, 42, 42, True]
    create = Mock(return_value=engine)
    monkeypatch.setattr(locks, "create_database_engine", create)
    monkeypatch.setattr(locks.settings, "market_data_worker_database_url", None)
    monkeypatch.setattr(locks.settings, "database_url", None)
    return engine, connection, create


def test_dedicated_lock_lives_across_commits_and_is_closed_on_exit(harness):
    engine, connection, create = harness
    with locks.market_data_lease(locks.REFRESH_LOCK_KEY) as lease:
        lease.verify()
        assert lease.backend_pid == 42
        assert connection.commit.call_count == 2
    create.assert_called_once_with(None, isolated=True)
    engine.connect.return_value.__exit__.assert_called_once()
    engine.dispose.assert_called_once()
    assert "pg_try_advisory_lock" in str(connection.scalar.call_args_list[0].args[0])
    assert "pg_advisory_unlock" in str(connection.scalar.call_args_list[-1].args[0])
    connection.invalidate.assert_not_called()


def test_busy_lease_is_not_yielded_and_connection_is_closed(harness):
    engine, connection, create = harness
    connection.scalar.side_effect = [False, 42]
    with pytest.raises(locks.MarketDataRefreshBusyError):
        with locks.market_data_lease(locks.REFRESH_LOCK_KEY):
            pytest.fail("busy lease cannot run work")
    engine.connect.return_value.__exit__.assert_called_once()
    engine.dispose.assert_called_once()


@pytest.mark.parametrize("reason", ["invalidated", "closed", "changed_pid"])
def test_lost_session_lock_cannot_be_silently_reconnected(harness, reason):
    engine, connection, create = harness
    with locks.market_data_lease(locks.REFRESH_LOCK_KEY) as lease:
        if reason == "changed_pid":
            connection.scalar.side_effect = [99]
        else:
            setattr(connection, reason, True)
        with pytest.raises(locks.MarketDataLockLostError):
            lease.verify()


def test_transaction_pooled_supabase_worker_url_is_rejected_before_connect(harness, monkeypatch):
    from pydantic import PostgresDsn, TypeAdapter
    monkeypatch.setattr(locks.settings, "market_data_worker_database_url", TypeAdapter(PostgresDsn).validate_python(
        "postgresql+psycopg://example:placeholder@aws-0-example.pooler.supabase.com:6543/aura"))
    with pytest.raises(RuntimeError, match="direct or session-pooled"):
        with locks.market_data_lease(locks.WORKER_LOCK_KEY):
            pytest.fail("transaction pooling must not acquire a session lock")
    harness[2].assert_not_called()


def test_cleanup_never_reconnects_an_invalidated_session_to_unlock(harness):
    engine, connection, create = harness
    with locks.market_data_lease(locks.REFRESH_LOCK_KEY):
        connection.invalidated = True
    assert connection.scalar.call_count == 2
    engine.dispose.assert_called_once()
