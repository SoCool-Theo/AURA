"""Manual command for seeding processed historical market data."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path
import sys

import pandas as pd
from sqlalchemy.exc import SQLAlchemyError


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.data_pipeline.validator import raise_if_invalid
from app.database.connection import (
    create_database_engine,
    create_session_factory,
    session_scope,
)
from app.services.market_data_service import MarketDataService


PROJECT_ROOT = BACKEND_DIR.parent
PROCESSED_DATA_PATH = (
    PROJECT_ROOT / "data" / "processed" / "market_prices_clean.csv"
)


def _load_processed_market_data(input_path: Path) -> pd.DataFrame:
    """Load a processed CSV and restore its canonical pandas representation."""
    if not input_path.is_file():
        raise FileNotFoundError(
            f"Processed market-data CSV not found: {input_path}"
        )

    data = pd.read_csv(
        input_path,
        dtype={"symbol": "string", "source": "string"},
        keep_default_na=False,
    )

    if "date" in data.columns:
        data["date"] = pd.to_datetime(
            data["date"],
            errors="coerce",
        ).dt.normalize()
    if "symbol" in data.columns:
        data["symbol"] = data["symbol"].astype("string")
    if "adjusted_close" in data.columns:
        data["adjusted_close"] = pd.to_numeric(
            data["adjusted_close"],
            errors="coerce",
        ).astype(float)
    if "volume" in data.columns:
        volume_values = data["volume"].replace("", pd.NA)
        numeric_volume = pd.to_numeric(volume_values, errors="coerce")
        invalid_volume_text = volume_values.notna() & numeric_volume.isna()
        non_null_volume = numeric_volume.dropna()
        if (
            not invalid_volume_text.any()
            and ((non_null_volume % 1) == 0).all()
        ):
            data["volume"] = numeric_volume.astype("Int64")
        else:
            data["volume"] = volume_values
    if "source" in data.columns:
        data["source"] = data["source"].astype("string")

    return data


def seed_historical_data(
    input_path: Path = PROCESSED_DATA_PATH,
) -> int:
    """Validate and store one processed historical dataset atomically."""
    data = _load_processed_market_data(input_path)
    raise_if_invalid(data)

    engine = create_database_engine()
    try:
        session_factory = create_session_factory(engine)
        with session_scope(session_factory) as session:
            stored_count = MarketDataService(session).store(data)
            session.commit()
        return stored_count
    finally:
        engine.dispose()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Seed Aura's processed historical market data."
    )
    parser.add_argument(
        "--input-path",
        type=Path,
        default=PROCESSED_DATA_PATH,
        help=(
            "Processed market-data CSV path. Defaults to Aura's canonical "
            "processed market-data file."
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = _build_parser().parse_args(argv)

    try:
        stored_count = seed_historical_data(args.input_path)
    except (
        OSError,
        SQLAlchemyError,
        TypeError,
        ValueError,
        RuntimeError,
    ) as error:
        raise SystemExit(
            f"Aura historical market-data seed failed: {error}"
        ) from error

    print("Aura historical market-data seed completed.")
    print("-------------------------------------------")
    print(f"Input file:  {args.input_path}")
    print(f"Rows stored: {stored_count:,}")


if __name__ == "__main__":
    main()
