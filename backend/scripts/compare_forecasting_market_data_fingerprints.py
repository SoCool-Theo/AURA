"""Compare authoritative and frozen-local forecasting fingerprints."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
import json
from pathlib import Path
import sys


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.forecasting.fingerprints import (
    compare_market_data_fingerprints,
    fingerprint_from_dict,
    verification_json,
)


def _load(path: Path):
    return fingerprint_from_dict(json.loads(path.read_text(encoding="utf-8")))


def compare_files(*, authoritative_path: Path, local_path: Path):
    return compare_market_data_fingerprints(
        _load(authoritative_path),
        _load(local_path),
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify that authoritative and local fingerprints match."
    )
    parser.add_argument("--authoritative", type=Path, required=True)
    parser.add_argument("--local", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = _build_parser().parse_args(argv)
    try:
        verification = compare_files(
            authoritative_path=args.authoritative,
            local_path=args.local,
        )
        args.output.write_text(verification_json(verification), encoding="utf-8")
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise SystemExit(f"Forecasting fingerprint comparison failed: {error}") from error
    if not verification.matches:
        raise SystemExit(
            "Forecasting fingerprints do not match: "
            + ", ".join(verification.mismatch_fields)
        )
    print("Aura forecasting market-data fingerprints match.")
    print(f"Rows verified: {verification.local_total_row_count}")
    print(f"Output: {args.output}")


if __name__ == "__main__":
    main()
