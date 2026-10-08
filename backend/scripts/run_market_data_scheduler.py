"""Standalone production process for Aura's daily market-data scheduler."""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from pathlib import Path
import sys
import signal

from apscheduler.events import EVENT_JOB_ERROR


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings
from app.core.logging import configure_logging
from app.scheduler.market_data_job import catch_up_market_data, run_scheduled_market_data_update
from app.scheduler.market_data_scheduler import create_market_data_scheduler
from app.scheduler.market_data_lock import WORKER_LOCK_KEY, market_data_lease
from app.scheduler.market_data_worker import MarketDataWorker
from app.services.market_data_refresh_service import MarketDataRefreshError


logger = logging.getLogger(__name__)


def _run_worker(lease) -> None:
    """Configure and run the standalone scheduler until process interruption."""
    worker = MarketDataWorker(lease)
    worker.heartbeat()
    scheduled_time = settings.market_data_update_time_utc
    scheduler = create_market_data_scheduler(run_scheduled_market_data_update,
        heartbeat_callable=worker.heartbeat, catch_up_callable=catch_up_market_data)
    heartbeat_failed = False

    def stop_on_heartbeat_failure(event) -> None:
        nonlocal heartbeat_failed
        if event.job_id == "market-data-worker-heartbeat":
            heartbeat_failed = True
            logger.error("Worker lease/heartbeat unavailable; stopping for supervisor restart.")
            scheduler.shutdown(wait=False)

    scheduler.add_listener(stop_on_heartbeat_failure, EVENT_JOB_ERROR)

    logger.info(
        "Starting Aura market-data scheduler with daily schedule %s UTC.",
        scheduled_time.strftime("%H:%M"),
    )
    jobs = scheduler.get_jobs()
    if jobs:
        next_execution = jobs[0].trigger.get_next_fire_time(
            None,
            datetime.now(timezone.utc),
        )
        if next_execution is not None:
            logger.info(
                "Next scheduled market-data update: %s.",
                next_execution.isoformat(),
            )

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Market-data scheduler interruption received; stopping.")
    finally:
        if scheduler.running:
            scheduler.shutdown(wait=True)
        try:
            worker.stop()
        except Exception:
            logger.error("Unable to record worker stop; heartbeat will expire.")
        logger.info("Aura market-data scheduler stopped.")
    if heartbeat_failed:
        raise MarketDataRefreshError("database_unavailable")


def main() -> None:
    """Explicit deployment entry point; importing the API never starts a worker."""
    configure_logging()
    previous_handler = signal.getsignal(signal.SIGTERM)

    def terminate(signum, frame) -> None:
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, terminate)
    try:
        with market_data_lease(WORKER_LOCK_KEY) as lease:
            _run_worker(lease)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Market-data worker interrupted.")
    except MarketDataRefreshError:
        raise
    except Exception:
        raise MarketDataRefreshError("update_failed") from None
    finally:
        signal.signal(signal.SIGTERM, previous_handler)


if __name__ == "__main__":
    main()
