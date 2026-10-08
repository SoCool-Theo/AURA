"""Manual, one-run weekly final scoring; no range tuning or deployment models."""

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
from app.forecasting.finalization import ForecastFinalizationError
from app.forecasting.fingerprints import canonical_json_bytes, sha256_bytes
from app.forecasting.horizon_final_test import evaluate_final_histories, final_test_report_json, validate_calibration_report
from app.forecasting.horizon_selection_manifest import RELEASE_VERSION, FrozenHorizonManifest, HorizonSelectionError
from app.forecasting.selection_manifest import OFFICIAL_EVALUATION_CUTOFF
from app.services.market_data_service import MarketDataService
from backend.scripts.calibrate_forecasting_horizons import load_verified_selection
from backend.scripts.evaluate_forecasting_horizons import resolve_training_database_url, validate_local_database_url, validate_output_path
from backend.scripts.forecasting_selection_provenance import (
    DatabaseEnvironmentError, SelectionProvenanceError, database_url_from_env_file, provenance_payload, verify_selection_records,
)
from backend.scripts.freeze_forecasting_horizons import _reject_constant, _unique_object


def _run_paths() -> tuple[Path, Path]:
    # Fixed per release, never chosen from --output or an optional reset flag.
    directory = REPOSITORY_ROOT / "forecasting-evidence" / RELEASE_VERSION
    return directory / "final-test-started.json", directory / "final-test-completed.json"


def assert_run_not_started() -> None:
    if any(path.exists() or path.is_symlink() for path in _run_paths()):
        raise ForecastFinalizationError("final test already started for this weekly release; preserve the run markers and request review")


def validate_final_output(path: Path) -> Path:
    output = validate_output_path(path)
    if output.is_relative_to(_run_paths()[0].parent.resolve()):
        raise ForecastFinalizationError("final-test output cannot enter the reserved run-marker folder")
    return output


def start_final_test_run(*, manifest: FrozenHorizonManifest, calibration_sha256: str, output: Path) -> str:
    assert_run_not_started()
    path, _ = _run_paths()
    path = validate_output_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if validate_output_path(_run_paths()[0]) != path:
        raise ForecastFinalizationError("run-marker destination changed")
    state = {
        "schema_version": "forecast-weekly-final-test-run-v1", "release_version": RELEASE_VERSION,
        "stage": "final_test_started", "selection_manifest_sha256": manifest.manifest_sha256,
        "calibration_sha256": calibration_sha256,
        "market_data_fingerprint_sha256": manifest.market_data_fingerprint_sha256,
        "market_data_row_count": manifest.market_data_row_count,
        "output_relative_path": output.relative_to(REPOSITORY_ROOT.resolve()).as_posix(),
    }
    digest = sha256_bytes(canonical_json_bytes(state))
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps({**state, "run_state_sha256": digest}, allow_nan=False, indent=2, sort_keys=True) + "\n")
    return digest


def complete_final_test_run(*, run_state_sha256: str, final_test_sha256: str) -> None:
    _, path = _run_paths()
    path = validate_output_path(path)
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps({"schema_version": "forecast-weekly-final-test-run-v1",
                                "release_version": RELEASE_VERSION, "stage": "final_test_completed",
                                "run_state_sha256": run_state_sha256, "final_test_sha256": final_test_sha256},
                               allow_nan=False, indent=2, sort_keys=True) + "\n")


