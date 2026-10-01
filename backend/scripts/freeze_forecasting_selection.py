"""Freeze validated Phase 4/5 selection reports into one manifest."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
import json
from pathlib import Path
import sys


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.forecasting.fingerprints import sha256_file
from app.forecasting.selection_manifest import (
    freeze_selection_manifest,
    selection_manifest_json,
)


def freeze_files(*, return_report_path: Path, volatility_report_path: Path):
    return freeze_selection_manifest(
        return_report=json.loads(return_report_path.read_text(encoding="utf-8")),
        volatility_report=json.loads(
            volatility_report_path.read_text(encoding="utf-8")
        ),
        return_report_sha256=sha256_file(return_report_path),
        volatility_report_sha256=sha256_file(volatility_report_path),
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Freeze validated return and volatility selections."
    )
    parser.add_argument("--return-report", type=Path, required=True)
    parser.add_argument("--volatility-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = _build_parser().parse_args(argv)
    try:
        manifest = freeze_files(
            return_report_path=args.return_report,
            volatility_report_path=args.volatility_report,
        )
        args.output.write_text(selection_manifest_json(manifest), encoding="utf-8")
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise SystemExit(f"Forecasting selection freeze failed: {error}") from error
    print("Aura forecasting selection manifest frozen.")
    print(f"Selections: {manifest.selection_count}")
    print(f"Manifest SHA-256: {manifest.manifest_sha256}")
    print(f"Output: {args.output}")


if __name__ == "__main__":
    main()
