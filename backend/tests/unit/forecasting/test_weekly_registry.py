"""Synthetic trusted bundles only; never load deployment artifacts in tests."""

from io import BytesIO
import json

import joblib
import pytest

from app.core.instruments import USER_ASSET_SYMBOLS
from app.forecasting import weekly_registry as module
from app.forecasting.evaluation import ForecastTargetType
from app.forecasting.features import FEATURE_NAMES, FEATURE_SET_VERSION
from app.forecasting.finalization import ForecastArtifactModel
from app.forecasting.fingerprints import canonical_json_bytes, sha256_bytes
from app.forecasting.horizon_artifacts import WeeklyArtifactModel
from app.forecasting.inference_errors import ForecastArtifactInvalidError, ForecastArtifactMissingError


def write_json(path, value):
    path.write_bytes(canonical_json_bytes(value))


def pin(root, manifest):
    manifest.pop("manifest_sha256", None)
    digest = sha256_bytes(canonical_json_bytes(manifest))
    manifest["manifest_sha256"] = digest
    write_json(root / "manifest.json", manifest)
    return module.WeeklyArtifactRegistry(artifact_root=root, expected_manifest_sha256=digest)


@pytest.fixture
def bundle(tmp_path):
    root = tmp_path / "synthetic-weekly"
    root.mkdir()
    binding = dict(artifact_version=module.WEEKLY_VERSION, evaluation_cutoff="2026-09-17",
        selection_manifest_sha256="a" * 64, calibration_sha256="b" * 64, final_test_sha256="c" * 64,
        final_test_run_state_sha256="d" * 64, training_data_fingerprint_sha256="e" * 64,
        training_data_row_count=69928, quality_status=module.QUALITY_STATUS,
        experimental_quality_acknowledged=True, predictive_quality_approved=False, runtime_activated=False)
    entries = []
    for horizon in module.WEEKLY_HORIZONS:
        for symbol in USER_ASSET_SYMBOLS:
            for target in ForecastTargetType:
                name = module.weekly_target_name(target, horizon)
                directory = root / f"{horizon}d" / symbol / name
                directory.mkdir(parents=True)
                model = WeeklyArtifactModel(symbol, horizon, name, "historical_average",
                    ForecastArtifactModel("historical_average", target, "historical_average", constant_prediction=horizon / 1000),
                    FEATURE_SET_VERSION, f"forecast-targets-{horizon}d-v1")
                stream = BytesIO()
                joblib.dump(model, stream)
                (directory / "model.joblib").write_bytes(stream.getvalue())
                model_hash = sha256_bytes(stream.getvalue())
                identity = dict(symbol=symbol, horizon_days=horizon, target_type=name, selected_candidate_id="historical_average")
                meta = dict(binding, **identity, artifact_schema_version=module.MODEL_SCHEMA,
                    horizon_unit="calendar_days", feature_version=FEATURE_SET_VERSION, feature_names=list(FEATURE_NAMES),
                    target_version=f"forecast-targets-{horizon}d-v1",
                    horizon_definition={"calendar_days": horizon, "maximum_endpoint_slippage_days": 4},
                    artifact_file_sha256=model_hash, nominal_interval_coverage=.8,
                    model_family="historical_average", model_parameters={"aggregation": "all_completed_labels"},
                    calibration_residual_q10=-.1, calibration_residual_q90=.2,
                    volatility_prediction_rule="max(raw_prediction, 0.0)" if target is ForecastTargetType.VOLATILITY else None,
                    warning_codes=["final_interval_coverage_below_nominal"], deployment_fit_warning=None,
                    selection_evidence=identity,
                    calibration_evidence=dict(identity, observation_count=60, residual_q10=-.1, residual_q90=.2),
                    final_test_evidence=dict(identity, frozen_residual_q10=-.1, frozen_residual_q90=.2,
                        interval_coverage={"empirical_coverage": .7}))
                write_json(directory / "metadata.json", meta)
                entries.append(dict(identity, model_path=(directory / "model.joblib").relative_to(root).as_posix(),
                    metadata_path=(directory / "metadata.json").relative_to(root).as_posix(), model_sha256=model_hash,
                    metadata_sha256=sha256_bytes((directory / "metadata.json").read_bytes()),
                    warning_codes=meta["warning_codes"], deployment_fit_warning=None))
    evidence = {}
    for name in ("selection_manifest.json", "calibration_report.json", "final_test_report.json",
                 "source_selection_report.json", "training_started.json"):
        write_json(root / name, {"synthetic": True})
        evidence[name] = sha256_bytes((root / name).read_bytes())
    manifest = dict(binding, artifact_schema_version=module.ROOT_SCHEMA,
        expected_symbol_count=17, expected_target_count=2, expected_artifact_count=102,
        generated_artifact_count=102, horizons=[7,14,21], horizon_unit="calendar_days",
        feature_version=FEATURE_SET_VERSION, training_completed=True, final_test_completed=True,
        generated_artifacts=entries, evidence_file_sha256=evidence)
    return root, manifest, pin(root, manifest)


def test_complete_bundle_before_load_cache_and_distinct_horizons(bundle, monkeypatch):
    root, manifest, registry = bundle
    load = module.joblib.load
    calls = []
    def checked_load(content):
        assert len(registry._records) == len(registry._metadata) == 102
        calls.append(1)
        return load(content)
    monkeypatch.setattr(module.joblib, "load", checked_load)
    for horizon in (7,14,21):
        artifact = registry.get("AAPL", ForecastTargetType.RETURN, horizon)
        assert artifact.model.predict(steps=1) == (horizon / 1000,)
        assert artifact.warning_codes == ("final_interval_coverage_below_nominal",)
        assert registry.get("AAPL", ForecastTargetType.RETURN, horizon) is artifact
    assert len(calls) == 3


