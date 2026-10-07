"""Manual experimental weekly deployment fitting, after frozen final evidence.

No selection, calibration, final-test scoring, provider calls, DB writes or
runtime activation. Output is a new fixed weekly folder, never the 30-day V1.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
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
from app.forecasting.artifacts import read_git_revision_state
from app.forecasting.data import build_price_histories
from app.forecasting.finalization import ForecastFinalizationError
from app.forecasting.fingerprints import canonical_json_bytes, sha256_bytes, sha256_file
from app.forecasting.horizon_artifacts import assert_new_artifact_root, validate_final_report, write_weekly_bundle
from app.forecasting.horizon_selection_manifest import RELEASE_VERSION, FrozenHorizonManifest, HorizonSelectionError
from app.forecasting.selection_manifest import OFFICIAL_EVALUATION_CUTOFF
from app.services.market_data_service import MarketDataService
from backend.scripts.calibrate_forecasting_horizons import load_verified_selection
from backend.scripts.evaluate_forecasting_horizons import resolve_training_database_url, validate_local_database_url
from backend.scripts.forecasting_selection_provenance import (
    DatabaseEnvironmentError, SelectionProvenanceError, database_url_from_env_file, verify_selection_records,
)
from backend.scripts.freeze_forecasting_horizons import _reject_constant, _unique_object


def artifact_root() -> Path:
    return REPOSITORY_ROOT / "backend" / "artifacts" / "forecasting" / RELEASE_VERSION


def _read_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_bytes(), object_pairs_hook=_unique_object, parse_constant=_reject_constant)
    if not isinstance(payload, dict):
        raise ForecastFinalizationError("training evidence must be a JSON object")
    return payload


def validate_completed_run(
    *, manifest: FrozenHorizonManifest, calibration_sha256: str, final_report: dict[str, object], final_path: Path,
) -> None:
    """Read the existing one-run markers without changing or resetting them."""
    directory = REPOSITORY_ROOT / "forecasting-evidence" / RELEASE_VERSION
    started = _read_json(directory / "final-test-started.json")
    completed = _read_json(directory / "final-test-completed.json")
    base = {key: value for key, value in started.items() if key != "run_state_sha256"}
    digest = sha256_bytes(canonical_json_bytes(base))
    expected_started = {
        "schema_version": "forecast-weekly-final-test-run-v1", "release_version": RELEASE_VERSION,
        "stage": "final_test_started", "selection_manifest_sha256": manifest.manifest_sha256,
        "calibration_sha256": calibration_sha256,
        "market_data_fingerprint_sha256": manifest.market_data_fingerprint_sha256,
        "market_data_row_count": manifest.market_data_row_count,
        "output_relative_path": final_path.resolve().relative_to(REPOSITORY_ROOT.resolve()).as_posix(),
        "run_state_sha256": digest,
    }
    expected_completed = {
        "schema_version": "forecast-weekly-final-test-run-v1", "release_version": RELEASE_VERSION,
        "stage": "final_test_completed", "run_state_sha256": digest,
        "final_test_sha256": final_report["final_test_sha256"],
    }
    if started != expected_started or completed != expected_completed or final_report["run_state_sha256"] != digest:
        raise ForecastFinalizationError("final-test completion markers differ from pinned training evidence")


def source_hashes() -> dict[str, str]:
    """Capture actual local source bytes, including uncommitted experimental code.

    Unlike official 30-day builds this experimental checkpoint permits a dirty
    worktree. HEAD, actual source hashes and dirty state are recorded truthfully.
    Environment files, evidence, serialized models and credentials are excluded.
    """
    paths = [*sorted((REPOSITORY_ROOT / "backend/app/forecasting").rglob("*.py")),
        REPOSITORY_ROOT / "backend/app/core/instruments.py",
        *(REPOSITORY_ROOT / "backend/scripts" / name for name in (
            "train_forecasting_horizons.py", "calibrate_forecasting_horizons.py", "evaluate_forecasting_horizons.py",
            "forecasting_selection_provenance.py", "fingerprint_forecasting_market_data.py", "freeze_forecasting_horizons.py"))]
    return {path.relative_to(REPOSITORY_ROOT).as_posix(): sha256_file(path) for path in paths}


def read_verified_training_histories(*, database_url: str, manifest: FrozenHorizonManifest):
    validate_local_database_url(database_url)
    engine = create_database_engine(database_url, isolated=True)
    try:
        factory = create_session_factory(engine)
        with session_scope(factory) as session:
            session.execute(text("SET TRANSACTION READ ONLY"))
            records = tuple(MarketDataService(session).get_range(USER_ASSET_SYMBOLS, date.min, OFFICIAL_EVALUATION_CUTOFF))
            verify_selection_records(records, evaluation_cutoff=OFFICIAL_EVALUATION_CUTOFF,
                expected_fingerprint=manifest.market_data_fingerprint_sha256, expected_row_count=manifest.market_data_row_count)
            histories = build_price_histories(records)
    finally:
        engine.dispose()
    if len(histories) != len(USER_ASSET_SYMBOLS) or {history.symbol for history in histories} != set(USER_ASSET_SYMBOLS):
        raise SelectionProvenanceError("weekly training snapshot must contain all 17 unique assets")
    return histories


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train a separate experimental 7/14/21-day package; never rescore or activate.")
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--database-url-key", default="TEST_DATABASE_URL")
    parser.add_argument("--database-name", required=True)
    parser.add_argument("--selection-manifest", type=Path, required=True)
    parser.add_argument("--selection-report", type=Path, required=True)
    parser.add_argument("--expected-manifest-sha256", required=True)
    parser.add_argument("--calibration", type=Path, required=True)
    parser.add_argument("--expected-calibration-sha256", required=True)
    parser.add_argument("--final-test", type=Path, required=True)
    parser.add_argument("--expected-final-test-sha256", required=True)
    parser.add_argument("--accept-experimental-quality", action="store_true",
        help="Acknowledge mixed reviewed performance, not approval of predictive quality.")
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = _build_parser().parse_args(argv)
    try:
        if not args.accept_experimental_quality:
            raise ForecastFinalizationError("pass --accept-experimental-quality to acknowledge mixed weekly V1 quality")
        root = artifact_root()
        assert_new_artifact_root(root)
        manifest = load_verified_selection(manifest_path=args.selection_manifest, selection_report_path=args.selection_report,
            expected_manifest_sha256=args.expected_manifest_sha256)
        calibration, final_report = _read_json(args.calibration), _read_json(args.final_test)
        validate_final_report(final_report, manifest=manifest, calibration_report=calibration,
            expected_calibration_sha256=args.expected_calibration_sha256, expected_final_test_sha256=args.expected_final_test_sha256)
        validate_completed_run(manifest=manifest, calibration_sha256=calibration["calibration_sha256"],
            final_report=final_report, final_path=args.final_test)
        source_bytes = args.selection_report.read_bytes()
        if sha256_bytes(source_bytes) != manifest.source_selection_report_sha256:
            raise ForecastFinalizationError("source selection report changed during training preflight")
        git_state, hashes = read_git_revision_state(REPOSITORY_ROOT), source_hashes()
        database_url = resolve_training_database_url(database_url_from_env_file(args.env_file,
            database_url_key=args.database_url_key), args.database_name)
        histories = read_verified_training_histories(database_url=database_url, manifest=manifest)
        # Database is closed, all evidence/markers/provenance checked before fit.
        if source_hashes() != hashes or read_git_revision_state(REPOSITORY_ROOT) != git_state:
            raise ForecastFinalizationError("source revision changed during training preflight")
        result = write_weekly_bundle(histories, artifact_root=root, manifest=manifest, calibration_report=calibration,
            final_report=final_report, expected_calibration_sha256=args.expected_calibration_sha256,
            expected_final_test_sha256=args.expected_final_test_sha256, source_selection_bytes=source_bytes,
            git_state=git_state, source_file_sha256=hashes, accept_experimental_quality=True,
            progress=lambda message: print(message, flush=True))
    except (HorizonSelectionError, SelectionProvenanceError, DatabaseEnvironmentError, ForecastFinalizationError) as error:
        raise SystemExit(f"Weekly training stopped: {error}. Preserve any partial weekly output for review.") from None
    except (OSError, SQLAlchemyError, TypeError, ValueError, RuntimeError, OverflowError, RecursionError):
        raise SystemExit("Weekly training failed: evidence, database, candidate or new-output validation failed. Preserve any partial weekly folder; no runtime activation occurred.") from None
    print(f"Weekly models trained and reload-checked: {result['generated_artifact_count']}")
    print(f"Deployment fit warnings: {result['deployment_fit_warning_count']}")
    print(f"Package manifest SHA-256: {result['manifest_sha256']}")
    print(f"Root: {root}")
    print("Experimental educational package only. Frozen test evidence was reused, not rescored; original 30-day V1 and runtime remain unchanged.")


if __name__ == "__main__":
    main()
