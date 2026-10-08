"""Offline Phase 6 artifact serialization and reproducibility safeguards."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from importlib.metadata import version as package_version
import json
from pathlib import Path
import platform
import subprocess
from typing import Any

import joblib

from ..core.instruments import USER_ASSET_SYMBOLS
from .features import FEATURE_SET_VERSION
from .finalization import (
    CALIBRATION_MINIMUM_OBSERVATIONS,
    NOMINAL_INTERVAL_COVERAGE,
    CalibrationResult,
    DeploymentTrainingResult,
    FinalTestResult,
    ForecastArtifactModel,
)
from .fingerprints import (
    ForecastFingerprintVerification,
    ForecastMarketDataFingerprint,
    canonical_json_bytes,
    sha256_bytes,
    sha256_file,
    verification_json,
)
from .selection_manifest import (
    EXPECTED_SELECTION_RECORD_COUNT,
    FrozenSelectionManifest,
    FrozenSelectionRecord,
    selection_manifest_json,
)
from .targets import (
    FORECAST_HORIZON_DAYS,
    MAX_ENDPOINT_SLIPPAGE_DAYS,
    TARGET_SET_VERSION,
)


OFFICIAL_ARTIFACT_VERSION = "forecast-v1-20260917"
ARTIFACT_SCHEMA_VERSION = "forecast-artifact-v1"
ROOT_MANIFEST_SCHEMA_VERSION = "forecast-root-manifest-v1"
RUN_STATE_SCHEMA_VERSION = "forecast-artifact-run-state-v1"
PREFLIGHT_SCHEMA_VERSION = "forecast-artifact-preflight-v1"
EXPECTED_ARTIFACT_COUNT = EXPECTED_SELECTION_RECORD_COUNT


class ForecastArtifactError(ValueError):
    """Raised when official artifact generation is unsafe or incomplete."""


@dataclass(frozen=True, slots=True)
class GitRevisionState:
    commit: str
    tracked_working_tree_clean: bool


@dataclass(frozen=True, slots=True)
class ArtifactRunState:
    schema_version: str
    artifact_version: str
    final_test_started: bool
    completed: bool


@dataclass(frozen=True, slots=True)
class ArtifactPreflight:
    schema_version: str
    artifact_version: str
    evaluation_cutoff: str
    selection_manifest_sha256: str
    verification_sha256: str
    local_fingerprint_sha256: str
    git_commit: str
    tracked_working_tree_clean: bool
    artifact_root_absent: bool
    ready: bool


@dataclass(frozen=True, slots=True)
class GeneratedArtifactRecord:
    symbol: str
    target_type: str
    selected_candidate_id: str
    model_path: str
    metadata_path: str
    model_sha256: str
    metadata_sha256: str


def utc_creation_timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def read_git_revision_state(repository_root: Path) -> GitRevisionState:
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repository_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=no"],
            cwd=repository_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as error:
        raise ForecastArtifactError("Git revision state is unavailable") from error
    if len(commit) != 40:
        raise ForecastArtifactError("Git commit hash is invalid")
    return GitRevisionState(
        commit=commit,
        tracked_working_tree_clean=not status,
    )


def require_clean_official_revision(state: GitRevisionState) -> None:
    if not state.tracked_working_tree_clean:
        raise ForecastArtifactError(
            "official artifact generation requires a clean tracked worktree"
        )


def build_artifact_preflight(
    *,
    artifact_root: Path,
    artifact_version: str,
    selection_manifest: FrozenSelectionManifest,
    verification: ForecastFingerprintVerification,
    fingerprint: ForecastMarketDataFingerprint,
    git_state: GitRevisionState,
) -> ArtifactPreflight:
    if not verification.matches:
        raise ForecastArtifactError("training-data fingerprints do not match")
    if (
        verification.evaluation_cutoff != fingerprint.evaluation_cutoff
        or verification.symbols != fingerprint.symbols
    ):
        raise ForecastArtifactError(
            "verification identity does not match the local fingerprint"
        )
    if fingerprint.sha256 != verification.local_sha256:
        raise ForecastArtifactError("local database no longer matches verification")
    if selection_manifest.evaluation_cutoff != fingerprint.evaluation_cutoff:
        raise ForecastArtifactError("selection and fingerprint cutoff mismatch")
    if tuple(sorted(fingerprint.symbols)) != tuple(sorted(USER_ASSET_SYMBOLS)):
        raise ForecastArtifactError("fingerprint symbol set is not official")
    if artifact_version == OFFICIAL_ARTIFACT_VERSION:
        require_clean_official_revision(git_state)
    if artifact_root.exists():
        raise ForecastArtifactError("artifact version already exists")
    state_path = _run_state_path(artifact_root)
    if state_path.exists():
        try:
            prior_state = ArtifactRunState(
                **json.loads(state_path.read_text(encoding="utf-8"))
            )
        except (OSError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise ForecastArtifactError("artifact run state is invalid") from error
        if prior_state.final_test_started or prior_state.completed:
            raise ForecastArtifactError(
                "final test already started for this artifact version"
            )
    return ArtifactPreflight(
        schema_version=PREFLIGHT_SCHEMA_VERSION,
        artifact_version=artifact_version,
        evaluation_cutoff=selection_manifest.evaluation_cutoff.isoformat(),
        selection_manifest_sha256=selection_manifest.manifest_sha256,
        verification_sha256=verification.verification_sha256,
        local_fingerprint_sha256=fingerprint.sha256,
        git_commit=git_state.commit,
        tracked_working_tree_clean=git_state.tracked_working_tree_clean,
        artifact_root_absent=True,
        ready=True,
    )


def preflight_json(preflight: ArtifactPreflight) -> str:
    return json.dumps(
        asdict(preflight), allow_nan=False, indent=2, sort_keys=True
    ) + "\n"


def preflight_from_dict(payload: object) -> ArtifactPreflight:
    if not isinstance(payload, dict):
        raise ForecastArtifactError("preflight payload must be an object")
    try:
        preflight = ArtifactPreflight(**payload)
    except TypeError as error:
        raise ForecastArtifactError("preflight payload is malformed") from error
    if (
        preflight.schema_version != PREFLIGHT_SCHEMA_VERSION
        or not preflight.ready
        or not preflight.artifact_root_absent
        or not preflight.tracked_working_tree_clean
        or len(preflight.git_commit) != 40
    ):
        raise ForecastArtifactError("preflight is not ready")
    return preflight


def _run_state_path(artifact_root: Path) -> Path:
    return artifact_root.parent / f".{artifact_root.name}.run-state.json"


def _write_json_atomic(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, allow_nan=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def prepare_artifact_run(
    *,
    artifact_root: Path,
    artifact_version: str,
) -> ArtifactRunState:
    """Allow pre-final-test restart but never overwrite or rerun final test."""
    if artifact_root.exists():
        raise ForecastArtifactError("artifact version already exists")
    state_path = _run_state_path(artifact_root)
    if state_path.exists():
        try:
            payload = json.loads(state_path.read_text(encoding="utf-8"))
            state = ArtifactRunState(**payload)
        except (OSError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise ForecastArtifactError("artifact run state is invalid") from error
        if (
            state.schema_version != RUN_STATE_SCHEMA_VERSION
            or state.artifact_version != artifact_version
        ):
            raise ForecastArtifactError("artifact run-state version mismatch")
        if state.final_test_started or state.completed:
            raise ForecastArtifactError(
                "final test already started for this artifact version"
            )
        return state
    state = ArtifactRunState(
        schema_version=RUN_STATE_SCHEMA_VERSION,
        artifact_version=artifact_version,
        final_test_started=False,
        completed=False,
    )
    _write_json_atomic(state_path, asdict(state))
    return state


def mark_final_test_started(
    *,
    artifact_root: Path,
    state: ArtifactRunState,
) -> ArtifactRunState:
    if state.final_test_started or state.completed:
        raise ForecastArtifactError("final test cannot be started again")
    started = ArtifactRunState(
        schema_version=state.schema_version,
        artifact_version=state.artifact_version,
        final_test_started=True,
        completed=False,
    )
    _write_json_atomic(_run_state_path(artifact_root), asdict(started))
    return started


def mark_artifact_run_completed(
    *,
    artifact_root: Path,
    state: ArtifactRunState,
) -> ArtifactRunState:
    if not state.final_test_started or state.completed:
        raise ForecastArtifactError("artifact run cannot be completed")
    completed = ArtifactRunState(
        schema_version=state.schema_version,
        artifact_version=state.artifact_version,
        final_test_started=True,
        completed=True,
    )
    _write_json_atomic(_run_state_path(artifact_root), asdict(completed))
    return completed


def _result_key(result: object) -> tuple[str, str]:
    return (result.symbol, result.target_type.value)


def _json_safe_dataclass(value: object) -> dict[str, object]:
    payload = asdict(value)
    target_type = payload.get("target_type")
    if hasattr(target_type, "value"):
        payload["target_type"] = target_type.value
    return payload


def _assert_no_secret_keys(value: object) -> None:
    forbidden = ("password", "database_url", "api_key", "secret")
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).casefold()
            if any(item in normalized for item in forbidden):
                raise ForecastArtifactError("artifact metadata contains a secret key")
            _assert_no_secret_keys(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            _assert_no_secret_keys(child)


def _library_versions() -> dict[str, str]:
    return {
        "python": platform.python_version(),
        "numpy": package_version("numpy"),
        "pandas": package_version("pandas"),
        "scikit_learn": package_version("scikit-learn"),
        "statsmodels": package_version("statsmodels"),
        "joblib": package_version("joblib"),
    }


def _warning_codes(
    selection: FrozenSelectionRecord,
    calibration: CalibrationResult,
    final_test: FinalTestResult,
    training: DeploymentTrainingResult,
) -> list[str]:
    return list(
        dict.fromkeys(
            warning
            for warning in (
                selection.selection_warning,
                calibration.warning,
                final_test.warning,
                training.warning,
            )
            if warning
        )
    )


def _metadata_payload(
    *,
    artifact_version: str,
    selection: FrozenSelectionRecord,
    calibration: CalibrationResult,
    final_test: FinalTestResult,
    training: DeploymentTrainingResult,
    fingerprint: ForecastMarketDataFingerprint,
    selection_manifest: FrozenSelectionManifest,
    git_state: GitRevisionState,
    creation_timestamp: str,
    model_sha256: str,
) -> dict[str, object]:
    volatility_clipping = (
        {
            "calibration_negative_prediction_clipped_count": (
                calibration.negative_prediction_clipped_count
            ),
            "final_test_negative_prediction_clipped_count": (
                final_test.negative_prediction_clipped_count
            ),
            "deployment_prediction_rule": "max(raw_prediction, 0.0)",
        }
        if selection.target_type.value == "realized_volatility_30d"
        else None
    )
    payload: dict[str, object] = {
        "artifact_schema_version": ARTIFACT_SCHEMA_VERSION,
        "artifact_version": artifact_version,
        "symbol": selection.symbol,
        "target_type": selection.target_type.value,
        "selected_candidate_id": selection.selected_candidate_id,
        "model_family": training.model_family,
        "model_parameters": training.model_parameters,
        "feature_version": FEATURE_SET_VERSION,
        "target_version": TARGET_SET_VERSION,
        "horizon_definition": {
            "calendar_days": FORECAST_HORIZON_DAYS,
            "maximum_endpoint_slippage_days": MAX_ENDPOINT_SLIPPAGE_DAYS,
        },
        "evaluation_cutoff": selection.evaluation_cutoff.isoformat(),
        "deployment_training_row_count": training.training_row_count,
        "deployment_training_origin_min": (
            training.training_origin_min.isoformat()
        ),
        "deployment_training_origin_max": (
            training.training_origin_max.isoformat()
        ),
        "training_label_completion_rule": (
            "target endpoint_date must be on or before evaluation_cutoff"
        ),
        "deployment_training_policy": (
            "fit frozen selection on all label-complete history after "
            "calibration and final-test metrics are frozen"
        ),
        "dataset_fingerprint_sha256": fingerprint.sha256,
        "selection_manifest_sha256": selection_manifest.manifest_sha256,
        "selection_mean_mae": (
            selection.selected_candidate_mean_selection_mae
        ),
        "best_baseline_mean_mae": (
            selection.best_baseline_mean_selection_mae
        ),
        "improvement_vs_best_baseline_percent": (
            selection.improvement_vs_best_baseline_percent
        ),
        "calibration_observation_count": calibration.observation_count,
        "calibration_mae": calibration.mae,
        "calibration_rmse": calibration.rmse,
        "calibration_residual_q10": calibration.residual_q10,
        "calibration_residual_q90": calibration.residual_q90,
        "nominal_interval_coverage": NOMINAL_INTERVAL_COVERAGE,
        "interval_type": "empirical prediction interval",
        "final_test_mae": final_test.mae,
        "final_test_rmse": final_test.rmse,
        "final_test_directional_accuracy": (
            final_test.directional_accuracy
        ),
        "volatility_clipping": volatility_clipping,
        "warning_codes": _warning_codes(
            selection,
            calibration,
            final_test,
            training,
        ),
        "random_seed": (
            training.model_parameters.get("random_state")
            if training.model_family == "random_forest"
            else None
        ),
        "runtime_versions": _library_versions(),
        "git_commit": git_state.commit,
        "creation_timestamp_utc": creation_timestamp,
        "artifact_file_sha256": model_sha256,
    }
    _assert_no_secret_keys(payload)
    return payload


def _write_model_artifact(
    *,
    artifact_root: Path,
    artifact_version: str,
    selection: FrozenSelectionRecord,
    calibration: CalibrationResult,
    final_test: FinalTestResult,
    training: DeploymentTrainingResult,
    fingerprint: ForecastMarketDataFingerprint,
    selection_manifest: FrozenSelectionManifest,
    git_state: GitRevisionState,
    creation_timestamp: str,
) -> GeneratedArtifactRecord:
    target_directory = artifact_root / selection.symbol / selection.target_type.value
    target_directory.mkdir(parents=True, exist_ok=False)
    model_path = target_directory / "model.joblib"
    joblib.dump(training.artifact_model, model_path, compress=0)
    loaded = joblib.load(model_path)
    if (
        not isinstance(loaded, ForecastArtifactModel)
        or loaded.candidate_id != selection.selected_candidate_id
        or loaded.target_type is not selection.target_type
    ):
        raise ForecastArtifactError("serialized model reload verification failed")
    model_hash = sha256_file(model_path)
    metadata = _metadata_payload(
        artifact_version=artifact_version,
        selection=selection,
        calibration=calibration,
        final_test=final_test,
        training=training,
        fingerprint=fingerprint,
        selection_manifest=selection_manifest,
        git_state=git_state,
        creation_timestamp=creation_timestamp,
        model_sha256=model_hash,
    )
    metadata_path = target_directory / "metadata.json"
    metadata_path.write_text(
        json.dumps(metadata, allow_nan=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return GeneratedArtifactRecord(
        symbol=selection.symbol,
        target_type=selection.target_type.value,
        selected_candidate_id=selection.selected_candidate_id,
        model_path=model_path.relative_to(artifact_root).as_posix(),
        metadata_path=metadata_path.relative_to(artifact_root).as_posix(),
        model_sha256=model_hash,
        metadata_sha256=sha256_file(metadata_path),
    )


def write_artifact_bundle(
    *,
    artifact_root: Path,
    artifact_version: str,
    selection_manifest: FrozenSelectionManifest,
    verification: ForecastFingerprintVerification,
    fingerprint: ForecastMarketDataFingerprint,
    calibrations: tuple[CalibrationResult, ...],
    final_tests: tuple[FinalTestResult, ...],
    training_results: tuple[DeploymentTrainingResult, ...],
    git_state: GitRevisionState,
    creation_timestamp: str | None = None,
    run_state: ArtifactRunState | None = None,
) -> tuple[GeneratedArtifactRecord, ...]:
    """Write exactly 34 reload-verified artifacts and the root manifest."""
    if artifact_root.exists():
        raise ForecastArtifactError("artifact version already exists")
    if not verification.matches:
        raise ForecastArtifactError("training-data fingerprints do not match")
    if fingerprint.sha256 != verification.local_sha256:
        raise ForecastArtifactError(
            "current local training-data fingerprint is not verified"
        )
    if artifact_version == OFFICIAL_ARTIFACT_VERSION:
        require_clean_official_revision(git_state)
        if (
            run_state is None
            or run_state.artifact_version != artifact_version
            or not run_state.final_test_started
            or run_state.completed
        ):
            raise ForecastArtifactError(
                "official artifacts require an active final-test run state"
            )
    collections = (
        selection_manifest.records,
        calibrations,
        final_tests,
        training_results,
    )
    if any(len(items) != EXPECTED_ARTIFACT_COUNT for items in collections):
        raise ForecastArtifactError(
            "artifact generation requires exactly 34 complete records"
        )
    expected_keys = {
        (record.symbol, record.target_type.value)
        for record in selection_manifest.records
    }
    calibration_by_key = {_result_key(item): item for item in calibrations}
    final_by_key = {_result_key(item): item for item in final_tests}
    training_by_key = {_result_key(item): item for item in training_results}
    if (
        len(expected_keys) != EXPECTED_ARTIFACT_COUNT
        or set(calibration_by_key) != expected_keys
        or set(final_by_key) != expected_keys
        or set(training_by_key) != expected_keys
    ):
        raise ForecastArtifactError("artifact record keys are incomplete")
    timestamp = creation_timestamp or utc_creation_timestamp()
    artifact_root.mkdir(parents=True, exist_ok=False)
    (artifact_root / "selection_manifest.json").write_text(
        selection_manifest_json(selection_manifest),
        encoding="utf-8",
    )
    (artifact_root / "training_data_verification.json").write_text(
        verification_json(verification),
        encoding="utf-8",
    )
    calibration_payload = {
        "minimum_observations": CALIBRATION_MINIMUM_OBSERVATIONS,
        "nominal_interval_coverage": NOMINAL_INTERVAL_COVERAGE,
        "results": [
            _json_safe_dataclass(item)
            for item in sorted(calibrations, key=_result_key)
        ],
    }
    final_payload = {
        "selection_manifest_sha256": selection_manifest.manifest_sha256,
        "training_data_fingerprint_sha256": fingerprint.sha256,
        "completed": True,
        "results": [
            _json_safe_dataclass(item)
            for item in sorted(final_tests, key=_result_key)
        ],
    }
    (artifact_root / "calibration_report.json").write_text(
        json.dumps(
            calibration_payload,
            allow_nan=False,
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )
    (artifact_root / "final_test_report.json").write_text(
        json.dumps(
            final_payload,
            allow_nan=False,
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )

    generated: list[GeneratedArtifactRecord] = []
    for selection in selection_manifest.records:
        key = (selection.symbol, selection.target_type.value)
        generated.append(
            _write_model_artifact(
                artifact_root=artifact_root,
                artifact_version=artifact_version,
                selection=selection,
                calibration=calibration_by_key[key],
                final_test=final_by_key[key],
                training=training_by_key[key],
                fingerprint=fingerprint,
                selection_manifest=selection_manifest,
                git_state=git_state,
                creation_timestamp=timestamp,
            )
        )
    if len(generated) != EXPECTED_ARTIFACT_COUNT:
        raise ForecastArtifactError("fewer than 34 artifacts were generated")
    root_payload: dict[str, Any] = {
        "artifact_version": artifact_version,
        "artifact_schema_version": ROOT_MANIFEST_SCHEMA_VERSION,
        "evaluation_cutoff": selection_manifest.evaluation_cutoff.isoformat(),
        "creation_timestamp_utc": timestamp,
        "git_commit": git_state.commit,
        "tracked_working_tree_clean": git_state.tracked_working_tree_clean,
        "training_data_fingerprint_sha256": fingerprint.sha256,
        "selection_manifest_sha256": selection_manifest.manifest_sha256,
        "feature_version": FEATURE_SET_VERSION,
        "target_version": TARGET_SET_VERSION,
        "expected_symbol_count": len(USER_ASSET_SYMBOLS),
        "expected_target_count": 2,
        "expected_artifact_count": EXPECTED_ARTIFACT_COUNT,
        "generated_artifact_count": len(generated),
        "generated_artifacts": [asdict(item) for item in generated],
        "calibration_minimum_observations": (
            CALIBRATION_MINIMUM_OBSERVATIONS
        ),
        "nominal_interval_coverage": NOMINAL_INTERVAL_COVERAGE,
        "final_test_completed": True,
    }
    _assert_no_secret_keys(root_payload)
    (artifact_root / "manifest.json").write_text(
        json.dumps(root_payload, allow_nan=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return tuple(generated)


def checksum_bytes(value: bytes) -> str:
    """Expose deterministic byte checksums for artifact tests and audits."""
    return sha256_bytes(value)