@pytest.mark.parametrize("kind", ["model", "metadata", "evidence", "missing"])
def test_any_pair_or_evidence_drift_blocks_first_deserialization(bundle, monkeypatch, kind):
    root, manifest, registry = bundle
    record = manifest["generated_artifacts"][-1]  # Not the requested asset/target.
    if kind == "missing":
        (root / record["model_path"]).unlink()
    elif kind == "evidence":
        (root / "calibration_report.json").write_bytes(b"{}")
    else:
        (root / record[f"{kind}_path"]).write_bytes(b"tampered")
    load = []
    monkeypatch.setattr(module.joblib, "load", lambda *args: load.append(1))
    with pytest.raises((ForecastArtifactInvalidError, ForecastArtifactMissingError)):
        registry.get("AAPL", ForecastTargetType.RETURN, 7)
    assert load == []


def test_rehashed_unapproved_root_still_fails_external_pin(bundle):
    root, manifest, registry = bundle
    manifest["generated_artifacts"][0]["selected_candidate_id"] = "moving_average_90_calendar_days"
    pin(root, manifest)  # Recomputing a self-digest cannot change the original approval pin.
    with pytest.raises(ForecastArtifactInvalidError, match="reviewed"):
        registry.get("AAPL", ForecastTargetType.RETURN, 7)


@pytest.mark.parametrize("mutation", ["path", "duplicate", "missing_horizon", "bool_count", "approved"])
def test_trusted_test_pin_does_not_bypass_contract(bundle, mutation):
    root, manifest, _ = bundle
    if mutation == "path":
        manifest["generated_artifacts"][0]["model_path"] = "../model.joblib"
    elif mutation == "duplicate":
        manifest["generated_artifacts"][-1] = manifest["generated_artifacts"][0]
    elif mutation == "missing_horizon":
        manifest["horizons"] = [7,14,30]
    elif mutation == "bool_count":
        manifest["expected_target_count"] = True
    else:
        manifest["predictive_quality_approved"] = True
    with pytest.raises(ForecastArtifactInvalidError):
        pin(root, manifest).get("AAPL", ForecastTargetType.RETURN, 7)


@pytest.mark.parametrize("mutation", ["quantiles", "horizon", "warnings", "coverage", "feature_names"])
def test_rehashed_bad_metadata_rejected_before_loading(bundle, mutation, monkeypatch):
    root, manifest, _ = bundle
    record = manifest["generated_artifacts"][0]
    path = root / record["metadata_path"]
    meta = json.loads(path.read_bytes())
    if mutation == "quantiles":
        meta["calibration_residual_q10"] = .3
    elif mutation == "horizon":
        meta["horizon_days"] = 14
    elif mutation == "warnings":
        meta["warning_codes"] = ["suppressed"]
    elif mutation == "coverage":
        meta["final_test_evidence"]["interval_coverage"]["empirical_coverage"] = .9
    else:
        meta["feature_names"] = []
    write_json(path, meta)
    record["metadata_sha256"] = sha256_bytes(path.read_bytes())
    monkeypatch.setattr(module.joblib, "load", lambda *args: pytest.fail("deserialized bad metadata"))
    with pytest.raises(ForecastArtifactInvalidError):
        pin(root, manifest).get("AAPL", ForecastTargetType.RETURN, 7)


def test_bytes_rechecked_before_later_uncached_load(bundle):
    root, manifest, registry = bundle
    registry.get("AAPL", ForecastTargetType.RETURN, 7)
    record = next(row for row in manifest["generated_artifacts"]
                  if row["symbol"] == "AAPL" and row["target_type"] == "return_14d")
    (root / record["model_path"]).write_bytes(b"changed after validation")
    with pytest.raises(ForecastArtifactInvalidError, match="checksum"):
        registry.get("AAPL", ForecastTargetType.RETURN, 14)


@pytest.mark.parametrize("payload", [b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":1e999}', b'[]'])
def test_strict_json(payload):
    with pytest.raises(ForecastArtifactInvalidError):
        module._strict_json(payload)


@pytest.mark.parametrize("horizon", [True, 7., 0, 8, 30, "7"])
def test_invalid_horizon_rejected_without_reading(horizon, tmp_path):
    with pytest.raises(ForecastArtifactInvalidError):
        module.WeeklyArtifactRegistry(artifact_root=tmp_path).get("AAPL", ForecastTargetType.RETURN, horizon)


def test_wrong_serialized_wrapper_is_rejected_even_with_valid_pair_checksums(bundle, monkeypatch):
    _, _, registry = bundle
    wrong = WeeklyArtifactModel("MSFT", 14, "return_14d", "historical_average",
        ForecastArtifactModel("historical_average", ForecastTargetType.RETURN, "historical_average", constant_prediction=.01),
        FEATURE_SET_VERSION, "forecast-targets-14d-v1")
    monkeypatch.setattr(module.joblib, "load", lambda *args: wrong)
    with pytest.raises(ForecastArtifactInvalidError, match="serialized"):
        registry.get("AAPL", ForecastTargetType.RETURN, 7)
