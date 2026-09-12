"""Production scheduled execution wrapper for market-data updates."""

from __future__ import annotations

import logging

from ..core.instruments import MARKET_UPDATE_SYMBOLS
from ..services.market_data_update_service import update_market_data_and_persist


logger = logging.getLogger(__name__)


def run_scheduled_market_data_update() -> None:
    """Run, log, and propagate one scheduled market-data update."""
    logger.info("Scheduled market-data update starting.")
    try:
        persisted_result = update_market_data_and_persist(
            symbols=MARKET_UPDATE_SYMBOLS
        )
    except Exception:
        logger.exception("Scheduled market-data update failed.")
        raise

    update_result = persisted_result.update_result
    logger.info(
        "Scheduled market-data update succeeded: processed_rows=%d, "
        "stored_rows=%d, symbols=%s, requested_range=%s to %s, "
        "actual_range=%s to %s.",
        update_result.row_count,
        persisted_result.stored_count,
        ", ".join(update_result.symbols),
        update_result.requested_start_date,
        update_result.requested_end_date,
        update_result.actual_start_date,
        update_result.actual_end_date,
    )
    if update_result.failed_symbols:
        logger.warning(
            "Scheduled market-data update completed with provider failures: %s.",
            ", ".join(update_result.failed_symbols),
        )
