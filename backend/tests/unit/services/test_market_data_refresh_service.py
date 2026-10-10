"""Deterministic reliability tests: never contact providers or production DBs."""

from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

import pandas as pd
import pytest
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from backend.app.data_pipeline.providers import MarketDataProviderError
from backend.app.data_pipeline.updater import MarketDataUpdateResult
from backend.app.scheduler.market_data_lock import MarketDataLockLostError, MarketDataRefreshBusyError
import backend.app.services.market_data_refresh_service as service

NOW = datetime(2026, 10, 6, 10, tzinfo=UTC)
CUTOFF = date(2026, 10, 5)


class Clock(datetime):
    @classmethod
    def now(cls, tz=None):
        return NOW


@pytest.fixture
def harness(monkeypatch, tmp_path):
    monkeypatch.setattr(service, "datetime", Clock)
    monkeypatch.setattr(service.settings, "market_data_refresh_max_attempts", 3)
    monkeypatch.setattr(service.settings, "market_data_refresh_retry_seconds", 10)
    connection = MagicMock(closed=False, invalidated=False)
    lease = SimpleNamespace(connection=connection, verify=Mock())
    lease_context = MagicMock()
    lease_context.__enter__.return_value = lease
    monkeypatch.setattr(service, "market_data_lease", Mock(return_value=lease_context))
    session = MagicMock(spec=Session)
    session.__enter__.return_value = session
    monkeypatch.setattr(service, "Session", Mock(return_value=session))
    repository = Mock()
    repository.get.return_value = None
    repository.latest_dates.return_value = dict.fromkeys(service.MARKET_UPDATE_SYMBOLS, CUTOFF)
    monkeypatch.setattr(service, "MarketDataRefreshRepository", Mock(return_value=repository))
    storage = Mock()
    storage.store.return_value = 18
    monkeypatch.setattr(service, "MarketDataService", Mock(return_value=storage))
    result = MarketDataUpdateResult(tmp_path / "raw.csv", tmp_path / "clean.csv", 18,
        service.MARKET_UPDATE_SYMBOLS, (), "2010-01-01", CUTOFF.isoformat(), CUTOFF.isoformat(), CUTOFF.isoformat())
    frame = pd.DataFrame({"symbol": list(service.MARKET_UPDATE_SYMBOLS), "date": [CUTOFF] * 18})
    pipeline = Mock(return_value=(result, frame))
    monkeypatch.setattr(service, "_update_market_data_with_frame", pipeline)
    sleep = Mock()
    monkeypatch.setattr(service.time, "sleep", sleep)
    return SimpleNamespace(lease=lease, session=session, repository=repository, storage=storage,
        result=result, frame=frame, pipeline=pipeline, sleep=sleep)


def test_full_update_uses_completed_utc_day_and_commits_status_with_prices(harness):
    result = service.run_market_data_refresh()
    assert result.stored_count == 18
    assert result.update_result is harness.result
    assert harness.pipeline.call_args.kwargs["end_date"] == CUTOFF
    harness.storage.store.assert_called_once_with(harness.frame)
    final = harness.repository.save.call_args.kwargs
    assert final["status"] == "success"
    assert final["last_complete_slot"] == datetime(2026, 10, 6, 2, tzinfo=UTC)
    assert final["last_complete_at"] == NOW
    assert final["failed_symbols"] == []
    assert harness.session.commit.call_count == 3  # start, attempt, prices+final state
    harness.sleep.assert_not_called()
    assert harness.lease.verify.call_count == 2


def test_completed_slot_skips_catchup_only_when_coverage_is_current(harness):
    harness.repository.get.return_value = SimpleNamespace(status="success", last_complete_slot=service.latest_schedule_slot(NOW))
    assert service.run_market_data_refresh(only_if_due=True) is None
    harness.pipeline.assert_not_called()
    harness.repository.save.assert_not_called()
    harness.repository.latest_dates.return_value = {}
    service.run_market_data_refresh(only_if_due=True)
    assert harness.pipeline.call_count == 3
    assert harness.repository.save.call_args.kwargs["status"] == "partial"


def test_restart_after_missed_days_runs_once_not_every_missed_slot(harness):
    harness.repository.get.return_value = SimpleNamespace(status="success", last_complete_slot=NOW - timedelta(days=8))
    service.run_market_data_refresh(only_if_due=True)
    harness.pipeline.assert_called_once()


@pytest.mark.parametrize("failure", [MarketDataProviderError("private provider details"), TimeoutError("private URL"),
    OperationalError("private SQL", {}, Exception("private password"))])
def test_transient_failure_retries_with_bounded_backoff_then_recovers(harness, failure):
    harness.pipeline.side_effect = [failure, failure, (harness.result, harness.frame)]
    service.run_market_data_refresh()
    assert harness.pipeline.call_count == 3
    assert [call.args for call in harness.sleep.call_args_list] == [(10,), (20,)]
    assert harness.repository.save.call_args.kwargs["status"] == "success"


