"""Synthetic/mocked weekly calibration checks; no live DB or estimator fit."""

from contextlib import contextmanager
from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import backend.scripts.calibrate_forecasting_horizons as script
import backend.scripts.evaluate_forecasting_horizons as evaluator
from app.forecasting import horizon_calibration as calibration
from app.forecasting.data import AssetPriceHistory, ForecastPriceObservation
from app.forecasting.evaluation import CandidatePrediction, ForecastTargetType
from app.forecasting.finalization import ForecastFinalizationError
from app.forecasting.fingerprints import canonical_json_bytes, sha256_bytes, build_market_data_fingerprint
from app.forecasting.horizon_selection_manifest import (
    HorizonSelectionError, freeze_horizon_manifest, horizon_manifest_json,
)
from app.forecasting.models import ARIMA_FIT_CONVERGENCE_WARNING
from app.forecasting.multi_horizon import HorizonDataset, HorizonDatasetRow, HorizonTargetRow, NEW_HORIZONS, target_name

# Reuse the existing complete synthetic selection fixture, not local evidence.
from backend.tests.unit.forecasting.test_horizon_selection_manifest import evidence_template, FINGERPRINT, ROW_COUNT


@pytest.fixture(scope="module")
def manifest(evidence_template):
    raw = evaluator.report_json(evidence_template).encode()
    return freeze_horizon_manifest(report=evidence_template, source_report_sha256=sha256_bytes(raw),
                                  expected_market_data_fingerprint=FINGERPRINT, expected_row_count=ROW_COUNT)


def _frozen(manifest, horizon=7, target=ForecastTargetType.RETURN):
    return next(record for record in manifest.records if record.horizon_days == horizon
                and record.selection.symbol == "AAPL" and record.selection.target_type is target)


def _row(origin, horizon, value):
    endpoint = origin + timedelta(days=horizon)
    return HorizonDatasetRow(SimpleNamespace(symbol="AAPL", origin_date=origin),
                             HorizonTargetRow("AAPL", horizon, origin, endpoint, endpoint, 0, value, max(0., value)))


def _dataset(horizon=7, training_count=800, calibration_count=60):
    fold = calibration.CALIBRATION_FOLD
    rows = [*(_row(date(2022, 1, 1) + timedelta(days=index), horizon, .1) for index in range(training_count)),
            _row(fold.origin_start - timedelta(days=horizon), horizon, 99.),  # training endpoint equals start
            *(_row(fold.origin_start + timedelta(days=index), horizon, index / 100) for index in range(calibration_count)),
            _row(fold.origin_end - timedelta(days=horizon), horizon, 999.),  # scored endpoint equals end
            _row(fold.origin_end, horizon, 9999.)]  # final-test origin
    return HorizonDataset("AAPL", horizon, 2000, len(rows), len(rows),
                          tuple(sorted(rows, key=lambda row: row.features.origin_date)))


class _ConstantCandidate:
    candidate_id = "historical_average"

    def __init__(self, value=.1, warning=None):
        self.value, self.warning = value, warning
        self.calls = []

    def predict(self, *, training_rows, evaluation_rows, target_type, information_cutoff):
        self.calls.append((training_rows, evaluation_rows, target_type, information_cutoff))
        return CandidatePrediction(self.candidate_id, tuple(self.value for _ in evaluation_rows),
                                   len(training_rows), warning=self.warning)


def _use_candidate(monkeypatch, candidate):
    real_calibration = calibration.calibrate_frozen_selection
    monkeypatch.setattr(calibration, "calibrate_frozen_selection",
                        lambda **kwargs: real_calibration(**kwargs, candidate=candidate))


