"""Tracked daily refreshes; no API startup side effects or snapshot mutation."""

from collections.abc import Iterable
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
import logging
import time

import pandas as pd
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import Session

from ..core.config import settings
from ..core.instruments import MARKET_UPDATE_SYMBOLS
from ..data_pipeline.fetcher import DEFAULT_START_DATE
from ..data_pipeline.providers import MarketDataProvider, MarketDataProviderError
from ..data_pipeline.providers.market_provider import _normalize_symbols
from ..data_pipeline.updater import PROCESSED_DATA_PATH, RAW_DATA_PATH, _update_market_data_with_frame
from ..database.repositories.market_data_refresh_repository import MarketDataRefreshRepository
from ..scheduler.market_data_lock import REFRESH_LOCK_KEY, MarketDataLockLostError, MarketDataRefreshBusyError, market_data_lease
from .market_data_service import MAX_LATEST_OBSERVATION_AGE_DAYS, MarketDataService
from .market_data_update_service import PersistedMarketDataUpdateResult

logger = logging.getLogger(__name__)


class MarketDataRefreshError(RuntimeError):
    """Only safe classifications cross the worker/CLI boundary."""
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(f"Market-data refresh failed ({code}).")


def latest_schedule_slot(now: datetime) -> datetime:
    now = now.astimezone(UTC)
    slot = datetime.combine(now.date(), settings.market_data_update_time_utc, UTC)
    return slot if now >= slot else slot - timedelta(days=1)


def observation_is_current(symbol: str, observed: date | None, today: date) -> bool:
    if observed is None or observed >= today:
        return False
    # Crypto trades daily. Other instruments retain the existing four-calendar-
    # day freshness boundary; do not invent prices on holidays/weekends.
    maximum_age = 1 if symbol in {"BTC-USD", "ETH-USD"} else MAX_LATEST_OBSERVATION_AGE_DAYS
    return (today - observed).days <= maximum_age


def _error_code(error: Exception) -> str:
    if isinstance(error, MarketDataLockLostError):
        return "lock_lost"
    if isinstance(error, SQLAlchemyError):
        return "database_unavailable"
    if isinstance(error, (MarketDataProviderError, TimeoutError, ConnectionError)):
        return "provider_unavailable"
    if isinstance(error, (ValueError, TypeError)):
        return "validation_failed"
    return "update_failed"


