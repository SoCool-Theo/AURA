"""Standalone production process for Aura's daily market-data scheduler."""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from pathlib import Path
import sys


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings
from app.core.logging import configure_logging
from app.scheduler.market_data_job import run_scheduled_market_data_update
from app.scheduler.market_data_scheduler import create_market_data_scheduler


logger = logging.getLogger(__name__)


def main() -> None:
    """Configure and run the standalone scheduler until process interruption."""
    configure_logging()
    scheduled_time = settings.market_data_update_time_utc
    scheduler = create_market_data_scheduler(run_scheduled_market_data_update)

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
        logger.info("Aura market-data scheduler stopped.")


if __name__ == "__main__":
    main()