@pytest.mark.parametrize("horizon", NEW_HORIZONS)
@pytest.mark.parametrize("target", list(ForecastTargetType))
def test_actual_horizon_calibration_purges_both_endpoints_and_does_not_scale_v1(manifest, monkeypatch, horizon, target):
    candidate = _ConstantCandidate()
    _use_candidate(monkeypatch, candidate)
    result = calibration.calibrate_horizon_selection(dataset=_dataset(horizon), frozen=_frozen(manifest, horizon, target))
    assert len(candidate.calls) == 1
    training, evaluated, actual_target, cutoff = candidate.calls[0]
    assert len(training) == result["training_observation_count"] == 800
    assert len(evaluated) == result["observation_count"] == 60
    assert actual_target is target and cutoff == calibration.CALIBRATION_FOLD.origin_start
    assert all(row.target.endpoint_date < cutoff for row in training)
    assert all(cutoff <= row.features.origin_date < calibration.CALIBRATION_FOLD.origin_end
               and row.target.endpoint_date < calibration.CALIBRATION_FOLD.origin_end for row in evaluated)
    assert [row.target.return_30d for row in evaluated] == pytest.approx([index / 100 for index in range(60)])
    assert result["target_type"] == target_name(target, horizon)
    assert result["target_set_version"] == f"forecast-targets-{horizon}d-v1"
    assert result["residual_q10"] == pytest.approx(-.041)
    assert result["residual_q90"] == pytest.approx(.431)
    assert result["training_endpoint_max"] < result["training_cutoff_exclusive"]
    assert result["evaluated_endpoint_max"] < result["evaluation_origin_end_exclusive"]


def test_volatility_is_clipped_before_new_residual_quantiles(manifest, monkeypatch):
    candidate = _ConstantCandidate(value=-.2)
    _use_candidate(monkeypatch, candidate)
    result = calibration.calibrate_horizon_selection(dataset=_dataset(), frozen=_frozen(manifest, target=ForecastTargetType.VOLATILITY))
    assert result["negative_prediction_clipped_count"] == 60
    assert result["residual_q10"] == pytest.approx(.059)
    assert result["residual_q90"] == pytest.approx(.531)


@pytest.mark.parametrize("training_count,calibration_count", [(755, 60), (800, 59)])
def test_insufficient_training_or_residuals_stops_before_fitting(manifest, monkeypatch, training_count, calibration_count):
    fitting = MagicMock()
    monkeypatch.setattr(calibration, "calibrate_frozen_selection", fitting)
    with pytest.raises(ForecastFinalizationError):
        calibration.calibrate_horizon_selection(dataset=_dataset(training_count=training_count, calibration_count=calibration_count),
                                                frozen=_frozen(manifest))
    fitting.assert_not_called()


@pytest.mark.parametrize("change", ["symbol", "horizon", "cutoff", "monthly"])
def test_wrong_selection_identity_stops_before_fitting(manifest, monkeypatch, change):
    frozen = _frozen(manifest)
    if change == "symbol":
        frozen = replace(frozen, selection=replace(frozen.selection, symbol="MSFT"))
    elif change == "cutoff":
        frozen = replace(frozen, selection=replace(frozen.selection, evaluation_cutoff=date(2026, 10, 7)))
    else:
        frozen = replace(frozen, horizon_days=14 if change == "horizon" else 30)
    fitting = MagicMock()
    monkeypatch.setattr(calibration, "calibrate_frozen_selection", fitting)
    with pytest.raises(ForecastFinalizationError):
        calibration.calibrate_horizon_selection(dataset=_dataset(), frozen=frozen)
    fitting.assert_not_called()


def test_different_candidate_is_not_used_as_a_fallback(manifest, monkeypatch):
    candidate = _ConstantCandidate()
    candidate.candidate_id = "moving_average_90_calendar_days"
    _use_candidate(monkeypatch, candidate)
    with pytest.raises(ForecastFinalizationError, match="frozen selection"):
        calibration.calibrate_horizon_selection(dataset=_dataset(), frozen=_frozen(manifest))
    assert candidate.calls == []


def test_selected_and_new_fit_warnings_remain_separate(manifest, monkeypatch):
    frozen = next(record for record in manifest.records if record.selection.selection_warning)
    original = _dataset(frozen.horizon_days)
    dataset = replace(original, symbol=frozen.selection.symbol, rows=tuple(HorizonDatasetRow(
        SimpleNamespace(symbol=frozen.selection.symbol, origin_date=row.features.origin_date),
        replace(row.target, symbol=frozen.selection.symbol),
    ) for row in original.rows))
    candidate = _ConstantCandidate(warning=ARIMA_FIT_CONVERGENCE_WARNING)
    candidate.candidate_id = frozen.selection.selected_candidate_id
    _use_candidate(monkeypatch, candidate)
    result = calibration.calibrate_horizon_selection(dataset=dataset, frozen=frozen)
    assert result["selection_warning"] == result["warning"] == ARIMA_FIT_CONVERGENCE_WARNING


