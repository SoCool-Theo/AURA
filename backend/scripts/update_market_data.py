"""Manual command for refreshing Aura's historical market-data files."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.data_pipeline.fetcher import DEFAULT_START_DATE, DEFAULT_SYMBOLS
from app.data_pipeline.updater import update_market_data


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fetch and prepare Aura historical market data."
    )
    parser.add_argument(
        "--symbols",
        nargs="+",
        default=None,
        help=(
            "Symbols to update, separated by spaces. Defaults to Aura's "
            "standard historical symbol set."
        ),
    )
    parser.add_argument(
        "--start-date",
        default=DEFAULT_START_DATE,
        help="Inclusive start date in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--end-date",
        default=None,
        help="Inclusive end date in YYYY-MM-DD format. Defaults to today.",
    )
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    symbols = args.symbols if args.symbols is not None else DEFAULT_SYMBOLS

    try:
        result = update_market_data(
            symbols=symbols,
            start_date=args.start_date,
            end_date=args.end_date,
        )
    except (TypeError, ValueError, RuntimeError) as error:
        raise SystemExit(f"Aura market-data update failed: {error}") from error

    print("Aura market-data update completed.")
    print("----------------------------------")
    print(f"Raw file:       {result.raw_path}")
    print(f"Processed file: {result.processed_path}")
    print(f"Rows:           {result.row_count:,}")
    print(f"Symbols:        {', '.join(result.symbols)}")
    print(
        "Requested range: "
        f"{result.requested_start_date} to {result.requested_end_date}"
    )
    print(
        "Actual range:    "
        f"{result.actual_start_date} to {result.actual_end_date}"
    )
    if result.failed_symbols:
        print(f"Failed symbols: {', '.join(result.failed_symbols)}")


if __name__ == "__main__":
    main()
