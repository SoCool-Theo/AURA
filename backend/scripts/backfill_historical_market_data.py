"""Manual command for audited historical market-data backfills."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from datetime import date, datetime
from pathlib import Path
import sys

from sqlalchemy.exc import SQLAlchemyError


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.data_pipeline.fetcher import DEFAULT_SYMBOLS
from app.data_pipeline.providers.market_provider import _coerce_date
from app.database.connection import (
    create_database_engine,
    create_session_factory,
    session_scope,
)
from app.services.market_data_backfill_service import (
    MarketDataBackfillResult,
    MarketDataBackfillService,
)


DEFAULT_BACKFILL_START_DATE = "2000-01-01"


def _resolve_date_range(
    start_date: date | datetime | str,
    end_date: date | datetime | str | None,
) -> tuple[date, date]:
    requested_start = _coerce_date(start_date, "start_date")
    requested_end = _coerce_date(
        end_date if end_date is not None else date.today(),
        "end_date",
    )
    if requested_start > requested_end:
        raise ValueError("start_date must be on or before end_date")
    return requested_start, requested_end


def backfill_historical_market_data(
    symbols: Sequence[str] | None = None,
    start_date: date | datetime | str = DEFAULT_BACKFILL_START_DATE,
    end_date: date | datetime | str | None = None,
) -> MarketDataBackfillResult:
    """Run one audited backfill and commit at the caller boundary."""
    requested_start, requested_end = _resolve_date_range(
        start_date,
        end_date,
    )
    requested_symbols = symbols if symbols is not None else DEFAULT_SYMBOLS

    engine = create_database_engine()
    try:
        session_factory = create_session_factory(engine)
        with session_scope(session_factory) as session:
            result = MarketDataBackfillService(session).run(
                requested_symbols,
                requested_start,
                requested_end,
            )
            session.commit()
        return result
    finally:
        engine.dispose()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Backfill audited Aura historical market data into PostgreSQL."
        )
    )
    parser.add_argument(
        "--symbols",
        nargs="+",
        default=None,
        help=(
            "Symbols to backfill, separated by spaces. Defaults to Aura's "
            "standard historical symbol set."
        ),
    )
    parser.add_argument(
        "--start-date",
        default=DEFAULT_BACKFILL_START_DATE,
        help="Inclusive start date in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--end-date",
        default=None,
        help="Inclusive end date in YYYY-MM-DD format. Defaults to today.",
    )
    return parser


def _observation_text(value: date | None) -> str:
    return "unavailable" if value is None else value.isoformat()


def _print_result(result: MarketDataBackfillResult) -> None:
    print("Aura historical market-data backfill completed.")
    print("------------------------------------------------")
    print(
        "Requested range: "
        f"{result.requested_start_date} to {result.requested_end_date}"
    )
    print(f"Symbols:         {', '.join(result.requested_symbols)}")
    print(f"Rows processed:  {result.row_count:,}")
    print(f"Rows stored:     {result.stored_count:,}")
    print("Per-symbol coverage:")
    for item in result.coverage:
        print(f"  {item.symbol}")
        print(f"    rows: {item.row_count:,}")
        print(
            "    earliest available observation: "
            f"{_observation_text(item.earliest_date)}"
        )
        print(
            "    latest available observation: "
            f"{_observation_text(item.latest_date)}"
        )


def main(argv: Sequence[str] | None = None) -> None:
    args = _build_parser().parse_args(argv)

    try:
        result = backfill_historical_market_data(
            symbols=args.symbols,
            start_date=args.start_date,
            end_date=args.end_date,
        )
    except (SQLAlchemyError, TypeError, ValueError, RuntimeError) as error:
        raise SystemExit(
            f"Aura historical market-data backfill failed: {error}"
        ) from error

    _print_result(result)


if __name__ == "__main__":
    main()
