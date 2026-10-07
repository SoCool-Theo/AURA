"""Synthetic weekly packaging and mocked DB/CLI checks; no live training data."""

from contextlib import contextmanager
from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import joblib
import pytest

import backend.scripts.train_forecasting_horizons as script
import backend.scripts.evaluate_forecasting_horizons as evaluator
from app.forecasting import finalization, horizon_artifacts as artifacts, horizon_final_test as final
from app.forecasting.artifacts import GitRevisionState
from app.forecasting.data import AssetPriceHistory, ForecastPriceObservation
from app.forecasting.evaluation import ForecastTargetType
from app.forecasting.features import FEATURE_NAMES, ForecastFeatureRow
from app.forecasting.finalization import ForecastArtifactModel, ForecastFinalizationError
from app.forecasting.fingerprints import canonical_json_bytes, sha256_bytes, sha256_file
from app.forecasting.multi_horizon import HorizonDataset, HorizonDatasetRow, HorizonTargetRow, target_name
from app.forecasting.selection_manifest import OFFICIAL_EVALUATION_CUTOFF
from backend.tests.unit.forecasting.test_horizon_selection_manifest import evidence_template
from backend.tests.unit.forecasting.test_horizon_calibration import manifest, _frozen
from backend.tests.unit.forecasting.test_horizon_final_test import calibration_template, calibration_report


def _rehash_final(payload):
    base = {key: value for key, value in payload.items() if key != "final_test_sha256"}
    return {**base, "final_test_sha256": sha256_bytes(canonical_json_bytes(base))}


def _final_record(calibration):
    horizon = calibration["horizon_days"]
    volatility = calibration["target_type"].startswith("realized")
    coverage = final.interval_coverage(actual_values=[0.] * 100, prediction_values=[0.] * 100,
        residual_q10=-.1, residual_q90=.1,
        target_type=ForecastTargetType.VOLATILITY if volatility else ForecastTargetType.RETURN)
    return {**{key: calibration[key] for key in ("symbol", "horizon_days", "target_type", "selected_candidate_id",
            "selection_warning", "feature_set_version", "target_set_version")},
        "calibration_warning": calibration["warning"], "warning": None, "fold_id": final.FINAL_FOLD.fold_id,
        "frozen_residual_q10": calibration["residual_q10"], "frozen_residual_q90": calibration["residual_q90"],
        "observation_count": 100, "training_observation_count": 1000, "candidate_training_value_count": 1000,
        "mae": .1, "rmse": .2, "directional_accuracy": None if volatility else .5,
        "negative_prediction_clipped_count": 0 if volatility else None,
        "interval_coverage": coverage, "training_cutoff_exclusive": "2025-09-18",
        "training_origin_min": "2020-01-01", "training_origin_max": (date(2025, 9, 17) - timedelta(days=horizon)).isoformat(),
        "training_endpoint_max": "2025-09-17", "evaluation_origin_start": "2025-09-18",
        "evaluation_origin_end_exclusive": "2026-09-18", "evaluated_origin_min": "2025-09-18",
        "evaluated_origin_max": (date(2026, 9, 17) - timedelta(days=horizon)).isoformat(), "evaluated_endpoint_max": "2026-09-17"}


@pytest.fixture
def final_report(manifest, calibration_report):
    report = {
        "report_schema": final.REPORT_SCHEMA, "stage": final.STAGE, "release_version": artifacts.RELEASE_VERSION,
        "evaluation_cutoff": "2026-09-17", "horizons": [7, 14, 21], "horizon_unit": "calendar_days",
        "record_count": 102, "selection_manifest_sha256": manifest.manifest_sha256,
        "source_selection_report_sha256": manifest.source_selection_report_sha256,
        "calibration_sha256": calibration_report["calibration_sha256"], "data_provenance": calibration_report["data_provenance"],
        "final_test_fold": {"fold_id": final.FINAL_FOLD.fold_id, "purpose": "final_test", "origin_start": "2025-09-18", "origin_end": "2026-09-18"},
        "nominal_interval_coverage": .8, "final_test_completed": True, "deployment_artifacts_created": False,
        "run_state_sha256": "c" * 64, "limitations": ["Overlapping labels are not independent."],
        "records": [_final_record(record) for record in calibration_report["records"]],
    }
    return _rehash_final(report)


