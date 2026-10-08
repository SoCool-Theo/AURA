"""Manual weekly calibration only; never final testing or deployment fitting."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence
from datetime import date
import json
from pathlib import Path
import sys

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPOSITORY_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.instruments import USER_ASSET_SYMBOLS
from app.database.connection import create_database_engine, create_session_factory, session_scope
from app.forecasting.data import build_price_histories
from app.forecasting.horizon_calibration import calibration_report_json, calibrate_histories
from app.forecasting.horizon_selection_manifest import (
    FrozenHorizonManifest, HorizonSelectionError, freeze_horizon_manifest,
    horizon_manifest_from_dict, validate_digest,
)
from app.forecasting.selection_manifest import OFFICIAL_EVALUATION_CUTOFF
from app.services.market_data_service import MarketDataService
from backend.scripts.evaluate_forecasting_horizons import (
    resolve_training_database_url, validate_local_database_url, validate_output_path,
)
from backend.scripts.forecasting_selection_provenance import (
    DatabaseEnvironmentError, SelectionProvenanceError, database_url_from_env_file,
    provenance_payload, verify_selection_records,
)
from backend.scripts.freeze_forecasting_horizons import _reject_constant, _unique_object, read_verified_report


def load_verified_selection(
    *, manifest_path: Path, selection_report_path: Path, expected_manifest_sha256: str,
) -> FrozenHorizonManifest:
    """Pin canonical manifest and original report bytes before any DB/fitting."""
    expected = validate_digest(expected_manifest_sha256)
    payload = json.loads(manifest_path.read_bytes(), object_pairs_hook=_unique_object, parse_constant=_reject_constant)
    manifest = horizon_manifest_from_dict(payload)
    if manifest.manifest_sha256 != expected:
        raise HorizonSelectionError("selection manifest differs from the reviewed checksum")
    report, source_hash = read_verified_report(selection_report_path, manifest.source_selection_report_sha256)
    reproduced = freeze_horizon_manifest(
        report=report, source_report_sha256=source_hash,
        expected_market_data_fingerprint=manifest.market_data_fingerprint_sha256,
        expected_row_count=manifest.market_data_row_count,
    )
    if reproduced != manifest:
        raise HorizonSelectionError("frozen selections differ from the reviewed source evidence")
    return manifest


def run_persisted_calibration(
    *, database_url: str, manifest: FrozenHorizonManifest,
    progress: Callable[[str], None] | None = None,
) -> dict[str, object]:
    """Read/verify once, close DB, then calibrate selected candidates only."""
    validate_local_database_url(database_url)
    engine = create_database_engine(database_url, isolated=True)
    try:
        factory = create_session_factory(engine)
        with session_scope(factory) as session:
            session.execute(text("SET TRANSACTION READ ONLY"))
            records = tuple(MarketDataService(session).get_range(USER_ASSET_SYMBOLS, date.min, OFFICIAL_EVALUATION_CUTOFF))
            provenance = verify_selection_records(
                records, evaluation_cutoff=OFFICIAL_EVALUATION_CUTOFF,
                expected_fingerprint=manifest.market_data_fingerprint_sha256,
                expected_row_count=manifest.market_data_row_count,
            )
            histories = build_price_histories(records)
        if {history.symbol for history in histories} != set(USER_ASSET_SYMBOLS):
            raise SelectionProvenanceError("the verified calibration snapshot must contain all 17 assets")
    finally:
        engine.dispose()
    report = calibrate_histories(histories, manifest=manifest, progress=progress)
    report["data_provenance"] = provenance_payload(provenance, evaluation_cutoff=OFFICIAL_EVALUATION_CUTOFF)
    return report


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Calibrate frozen 7/14/21-day selections only; never deploy models.")
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--database-url-key", default="TEST_DATABASE_URL")
    parser.add_argument("--database-name", required=True, help="Explicit isolated aura_forecast_training_ database.")
    parser.add_argument("--selection-manifest", type=Path, required=True)
    parser.add_argument("--selection-report", type=Path, required=True)
    parser.add_argument("--expected-manifest-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = _build_parser().parse_args(argv)
    try:
        output = validate_output_path(args.output)
        manifest = load_verified_selection(manifest_path=args.selection_manifest, selection_report_path=args.selection_report,
                                           expected_manifest_sha256=args.expected_manifest_sha256)
        database_url = resolve_training_database_url(
            database_url_from_env_file(args.env_file, database_url_key=args.database_url_key), args.database_name)
        report = run_persisted_calibration(database_url=database_url, manifest=manifest,
                                           progress=lambda message: print(message, flush=True))
        payload = calibration_report_json(report)
        output.parent.mkdir(parents=True, exist_ok=True)
        if validate_output_path(args.output) != output:
            raise HorizonSelectionError("output destination changed during calibration")
        with output.open("x", encoding="utf-8") as stream:
            stream.write(payload)
    except (HorizonSelectionError, SelectionProvenanceError, DatabaseEnvironmentError) as error:
        raise SystemExit(f"Horizon calibration stopped: {error}") from None
    except (OSError, SQLAlchemyError, TypeError, ValueError, RuntimeError, OverflowError, RecursionError):
        raise SystemExit("Horizon calibration failed: evidence, database, candidate or new-output validation failed; no deployment was activated.") from None
    print(f"Calibrated selections: {report['record_count']}")
    print(f"Selection warnings retained: {sum(record['selection_warning'] is not None for record in report['records'])}")
    print(f"Calibration fit warnings: {sum(record['warning'] is not None for record in report['records'])}")
    print(f"Calibration SHA-256: {json.loads(payload)['calibration_sha256']}")
    print(f"Output: {output}")
    print("Calibration only. No final test, deployment-artifact training or activation was run.")


if __name__ == "__main__":
    main()
