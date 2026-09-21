"""Read-only deterministic fingerprint of one forecasting database slice."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from datetime import date
from pathlib import Path
import sys

from dotenv import dotenv_values
from sqlalchemy.exc import SQLAlchemyError


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.instruments import USER_ASSET_SYMBOLS
from app.database.connection import (
    create_database_engine,
    create_session_factory,
    session_scope,
)
from app.forecasting.fingerprints import (
    ForecastMarketDataFingerprint,
    build_market_data_fingerprint,
    fingerprint_json,
)
from app.services.market_data_service import MarketDataService


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("date must use YYYY-MM-DD") from error


def database_url_from_env_file(path: Path) -> str:
    if not path.is_file():
        raise ValueError("database environment file does not exist")
    value = dotenv_values(path).get("DATABASE_URL")
    if not isinstance(value, str) or not value:
        raise ValueError("DATABASE_URL is missing from the environment file")
    return value


def fingerprint_persisted_market_data(
    *,
    database_url: str,
    evaluation_cutoff: date,
) -> ForecastMarketDataFingerprint:
    engine = create_database_engine(database_url)
    try:
        factory = create_session_factory(engine)
        with session_scope(factory) as session:
            records = MarketDataService(session).get_range(
                USER_ASSET_SYMBOLS,
                date.min,
                evaluation_cutoff,
            )
        return build_market_data_fingerprint(
            records,
            evaluation_cutoff=evaluation_cutoff,
            symbols=USER_ASSET_SYMBOLS,
        )
    finally:
        engine.dispose()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fingerprint Aura's read-only forecasting market-data slice."
    )
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--evaluation-cutoff", type=_parse_date, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = _build_parser().parse_args(argv)
    try:
        fingerprint = fingerprint_persisted_market_data(
            database_url=database_url_from_env_file(args.env_file),
            evaluation_cutoff=args.evaluation_cutoff,
        )
        args.output.write_text(fingerprint_json(fingerprint), encoding="utf-8")
    except (OSError, SQLAlchemyError, TypeError, ValueError) as error:
        raise SystemExit(f"Forecasting fingerprint failed: {error}") from error
    print("Aura forecasting market-data fingerprint completed.")
    print(f"Evaluation cutoff: {fingerprint.evaluation_cutoff.isoformat()}")
    print(f"Symbols: {len(fingerprint.symbols)}")
    print(f"Rows: {fingerprint.total_row_count}")
    print(f"Output: {args.output}")


if __name__ == "__main__":
    main()