def run_persisted_final_test(
    *, database_url: str, manifest: FrozenHorizonManifest, calibration_report: dict[str, object],
    expected_calibration_sha256: str, before_evaluation: Callable[[], None],
    progress: Callable[[str], None] | None = None,
) -> dict[str, object]:
    validate_calibration_report(calibration_report, manifest=manifest, expected_calibration_sha256=expected_calibration_sha256)
    validate_local_database_url(database_url)
    engine = create_database_engine(database_url, isolated=True)
    try:
        factory = create_session_factory(engine)
        with session_scope(factory) as session:
            session.execute(text("SET TRANSACTION READ ONLY"))
            records = tuple(MarketDataService(session).get_range(USER_ASSET_SYMBOLS, date.min, OFFICIAL_EVALUATION_CUTOFF))
            provenance = verify_selection_records(records, evaluation_cutoff=OFFICIAL_EVALUATION_CUTOFF,
                expected_fingerprint=manifest.market_data_fingerprint_sha256, expected_row_count=manifest.market_data_row_count)
            histories = build_price_histories(records)
        if {history.symbol for history in histories} != set(USER_ASSET_SYMBOLS):
            raise SelectionProvenanceError("final-test snapshot must contain all 17 assets")
    finally:
        engine.dispose()
    # Reserve this release before constructing/scoring final-test targets. A
    # failure from here onward remains consumed: never clear the marker silently.
    before_evaluation()
    report = evaluate_final_histories(histories, manifest=manifest, calibration_report=calibration_report,
                                      expected_calibration_sha256=expected_calibration_sha256, progress=progress)
    report["data_provenance"] = provenance_payload(provenance, evaluation_cutoff=OFFICIAL_EVALUATION_CUTOFF)
    return report


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Score frozen weekly forecasts once, without deploying or retuning.")
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--database-url-key", default="TEST_DATABASE_URL")
    parser.add_argument("--database-name", required=True)
    parser.add_argument("--selection-manifest", type=Path, required=True)
    parser.add_argument("--selection-report", type=Path, required=True)
    parser.add_argument("--expected-manifest-sha256", required=True)
    parser.add_argument("--calibration", type=Path, required=True)
    parser.add_argument("--expected-calibration-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = _build_parser().parse_args(argv)
    run_state_hash = None
    try:
        output = validate_final_output(args.output)
        assert_run_not_started()
        manifest = load_verified_selection(manifest_path=args.selection_manifest, selection_report_path=args.selection_report,
                                           expected_manifest_sha256=args.expected_manifest_sha256)
        calibration = json.loads(args.calibration.read_bytes(), object_pairs_hook=_unique_object, parse_constant=_reject_constant)
        validate_calibration_report(calibration, manifest=manifest, expected_calibration_sha256=args.expected_calibration_sha256)
        database_url = resolve_training_database_url(database_url_from_env_file(args.env_file, database_url_key=args.database_url_key), args.database_name)
        def reserve_run() -> None:
            nonlocal run_state_hash
            # Recheck report destination before consuming the final-test release.
            if validate_final_output(args.output) != output:
                raise ForecastFinalizationError("final-test output destination changed")
            run_state_hash = start_final_test_run(manifest=manifest, calibration_sha256=calibration["calibration_sha256"], output=output)
        report = run_persisted_final_test(database_url=database_url, manifest=manifest, calibration_report=calibration,
            expected_calibration_sha256=args.expected_calibration_sha256, before_evaluation=reserve_run,
            progress=lambda message: print(message, flush=True))
        if run_state_hash is None:
            raise ForecastFinalizationError("final-test run was not reserved")
        report["run_state_sha256"] = run_state_hash
        payload = final_test_report_json(report)
        output.parent.mkdir(parents=True, exist_ok=True)
        if validate_final_output(args.output) != output:
            raise ForecastFinalizationError("final-test output destination changed")
        with output.open("x", encoding="utf-8") as stream:
            stream.write(payload)
        final_hash = json.loads(payload)["final_test_sha256"]
        complete_final_test_run(run_state_sha256=run_state_hash, final_test_sha256=final_hash)
    except (HorizonSelectionError, SelectionProvenanceError, DatabaseEnvironmentError, ForecastFinalizationError) as error:
        raise SystemExit(f"Weekly final test stopped: {error}. Preserve any run markers; do not force a rerun.") from None
    except (OSError, SQLAlchemyError, TypeError, ValueError, RuntimeError, OverflowError, RecursionError):
        raise SystemExit("Weekly final test failed: input, database, model or output validation failed. Preserve any run markers and share the failure; no deployment was activated.") from None
    print(f"Final-tested selections: {report['record_count']}")
    print(f"Final fit warnings: {sum(record['warning'] is not None for record in report['records'])}")
    print(f"Empty intervals: {sum(record['interval_coverage']['empty_interval_count'] for record in report['records'])}")
    print(f"Final-test SHA-256: {final_hash}")
    print(f"Output: {output}")
    print("Final scoring completed once. Predictive-quality review is pending; no deployment models or activation were created.")


if __name__ == "__main__":
    main()