def _validate(report, manifest, calibration):
    return artifacts.validate_final_report(report, manifest=manifest, calibration_report=calibration,
        expected_calibration_sha256=calibration["calibration_sha256"], expected_final_test_sha256=report["final_test_sha256"])


def test_final_report_is_pinned_and_preserves_warning_and_full_coverage(manifest, calibration_report, final_report):
    records = _validate(final_report, manifest, calibration_report)
    assert len(records) == 102 and sum(bool(row["selection_warning"]) for row in records) == 1
    with pytest.raises(ForecastFinalizationError, match="checksum"):
        artifacts.validate_final_report(final_report, manifest=manifest, calibration_report=calibration_report,
            expected_calibration_sha256=calibration_report["calibration_sha256"], expected_final_test_sha256="0" * 64)


@pytest.mark.parametrize("field,value", [("stage", "approved"), ("final_test_completed", False),
    ("deployment_artifacts_created", True), ("horizons", [7, 14, 30]), ("record_count", True),
    ("calibration_sha256", "0" * 64), ("selection_manifest_sha256", "0" * 64),
    ("data_provenance", {"provenance_verified": False}), ("run_state_sha256", "invalid"), ("limitations", "removed")])
def test_rehashed_wrong_final_contract_is_rejected(manifest, calibration_report, final_report, field, value):
    final_report[field] = value
    with pytest.raises(ValueError):
        _validate(_rehash_final(final_report), manifest, calibration_report)


@pytest.mark.parametrize("field,value", [("frozen_residual_q10", -.2), ("target_type", "realized_volatility_30d"),
    ("selected_candidate_id", "other"), ("horizon_days", 7.0), ("selection_warning", "removed"),
    ("calibration_warning", "removed"), ("observation_count", True), ("training_observation_count", 755),
    ("candidate_training_value_count", 1001), ("mae", -1), ("rmse", float("inf")),
    ("negative_prediction_clipped_count", 101), ("directional_accuracy", .5),
    ("training_endpoint_max", "2025-09-18"), ("evaluated_endpoint_max", "2026-09-18"), ("warning", "suppressed")])
def test_rehashed_invalid_final_record_is_rejected(manifest, calibration_report, final_report, field, value):
    final_report["records"][0][field] = value
    with pytest.raises(ValueError):
        _validate(_rehash_final(final_report), manifest, calibration_report)


@pytest.mark.parametrize("field,value", [("covered_count", 99), ("missed_count", 1), ("above_interval_count", 1),
    ("valid_interval_count", 99), ("observation_count", 99), ("empirical_coverage", .9),
    ("nominal_coverage", .9), ("warning", "removed"), ("mean_valid_interval_width", -1)])
def test_rehashed_bad_coverage_is_rejected(manifest, calibration_report, final_report, field, value):
    final_report["records"][0]["interval_coverage"][field] = value
    with pytest.raises(ValueError):
        _validate(_rehash_final(final_report), manifest, calibration_report)


def test_low_coverage_and_empty_intervals_are_retained_without_quality_gate(manifest, calibration_report, final_report):
    coverage = final_report["records"][0]["interval_coverage"]
    coverage.update(covered_count=0, missed_count=100, above_interval_count=100, empirical_coverage=0.)
    assert _validate(_rehash_final(final_report), manifest, calibration_report)[0]["interval_coverage"]["empirical_coverage"] == 0
    coverage.update(above_interval_count=0, empty_interval_count=100, valid_interval_count=0,
        mean_valid_interval_width=None, warning="empty_volatility_intervals_counted_as_misses")
    assert _validate(_rehash_final(final_report), manifest, calibration_report)[0]["interval_coverage"]["empty_interval_count"] == 100
    final_report["records"].reverse()
    with pytest.raises(ValueError):
        _validate(_rehash_final(final_report), manifest, calibration_report)


def _row(symbol, horizon, origin, value):
    features = ForecastFeatureRow(symbol, origin, **{name: .01 for name in FEATURE_NAMES})
    endpoint = origin + timedelta(days=horizon)
    return HorizonDatasetRow(features, HorizonTargetRow(symbol, horizon, origin, endpoint, endpoint, 0, value, abs(value)))