@pytest.mark.parametrize("failure, attempts, code", [
    (MarketDataProviderError("password=private"), 3, "provider_unavailable"),
    (ValueError("private invalid input"), 1, "validation_failed"),
    (RuntimeError("private implementation detail"), 1, "update_failed"),
])
def test_failure_is_sanitized_bounded_and_does_not_overwrite_last_complete(harness, failure, attempts, code, caplog):
    harness.pipeline.side_effect = failure
    with pytest.raises(service.MarketDataRefreshError, match=code) as raised:
        service.run_market_data_refresh()
    assert "private" not in str(raised.value)
    assert "private" not in caplog.text
    assert harness.pipeline.call_count == attempts
    harness.storage.store.assert_not_called()
    final = harness.repository.save.call_args.kwargs
    assert final["status"] == "failed"
    assert "last_complete_at" not in final
    assert "last_complete_slot" not in final


def test_partial_fetch_preserves_existing_data_retries_and_never_claims_complete(harness):
    from dataclasses import replace
    result = replace(harness.result, symbols=("AAPL",), failed_symbols=("MSFT",))
    frame = harness.frame.iloc[:1]
    harness.pipeline.return_value = result, frame
    service.run_market_data_refresh()
    assert harness.storage.store.call_count == 3
    assert all(call.args[0] is frame for call in harness.storage.store.call_args_list)
    final = harness.repository.save.call_args.kwargs
    assert final["status"] == "partial"
    assert "MSFT" in final["failed_symbols"]
    assert "last_complete_slot" not in final
    assert "last_complete_at" not in final


def test_successful_subset_or_historical_backfill_does_not_satisfy_daily_schedule(harness):
    from dataclasses import replace
    harness.pipeline.return_value = replace(harness.result, symbols=("AAPL",)), harness.frame.iloc[:1]
    service.run_market_data_refresh(symbols=[" aapl "], end_date="2026-10-05")
    assert harness.pipeline.call_args.kwargs["symbols"] == ("AAPL",)
    assert harness.repository.save.call_args.kwargs["status"] == "success"
    assert "last_complete_slot" not in harness.repository.save.call_args.kwargs
    historical = harness.frame.copy()
    historical["date"] = date(2026, 10, 1)
    harness.pipeline.return_value = harness.result, historical
    service.run_market_data_refresh(end_date="2026-10-01")
    assert harness.repository.save.call_args.kwargs["status"] == "success"
    assert "last_complete_slot" not in harness.repository.save.call_args.kwargs


def test_provider_future_or_out_of_range_observations_are_never_stored(harness):
    harness.frame.loc[0, "date"] = NOW.date()
    with pytest.raises(service.MarketDataRefreshError, match="validation_failed"):
        service.run_market_data_refresh()
    harness.storage.store.assert_not_called()
    harness.sleep.assert_not_called()


def test_provider_unrequested_symbol_is_never_stored(harness):
    harness.frame.loc[0, "symbol"] = "UNREQUESTED"
    with pytest.raises(service.MarketDataRefreshError, match="validation_failed"):
        service.run_market_data_refresh()
    harness.storage.store.assert_not_called()


def test_lost_lock_never_reconnects_to_store_or_write_status(harness):
    harness.lease.verify.side_effect = [None, MarketDataLockLostError()]
    with pytest.raises(service.MarketDataRefreshError, match="lock_lost"):
        service.run_market_data_refresh()
    harness.storage.store.assert_not_called()
    assert harness.repository.save.call_count == 2


def test_duplicate_process_does_not_fetch_or_change_operational_state(harness, monkeypatch):
    monkeypatch.setattr(service, "market_data_lease", Mock(side_effect=MarketDataRefreshBusyError()))
    with pytest.raises(MarketDataRefreshBusyError):
        service.run_market_data_refresh()
    harness.pipeline.assert_not_called()
    harness.repository.save.assert_not_called()


def test_database_initialization_errors_never_expose_credentials(harness, monkeypatch):
    monkeypatch.setattr(service, "market_data_lease", Mock(side_effect=OperationalError("postgresql://private", {}, Exception("secret"))))
    with pytest.raises(service.MarketDataRefreshError, match="database_unavailable") as raised:
        service.run_market_data_refresh()
    assert "private" not in str(raised.value)
    harness.pipeline.assert_not_called()


def test_partial_or_failed_latest_run_retries_even_with_prior_completed_slot(harness):
    harness.repository.get.return_value = SimpleNamespace(status="partial", last_complete_slot=service.latest_schedule_slot(NOW))
    service.run_market_data_refresh(only_if_due=True)
    harness.pipeline.assert_called_once()


def test_invalid_requested_dates_do_not_fetch_or_replace_last_status(harness):
    with pytest.raises(service.MarketDataRefreshError, match="validation_failed"):
        service.run_market_data_refresh(start_date="2099-01-01")
    harness.pipeline.assert_not_called()
    harness.repository.save.assert_not_called()


@pytest.mark.parametrize("hour, expected_day", [(1, 5), (2, 6), (23, 6)])
def test_schedule_slot_uses_utc_and_handles_before_schedule(hour, expected_day):
    assert service.latest_schedule_slot(NOW.replace(hour=hour)) == datetime(2026, 10, expected_day, 2, tzinfo=UTC)


@pytest.mark.parametrize("symbol, observed, current", [("AAPL", date(2026, 10, 2), True),
    ("AAPL", date(2026, 10, 1), False), ("BTC-USD", date(2026, 10, 4), False),
    ("ETH-USD", CUTOFF, True), ("THB=X", CUTOFF, True), ("AAPL", NOW.date(), False), ("AAPL", None, False)])
def test_freshness_handles_weekends_crypto_and_missing_or_unfinished_dates(symbol, observed, current):
    assert service.observation_is_current(symbol, observed, NOW.date()) is current