def _short_histories():
    return tuple(AssetPriceHistory(symbol, (
        ForecastPriceObservation(date(2024, 1, 1), 100.),
        ForecastPriceObservation(date(2025, 4, 1), 110.),
        ForecastPriceObservation(calibration.CALIBRATION_FOLD.origin_end, 10000.),
        ForecastPriceObservation(date(2026, 9, 17), 20000.),
    )) for symbol in script.USER_ASSET_SYMBOLS)


def _mock_history_calibration(monkeypatch):
    seen = []
    features = MagicMock(side_effect=lambda history: seen.append(history) or ())
    datasets = MagicMock(side_effect=lambda history, **kwargs: SimpleNamespace(symbol=history.symbol, horizon_days=kwargs["horizon_days"]))
    def calibrate(*, dataset, frozen):
        assert dataset.symbol == frozen.selection.symbol and dataset.horizon_days == frozen.horizon_days
        return {"symbol": dataset.symbol, "horizon_days": dataset.horizon_days,
                "target_type": target_name(frozen.selection.target_type, frozen.horizon_days),
                "selection_warning": frozen.selection.selection_warning, "warning": None}
    calls = MagicMock(side_effect=calibrate)
    monkeypatch.setattr(calibration, "build_feature_rows", features)
    monkeypatch.setattr(calibration, "build_horizon_dataset", datasets)
    monkeypatch.setattr(calibration, "calibrate_horizon_selection", calls)
    return seen, features, datasets, calls


def test_all_102_calibrations_reuse_features_and_never_construct_final_period_labels(manifest, monkeypatch):
    seen, features, datasets, calls = _mock_history_calibration(monkeypatch)
    histories = _short_histories()
    report = calibration.calibrate_histories(histories, manifest=manifest)
    assert features.call_count == 17 and datasets.call_count == 51 and calls.call_count == 102
    assert all(row.date < calibration.CALIBRATION_FOLD.origin_end for history in seen for row in history.observations)
    assert histories[0].observations[-1].adjusted_close == 20000.  # input untouched
    assert report["record_count"] == len(report["records"]) == 102
    assert report["data_provenance"]["provenance_verified"] is False  # pure histories are not persisted proof
    assert report["final_test_completed"] is report["deployment_artifacts_created"] is False
    assert report["interval_method"]["nominal_coverage"] == .8
    assert report["interval_method"]["minimum_observations"] == 60
    assert sum(item["selection_warning"] is not None for item in report["records"]) == 1
    text = calibration.calibration_report_json(report)
    assert "return_30d" not in text and "realized_volatility_30d" not in text
    assert text == calibration.calibration_report_json(report)
    payload = json.loads(text)
    digest = payload.pop("calibration_sha256")
    assert sha256_bytes(canonical_json_bytes(payload)) == digest
    changed = tuple(replace(history, observations=tuple(replace(row, adjusted_close=1.)
                    if row.date >= calibration.CALIBRATION_FOLD.origin_end else row for row in history.observations)) for history in histories)
    assert calibration.calibration_report_json(calibration.calibrate_histories(changed, manifest=manifest)) == text


@pytest.mark.parametrize("change", ["missing", "duplicate", "future"])
def test_invalid_history_coverage_and_future_data_stop_before_fitting(manifest, monkeypatch, change):
    histories = _short_histories()
    if change == "missing":
        histories = histories[:-1]
    elif change == "duplicate":
        histories = (*histories[:-1], histories[0])
    else:
        histories = (replace(histories[0], observations=(*histories[0].observations, ForecastPriceObservation(date(2026, 10, 7), 1.))), *histories[1:])
    calls = MagicMock()
    monkeypatch.setattr(calibration, "calibrate_horizon_selection", calls)
    with pytest.raises(ForecastFinalizationError):
        calibration.calibrate_histories(histories, manifest=manifest)
    calls.assert_not_called()


def test_nonfinite_or_double_hashed_evidence_is_rejected():
    for report in [{"metric": float("nan")}, {"calibration_sha256": "0" * 64}]:
        with pytest.raises(ValueError):
            calibration.calibration_report_json(report)


def _selection_files(tmp_path, manifest, evidence_template):
    manifest_path = tmp_path / "manifest.json"
    report_path = tmp_path / "selection.json"
    manifest_path.write_text(horizon_manifest_json(manifest), encoding="utf-8")
    report_path.write_bytes(evaluator.report_json(evidence_template).encode())
    return manifest_path, report_path