def _dataset(symbol="AAPL", horizon=7, count=800):
    rows = [_row(symbol, horizon, date(2023, 1, 1) + timedelta(days=index), .1) for index in range(count)]
    rows += [_row(symbol, horizon, OFFICIAL_EVALUATION_CUTOFF - timedelta(days=horizon), .2),
             _row(symbol, horizon, OFFICIAL_EVALUATION_CUTOFF - timedelta(days=horizon - 1), 999.)]
    return HorizonDataset(symbol, horizon, 2000, len(rows), len(rows), tuple(rows))


@pytest.mark.parametrize("horizon", [7, 14, 21])
@pytest.mark.parametrize("target", list(ForecastTargetType))
def test_training_uses_actual_labels_complete_through_cutoff_not_future_labels(manifest, horizon, target):
    dataset = _dataset(horizon=horizon)
    model, trained, eligible, features = artifacts.train_horizon_artifact(dataset=dataset, frozen=_frozen(manifest, horizon, target))
    assert len(eligible.rows) == trained.training_row_count == 801
    assert model.horizon_days == horizon and model.target_type == target_name(target, horizon)
    assert eligible.rows[-1].target.endpoint_date == OFFICIAL_EVALUATION_CUTOFF
    assert model.predict(steps=1, feature_matrix=features) == pytest.approx(((800 * .1 + .2) / 801,))
    assert trained.training_origin_max == OFFICIAL_EVALUATION_CUTOFF - timedelta(days=horizon)


def test_bad_identity_or_insufficient_history_blocks_fitting(manifest, monkeypatch):
    fitter = MagicMock()
    monkeypatch.setattr(artifacts, "train_deployment_artifact", fitter)
    with pytest.raises(ValueError, match="identity"):
        artifacts.train_horizon_artifact(dataset=_dataset(horizon=14), frozen=_frozen(manifest))
    with pytest.raises(ValueError, match="minimum"):
        artifacts.train_horizon_artifact(dataset=_dataset(count=10), frozen=_frozen(manifest))
    fitter.assert_not_called()


def test_wrapper_clips_volatility_but_preserves_negative_return_and_weekly_identity():
    for target in ForecastTargetType:
        inner = ForecastArtifactModel("historical_average", target, "historical_average", constant_prediction=-.2)
        model = artifacts.WeeklyArtifactModel("AAPL", 7, target_name(target, 7), inner.candidate_id, inner,
            "forecast-features-v1", "forecast-targets-7d-v1")
        assert model.predict(steps=1) == (0. if target is ForecastTargetType.VOLATILITY else -.2,)
        model.horizon_days = 30
        with pytest.raises(ValueError, match="identity"):
            model.predict(steps=1)


def _writer_args(tmp_path, manifest, evidence_template, calibration_report, final_report):
    return dict(artifact_root=tmp_path / "forecasting" / artifacts.RELEASE_VERSION, manifest=manifest,
        calibration_report=calibration_report, final_report=final_report,
        expected_calibration_sha256=calibration_report["calibration_sha256"], expected_final_test_sha256=final_report["final_test_sha256"],
        source_selection_bytes=evaluator.report_json(evidence_template).encode(), git_state=GitRevisionState("a" * 40, False),
        source_file_sha256={"backend/app/forecasting/horizon_artifacts.py": "d" * 64}, accept_experimental_quality=True)


def _histories():
    return tuple(AssetPriceHistory(symbol, (ForecastPriceObservation(date(2024, 1, 1), 100.),)) for symbol in script.USER_ASSET_SYMBOLS)


class _ConstantFitted:
    def fit(self, features, targets):
        assert len(features) == len(targets) and max(targets) < 999
        return self

    def forecast(self, *, steps):
        return [.1] * steps

    def predict(self, features):
        return [.1] * len(features)


