import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import joblib
import pytest

from backend.app.core.instruments import USER_ASSET_SYMBOLS
from backend.app.forecasting.evaluation import ForecastTargetType
from backend.app.forecasting.finalization import ForecastArtifactModel
from backend.app.forecasting.inference_errors import (
    ForecastArtifactInvalidError, ForecastArtifactMissingError,
    ForecastArtifactVersionError, ForecastSymbolUnsupportedError,
)
from backend.app.forecasting.registry import ForecastArtifactRegistry


VERSION = "forecast-v1-20260917"


class FrozenSyntheticModel:
    def predict(self, features):
        return tuple(0.15 for row in features)

    def forecast(self, *, steps):
        return tuple(index / 100 for index in range(1, steps + 1))

    def __getattr__(self, name):
        if name in {"fit", "refit", "partial_fit", "append", "extend", "update"}:
            raise AssertionError("training or state update attempted")
        raise AttributeError(name)


def write_json(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def bundle(tmp_path):
    entries = []
    for symbol in USER_ASSET_SYMBOLS:
        for target in ForecastTargetType:
            directory = tmp_path / symbol / target.value
            directory.mkdir(parents=True)
            model_path = directory / "model.joblib"
            joblib.dump(ForecastArtifactModel("historical_average", target,
                                             "historical_average", constant_prediction=0.1), model_path)
            model_hash = hashlib.sha256(model_path.read_bytes()).hexdigest()
            metadata = {
                "artifact_schema_version": "forecast-artifact-v1", "artifact_version": VERSION,
                "symbol": symbol, "target_type": target.value, "selected_candidate_id": "historical_average",
                "model_family": "historical_average", "evaluation_cutoff": "2026-09-17",
                "feature_version": "forecast-features-v1", "target_version": "forecast-targets-v1",
                "nominal_interval_coverage": 0.80, "interval_type": "empirical prediction interval",
                "calibration_residual_q10": -0.2, "calibration_residual_q90": 0.3,
                "calibration_observation_count": 60, "artifact_file_sha256": model_hash,
                "selection_manifest_sha256": "a" * 64, "dataset_fingerprint_sha256": "b" * 64,
            }
            metadata_hash = write_json(directory / "metadata.json", metadata)
            entries.append({"symbol": symbol, "target_type": target.value,
                            "selected_candidate_id": "historical_average",
                            "model_path": f"{symbol}/{target.value}/model.joblib",
                            "metadata_path": f"{symbol}/{target.value}/metadata.json",
                            "model_sha256": model_hash, "metadata_sha256": metadata_hash})
    manifest = {
        "artifact_schema_version": "forecast-root-manifest-v1", "artifact_version": VERSION,
        "evaluation_cutoff": "2026-09-17", "expected_symbol_count": 17,
        "expected_target_count": 2, "expected_artifact_count": 34, "generated_artifact_count": 34,
        "final_test_completed": True, "nominal_interval_coverage": 0.80,
        "feature_version": "forecast-features-v1", "target_version": "forecast-targets-v1",
        "selection_manifest_sha256": "a" * 64, "training_data_fingerprint_sha256": "b" * 64,
        "generated_artifacts": entries,
    }
    write_json(tmp_path / "manifest.json", manifest)
    return tmp_path, manifest


def loader(root):
    return ForecastArtifactRegistry(artifact_version=VERSION, artifact_root=root)


def test_valid_bundle_model_cache_and_read_only_files(bundle):
    root, manifest = bundle
    before = {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()}
    registry = loader(root)
    with patch("backend.app.forecasting.registry.joblib.load", wraps=joblib.load) as load:
        first = registry.get("AAPL", ForecastTargetType.RETURN)
        assert registry.get("AAPL", ForecastTargetType.RETURN) is first
        registry.get("AAPL", ForecastTargetType.VOLATILITY)
        assert load.call_count == 2
    assert first.model.predict(steps=1) == (0.1,)
    after = {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()}
    assert after == before


@pytest.mark.parametrize("filename", ["manifest.json", "AAPL/return_30d/model.joblib", "AAPL/return_30d/metadata.json"])
def test_missing_required_files_fail_before_loading(bundle, filename):
    root, _ = bundle
    (root / filename).unlink()
    with patch("backend.app.forecasting.registry.joblib.load") as load:
        with pytest.raises(ForecastArtifactMissingError):
            loader(root).get("AAPL", ForecastTargetType.RETURN)
        load.assert_not_called()


@pytest.mark.parametrize("kind", ["model", "metadata"])
def test_corrupted_checksums_fail_before_deserialization(bundle, kind):
    root, manifest = bundle
    entry = next(item for item in manifest["generated_artifacts"] if item["symbol"] == "VTI")
    with (root / entry[f"{kind}_path"]).open("ab") as stream:
        stream.write(b"corruption")
    with patch("backend.app.forecasting.registry.joblib.load") as load:
        with pytest.raises(ForecastArtifactInvalidError, match="checksum"):
            loader(root).get("AAPL", ForecastTargetType.RETURN)
        load.assert_not_called()


@pytest.mark.parametrize("key, value", [
    ("expected_symbol_count", 16), ("expected_target_count", 1),
    ("expected_artifact_count", 33), ("generated_artifact_count", 33),
    ("final_test_completed", False), ("final_test_completed", 1),
    ("feature_version", "unknown"), ("target_version", "unknown"),
    ("artifact_schema_version", "unknown"),
])
def test_invalid_root_manifest_contract(bundle, key, value):
    root, manifest = bundle
    manifest[key] = value
    write_json(root / "manifest.json", manifest)
    with pytest.raises(ForecastArtifactInvalidError):
        loader(root).get("AAPL", ForecastTargetType.RETURN)


def test_configured_version_must_match(bundle):
    root, _ = bundle
    with pytest.raises(ForecastArtifactVersionError):
        ForecastArtifactRegistry(artifact_version="forecast-v2-20261001", artifact_root=root).get("AAPL", ForecastTargetType.RETURN)


def test_unsupported_symbol_never_loads(bundle):
    root, _ = bundle
    with patch("backend.app.forecasting.registry.joblib.load") as load:
        with pytest.raises(ForecastSymbolUnsupportedError):
            loader(root).get("UNKNOWN", ForecastTargetType.RETURN)
        load.assert_not_called()


@pytest.mark.parametrize("mutation", ["duplicate", "path", "candidate", "missing"])
def test_manifest_pair_identity_and_safe_paths(bundle, mutation):
    root, manifest = bundle
    entries = manifest["generated_artifacts"]
    if mutation == "duplicate":
        entries[-1] = entries[0]
    elif mutation == "path":
        entries[0]["model_path"] = "../outside.joblib"
    elif mutation == "candidate":
        entries[0]["selected_candidate_id"] = "unknown"
    else:
        entries.pop()
    write_json(root / "manifest.json", manifest)
    with pytest.raises(ForecastArtifactInvalidError):
        loader(root).get("AAPL", ForecastTargetType.RETURN)


@pytest.mark.parametrize("key, value", [
    ("calibration_residual_q10", float("nan")),
    ("calibration_residual_q10", 10 ** 500),
    ("calibration_residual_q90", -1), ("calibration_observation_count", 59),
    ("artifact_version", "wrong"), ("target_type", "wrong"),
])
def test_metadata_contract_checked_even_when_checksum_matches(bundle, key, value):
    root, manifest = bundle
    entry = manifest["generated_artifacts"][0]
    path = root / entry["metadata_path"]
    metadata = json.loads(path.read_text())
    metadata[key] = value
    entry["metadata_sha256"] = write_json(path, metadata)
    write_json(root / "manifest.json", manifest)
    with pytest.raises(ForecastArtifactInvalidError):
        loader(root).get("AAPL", ForecastTargetType.RETURN)


def test_unreadable_joblib_with_matching_checksum_is_controlled(bundle):
    root, manifest = bundle
    entry = manifest["generated_artifacts"][0]
    path = root / entry["model_path"]
    path.write_bytes(b"not joblib")
    entry["model_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    meta_path = root / entry["metadata_path"]
    meta = json.loads(meta_path.read_text())
    meta["artifact_file_sha256"] = entry["model_sha256"]
    entry["metadata_sha256"] = write_json(meta_path, meta)
    write_json(root / "manifest.json", manifest)
    with pytest.raises(ForecastArtifactInvalidError, match="deserialized"):
        loader(root).get(entry["symbol"], ForecastTargetType(entry["target_type"]))


@pytest.mark.parametrize("candidate, family", [
    ("volatility_linear_regression_v1", "linear_regression"),
    ("volatility_random_forest_v1", "random_forest"),
    ("volatility_arima_1_0_1_v1", "arima"),
])
def test_registry_loads_frozen_complex_models_without_fitting(bundle, candidate, family):
    root, manifest = bundle
    entry = next(item for item in manifest["generated_artifacts"]
                 if item["symbol"] == "AAPL" and item["target_type"] == ForecastTargetType.VOLATILITY.value)
    target = ForecastTargetType.VOLATILITY
    model_path = root / entry["model_path"]
    joblib.dump(ForecastArtifactModel(candidate, target, family, fitted_model=FrozenSyntheticModel()), model_path)
    entry["selected_candidate_id"] = candidate
    entry["model_sha256"] = hashlib.sha256(model_path.read_bytes()).hexdigest()
    metadata_path = root / entry["metadata_path"]
    metadata = json.loads(metadata_path.read_text())
    metadata.update(selected_candidate_id=candidate, model_family=family,
                    artifact_file_sha256=entry["model_sha256"])
    entry["metadata_sha256"] = write_json(metadata_path, metadata)
    write_json(root / "manifest.json", manifest)
    loaded = loader(root).get("AAPL", target)
    assert loaded.model.candidate_id == candidate
    assert loaded.model.predict(steps=1, feature_matrix=((1.0,),)) == (0.01 if family == "arima" else 0.15,)


def test_metadata_drift_before_later_model_load_is_rejected(bundle):
    root, _ = bundle
    registry = loader(root)
    registry.get("AAPL", ForecastTargetType.RETURN)
    path = root / "AAPL/realized_volatility_30d/metadata.json"
    with path.open("ab") as stream:
        stream.write(b" ")
    with pytest.raises(ForecastArtifactInvalidError, match="metadata checksum"):
        registry.get("AAPL", ForecastTargetType.VOLATILITY)
