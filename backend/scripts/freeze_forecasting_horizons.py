"""User-run weekly selection freezer: no database, fitting or artifact writes."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
import json
from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPOSITORY_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.forecasting.fingerprints import sha256_bytes
from app.forecasting.horizon_selection_manifest import (
    HorizonSelectionError, freeze_horizon_manifest, horizon_manifest_from_dict,
    horizon_manifest_json, validate_digest,
)
from backend.scripts.evaluate_forecasting_horizons import validate_output_path


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise HorizonSelectionError("selection JSON contains duplicate object keys")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise HorizonSelectionError("selection JSON contains a non-finite number")


def read_verified_report(path: Path, expected_sha256: str) -> tuple[object, str]:
    """Hash exactly the bytes being parsed; reject changed or ambiguous input."""
    expected = validate_digest(expected_sha256)
    raw = path.read_bytes()
    digest = sha256_bytes(raw)
    if digest != expected:
        raise HorizonSelectionError("selection report SHA-256 differs from the reviewed report")
    try:
        report = json.loads(raw, object_pairs_hook=_unique_object, parse_constant=_reject_constant)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise HorizonSelectionError("selection report is not valid UTF JSON") from error
    return report, digest


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Freeze reviewed 7/14/21-day choices without fitting or deploying.")
    parser.add_argument("--selection-report", type=Path, required=True)
    parser.add_argument("--expected-selection-report-sha256", required=True)
    parser.add_argument("--expected-market-data-fingerprint", required=True)
    parser.add_argument("--expected-row-count", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = _build_parser().parse_args(argv)
    try:
        output = validate_output_path(args.output)
        report, digest = read_verified_report(args.selection_report, args.expected_selection_report_sha256)
        manifest = freeze_horizon_manifest(
            report=report, source_report_sha256=digest,
            expected_market_data_fingerprint=args.expected_market_data_fingerprint,
            expected_row_count=args.expected_row_count,
        )
        payload = horizon_manifest_json(manifest)
        # Validate the emitted representation before creating any output.
        horizon_manifest_from_dict(json.loads(payload))
        output.parent.mkdir(parents=True, exist_ok=True)
        if validate_output_path(args.output) != output:
            raise HorizonSelectionError("output destination changed during freezing")
        with output.open("x", encoding="utf-8") as stream:
            stream.write(payload)
    except (HorizonSelectionError, ValueError) as error:
        raise SystemExit(f"Horizon freeze stopped: {error}") from None
    except (OSError, TypeError, OverflowError, RecursionError):
        raise SystemExit("Horizon freeze failed: evidence or new-output validation failed; no deployment was activated.") from None
    warnings = sum(record.selection.selection_warning is not None for record in manifest.records)
    print(f"Frozen selections: {len(manifest.records)}")
    print(f"Selected-model warnings retained: {warnings}")
    print(f"Manifest SHA-256: {manifest.manifest_sha256}")
    print(f"Output: {output}")
    print("Selection frozen only. No calibration, final test, model training or deployment was run.")


if __name__ == "__main__":
    main()
