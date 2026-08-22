from datetime import time
from pathlib import Path
from unittest.mock import Mock

import pytest
from apscheduler.schedulers.base import STATE_STOPPED
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from pydantic import ValidationError

from backend.app.core.config import Settings
import backend.app.scheduler.market_data_scheduler as scheduler_module
from backend.app.scheduler.market_data_scheduler import (
    MARKET_DATA_JOB_ID,
    create_market_data_scheduler,
)


def test_default_market_data_update_time_is_approved_utc_time(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("MARKET_DATA_UPDATE_TIME_UTC", raising=False)

    configured = Settings(_env_file=None)

    assert configured.market_data_update_time_utc == time(hour=2)


@pytest.mark.parametrize(
    ("configured_value", "expected"),
    [
        ("00:00", time(hour=0, minute=0)),
        ("02:00", time(hour=2, minute=0)),
        ("23:59", time(hour=23, minute=59)),
    ],
)
def test_valid_strict_daily_times_are_accepted(
    configured_value: str,
    expected: time,
) -> None:
    configured = Settings(
        _env_file=None,
        market_data_update_time_utc=configured_value,
    )

    assert configured.market_data_update_time_utc == expected


@pytest.mark.parametrize(
    "configured_value",
    ["24:00", "02:60", "2:00", "2am", "hello", "02:00:00"],
)
def test_invalid_daily_times_are_rejected(configured_value: str) -> None:
    with pytest.raises(
        ValidationError,
        match="MARKET_DATA_UPDATE_TIME_UTC must use strict HH:MM format",
    ):
        Settings(
            _env_file=None,
            market_data_update_time_utc=configured_value,
        )


def test_scheduler_registers_one_daily_utc_job_without_starting_or_running() -> None:
    job_callable = Mock()

    scheduler = create_market_data_scheduler(
        job_callable,
        update_time=time(hour=5, minute=45),
    )

    assert isinstance(scheduler, BlockingScheduler)
    assert str(scheduler.timezone) == "UTC"
    assert scheduler.state == STATE_STOPPED
    jobs = scheduler.get_jobs()
    assert len(jobs) == 1
    job = jobs[0]
    assert job.id == MARKET_DATA_JOB_ID
    assert job.func is job_callable
    assert job.coalesce is True
    assert job.max_instances == 1
    assert job.misfire_grace_time is None
    assert isinstance(job.trigger, CronTrigger)
    trigger_fields = dict(zip(job.trigger.FIELD_NAMES, job.trigger.fields))
    assert str(trigger_fields["hour"]) == "5"
    assert str(trigger_fields["minute"]) == "45"
    assert str(trigger_fields["second"]) == "0"
    assert str(job.trigger.timezone) == "UTC"
    job_callable.assert_not_called()


def test_scheduler_core_has_no_runner_retry_or_persistent_job_store() -> None:
    source = Path(scheduler_module.__file__).read_text(encoding="utf-8").lower()

    assert ".start(" not in source
    assert "retry" not in source
    assert "sleep" not in source
    assert "jobstore" not in source
    assert "update_market_data_and_persist" not in source
