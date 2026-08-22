"""One-shot market-data update and PostgreSQL persistence orchestration."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from ..data_pipeline.fetcher import DEFAULT_START_DATE
from ..data_pipeline.providers import MarketDataProvider
from ..data_pipeline.updater import (
    PROCESSED_DATA_PATH,
    RAW_DATA_PATH,
    MarketDataUpdateResult,
    _update_market_data_with_frame,
)
from ..database.connection import (
    create_database_engine,
    create_session_factory,
    session_scope,
)
from .market_data_service import MarketDataService


@dataclass(frozen=True, slots=True)
class PersistedMarketDataUpdateResult:
    """Summary of one successfully persisted market-data update."""

    update_result: MarketDataUpdateResult
    stored_count: int


def update_market_data_and_persist(
    symbols: Iterable[str] | None = None,
    start_date: date | datetime | str = DEFAULT_START_DATE,
    end_date: date | datetime | str | None = None,
    *,
    provider: MarketDataProvider | None = None,
    raw_path: Path = RAW_DATA_PATH,
    processed_path: Path = PROCESSED_DATA_PATH,
) -> PersistedMarketDataUpdateResult:
    """Run one complete update and commit its canonical rows to PostgreSQL."""
    update_result, data = _update_market_data_with_frame(
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        provider=provider,
        raw_path=raw_path,
        processed_path=processed_path,
    )

    engine = create_database_engine()
    try:
        session_factory = create_session_factory(engine)
        with session_scope(session_factory) as session:
            stored_count = MarketDataService(session).store(data)
            session.commit()
    finally:
        engine.dispose()

    return PersistedMarketDataUpdateResult(
        update_result=update_result,
        stored_count=stored_count,
    )