def test_pinned_manifest_is_reproduced_from_exact_original_evidence(manifest, evidence_template, tmp_path):
    manifest_path, source = _selection_files(tmp_path, manifest, evidence_template)
    assert script.load_verified_selection(manifest_path=manifest_path, selection_report_path=source,
                                          expected_manifest_sha256=manifest.manifest_sha256) == manifest
    with pytest.raises(HorizonSelectionError, match="reviewed checksum"):
        script.load_verified_selection(manifest_path=manifest_path, selection_report_path=source, expected_manifest_sha256="0" * 64)
    source.write_bytes(source.read_bytes() + b" ")
    with pytest.raises(HorizonSelectionError, match="reviewed report"):
        script.load_verified_selection(manifest_path=manifest_path, selection_report_path=source,
                                       expected_manifest_sha256=manifest.manifest_sha256)


def test_even_a_rehashed_manifest_cannot_silently_drop_source_warnings(manifest, evidence_template, tmp_path):
    manifest_path, source = _selection_files(tmp_path, manifest, evidence_template)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    warned = next(record for record in payload["records"] if record["selection_warning"])
    warned["selection_warning"] = None
    payload.pop("manifest_sha256")
    digest = sha256_bytes(canonical_json_bytes(payload))
    manifest_path.write_text(json.dumps({**payload, "manifest_sha256": digest}), encoding="utf-8")
    with pytest.raises(HorizonSelectionError, match="source evidence"):
        script.load_verified_selection(manifest_path=manifest_path, selection_report_path=source, expected_manifest_sha256=digest)


def _database_mocks(monkeypatch):
    engine, session, calibrate = MagicMock(), MagicMock(), MagicMock(return_value={})
    records = tuple(SimpleNamespace(symbol=symbol, date=date(2024, 1, 1), adjusted_close=Decimal("100"),
                                    volume=None, source="synthetic") for symbol in script.USER_ASSET_SYMBOLS)
    @contextmanager
    def scope(_):
        yield session
    monkeypatch.setattr(script, "create_database_engine", lambda *args, **kwargs: engine)
    monkeypatch.setattr(script, "create_session_factory", lambda _: object())
    monkeypatch.setattr(script, "session_scope", scope)
    monkeypatch.setattr(script, "MarketDataService", lambda _: SimpleNamespace(get_range=lambda *args: records))
    monkeypatch.setattr(script, "calibrate_histories", calibrate)
    fingerprint = build_market_data_fingerprint(records, evaluation_cutoff=date(2026, 9, 17), symbols=script.USER_ASSET_SYMBOLS)
    return engine, session, calibrate, fingerprint


def test_dataset_mismatch_stops_before_any_calibration_and_closes_database(manifest, monkeypatch):
    engine, session, calibrate, _ = _database_mocks(monkeypatch)
    with pytest.raises(script.SelectionProvenanceError, match="mismatch"):
        script.run_persisted_calibration(database_url="postgresql+psycopg://aura:private@127.0.0.1:5433/db", manifest=manifest)
    engine.dispose.assert_called_once()
    calibrate.assert_not_called()
    assert str(session.execute.call_args.args[0]) == "SET TRANSACTION READ ONLY"
    session.add.assert_not_called()
    session.delete.assert_not_called()


def test_verified_read_only_snapshot_closes_before_calibration_and_keeps_credentials_out(manifest, monkeypatch):
    engine, session, calibrate, fingerprint = _database_mocks(monkeypatch)
    manifest = replace(manifest, market_data_fingerprint_sha256=fingerprint.sha256, market_data_row_count=fingerprint.total_row_count)
    def run(histories, **kwargs):
        engine.dispose.assert_called_once()
        assert len(histories) == 17
        return {"stage": calibration.STAGE}
    calibrate.side_effect = run
    report = script.run_persisted_calibration(database_url="postgresql+psycopg://aura:private@127.0.0.1:5433/db", manifest=manifest)
    assert report["data_provenance"]["provenance_verified"] is True
    assert "private" not in calibration.calibration_report_json(report)
    session.commit.assert_not_called()
    session.add.assert_not_called()
    session.delete.assert_not_called()


def _args(manifest_path, source_path, output, digest):
    return ["--env-file", "selected.env", "--database-name", "aura_forecast_training_20260917",
            "--selection-manifest", str(manifest_path), "--selection-report", str(source_path),
            "--expected-manifest-sha256", digest, "--output", str(output)]