@pytest.mark.parametrize("candidate", ["moving_average_90_calendar_days", "linear_regression_v1", "random_forest_v1", "arima_1_0_1_v1"])
def test_frozen_families_parameters_and_warning_are_reused_without_live_fitting(manifest, monkeypatch, candidate):
    frozen = _frozen(manifest)
    frozen = replace(frozen, selection=replace(frozen.selection, selected_candidate_id=candidate))
    monkeypatch.setattr(finalization, "build_linear_regression_pipeline", _ConstantFitted)
    monkeypatch.setattr(finalization, "build_random_forest_regressor", _ConstantFitted)
    monkeypatch.setattr(finalization, "_fit_arima_with_warning_metadata", lambda _: (_ConstantFitted(), True))
    start = OFFICIAL_EVALUATION_CUTOFF - timedelta(days=806)
    rows = tuple(_row("AAPL", 7, start + timedelta(days=index), .1) for index in range(800))
    rows += (_row("AAPL", 7, OFFICIAL_EVALUATION_CUTOFF - timedelta(days=6), 999.),)
    dataset = HorizonDataset("AAPL", 7, 2000, len(rows), len(rows), rows)
    model, trained, eligible, _ = artifacts.train_horizon_artifact(dataset=dataset, frozen=frozen)
    assert model.candidate_id == candidate
    assert (trained.model_family, trained.model_parameters) == finalization._model_family_and_parameters(candidate)
    assert max(row.target.endpoint_date for row in eligible.rows) == OFFICIAL_EVALUATION_CUTOFF
    if candidate == "moving_average_90_calendar_days":
        assert trained.training_row_count == 90
        assert model.predict(steps=1) == pytest.approx((.1,))
    if candidate == "arima_1_0_1_v1":
        assert trained.warning == "arima_fit_convergence_warning"


def _mock_builders(monkeypatch):
    features, datasets = MagicMock(return_value=()), MagicMock(side_effect=lambda history, **kw: _dataset(history.symbol, kw["horizon_days"]))
    monkeypatch.setattr(artifacts, "build_feature_rows", features)
    monkeypatch.setattr(artifacts, "build_horizon_dataset", datasets)
    def training(*, dataset, selection, evaluation_cutoff):
        # Keep the entire packaging test synthetic, including selected ARIMA.
        family, parameters = finalization._model_family_and_parameters(selection.selected_candidate_id)
        baseline = family in {"historical_average", "moving_average"}
        model = ForecastArtifactModel(selection.selected_candidate_id, selection.target_type, family,
            constant_prediction=.1 if baseline else None, fitted_model=None if baseline else _ConstantFitted())
        return finalization.DeploymentTrainingResult(dataset.symbol, selection.target_type, selection.selected_candidate_id,
            family, parameters, model, len(dataset.rows),
            dataset.rows[0].features.origin_date, dataset.rows[-1].features.origin_date, None)
    monkeypatch.setattr(artifacts, "train_deployment_artifact", training)
    return features, datasets


def test_bundle_has_102_reload_checked_models_actual_horizons_and_frozen_evidence(tmp_path, manifest, evidence_template,
    calibration_report, final_report, monkeypatch):
    features, datasets = _mock_builders(monkeypatch)
    final_report["records"][0]["interval_coverage"].update(covered_count=50, missed_count=50, above_interval_count=50, empirical_coverage=.5)
    final_report = _rehash_final(final_report)
    args = _writer_args(tmp_path, manifest, evidence_template, calibration_report, final_report)
    originals = canonical_json_bytes([calibration_report, final_report])
    result = artifacts.write_weekly_bundle(_histories(), **args)
    root = args["artifact_root"]
    assert features.call_count == 17 and datasets.call_count == 51
    assert len(result["generated_artifacts"]) == 102 and len(list(root.rglob("model.joblib"))) == 102
    assert result["runtime_activated"] is False and result["predictive_quality_approved"] is False
    assert result["tracked_working_tree_clean"] is False
    assert result["quality_status"] == artifacts.QUALITY_STATUS
    digest = result["manifest_sha256"]
    assert digest == sha256_bytes(canonical_json_bytes({key: value for key, value in result.items() if key != "manifest_sha256"}))
    for record in result["generated_artifacts"]:
        model = joblib.load(root / record["model_path"])
        metadata = json.loads((root / record["metadata_path"]).read_text())
        assert isinstance(model, artifacts.WeeklyArtifactModel)
        assert model.horizon_days == metadata["horizon_days"] == record["horizon_days"]
        assert model.target_type == metadata["target_type"] == record["target_type"]
        assert sha256_file(root / record["model_path"]) == record["model_sha256"]
        assert sha256_file(root / record["metadata_path"]) == record["metadata_sha256"]
        assert metadata["eligible_training_endpoint_max"] == "2026-09-17"
        assert "30d" not in json.dumps(metadata)
    first = json.loads((root / result["generated_artifacts"][0]["metadata_path"]).read_text())
    assert "final_interval_coverage_below_nominal" in first["warning_codes"]
    assert first["final_test_evidence"]["interval_coverage"]["empirical_coverage"] == .5
    assert canonical_json_bytes([calibration_report, final_report]) == originals
    for name, digest in result["evidence_file_sha256"].items():
        assert sha256_file(root / name) == digest
    assert (root / "source_selection_report.json").read_bytes() == args["source_selection_bytes"]
    with pytest.raises(ValueError, match="already exists"):
        artifacts.write_weekly_bundle(_histories(), **args)


