"""Experimental weekly artifact training; never final scoring or activation.

The unchanged V1 fitter is a private algorithm bridge carrying actual weekly
labels. The serialized outer wrapper and all public metadata identify the real
horizon. This format deliberately cannot load through the 30-day V1 registry.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from datetime import timedelta
import json
import math
from pathlib import Path

import joblib

from ..core.instruments import USER_ASSET_SYMBOLS
from .artifacts import GitRevisionState, _library_versions, utc_creation_timestamp
from .data import AssetPriceHistory, MIN_LABEL_COMPLETE_TRAINING_ORIGINS
from .evaluation import ForecastTargetType
from .features import FEATURE_NAMES, FEATURE_SET_VERSION, build_feature_rows
from .finalization import (
    ForecastArtifactModel, ForecastFinalizationError, _model_family_and_parameters, train_deployment_artifact,
)
from .fingerprints import canonical_json_bytes, sha256_bytes, sha256_file
from .horizon_final_test import (
    FINAL_FOLD, REPORT_SCHEMA as FINAL_SCHEMA, STAGE as FINAL_STAGE,
    _count, _date, _metric, validate_calibration_report,
)
from .horizon_selection_manifest import (
    RELEASE_VERSION, SELECTION_COUNT, FrozenHorizonManifest, FrozenHorizonSelection,
    horizon_manifest_from_dict, horizon_manifest_json, validate_digest,
)
from .models import ARIMA_CANDIDATE_ID, VOLATILITY_ARIMA_CANDIDATE_ID, ARIMA_FIT_CONVERGENCE_WARNING
from .multi_horizon import NEW_HORIZONS, HorizonDataset, _candidate_dataset, build_horizon_dataset, target_name, target_version
from .selection_manifest import OFFICIAL_EVALUATION_CUTOFF
from .targets import MAX_ENDPOINT_SLIPPAGE_DAYS


MODEL_SCHEMA = "forecast-weekly-artifact-v1"
ROOT_SCHEMA = "forecast-weekly-root-manifest-v1"
QUALITY_STATUS = "experimental_educational_not_predictive_quality_approved"


def validate_final_report(
    payload: object, *, manifest: FrozenHorizonManifest, calibration_report: dict[str, object],
    expected_calibration_sha256: str, expected_final_test_sha256: str,
) -> tuple[dict[str, object], ...]:
    """Verify completed, pinned evidence, retaining weak results without tuning."""
    calibrations = validate_calibration_report(calibration_report, manifest=manifest,
        expected_calibration_sha256=expected_calibration_sha256)
    try:
        expected = validate_digest(expected_final_test_sha256)
        if not isinstance(payload, dict):
            raise ForecastFinalizationError("final-test report must be an object")
        base = {key: value for key, value in payload.items() if key != "final_test_sha256"}
        if payload.get("final_test_sha256") != expected or sha256_bytes(canonical_json_bytes(base)) != expected:
            raise ForecastFinalizationError("final-test checksum differs from reviewed evidence")
        fixed = {
            "report_schema": FINAL_SCHEMA, "stage": FINAL_STAGE, "release_version": RELEASE_VERSION,
            "evaluation_cutoff": OFFICIAL_EVALUATION_CUTOFF.isoformat(), "horizons": list(NEW_HORIZONS),
            "horizon_unit": "calendar_days", "record_count": SELECTION_COUNT,
            "selection_manifest_sha256": manifest.manifest_sha256,
            "source_selection_report_sha256": manifest.source_selection_report_sha256,
            "calibration_sha256": expected_calibration_sha256,
            "data_provenance": calibration_report["data_provenance"],
            "final_test_fold": {"fold_id": FINAL_FOLD.fold_id, "purpose": "final_test",
                "origin_start": FINAL_FOLD.origin_start.isoformat(), "origin_end": FINAL_FOLD.origin_end.isoformat()},
            "nominal_interval_coverage": .8, "final_test_completed": True, "deployment_artifacts_created": False,
        }
        if canonical_json_bytes({key: payload.get(key) for key in fixed}) != canonical_json_bytes(fixed):
            raise ForecastFinalizationError("final-test contract or provenance differs from frozen inputs")
        validate_digest(payload.get("run_state_sha256"))
        if not isinstance(payload.get("limitations"), list) or any(not isinstance(item, str) for item in payload["limitations"]):
            raise ForecastFinalizationError("final-test limitations must be preserved as text records")
        records = payload.get("records")
        if not isinstance(records, list) or len(records) != SELECTION_COUNT:
            raise ForecastFinalizationError("final test requires 102 ordered records")
        for record, frozen, calibration in zip(records, manifest.records, calibrations, strict=True):
            selection, horizon = frozen.selection, frozen.horizon_days
            identity = {
                "symbol": selection.symbol, "horizon_days": horizon,
                "target_type": target_name(selection.target_type, horizon),
                "selected_candidate_id": selection.selected_candidate_id, "selection_warning": selection.selection_warning,
                "calibration_warning": calibration["warning"], "feature_set_version": FEATURE_SET_VERSION,
                "target_set_version": target_version(horizon), "fold_id": FINAL_FOLD.fold_id,
                "frozen_residual_q10": calibration["residual_q10"], "frozen_residual_q90": calibration["residual_q90"],
                "training_cutoff_exclusive": FINAL_FOLD.origin_start.isoformat(),
                "evaluation_origin_start": FINAL_FOLD.origin_start.isoformat(),
                "evaluation_origin_end_exclusive": FINAL_FOLD.origin_end.isoformat(),
            }
            if not isinstance(record, dict) or canonical_json_bytes({key: record.get(key) for key in identity}) != canonical_json_bytes(identity):
                raise ForecastFinalizationError("final-test record identity, order or ranges differ from frozen inputs")
            count = _count(record.get("observation_count"), 1)
            training_count = _count(record.get("training_observation_count"), MIN_LABEL_COMPLETE_TRAINING_ORIGINS)
            if _count(record.get("candidate_training_value_count"), 1) > training_count:
                raise ForecastFinalizationError("final candidate training count exceeds eligible history")
            if _metric(record.get("mae")) < 0 or _metric(record.get("rmse")) < 0:
                raise ForecastFinalizationError("final error metrics must be nonnegative")
            volatility = selection.target_type is ForecastTargetType.VOLATILITY
            if volatility:
                if record.get("directional_accuracy") is not None or _count(record.get("negative_prediction_clipped_count")) > count:
                    raise ForecastFinalizationError("final volatility metrics are invalid")
            elif record.get("negative_prediction_clipped_count") is not None or not 0 <= _metric(record.get("directional_accuracy")) <= 1:
                raise ForecastFinalizationError("final return metrics are invalid")
            if record.get("warning") is not None and (record["warning"] != ARIMA_FIT_CONVERGENCE_WARNING
                or selection.selected_candidate_id not in {ARIMA_CANDIDATE_ID, VOLATILITY_ARIMA_CANDIDATE_ID}):
                raise ForecastFinalizationError("final fit warning is unsupported")
            train_min, train_max, train_end = (_date(record[key]) for key in
                ("training_origin_min", "training_origin_max", "training_endpoint_max"))
            origin_min, origin_max, endpoint_max = (_date(record[key]) for key in
                ("evaluated_origin_min", "evaluated_origin_max", "evaluated_endpoint_max"))
            if not (train_min <= train_max < train_end < FINAL_FOLD.origin_start <= origin_min <= origin_max
                    < endpoint_max < FINAL_FOLD.origin_end
                    and horizon <= (train_end - train_max).days <= horizon + MAX_ENDPOINT_SLIPPAGE_DAYS
                    and horizon <= (endpoint_max - origin_max).days <= horizon + MAX_ENDPOINT_SLIPPAGE_DAYS):
                raise ForecastFinalizationError("final-test endpoint boundaries are invalid")
            coverage = record["interval_coverage"]
            covered, missed, below, above, empty, valid = (_count(coverage[key]) for key in
                ("covered_count", "missed_count", "below_interval_count", "above_interval_count", "empty_interval_count", "valid_interval_count"))
            if (_count(coverage["observation_count"], 1) != count or covered + missed != count
                or below + above + empty != missed or valid + empty != count or (empty and not volatility)
                or _metric(coverage["nominal_coverage"]) != .8
                or not math.isclose(_metric(coverage["empirical_coverage"]), covered / count, rel_tol=0, abs_tol=1e-12)
                or coverage["warning"] != ("empty_volatility_intervals_counted_as_misses" if empty else None)):
                raise ForecastFinalizationError("final-test interval coverage counts are inconsistent")
            if (valid and _metric(coverage["mean_valid_interval_width"]) < 0) or (not valid and coverage["mean_valid_interval_width"] is not None):
                raise ForecastFinalizationError("final-test interval widths are invalid")
        return tuple(records)
    except ForecastFinalizationError:
        raise
    except (KeyError, TypeError, ValueError, OverflowError) as error:
        raise ForecastFinalizationError("final-test evidence is malformed") from error


@dataclass(slots=True)
class WeeklyArtifactModel:
    """Actual horizon identity around a private, unchanged candidate algorithm."""

    symbol: str
    horizon_days: int
    target_type: str
    candidate_id: str
    _model: ForecastArtifactModel
    feature_version: str
    target_version: str

    def __post_init__(self) -> None:
        if (self.symbol not in USER_ASSET_SYMBOLS or type(self.horizon_days) is not int or self.horizon_days not in NEW_HORIZONS
            or not isinstance(self._model, ForecastArtifactModel)
            or self.target_type != target_name(self._model.target_type, self.horizon_days)
            or self.candidate_id != self._model.candidate_id or self.feature_version != FEATURE_SET_VERSION
            or self.target_version != target_version(self.horizon_days)):
            raise ForecastFinalizationError("weekly artifact identity is invalid")

    def predict(self, *, steps: int, feature_matrix: Sequence[Sequence[float]] | None = None) -> tuple[float, ...]:
        self.__post_init__()
        values = self._model.predict(steps=steps, feature_matrix=feature_matrix)
        if len(values) != steps or any(not math.isfinite(value) for value in values):
            raise ForecastFinalizationError("weekly artifact predictions must be finite and aligned")
        return values


def train_horizon_artifact(*, dataset: HorizonDataset, frozen: FrozenHorizonSelection):
    """Fit only completed actual-horizon labels using the frozen family/parameters."""
    selection, horizon = frozen.selection, frozen.horizon_days
    if (dataset.symbol != selection.symbol or dataset.horizon_days != horizon or type(horizon) is not int
        or horizon not in NEW_HORIZONS or selection.evaluation_cutoff != OFFICIAL_EVALUATION_CUTOFF):
        raise ForecastFinalizationError("weekly training dataset differs from frozen identity")
    bridged = _candidate_dataset(dataset, endpoint_before=OFFICIAL_EVALUATION_CUTOFF + timedelta(days=1))
    if len(bridged.rows) < MIN_LABEL_COMPLETE_TRAINING_ORIGINS:
        raise ForecastFinalizationError("weekly deployment training lacks minimum eligible history")
    trained = train_deployment_artifact(dataset=bridged, selection=selection, evaluation_cutoff=OFFICIAL_EVALUATION_CUTOFF)
    expected_family, expected_parameters = _model_family_and_parameters(selection.selected_candidate_id)
    if (trained.symbol != selection.symbol or trained.target_type is not selection.target_type
        or trained.selected_candidate_id != selection.selected_candidate_id
        or trained.model_family != expected_family or trained.model_parameters != expected_parameters
        or trained.artifact_model.model_family != trained.model_family
        or type(trained.training_row_count) is not int or not 1 <= trained.training_row_count <= len(bridged.rows)
        or trained.training_origin_min < bridged.rows[0].features.origin_date
        or not trained.training_origin_min <= trained.training_origin_max <= bridged.rows[-1].features.origin_date):
        raise ForecastFinalizationError("trained weekly model differs from frozen selection or eligible history")
    if trained.warning is not None and (trained.warning != ARIMA_FIT_CONVERGENCE_WARNING
        or selection.selected_candidate_id not in {ARIMA_CANDIDATE_ID, VOLATILITY_ARIMA_CANDIDATE_ID}):
        raise ForecastFinalizationError("weekly training warning is unsupported")
    model = WeeklyArtifactModel(selection.symbol, horizon, target_name(selection.target_type, horizon),
        selection.selected_candidate_id, trained.artifact_model, FEATURE_SET_VERSION, target_version(horizon))
    verification_features = (tuple(float(getattr(bridged.rows[-1].features, name)) for name in FEATURE_NAMES),)
    model.predict(steps=1, feature_matrix=verification_features)
    return model, trained, bridged, verification_features


def assert_new_artifact_root(artifact_root: Path) -> None:
    if artifact_root.name != RELEASE_VERSION or artifact_root.parent.name != "forecasting":
        raise ForecastFinalizationError("weekly artifacts require their separate fixed release folder")
    if any(path.is_symlink() or path.is_junction() for path in (artifact_root, *artifact_root.parents)):
        raise ForecastFinalizationError("artifact destinations cannot contain symbolic links or junctions")
    if artifact_root.exists():
        raise ForecastFinalizationError("weekly artifact folder already exists; preserve partial or completed output for review")


def _write_json_new(path: Path, payload: object) -> None:
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(payload, allow_nan=False, indent=2, sort_keys=True) + "\n")


def write_weekly_bundle(
    histories: Sequence[AssetPriceHistory], *, artifact_root: Path, manifest: FrozenHorizonManifest,
    calibration_report: dict[str, object], final_report: dict[str, object],
    expected_calibration_sha256: str, expected_final_test_sha256: str,
    source_selection_bytes: bytes, git_state: GitRevisionState, source_file_sha256: dict[str, str],
    accept_experimental_quality: bool, progress: Callable[[str], None] | None = None,
) -> dict[str, object]:
    """New-only package; root completion manifest is written after every reload check.

    Caller must verify the persisted snapshot and final-run markers before this
    offline writer. Partial output is preserved, never deleted or auto-retried.
    """
    if accept_experimental_quality is not True:
        raise ForecastFinalizationError("explicit experimental-quality acknowledgement is required")
    assert_new_artifact_root(artifact_root)
    manifest = horizon_manifest_from_dict(json.loads(horizon_manifest_json(manifest)))
    final_records = validate_final_report(final_report, manifest=manifest, calibration_report=calibration_report,
        expected_calibration_sha256=expected_calibration_sha256, expected_final_test_sha256=expected_final_test_sha256)
    if sha256_bytes(source_selection_bytes) != manifest.source_selection_report_sha256:
        raise ForecastFinalizationError("source selection bytes differ from frozen evidence")
    ordered = tuple(sorted(histories, key=lambda history: history.symbol))
    if len(ordered) != len(USER_ASSET_SYMBOLS) or {history.symbol for history in ordered} != set(USER_ASSET_SYMBOLS):
        raise ForecastFinalizationError("weekly training requires all 17 unique assets")
    if any(row.date > OFFICIAL_EVALUATION_CUTOFF for history in ordered for row in history.observations):
        raise ForecastFinalizationError("weekly training history exceeds the approved cutoff")
    timestamp = utc_creation_timestamp()
    versions = _library_versions()
    # Exclusive creation is the training guard. A failed build cannot overwrite
    # files or masquerade as a completed package; no final-run marker is changed.
    artifact_root.mkdir(parents=True, exist_ok=False)
    evidence = {
        "selection_manifest.json": json.loads(horizon_manifest_json(manifest)),
        "calibration_report.json": calibration_report, "final_test_report.json": final_report,
    }
    for name, payload in evidence.items():
        _write_json_new(artifact_root / name, payload)
    with (artifact_root / "source_selection_report.json").open("xb") as stream:
        stream.write(source_selection_bytes)
    binding = {
        "artifact_version": RELEASE_VERSION, "evaluation_cutoff": OFFICIAL_EVALUATION_CUTOFF.isoformat(),
        "selection_manifest_sha256": manifest.manifest_sha256,
        "calibration_sha256": expected_calibration_sha256, "final_test_sha256": expected_final_test_sha256,
        "final_test_run_state_sha256": final_report["run_state_sha256"],
        "training_data_fingerprint_sha256": manifest.market_data_fingerprint_sha256,
        "training_data_row_count": manifest.market_data_row_count, "git_commit": git_state.commit,
        "tracked_working_tree_clean": git_state.tracked_working_tree_clean,
        "source_file_sha256": source_file_sha256, "runtime_versions": versions, "creation_timestamp_utc": timestamp,
        "quality_status": QUALITY_STATUS, "experimental_quality_acknowledged": True,
        "predictive_quality_approved": False, "runtime_activated": False,
    }
    _write_json_new(artifact_root / "training_started.json", {**binding, "stage": "training_started"})
    features = {history.symbol: build_feature_rows(history) for history in ordered}
    by_symbol = {history.symbol: history for history in ordered}
    datasets, generated = {}, []
    for frozen, calibration, final in zip(manifest.records, calibration_report["records"], final_records, strict=True):
        selection, horizon = frozen.selection, frozen.horizon_days
        key = (selection.symbol, horizon)
        if key not in datasets:
            datasets[key] = build_horizon_dataset(by_symbol[key[0]], horizon_days=horizon, features=features[key[0]])
        if progress:
            progress(f"Training {selection.symbol} {target_name(selection.target_type, horizon)}, frozen candidate only...")
        model, trained, bridged, verification_features = train_horizon_artifact(dataset=datasets[key], frozen=frozen)
        directory = artifact_root / f"{horizon}d" / selection.symbol / model.target_type
        directory.mkdir(parents=True, exist_ok=False)
        model_path = directory / "model.joblib"
        with model_path.open("xb") as stream:
            joblib.dump(model, stream, compress=0)
        # Only deserialize the new trusted local output, never user-supplied paths.
        loaded = joblib.load(model_path)
        if (not isinstance(loaded, WeeklyArtifactModel) or loaded.symbol != model.symbol
            or loaded.horizon_days != model.horizon_days or loaded.target_type != model.target_type
            or loaded.candidate_id != model.candidate_id or loaded._model.model_family != trained.model_family
            or loaded.predict(steps=1, feature_matrix=verification_features) != model.predict(steps=1, feature_matrix=verification_features)):
            raise ForecastFinalizationError("weekly serialized model reload verification failed")
        coverage = final["interval_coverage"]
        warnings = list(dict.fromkeys(code for code in (selection.selection_warning, calibration["warning"],
            final["warning"], coverage["warning"], trained.warning) if code))
        if coverage["empirical_coverage"] < coverage["nominal_coverage"]:
            warnings.append("final_interval_coverage_below_nominal")
        metadata = {
            **binding, "artifact_schema_version": MODEL_SCHEMA, "symbol": model.symbol,
            "horizon_days": horizon, "horizon_unit": "calendar_days", "target_type": model.target_type,
            "feature_version": model.feature_version, "feature_names": list(FEATURE_NAMES), "target_version": model.target_version,
            "horizon_definition": {"calendar_days": horizon, "maximum_endpoint_slippage_days": MAX_ENDPOINT_SLIPPAGE_DAYS},
            "selected_candidate_id": model.candidate_id, "model_family": trained.model_family,
            "model_parameters": trained.model_parameters, "artifact_file_sha256": sha256_file(model_path),
            "eligible_completed_label_count": len(bridged.rows), "deployment_training_row_count": trained.training_row_count,
            "deployment_training_origin_min": trained.training_origin_min.isoformat(),
            "deployment_training_origin_max": trained.training_origin_max.isoformat(),
            "eligible_training_endpoint_max": max(row.target.endpoint_date for row in bridged.rows).isoformat(),
            "deployment_training_policy": "frozen candidate on all eligible labels complete through cutoff after final evidence is frozen; moving average retains its frozen window",
            "calibration_residual_q10": calibration["residual_q10"], "calibration_residual_q90": calibration["residual_q90"],
            "nominal_interval_coverage": .8, "interval_type": "empirical prediction interval; coverage not guaranteed",
            "volatility_prediction_rule": "max(raw_prediction, 0.0)" if selection.target_type is ForecastTargetType.VOLATILITY else None,
            "selection_evidence": asdict(frozen.selection) | {"target_type": model.target_type, "evaluation_cutoff": OFFICIAL_EVALUATION_CUTOFF.isoformat()},
            "calibration_evidence": calibration, "final_test_evidence": final,
            "deployment_fit_warning": trained.warning, "warning_codes": warnings,
        }
        _write_json_new(directory / "metadata.json", metadata)
        generated.append({"symbol": model.symbol, "horizon_days": horizon, "target_type": model.target_type,
            "selected_candidate_id": model.candidate_id, "model_path": model_path.relative_to(artifact_root).as_posix(),
            "metadata_path": (directory / "metadata.json").relative_to(artifact_root).as_posix(),
            "model_sha256": sha256_file(model_path), "metadata_sha256": sha256_file(directory / "metadata.json"),
            "deployment_fit_warning": trained.warning, "warning_codes": warnings})
    if len(generated) != SELECTION_COUNT:
        raise ForecastFinalizationError("weekly package did not complete all 102 models")
    for record in generated:
        if (sha256_file(artifact_root / record["model_path"]) != record["model_sha256"]
            or sha256_file(artifact_root / record["metadata_path"]) != record["metadata_sha256"]):
            raise ForecastFinalizationError("weekly artifact bytes changed before package completion")
    root_payload = {
        **binding, "artifact_schema_version": ROOT_SCHEMA, "horizons": list(NEW_HORIZONS), "horizon_unit": "calendar_days",
        "feature_version": FEATURE_SET_VERSION, "target_versions": {str(h): target_version(h) for h in NEW_HORIZONS},
        "expected_symbol_count": len(USER_ASSET_SYMBOLS), "expected_target_count": 2,
        "expected_artifact_count": SELECTION_COUNT, "generated_artifact_count": len(generated),
        "deployment_fit_warning_count": sum(record["deployment_fit_warning"] is not None for record in generated),
        "generated_artifacts": generated, "training_completed": True, "final_test_completed": True,
        "evidence_file_sha256": {name: sha256_file(artifact_root / name) for name in (*evidence, "source_selection_report.json", "training_started.json")},
        "limitations": final_report["limitations"] + [
            "Experimental weekly V1 has mixed per-asset quality and is not approved as reliable predictions.",
            "Post-evaluation fitting uses completed final-period labels for deployment, without rescoring the consumed final test.",
            "No runtime loader, API, portfolio interval, daily forecast path or client activation is implemented by this package.",
            "Joblib files are trusted local artifacts, never safe to load from an untrusted source; checksums alone are not signatures.",
        ],
    }
    payload = {**root_payload, "manifest_sha256": sha256_bytes(canonical_json_bytes(root_payload))}
    # Completion indicator written last. Missing manifest means incomplete output.
    _write_json_new(artifact_root / "manifest.json", payload)
    return payload
