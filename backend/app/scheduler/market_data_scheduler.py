"""Construction of Aura's stopped daily market-data scheduler."""

from __future__ import annotations

from collections.abc import Callable
from datetime import time
from typing import Any

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from ..core.config import settings


MARKET_DATA_JOB_ID = "market-data-daily-update"


def create_market_data_scheduler(
    job_callable: Callable[[], Any],
    *,
    update_time: time | None = None,
) -> BlockingScheduler:
    """Return a stopped scheduler containing one daily UTC update job."""
    scheduled_time = update_time or settings.market_data_update_time_utc
    scheduler = BlockingScheduler(timezone="UTC")
    trigger = CronTrigger(
        hour=scheduled_time.hour,
        minute=scheduled_time.minute,
        timezone="UTC",
    )
    scheduler.add_job(
        job_callable,
        trigger=trigger,
        id=MARKET_DATA_JOB_ID,
        coalesce=True,
        max_instances=1,
        misfire_grace_time=None,
    )
    return scheduler
