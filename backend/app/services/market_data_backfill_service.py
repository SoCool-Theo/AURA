"""Historical market-data backfill orchestration."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy.orm import Session

from ..data_pipeline.backfill import (
    HistoricalSymbolCoverage,
    audit_historical_coverage,
)
from ..data_pipeline.cleaner import clean_market_data
from ..data_pipeline.fetcher import fetch_historical_prices
from ..data_pipeline.providers import MarketDataProvider
from ..data_pipeline.validator import raise_if_invalid
from .market_data_service import MarketDataService


@dataclass(frozen=True, slots=True)
class MarketDataBackfillResult:
    """Deterministic summary of one successfully stored backfill."""

    requested_symbols: tuple[str, ...]
    requested_start_date: date
    requested_end_date: date
    row_count: int
    stored_count: int
    coverage: tuple[HistoricalSymbolCoverage, ...]


class MarketDataBackfillService:
    """Coordinate a fully audited backfill in a caller-owned transaction."""

    def __init__(self, session: Session) -> None:
        self._market_data_service = MarketDataService(session)

    def run(
        self,
        symbols: Iterable[str],
        start_date: date | datetime | str,
        end_date: date | datetime | str,
        *,
        provider: MarketDataProvider | None = None,
    ) -> MarketDataBackfillResult:
        """Fetch, prepare, audit, and store one complete historical range."""
        requested_symbols = tuple(symbols)
        raw_data = fetch_historical_prices(
            symbols=requested_symbols,
            start_date=start_date,
            end_date=end_date,
            provider=provider,
        )
        failed_symbols = tuple(raw_data.attrs.get("failed_symbols", ()))

        clean_data = clean_market_data(raw_data)
        raise_if_invalid(clean_data)
        audit = audit_historical_coverage(
            requested_symbols,
            start_date,
            end_date,
            clean_data,
            failed_symbols=failed_symbols,
        )

        stored_count = self._market_data_service.store(clean_data)
        return MarketDataBackfillResult(
            requested_symbols=tuple(
                item.symbol for item in audit.coverage
            ),
            requested_start_date=audit.requested_start_date,
            requested_end_date=audit.requested_end_date,
            row_count=int(len(clean_data)),
            stored_count=stored_count,
            coverage=audit.coverage,
        )