def _run_market_data_refresh(
    symbols: Iterable[str] | None = None,
    start_date: date | datetime | str = DEFAULT_START_DATE,
    end_date: date | datetime | str | None = None,
    *,
    provider: MarketDataProvider | None = None,
    raw_path: Path = RAW_DATA_PATH,
    processed_path: Path = PROCESSED_DATA_PATH,
    only_if_due: bool = False,
) -> PersistedMarketDataUpdateResult | None:
    """Lock across fetch/retries/write; commit observations and final state together.

    Default automatic coverage ends yesterday UTC, not an unfinished daily bar.
    Explicit historical CLI ranges are supported, but never advance past that
    cutoff. A subset/backfill does not satisfy the full-universe daily schedule.
    """
    selected = tuple(_normalize_symbols(symbols if symbols is not None else MARKET_UPDATE_SYMBOLS))
    now = datetime.now(UTC)
    cutoff = now.date() - timedelta(days=1)
    if end_date is not None:
        requested_end = end_date.date() if isinstance(end_date, datetime) else (
            end_date if isinstance(end_date, date) else date.fromisoformat(end_date))
        cutoff = min(cutoff, requested_end)
    lower = pd.Timestamp(start_date).date()
    if pd.isna(lower) or lower > cutoff:
        raise ValueError("Start date must precede the completed end date")
    slot = latest_schedule_slot(now)
    with market_data_lease(REFRESH_LOCK_KEY) as lease:
        with Session(bind=lease.connection) as session:
            repository = MarketDataRefreshRepository(session)
            state = repository.get()
            if only_if_due and state and state.status == "success" and state.last_complete_slot and state.last_complete_slot >= slot:
                dates = repository.latest_dates(MARKET_UPDATE_SYMBOLS)
                if all(observation_is_current(symbol, dates.get(symbol), now.date()) for symbol in MARKET_UPDATE_SYMBOLS):
                    return None
            repository.save(status="running", last_attempt_at=now, last_finished_at=None,
                attempt_count=0, stored_count=0, updated_symbols=[], failed_symbols=[], error_code=None)
            session.commit()

        last_result = None
        for attempt in range(1, settings.market_data_refresh_max_attempts + 1):
            try:
                lease.verify()
                with Session(bind=lease.connection) as session:
                    MarketDataRefreshRepository(session).save(status="running", last_finished_at=None, attempt_count=attempt)
                    session.commit()
                result, data = _update_market_data_with_frame(symbols=selected,
                    start_date=start_date, end_date=cutoff, provider=provider,
                    raw_path=raw_path, processed_path=processed_path)
                dates = pd.to_datetime(data["date"]).dt.date
                if (dates < lower).any() or (dates > cutoff).any():
                    raise ValueError("Provider observations fall outside the completed requested range")
                actual_symbols = set(data["symbol"])
                if not actual_symbols.issubset(selected) or actual_symbols != set(result.symbols):
                    raise ValueError("Provider observations do not match the requested symbols")
                lease.verify()  # Never silently reconnect and write after losing the lock.
                with Session(bind=lease.connection) as session:
                    stored_count = MarketDataService(session).store(data)
                    repository = MarketDataRefreshRepository(session)
                    latest = repository.latest_dates(selected)
                    missing = set(selected) - set(result.symbols)
                    failed = set(result.failed_symbols) | missing
                    # Historical backfills are valid but don't claim daily freshness.
                    if cutoff == now.date() - timedelta(days=1):
                        failed.update(symbol for symbol in selected
                            if not observation_is_current(symbol, latest.get(symbol), now.date()))
                    failed_symbols = [symbol for symbol in selected if symbol in failed]
                    full_complete = (set(selected) == set(MARKET_UPDATE_SYMBOLS) and not failed_symbols
                        and cutoff == now.date() - timedelta(days=1))
                    values = dict(status="partial" if failed_symbols else "success",
                        last_finished_at=datetime.now(UTC), stored_count=stored_count,
                        updated_symbols=list(result.symbols), failed_symbols=failed_symbols,
                        error_code="incomplete_coverage" if failed_symbols else None)
                    if full_complete:
                        values.update(last_complete_at=datetime.now(UTC), last_complete_slot=slot)
                    repository.save(**values)
                    session.commit()
                summary = result if result.failed_symbols == tuple(failed_symbols) else replace(result, failed_symbols=tuple(failed_symbols))
                last_result = PersistedMarketDataUpdateResult(summary, stored_count)
                if failed_symbols:
                    logger.warning("Market-data refresh partial; attempt=%d failed_symbols=%s", attempt, ",".join(failed_symbols))
                if not failed_symbols or attempt == settings.market_data_refresh_max_attempts:
                    return last_result
            except Exception as error:
                code = _error_code(error)
                # Retry only transient failures while the original lock is held.
                retryable = isinstance(error, (MarketDataProviderError, TimeoutError, ConnectionError, OperationalError))
                if isinstance(error, MarketDataLockLostError) or lease.connection.invalidated or lease.connection.closed:
                    raise MarketDataRefreshError("lock_lost") from None
                try:
                    lease.connection.rollback()
                    lease.verify()
                    with Session(bind=lease.connection) as session:
                        MarketDataRefreshRepository(session).save(status="partial" if last_result else "failed",
                            last_finished_at=datetime.now(UTC), error_code=code)
                        session.commit()
                except Exception:
                    raise MarketDataRefreshError("database_unavailable") from None
                logger.error("Market-data refresh attempt failed; attempt=%d code=%s", attempt, code)
                if not retryable or attempt == settings.market_data_refresh_max_attempts:
                    raise MarketDataRefreshError(code) from None
            time.sleep(min(settings.market_data_refresh_retry_seconds * 2 ** (attempt - 1), 60))
        return last_result


def run_market_data_refresh(
    symbols: Iterable[str] | None = None,
    start_date: date | datetime | str = DEFAULT_START_DATE,
    end_date: date | datetime | str | None = None,
    *,
    provider: MarketDataProvider | None = None,
    raw_path: Path = RAW_DATA_PATH,
    processed_path: Path = PROCESSED_DATA_PATH,
    only_if_due: bool = False,
) -> PersistedMarketDataUpdateResult | None:
    """Sanitize initialization/connection failures as well as run failures."""
    try:
        return _run_market_data_refresh(symbols=symbols, start_date=start_date, end_date=end_date,
            provider=provider, raw_path=raw_path, processed_path=processed_path, only_if_due=only_if_due)
    except (MarketDataRefreshBusyError, MarketDataRefreshError):
        raise
    except Exception as error:
        raise MarketDataRefreshError(_error_code(error)) from None
