from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from backend.app.core.config import Settings
from backend.app.core.instruments import MARKET_UPDATE_SYMBOLS
import backend.app.services.market_data_status_service as service

NOW = datetime(2026, 10, 6, 10, tzinfo=UTC)


def status(monkeypatch, *, state=None, dates=None):
    repository = Mock()
    repository.get.return_value = state
    repository.latest_dates.return_value = dates or {}
    monkeypatch.setattr(service, "MarketDataRefreshRepository", Mock(return_value=repository))
    response = service.MarketDataStatusService(Mock()).get(now=NOW)
    repository.save.assert_not_called()
    return response


def state(**changes):
    return SimpleNamespace(**{**dict(status="success", last_attempt_at=NOW - timedelta(hours=1),
        last_finished_at=NOW - timedelta(minutes=50), last_complete_at=NOW - timedelta(minutes=50),
        attempt_count=1, stored_count=18, updated_symbols=list(MARKET_UPDATE_SYMBOLS), failed_symbols=[],
        error_code=None, worker_running=True, worker_heartbeat_at=NOW - timedelta(seconds=60)), **changes})


def test_unconfigured_worker_and_missing_observations_are_truthful_without_writes(monkeypatch):
    result = status(monkeypatch)
    assert result.worker_status == "unknown"
    assert result.last_run_status == "never"
    assert result.data_status == "missing"
    assert len(result.observations) == 18
    assert all(item.latest_price_date is None for item in result.observations)
    assert result.observations[-1].symbol == "THB=X"
    assert result.observations[-1].kind == "fx"
    assert result.next_scheduled_at == datetime(2026, 10, 7, 2, tzinfo=UTC)


@pytest.mark.parametrize("changes, expected", [({}, "online"),
    ({"worker_heartbeat_at": NOW - timedelta(seconds=181)}, "offline"),
    ({"worker_heartbeat_at": NOW + timedelta(seconds=1)}, "offline"),
    ({"worker_running": False}, "offline"), ({"worker_heartbeat_at": None}, "unknown")])
def test_liveness_is_independent_from_last_success(monkeypatch, changes, expected):
    result = status(monkeypatch, state=state(**changes), dates=dict.fromkeys(MARKET_UPDATE_SYMBOLS, date(2026, 10, 5)))
    assert result.worker_status == expected
    assert result.data_status == "current"
    assert result.last_run_status == "success"


def test_successful_fetch_can_still_have_stale_observations(monkeypatch):
    result = status(monkeypatch, state=state(), dates=dict.fromkeys(MARKET_UPDATE_SYMBOLS, date(2026, 10, 1)))
    assert result.last_run_status == "success"
    assert result.data_status == "stale"
    assert all(item.age_days == 5 for item in result.observations)


def test_missing_or_future_observation_cannot_claim_current(monkeypatch):
    dates = dict.fromkeys(MARKET_UPDATE_SYMBOLS, date(2026, 10, 5))
    dates["AAPL"] = date(2099, 1, 1)
    result = status(monkeypatch, dates=dates)
    assert result.data_status == "stale"
    assert result.observations[0].age_days is None
    del dates["AAPL"]
    assert status(monkeypatch, dates=dates).data_status == "missing"


@pytest.mark.parametrize("field, value", [("market_data_refresh_max_attempts", 0),
    ("market_data_refresh_max_attempts", 6), ("market_data_refresh_retry_seconds", 0),
    ("market_data_refresh_retry_seconds", 61), ("market_data_worker_database_url", "postgresql://localhost/aura")])
def test_refresh_configuration_is_bounded_and_validated(field, value):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **{field: value})


def test_invalid_worker_configuration_does_not_log_connection_secrets():
    with pytest.raises(ValidationError) as raised:
        Settings(_env_file=None, market_data_worker_database_url="postgresql://example:private-password@example.invalid/aura")
    assert "private-password" not in str(raised.value)
    assert "example.invalid" not in str(raised.value)