def test_failed_training_preserves_partial_folder_without_completion_manifest(tmp_path, manifest, evidence_template,
    calibration_report, final_report, monkeypatch):
    _mock_builders(monkeypatch)
    monkeypatch.setattr(artifacts, "train_horizon_artifact", MagicMock(side_effect=RuntimeError("private failure")))
    args = _writer_args(tmp_path, manifest, evidence_template, calibration_report, final_report)
    with pytest.raises(RuntimeError):
        artifacts.write_weekly_bundle(_histories(), **args)
    assert (args["artifact_root"] / "training_started.json").exists()
    assert not (args["artifact_root"] / "manifest.json").exists()
    with pytest.raises(ValueError, match="already exists"):
        artifacts.write_weekly_bundle(_histories(), **args)


def test_failed_reload_never_creates_completed_manifest(tmp_path, manifest, evidence_template, calibration_report, final_report, monkeypatch):
    _mock_builders(monkeypatch)
    monkeypatch.setattr(artifacts.joblib, "load", lambda _: object())
    args = _writer_args(tmp_path, manifest, evidence_template, calibration_report, final_report)
    with pytest.raises(ValueError, match="reload"):
        artifacts.write_weekly_bundle(_histories(), **args)
    assert list(args["artifact_root"].rglob("model.joblib"))
    assert not (args["artifact_root"] / "manifest.json").exists()


@pytest.mark.parametrize("problem", ["acknowledgement", "source", "missing_history", "duplicate_history", "future_history", "final_hash", "v1_root"])
def test_preflight_failure_creates_no_folder_or_models(tmp_path, manifest, evidence_template, calibration_report, final_report, monkeypatch, problem):
    fit = MagicMock()
    monkeypatch.setattr(artifacts, "train_horizon_artifact", fit)
    args = _writer_args(tmp_path, manifest, evidence_template, calibration_report, final_report)
    histories = _histories()
    if problem == "acknowledgement": args["accept_experimental_quality"] = False
    if problem == "source": args["source_selection_bytes"] = b"changed"
    if problem == "missing_history": histories = histories[:-1]
    if problem == "duplicate_history": histories = (*histories[:-1], histories[0])
    if problem == "future_history": histories = (*histories[:-1], AssetPriceHistory(histories[-1].symbol,
        (ForecastPriceObservation(date(2026, 9, 18), 100.),)))
    if problem == "final_hash": args["expected_final_test_sha256"] = "0" * 64
    if problem == "v1_root": args["artifact_root"] = tmp_path / "forecasting/forecast-v1-20260917"
    with pytest.raises(ValueError):
        artifacts.write_weekly_bundle(histories, **args)
    fit.assert_not_called()
    assert not args["artifact_root"].exists()