def test_cli_writes_new_calibration_evidence_only_with_pinned_inputs(manifest, evidence_template, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(evaluator, "REPOSITORY_ROOT", tmp_path)
    manifest_path, source = _selection_files(tmp_path, manifest, evidence_template)
    original_manifest, original_source = manifest_path.read_bytes(), source.read_bytes()
    output = tmp_path / "forecasting-evidence/new/calibration.json"
    _mock_history_calibration(monkeypatch)
    report = calibration.calibrate_histories(_short_histories(), manifest=manifest)
    run = MagicMock(return_value=report)
    monkeypatch.setattr(script, "database_url_from_env_file", lambda *args, **kwargs: "postgresql+psycopg://aura:private@127.0.0.1:5433/aura_test")
    monkeypatch.setattr(script, "run_persisted_calibration", run)
    script.main(_args(manifest_path, source, output, manifest.manifest_sha256))
    assert evaluator.make_url(run.call_args.kwargs["database_url"]).database == "aura_forecast_training_20260917"
    assert json.loads(output.read_text(encoding="utf-8"))["stage"] == calibration.STAGE
    assert manifest_path.read_bytes() == original_manifest and source.read_bytes() == original_source
    assert "private" not in capsys.readouterr().out
    saved = output.read_bytes()
    run.reset_mock()
    with pytest.raises(SystemExit):
        script.main(_args(manifest_path, source, output, manifest.manifest_sha256))
    run.assert_not_called()
    assert output.read_bytes() == saved


@pytest.mark.parametrize("relative", ["forecasting-evidence/forecast-v1-20260917/calibration.json",
    "backend/artifacts/forecasting/forecast-v1-20260917/calibration.json", "calibration.json", "forecasting-evidence/new.txt"])
def test_invalid_output_paths_stop_before_input_or_database_reads(tmp_path, monkeypatch, relative):
    monkeypatch.setattr(evaluator, "REPOSITORY_ROOT", tmp_path)
    inputs, database = MagicMock(), MagicMock()
    monkeypatch.setattr(script, "load_verified_selection", inputs)
    monkeypatch.setattr(script, "run_persisted_calibration", database)
    output = tmp_path / relative
    with pytest.raises(SystemExit):
        script.main(_args(tmp_path / "missing.json", tmp_path / "missing-report.json", output, "0" * 64))
    inputs.assert_not_called()
    database.assert_not_called()
    assert not output.exists()


def test_wrong_manifest_hash_stops_before_environment_database_or_fitting(manifest, evidence_template, tmp_path, monkeypatch):
    monkeypatch.setattr(evaluator, "REPOSITORY_ROOT", tmp_path)
    manifest_path, source = _selection_files(tmp_path, manifest, evidence_template)
    env, run = MagicMock(), MagicMock()
    monkeypatch.setattr(script, "database_url_from_env_file", env)
    monkeypatch.setattr(script, "run_persisted_calibration", run)
    output = tmp_path / "forecasting-evidence/new/calibration.json"
    with pytest.raises(SystemExit, match="reviewed checksum"):
        script.main(_args(manifest_path, source, output, "0" * 64))
    env.assert_not_called()
    run.assert_not_called()
    assert not output.exists()


@pytest.mark.parametrize("url", ["postgresql+psycopg://aura:private@remote.example:5433/db",
    "postgresql+psycopg://aura:private@127.0.0.1:5432/db", "postgresql+psycopg://aura:private@127.0.0.1:5433/db?host=remote.example"])
def test_remote_or_redirected_connection_is_rejected_before_database(manifest, monkeypatch, url):
    engine = MagicMock()
    monkeypatch.setattr(script, "create_database_engine", engine)
    with pytest.raises(script.SelectionProvenanceError) as error:
        script.run_persisted_calibration(database_url=url, manifest=manifest)
    assert "private" not in str(error.value)
    engine.assert_not_called()


def test_calibration_workflow_has_no_final_test_artifact_or_runtime_entry_point():
    root = Path(script.__file__).resolve().parents[2]
    for module in [script, calibration]:
        source = Path(module.__file__).read_text(encoding="utf-8")
        assert "evaluate_frozen_final_test" not in source
        assert "train_deployment_artifact" not in source
        assert "write_artifact_bundle" not in source
    for relative in ["backend/app/forecasting/inference.py", "backend/app/forecasting/registry.py", "backend/app/api/routes/forecasting.py"]:
        assert "horizon_calibration" not in (root / relative).read_text(encoding="utf-8")
