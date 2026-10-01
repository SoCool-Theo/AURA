"""Official offline calibration, final test, and artifact generation.

This script must be run manually against the verified frozen local Docker
PostgreSQL copy. It performs no provider requests and no database writes.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from datetime import date, timedelta
import json
from pathlib import Path
import sys

from sqlalchemy.exc import SQLAlchemyError


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPOSITORY_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.instruments import USER_ASSET_SYMBOLS
from app.database.connection import (
    create_database_engine,
    create_session_factory,
    session_scope,
)
from app.forecasting.artifacts import (
    OFFICIAL_ARTIFACT_VERSION,
    ForecastArtifactError,
    build_artifact_preflight,
    mark_artifact_run_completed,
    mark_final_test_started,
    preflight_from_dict,
    prepare_artifact_run,
    read_git_revision_state,
    write_artifact_bundle,
)
from app.forecasting.data import build_forecast_dataset, build_price_histories
from app.forecasting.finalization import (
    calibrate_frozen_selection,
    evaluate_frozen_final_test,
    train_deployment_artifact,
)
from app.forecasting.fingerprints import (
    build_market_data_fingerprint,
    verification_from_dict,
)
from app.forecasting.selection_manifest import (
    EXPECTED_SELECTION_RECORD_COUNT,
    OFFICIAL_EVALUATION_CUTOFF,
    selection_manifest_from_dict,
)
from app.forecasting.splits import EvaluationPlanConfig, build_chronological_plan
from app.services.market_data_service import MarketDataService
from backend.scripts.fingerprint_forecasting_market_data import (
    DatabaseEnvironmentError,
    database_url_from_env_file,
)


OFFICIAL_ARTIFACT_ROOT = (
    REPOSITORY_ROOT
    / "backend"
    / "artifacts"
    / "forecasting"
    / OFFICIAL_ARTIFACT_VERSION
)


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def run_official_artifact_generation(
    *,
    env_file: Path,
    database_url_key: str = "DATABASE_URL",
    verification_path: Path,
    selection_manifest_path: Path,
    preflight_path: Path,
    artifact_root: Path = OFFICIAL_ARTIFACT_ROOT,
):
    """Execute the guarded official workflow; caller must invoke manually."""
    selection_manifest = selection_manifest_from_dict(
        _load_json(selection_manifest_path)
    )
    verification = verification_from_dict(_load_json(verification_path))
    preflight = preflight_from_dict(_load_json(preflight_path))
    git_state = read_git_revision_state(REPOSITORY_ROOT)
    if (
        preflight.artifact_version != OFFICIAL_ARTIFACT_VERSION
        or preflight.selection_manifest_sha256
        != selection_manifest.manifest_sha256
        or preflight.verification_sha256 != verification.verification_sha256
        or preflight.git_commit != git_state.commit
    ):
        raise ForecastArtifactError("preflight no longer matches official inputs")

    engine = create_database_engine(
        database_url_from_env_file(env_file, database_url_key=database_url_key)
    )
    try:
        factory = create_session_factory(engine)
        with session_scope(factory) as session:
            records = MarketDataService(session).get_range(
                USER_ASSET_SYMBOLS,
                date.min,
                OFFICIAL_EVALUATION_CUTOFF,
            )
            fingerprint = build_market_data_fingerprint(
                records,
                evaluation_cutoff=OFFICIAL_EVALUATION_CUTOFF,
                symbols=USER_ASSET_SYMBOLS,
            )
            histories = build_price_histories(records)
    finally:
        engine.dispose()

    current_preflight = build_artifact_preflight(
        artifact_root=artifact_root,
        artifact_version=OFFICIAL_ARTIFACT_VERSION,
        selection_manifest=selection_manifest,
        verification=verification,
        fingerprint=fingerprint,
        git_state=git_state,
    )
    if (
        current_preflight.local_fingerprint_sha256
        != preflight.local_fingerprint_sha256
    ):
        raise ForecastArtifactError("local database changed after preflight")
    histories_by_symbol = {history.symbol: history for history in histories}
    if set(histories_by_symbol) != set(USER_ASSET_SYMBOLS):
        raise ForecastArtifactError("local training data lacks official symbols")
    datasets = {
        symbol: build_forecast_dataset(histories_by_symbol[symbol])
        for symbol in USER_ASSET_SYMBOLS
    }
    plan = build_chronological_plan(
        EvaluationPlanConfig(
            evaluation_end_exclusive=OFFICIAL_EVALUATION_CUTOFF
            + timedelta(days=1)
        )
    )

    state = prepare_artifact_run(
        artifact_root=artifact_root,
        artifact_version=OFFICIAL_ARTIFACT_VERSION,
    )
    calibrations = tuple(
        calibrate_frozen_selection(
            dataset=datasets[selection.symbol],
            plan=plan,
            selection=selection,
        )
        for selection in selection_manifest.records
    )
    if len(calibrations) != EXPECTED_SELECTION_RECORD_COUNT:
        raise ForecastArtifactError("calibration did not complete 34 selections")

    state = mark_final_test_started(artifact_root=artifact_root, state=state)
    final_tests = tuple(
        evaluate_frozen_final_test(
            dataset=datasets[selection.symbol],
            plan=plan,
            selection=selection,
        )
        for selection in selection_manifest.records
    )
    if len(final_tests) != EXPECTED_SELECTION_RECORD_COUNT:
        raise ForecastArtifactError("final test did not complete 34 selections")

    training_results = tuple(
        train_deployment_artifact(
            dataset=datasets[selection.symbol],
            selection=selection,
            evaluation_cutoff=OFFICIAL_EVALUATION_CUTOFF,
        )
        for selection in selection_manifest.records
    )
    generated = write_artifact_bundle(
        artifact_root=artifact_root,
        artifact_version=OFFICIAL_ARTIFACT_VERSION,
        selection_manifest=selection_manifest,
        verification=verification,
        fingerprint=fingerprint,
        calibrations=calibrations,
        final_tests=final_tests,
        training_results=training_results,
        git_state=git_state,
        run_state=state,
    )
    mark_artifact_run_completed(artifact_root=artifact_root, state=state)
    return generated


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Calibrate, final-test, and train the frozen official forecasting "
            "artifact version using local Docker PostgreSQL only."
        )
    )
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--database-url-key", default="DATABASE_URL")
    parser.add_argument("--verification", type=Path, required=True)
    parser.add_argument("--selection-manifest", type=Path, required=True)
    parser.add_argument("--preflight", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = _build_parser().parse_args(argv)
    try:
        generated = run_official_artifact_generation(
            env_file=args.env_file,
            database_url_key=args.database_url_key,
            verification_path=args.verification,
            selection_manifest_path=args.selection_manifest,
            preflight_path=args.preflight,
        )
    except DatabaseEnvironmentError as error:
        raise SystemExit(
            f"Official forecasting artifact generation failed: {error}"
        ) from None
    except (
        OSError,
        SQLAlchemyError,
        TypeError,
        ValueError,
        RuntimeError,
        json.JSONDecodeError,
    ):
        raise SystemExit(
            "Official forecasting artifact generation failed: input, database, or model validation failed."
        ) from None
    print("Aura official forecasting artifacts generated.")
    print(f"Artifact version: {OFFICIAL_ARTIFACT_VERSION}")
    print(f"Artifacts: {len(generated)}")
    print(f"Root: {OFFICIAL_ARTIFACT_ROOT}")


if __name__ == "__main__":
    main()