def _files_args(tmp_path, manifest, evidence_template, calibration_report, final_report):
    evidence = tmp_path / "forecasting-evidence/new"
    evidence.mkdir(parents=True)
    manifest_path, source_path, cal_path, final_path = (evidence / name for name in ("manifest.json", "selection.json", "calibration.json", "final.json"))
    manifest_path.write_text(artifacts.horizon_manifest_json(manifest), encoding="utf-8")
    source_path.write_bytes(evaluator.report_json(evidence_template).encode())
    cal_path.write_text(json.dumps(calibration_report), encoding="utf-8")
    start = {"schema_version": "forecast-weekly-final-test-run-v1", "release_version": artifacts.RELEASE_VERSION,
        "stage": "final_test_started", "selection_manifest_sha256": manifest.manifest_sha256,
        "calibration_sha256": calibration_report["calibration_sha256"], "market_data_fingerprint_sha256": manifest.market_data_fingerprint_sha256,
        "market_data_row_count": manifest.market_data_row_count, "output_relative_path": final_path.relative_to(tmp_path).as_posix()}
    run_hash = sha256_bytes(canonical_json_bytes(start))
    final_report["run_state_sha256"] = run_hash
    final_report = _rehash_final(final_report)
    final_path.write_text(json.dumps(final_report), encoding="utf-8")
    marker_root = tmp_path / "forecasting-evidence" / artifacts.RELEASE_VERSION
    marker_root.mkdir()
    started, completed = marker_root / "final-test-started.json", marker_root / "final-test-completed.json"
    started.write_text(json.dumps({**start, "run_state_sha256": run_hash}), encoding="utf-8")
    completed.write_text(json.dumps({"schema_version": "forecast-weekly-final-test-run-v1", "release_version": artifacts.RELEASE_VERSION,
        "stage": "final_test_completed", "run_state_sha256": run_hash, "final_test_sha256": final_report["final_test_sha256"]}), encoding="utf-8")
    args = ["--env-file", str(tmp_path / "offline.env"), "--database-url-key", "TEST_DATABASE_URL", "--database-name", "aura_forecast_training_20260917",
        "--selection-manifest", str(manifest_path), "--selection-report", str(source_path), "--expected-manifest-sha256", manifest.manifest_sha256,
        "--calibration", str(cal_path), "--expected-calibration-sha256", calibration_report["calibration_sha256"],
        "--final-test", str(final_path), "--expected-final-test-sha256", final_report["final_test_sha256"], "--accept-experimental-quality"]
    return (manifest_path, source_path, cal_path, final_path, started, completed), args


def _patch_cli(tmp_path, monkeypatch):
    monkeypatch.setattr(script, "REPOSITORY_ROOT", tmp_path)
    monkeypatch.setattr(script, "source_hashes", lambda: {"source.py": "d" * 64})
    monkeypatch.setattr(script, "read_git_revision_state", lambda _: GitRevisionState("a" * 40, False))
    env = MagicMock(return_value="postgresql+psycopg://aura:private@127.0.0.1:5433/db")
    db = MagicMock(return_value=_histories())
    writer = MagicMock(return_value={"generated_artifact_count": 102, "deployment_fit_warning_count": 0, "manifest_sha256": "e" * 64})
    monkeypatch.setattr(script, "database_url_from_env_file", env)
    monkeypatch.setattr(script, "read_verified_training_histories", db)
    monkeypatch.setattr(script, "write_weekly_bundle", writer)
    return env, db, writer


def test_cli_preserves_evidence_markers_and_passes_exact_pins_without_final_scoring(tmp_path, manifest, evidence_template,
    calibration_report, final_report, monkeypatch, capsys):
    env, db, writer = _patch_cli(tmp_path, monkeypatch)
    files, args = _files_args(tmp_path, manifest, evidence_template, calibration_report, final_report)
    originals = [path.read_bytes() for path in files]
    script.main(args)
    assert evaluator.make_url(db.call_args.kwargs["database_url"]).database == "aura_forecast_training_20260917"
    assert writer.call_args.kwargs["expected_final_test_sha256"] == args[args.index("--expected-final-test-sha256") + 1]
    assert writer.call_args.kwargs["artifact_root"] == script.artifact_root()
    assert [path.read_bytes() for path in files] == originals
    assert "private" not in capsys.readouterr().out


@pytest.mark.parametrize("problem", ["acknowledgement", "final_pin", "bad_final_json", "completion_missing", "completion_hash", "start_binding", "existing_root"])
def test_cli_bad_preflight_stops_before_env_db_or_training(tmp_path, manifest, evidence_template, calibration_report, final_report, monkeypatch, problem):
    env, db, writer = _patch_cli(tmp_path, monkeypatch)
    files, args = _files_args(tmp_path, manifest, evidence_template, calibration_report, final_report)
    if problem == "acknowledgement": args.pop()
    if problem == "final_pin": args[args.index("--expected-final-test-sha256") + 1] = "0" * 64
    if problem == "bad_final_json": files[3].write_bytes(b'{"records": [], "records": [], "value": NaN}')
    if problem == "completion_missing": files[-1].unlink()
    if problem == "completion_hash":
        payload = json.loads(files[-1].read_text()); payload["final_test_sha256"] = "0" * 64
        files[-1].write_text(json.dumps(payload))
    if problem == "start_binding":
        payload = json.loads(files[-2].read_text()); payload["output_relative_path"] = "other.json"
        files[-2].write_text(json.dumps(payload))
    if problem == "existing_root": script.artifact_root().mkdir(parents=True)
    with pytest.raises(SystemExit) as error:
        script.main(args)
    assert "private" not in str(error.value)
    env.assert_not_called(); db.assert_not_called(); writer.assert_not_called()


def test_db_is_read_only_verified_and_closed_before_returning_histories(manifest, monkeypatch):
    engine, session = MagicMock(), MagicMock()
    records = tuple(SimpleNamespace(symbol=symbol, date=date(2024, 1, 1), adjusted_close=Decimal("100"), volume=None,
        source="synthetic") for symbol in script.USER_ASSET_SYMBOLS)
    @contextmanager
    def scope(_):
        yield session
    monkeypatch.setattr(script, "create_database_engine", lambda *a, **kw: engine)
    monkeypatch.setattr(script, "create_session_factory", lambda _: object())
    monkeypatch.setattr(script, "session_scope", scope)
    monkeypatch.setattr(script, "MarketDataService", lambda _: SimpleNamespace(get_range=lambda *a: records))
    # Real provenance mismatch must stop before fitting/output.
    with pytest.raises(script.SelectionProvenanceError):
        script.read_verified_training_histories(database_url="postgresql+psycopg://aura:private@127.0.0.1:5433/db", manifest=manifest)
    engine.dispose.assert_called_once()
    assert str(session.execute.call_args.args[0]) == "SET TRANSACTION READ ONLY"
    verify = MagicMock()
    monkeypatch.setattr(script, "verify_selection_records", verify)
    engine.dispose.reset_mock()
    histories = script.read_verified_training_histories(database_url="postgresql+psycopg://aura:private@127.0.0.1:5433/db", manifest=manifest)
    engine.dispose.assert_called_once()
    assert len(histories) == 17
    assert verify.call_args.kwargs["expected_fingerprint"] == manifest.market_data_fingerprint_sha256
    session.add.assert_not_called(); session.delete.assert_not_called()


def test_weekly_training_is_not_imported_by_runtime_and_never_rescores_final_test():
    root = Path(script.__file__).resolve().parents[2]
    for module in (script, artifacts):
        source = Path(module.__file__).read_text(encoding="utf-8")
        assert "evaluate_final_histories(" not in source and "calibrate_histories(" not in source
        assert "evaluate_frozen_final_test(" not in source and "mark_final_test_started(" not in source
    for relative in ("backend/app/forecasting/registry.py", "backend/app/forecasting/inference.py", "backend/app/api/routes/forecasting.py"):
        assert "horizon_artifacts" not in (root / relative).read_text(encoding="utf-8")


@pytest.mark.parametrize("link_kind", ["is_symlink", "is_junction"])
def test_linked_output_ancestors_are_rejected_without_writes(tmp_path, monkeypatch, link_kind):
    ancestor = tmp_path / "forecasting"
    monkeypatch.setattr(Path, link_kind, lambda path: path == ancestor)
    root = ancestor / artifacts.RELEASE_VERSION
    with pytest.raises(ValueError, match="links or junctions"):
        artifacts.assert_new_artifact_root(root)
    assert not root.exists()
