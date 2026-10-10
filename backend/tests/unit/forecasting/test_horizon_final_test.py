"""Synthetic weekly final-test/coverage and mocked one-run orchestration tests."""

from contextlib import contextmanager
from copy import deepcopy
from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

import backend.scripts.evaluate_forecasting_horizon_final_test as script
import backend.scripts.evaluate_forecasting_horizons as evaluator
from app.forecasting import horizon_calibration as calibration
from app.forecasting import horizon_final_test as final
from app.forecasting import horizon_selection_manifest as freezer
from app.forecasting.data import AssetPriceHistory, ForecastPriceObservation
from app.forecasting.evaluation import CandidatePrediction, ForecastTargetType
from app.forecasting.finalization import ForecastFinalizationError
from app.forecasting.fingerprints import canonical_json_bytes, sha256_bytes, build_market_data_fingerprint
from app.forecasting.multi_horizon import HorizonDataset, HorizonDatasetRow, HorizonTargetRow, NEW_HORIZONS, target_name, target_version
from backend.tests.unit.forecasting.test_horizon_calibration import manifest
from backend.tests.unit.forecasting.test_horizon_selection_manifest import evidence_template


def _rehash(payload):
    base = {key: value for key, value in payload.items() if key != "calibration_sha256"}
    return {**base, "calibration_sha256": sha256_bytes(canonical_json_bytes(base))}


def _calibration_record(frozen):
    fold, horizon, selection = calibration.CALIBRATION_FOLD, frozen.horizon_days, frozen.selection
    return {
        "symbol": selection.symbol, "horizon_days": horizon, "target_type": target_name(selection.target_type, horizon),
        "selected_candidate_id": selection.selected_candidate_id, "selection_warning": selection.selection_warning,
        "feature_set_version": "forecast-features-v1", "target_set_version": target_version(horizon),
        "fold_id": fold.fold_id, "observation_count": 100, "training_observation_count": 1000,
        "mae": .1, "rmse": .2, "residual_q10": -.1, "residual_q90": .1, "warning": None,
        "negative_prediction_clipped_count": 0 if selection.target_type is ForecastTargetType.VOLATILITY else None,
        "training_cutoff_exclusive": fold.origin_start.isoformat(), "training_origin_min": "2020-01-01",
        "training_origin_max": (fold.origin_start - timedelta(days=horizon + 1)).isoformat(),
        "training_endpoint_max": (fold.origin_start - timedelta(days=1)).isoformat(),
        "evaluation_origin_start": fold.origin_start.isoformat(), "evaluation_origin_end_exclusive": fold.origin_end.isoformat(),
        "evaluated_origin_min": fold.origin_start.isoformat(),
        "evaluated_origin_max": (fold.origin_end - timedelta(days=horizon + 1)).isoformat(),
        "evaluated_endpoint_max": (fold.origin_end - timedelta(days=1)).isoformat(),
    }


@pytest.fixture(scope="module")
def calibration_template(manifest):
    histories = tuple(AssetPriceHistory(symbol, (ForecastPriceObservation(date(2020, 1, 1), 100.),))
                      for symbol in script.USER_ASSET_SYMBOLS)
    with patch.object(calibration, "build_feature_rows", return_value=()), \
         patch.object(calibration, "build_horizon_dataset", return_value=object()), \
         patch.object(calibration, "calibrate_horizon_selection", side_effect=lambda **kw: _calibration_record(kw["frozen"])):
        report = calibration.calibrate_histories(histories, manifest=manifest)
    report["data_provenance"] = {"provenance_verified": True, "evaluation_cutoff": "2026-09-17",
        "symbol_count": 17, "row_count": manifest.market_data_row_count,
        "market_data_fingerprint_sha256": manifest.market_data_fingerprint_sha256}
    return _rehash(report)


@pytest.fixture
def calibration_report(calibration_template):
    return deepcopy(calibration_template)


def _validate(report, manifest, expected=None):
    return final.validate_calibration_report(report, manifest=manifest,
        expected_calibration_sha256=expected or report["calibration_sha256"])


def test_calibration_binding_full_coverage_and_order_are_validated(manifest, calibration_report):
    assert len(_validate(calibration_report, manifest)) == 102
    with pytest.raises(ForecastFinalizationError, match="checksum"):
        _validate(calibration_report, manifest, "0" * 64)
    original_digest = calibration_report["calibration_sha256"]
    calibration_report["records"][0]["residual_q90"] = .2
    with pytest.raises(ForecastFinalizationError, match="checksum"):
        _validate(_rehash(calibration_report), manifest, original_digest)


@pytest.mark.parametrize("field,value", [("stage", "deployable"), ("final_test_completed", True),
    ("horizons", [7, 14, 30]), ("record_count", 101), ("selection_manifest_sha256", "0" * 64),
    ("data_provenance", {"provenance_verified": False}), ("interval_method", {})])
def test_rehashed_calibration_contract_mismatch_is_rejected(manifest, calibration_report, field, value):
    calibration_report[field] = value
    with pytest.raises(ForecastFinalizationError):
        _validate(_rehash(calibration_report), manifest)


@pytest.mark.parametrize("field,value", [("observation_count", 59), ("training_observation_count", 755),
    ("observation_count", True), ("horizon_days", 7.0), ("selected_candidate_id", "unknown"),
    ("residual_q10", .2), ("mae", -1), ("rmse", True), ("warning", "suppressed"),
    ("training_endpoint_max", "2025-03-18"), ("evaluated_endpoint_max", "2025-09-18"),
    ("evaluated_origin_min", "2025-03-17"), ("negative_prediction_clipped_count", 101),
    ("target_set_version", "forecast-targets-v1")])
def test_invalid_calibration_record_is_rejected_even_when_rehashed(manifest, calibration_report, field, value):
    calibration_report["records"][0][field] = value
    with pytest.raises(ForecastFinalizationError):
        _validate(_rehash(calibration_report), manifest)


def test_warning_removal_duplicate_order_or_nonfinite_calibration_is_rejected(manifest, calibration_report):
    warned = next(record for record in calibration_report["records"] if record["selection_warning"])
    warned["selection_warning"] = None
    with pytest.raises(ForecastFinalizationError):
        _validate(_rehash(calibration_report), manifest)
    calibration_report["records"].reverse()
    with pytest.raises(ForecastFinalizationError):
        _validate(_rehash(calibration_report), manifest)
    calibration_report["records"][0]["residual_q10"] = float("nan")
    with pytest.raises(ForecastFinalizationError):
        _validate(calibration_report, manifest)


def test_coverage_is_inclusive_and_uses_fixed_ranges():
    result = final.interval_coverage(actual_values=[-.2, -.1, 0., .1, .2], prediction_values=[0.] * 5,
        residual_q10=-.1, residual_q90=.1, target_type=ForecastTargetType.RETURN)
    assert result["covered_count"] == 3 and result["empirical_coverage"] == .6
    assert result["below_interval_count"] == result["above_interval_count"] == 1
    assert result["empty_interval_count"] == 0 and result["mean_valid_interval_width"] == pytest.approx(.2)


def test_empty_volatility_intervals_are_misses_and_never_widened():
    result = final.interval_coverage(actual_values=[0., .05], prediction_values=[0., .2],
        residual_q10=-.3, residual_q90=-.1, target_type=ForecastTargetType.VOLATILITY)
    assert result["empty_interval_count"] == result["covered_count"] == result["missed_count"] == 1
    assert result["empirical_coverage"] == .5 and result["mean_valid_interval_width"] == pytest.approx(.1)
    assert result["warning"] == "empty_volatility_intervals_counted_as_misses"
    all_empty = final.interval_coverage(actual_values=[0.], prediction_values=[0.],
        residual_q10=-.3, residual_q90=-.1, target_type=ForecastTargetType.VOLATILITY)
    assert all_empty["empirical_coverage"] == 0 and all_empty["mean_valid_interval_width"] is None


@pytest.mark.parametrize("actual,predicted,q10,q90,target", [([], [], -.1, .1, ForecastTargetType.RETURN),
    ([0.], [], -.1, .1, ForecastTargetType.RETURN), ([float("nan")], [0.], -.1, .1, ForecastTargetType.RETURN),
    ([0.], [True], -.1, .1, ForecastTargetType.RETURN), ([0.], [0.], .2, .1, ForecastTargetType.RETURN),
    ([0.], [-1.], -.1, .1, ForecastTargetType.VOLATILITY), ([0.], [0.], -.1, .1, "return_30d")])
def test_unsafe_coverage_inputs_are_rejected(actual, predicted, q10, q90, target):
    with pytest.raises(ForecastFinalizationError):
        final.interval_coverage(actual_values=actual, prediction_values=predicted, residual_q10=q10, residual_q90=q90, target_type=target)


def _dataset(horizon):
    def row(origin, value):
        endpoint = origin + timedelta(days=horizon)
        return HorizonDatasetRow(SimpleNamespace(symbol="AAPL", origin_date=origin),
            HorizonTargetRow("AAPL", horizon, origin, endpoint, endpoint, 0, value, max(0., value)))
    rows = [*(row(date(2020, 1, 1) + timedelta(days=index), .1) for index in range(800)),
            row(final.FINAL_FOLD.origin_start - timedelta(days=horizon), 99.),
            *(row(final.FINAL_FOLD.origin_start + timedelta(days=index), index / 100) for index in range(60)),
            row(final.FINAL_FOLD.origin_end - timedelta(days=horizon), 999.)]
    return HorizonDataset("AAPL", horizon, 2000, len(rows), len(rows), tuple(sorted(rows, key=lambda item: item.features.origin_date)))


class _Candidate:
    candidate_id = "historical_average"

    def __init__(self, value=.1):
        self.value, self.calls = value, []

    def predict(self, **kwargs):
        self.calls.append(kwargs)
        return CandidatePrediction(self.candidate_id, tuple(self.value for _ in kwargs["evaluation_rows"]), len(kwargs["training_rows"]))


@pytest.mark.parametrize("horizon", NEW_HORIZONS)
@pytest.mark.parametrize("target", list(ForecastTargetType))
def test_final_scoring_uses_actual_horizon_fixed_ranges_and_purged_folds(manifest, calibration_report, monkeypatch, horizon, target):
    frozen = next(item for item in manifest.records if item.horizon_days == horizon and item.selection.symbol == "AAPL" and item.selection.target_type is target)
    record = next(item for item in calibration_report["records"] if item["horizon_days"] == horizon and item["symbol"] == "AAPL" and item["target_type"] == target_name(target, horizon))
    original = deepcopy(record)
    candidate = _Candidate(-.2 if target is ForecastTargetType.VOLATILITY else .1)
    real_evaluate = final.evaluate_frozen_selection_fold
    monkeypatch.setattr(final, "evaluate_frozen_selection_fold", lambda **kw: real_evaluate(**kw, candidate=candidate))
    result = final.evaluate_horizon_final_test(dataset=_dataset(horizon), frozen=frozen, calibration=record)
    assert len(candidate.calls) == 1 and record == original
    call = candidate.calls[0]
    assert len(call["training_rows"]) == 800 and len(call["evaluation_rows"]) == 60
    assert all(item.target.endpoint_date < final.FINAL_FOLD.origin_start for item in call["training_rows"])
    assert all(item.target.endpoint_date < final.FINAL_FOLD.origin_end for item in call["evaluation_rows"])
    assert result["frozen_residual_q10"] == -.1 and result["frozen_residual_q90"] == .1
    assert result["target_type"] == target_name(target, horizon)
    assert result["interval_coverage"]["covered_count"] == (11 if target is ForecastTargetType.VOLATILITY else 21)
    assert result["negative_prediction_clipped_count"] == (60 if target is ForecastTargetType.VOLATILITY else None)


def test_poor_final_performance_is_reported_without_reselection(manifest, calibration_report, monkeypatch):
    frozen = next(item for item in manifest.records if item.horizon_days == 7 and item.selection.symbol == "AAPL" and item.selection.target_type is ForecastTargetType.RETURN)
    record = next(item for item in calibration_report["records"] if item["symbol"] == "AAPL" and item["target_type"] == "return_7d")
    candidate = _Candidate(999.)
    real_evaluate = final.evaluate_frozen_selection_fold
    monkeypatch.setattr(final, "evaluate_frozen_selection_fold", lambda **kw: real_evaluate(**kw, candidate=candidate))
    result = final.evaluate_horizon_final_test(dataset=_dataset(7), frozen=frozen, calibration=record)
    assert result["mae"] > 998 and result["interval_coverage"]["empirical_coverage"] == 0
    assert result["selected_candidate_id"] == "historical_average" and len(candidate.calls) == 1


def test_wrong_horizon_stops_before_fit(manifest, calibration_report, monkeypatch):
    fitting = MagicMock()
    monkeypatch.setattr(final, "evaluate_frozen_selection_fold", fitting)
    with pytest.raises(ForecastFinalizationError):
        final.evaluate_horizon_final_test(dataset=_dataset(14), frozen=manifest.records[0], calibration=calibration_report["records"][0])
    fitting.assert_not_called()


def test_changed_candidate_or_unavailable_predictions_never_fall_back(manifest, calibration_report, monkeypatch):
    frozen = next(item for item in manifest.records if item.horizon_days == 7 and item.selection.symbol == "AAPL"
                  and item.selection.target_type is ForecastTargetType.RETURN)
    calibrated = next(item for item in calibration_report["records"] if item["symbol"] == "AAPL" and item["target_type"] == "return_7d")
    candidate = _Candidate()
    candidate.candidate_id = "moving_average_90_calendar_days"
    real_evaluate = final.evaluate_frozen_selection_fold
    monkeypatch.setattr(final, "evaluate_frozen_selection_fold", lambda **kw: real_evaluate(**kw, candidate=candidate))
    with pytest.raises(ForecastFinalizationError, match="frozen selection"):
        final.evaluate_horizon_final_test(dataset=_dataset(7), frozen=frozen, calibration=calibrated)
    assert candidate.calls == []
    candidate.candidate_id = frozen.selection.selected_candidate_id
    candidate.predict = MagicMock(return_value=CandidatePrediction(candidate.candidate_id, None, 800, warning="unavailable"))
    with pytest.raises(ForecastFinalizationError, match="unavailable"):
        final.evaluate_horizon_final_test(dataset=_dataset(7), frozen=frozen, calibration=calibrated)
    candidate.predict.assert_called_once()


def test_final_scoring_preserves_selection_calibration_and_fit_warnings(manifest, calibration_report, monkeypatch):
    frozen = next(item for item in manifest.records if item.selection.selection_warning)
    calibrated = next(item for item in calibration_report["records"] if item["symbol"] == frozen.selection.symbol
                      and item["target_type"] == target_name(frozen.selection.target_type, frozen.horizon_days))
    calibrated["warning"] = frozen.selection.selection_warning
    old_dataset = _dataset(frozen.horizon_days)
    dataset = replace(old_dataset, symbol=frozen.selection.symbol, rows=tuple(HorizonDatasetRow(
        SimpleNamespace(symbol=frozen.selection.symbol, origin_date=row.features.origin_date),
        replace(row.target, symbol=frozen.selection.symbol)) for row in old_dataset.rows))
    candidate = _Candidate()
    candidate.candidate_id = frozen.selection.selected_candidate_id
    candidate.predict = MagicMock(side_effect=lambda **kw: CandidatePrediction(candidate.candidate_id,
        tuple(.1 for _ in kw["evaluation_rows"]), len(kw["training_rows"]), warning=frozen.selection.selection_warning))
    real_evaluate = final.evaluate_frozen_selection_fold
    monkeypatch.setattr(final, "evaluate_frozen_selection_fold", lambda **kw: real_evaluate(**kw, candidate=candidate))
    result = final.evaluate_horizon_final_test(dataset=dataset, frozen=frozen, calibration=calibrated)
    assert result["selection_warning"] == result["calibration_warning"] == result["warning"] == frozen.selection.selection_warning


def _histories():
    return tuple(AssetPriceHistory(symbol, (ForecastPriceObservation(date(2020, 1, 1), 100.),))
                 for symbol in script.USER_ASSET_SYMBOLS)


def test_all_102_final_records_reuse_features_preserve_inputs_and_bind_checksums(manifest, calibration_report, monkeypatch):
    original = deepcopy(calibration_report)
    features = MagicMock(return_value=())
    datasets = MagicMock(return_value=object())
    def result(**kw):
        frozen, calibrated = kw["frozen"], kw["calibration"]
        return {"symbol": frozen.selection.symbol, "horizon_days": frozen.horizon_days,
            "target_type": target_name(frozen.selection.target_type, frozen.horizon_days),
            "frozen_residual_q10": calibrated["residual_q10"], "frozen_residual_q90": calibrated["residual_q90"],
            "selection_warning": frozen.selection.selection_warning}
    scores = MagicMock(side_effect=result)
    monkeypatch.setattr(final, "build_feature_rows", features)
    monkeypatch.setattr(final, "build_horizon_dataset", datasets)
    monkeypatch.setattr(final, "evaluate_horizon_final_test", scores)
    report = final.evaluate_final_histories(_histories(), manifest=manifest, calibration_report=calibration_report,
                                           expected_calibration_sha256=calibration_report["calibration_sha256"])
    assert features.call_count == 17 and datasets.call_count == 51 and scores.call_count == 102
    assert report["record_count"] == len(report["records"]) == 102 and calibration_report == original
    assert report["final_test_completed"] is True and report["deployment_artifacts_created"] is False
    assert report["data_provenance"]["provenance_verified"] is False
    assert report["calibration_sha256"] == calibration_report["calibration_sha256"]
    assert sum(record["selection_warning"] is not None for record in report["records"]) == 1
    text = final.final_test_report_json(report)
    assert text == final.final_test_report_json(report)
    assert "return_30d" not in text and "realized_volatility_30d" not in text
    payload = json.loads(text)
    digest = payload.pop("final_test_sha256")
    assert digest == sha256_bytes(canonical_json_bytes(payload))


@pytest.mark.parametrize("change", ["missing", "duplicate", "future"])
def test_history_validation_stops_before_features_or_scoring(manifest, calibration_report, monkeypatch, change):
    histories = _histories()
    if change == "missing":
        histories = histories[:-1]
    elif change == "duplicate":
        histories = (*histories[:-1], histories[0])
    else:
        histories = (replace(histories[0], observations=(*histories[0].observations, ForecastPriceObservation(date(2026, 10, 7), 1.))), *histories[1:])
    features = MagicMock()
    monkeypatch.setattr(final, "build_feature_rows", features)
    with pytest.raises(ForecastFinalizationError):
        final.evaluate_final_histories(histories, manifest=manifest, calibration_report=calibration_report,
                                       expected_calibration_sha256=calibration_report["calibration_sha256"])
    features.assert_not_called()


def _patch_roots(tmp_path, monkeypatch):
    monkeypatch.setattr(script, "REPOSITORY_ROOT", tmp_path)
    monkeypatch.setattr(evaluator, "REPOSITORY_ROOT", tmp_path)


def test_run_marker_is_exclusive_and_cannot_be_bypassed_with_another_output(manifest, calibration_report, tmp_path, monkeypatch):
    _patch_roots(tmp_path, monkeypatch)
    output = tmp_path / "forecasting-evidence/new/final-test.json"
    digest = script.start_final_test_run(manifest=manifest, calibration_sha256=calibration_report["calibration_sha256"], output=output)
    started, completed = script._run_paths()
    original = started.read_bytes()
    assert json.loads(original)["run_state_sha256"] == digest
    with pytest.raises(ForecastFinalizationError, match="already started"):
        script.start_final_test_run(manifest=manifest, calibration_sha256=calibration_report["calibration_sha256"], output=tmp_path / "forecasting-evidence/other.json")
    script.complete_final_test_run(run_state_sha256=digest, final_test_sha256="a" * 64)
    assert completed.exists() and started.read_bytes() == original
    with pytest.raises(ForecastFinalizationError):
        script.assert_run_not_started()


def _files_and_args(tmp_path, manifest, evidence_template, calibration_report):
    manifest_path, source, calibration_path = (tmp_path / name for name in ("manifest.json", "selection.json", "calibration.json"))
    manifest_path.write_text(freezer.horizon_manifest_json(manifest), encoding="utf-8")
    source.write_bytes(evaluator.report_json(evidence_template).encode())
    calibration_path.write_text(json.dumps(calibration_report), encoding="utf-8")
    output = tmp_path / "forecasting-evidence/new/final-test.json"
    args = ["--env-file", "selected.env", "--database-name", "aura_forecast_training_20260917",
        "--selection-manifest", str(manifest_path), "--selection-report", str(source), "--expected-manifest-sha256", manifest.manifest_sha256,
        "--calibration", str(calibration_path), "--expected-calibration-sha256", calibration_report["calibration_sha256"], "--output", str(output)]
    return (manifest_path, source, calibration_path), output, args


def _mock_final_run(monkeypatch, fail=False):
    monkeypatch.setattr(script, "database_url_from_env_file", lambda *a, **kw: "postgresql+psycopg://aura:private@127.0.0.1:5433/aura_test")
    def run(**kw):
        kw["before_evaluation"]()
        if fail:
            raise RuntimeError("private model failure")
        return {"report_schema": final.REPORT_SCHEMA, "stage": final.STAGE, "record_count": 102,
                "final_test_completed": True, "deployment_artifacts_created": False,
                "records": [{"warning": None, "interval_coverage": {"empty_interval_count": 0}} for _ in range(102)]}
    mock = MagicMock(side_effect=run)
    monkeypatch.setattr(script, "run_persisted_final_test", mock)
    return mock


def test_cli_writes_new_report_and_completion_without_changing_inputs(manifest, evidence_template, calibration_report, tmp_path, monkeypatch, capsys):
    _patch_roots(tmp_path, monkeypatch)
    files, output, args = _files_and_args(tmp_path, manifest, evidence_template, calibration_report)
    originals = [path.read_bytes() for path in files]
    run = _mock_final_run(monkeypatch)
    script.main(args)
    assert evaluator.make_url(run.call_args.kwargs["database_url"]).database == "aura_forecast_training_20260917"
    saved = output.read_bytes()
    report = json.loads(saved)
    assert report["final_test_completed"] is True and report["deployment_artifacts_created"] is False
    digest = report.pop("final_test_sha256")
    assert digest == sha256_bytes(canonical_json_bytes(report))
    assert json.loads(script._run_paths()[1].read_text(encoding="utf-8"))["final_test_sha256"] == digest
    assert [path.read_bytes() for path in files] == originals
    assert "private" not in capsys.readouterr().out
    run.reset_mock()
    args[-1] = str(tmp_path / "forecasting-evidence/new/second.json")
    with pytest.raises(SystemExit, match="already started"):
        script.main(args)
    run.assert_not_called()
    assert output.read_bytes() == saved


def test_failed_scoring_consumes_guard_and_never_creates_success_report(manifest, evidence_template, calibration_report, tmp_path, monkeypatch):
    _patch_roots(tmp_path, monkeypatch)
    _, output, args = _files_and_args(tmp_path, manifest, evidence_template, calibration_report)
    run = _mock_final_run(monkeypatch, fail=True)
    with pytest.raises(SystemExit) as failure:
        script.main(args)
    assert "private" not in str(failure.value)
    started, completed = script._run_paths()
    assert started.exists() and not completed.exists() and not output.exists()
    run.reset_mock()
    with pytest.raises(SystemExit, match="already started"):
        script.main(args)
    run.assert_not_called()


def test_bad_calibration_stops_before_env_database_or_guard(manifest, evidence_template, calibration_report, tmp_path, monkeypatch):
    _patch_roots(tmp_path, monkeypatch)
    _, output, args = _files_and_args(tmp_path, manifest, evidence_template, calibration_report)
    args[args.index("--expected-calibration-sha256") + 1] = "0" * 64
    env, run = MagicMock(), MagicMock()
    monkeypatch.setattr(script, "database_url_from_env_file", env)
    monkeypatch.setattr(script, "run_persisted_final_test", run)
    with pytest.raises(SystemExit, match="checksum"):
        script.main(args)
    env.assert_not_called()
    run.assert_not_called()
    assert not output.exists() and not script._run_paths()[0].exists()


@pytest.mark.parametrize("raw", [b'{"records":[],"records":[]}', b'{"value":NaN}', b'{"value":Infinity}', b'not-json'])
def test_ambiguous_calibration_json_stops_before_database_or_guard(manifest, evidence_template, calibration_report, tmp_path, monkeypatch, raw):
    _patch_roots(tmp_path, monkeypatch)
    files, output, args = _files_and_args(tmp_path, manifest, evidence_template, calibration_report)
    files[2].write_bytes(raw)
    env, run = MagicMock(), MagicMock()
    monkeypatch.setattr(script, "database_url_from_env_file", env)
    monkeypatch.setattr(script, "run_persisted_final_test", run)
    with pytest.raises(SystemExit):
        script.main(args)
    env.assert_not_called()
    run.assert_not_called()
    assert not output.exists() and not script._run_paths()[0].exists()


@pytest.mark.parametrize("relative", ["forecasting-evidence/forecast-v1-20260917/final.json",
    "backend/artifacts/forecasting/forecast-v1-20260917/final.json", "outside.json",
    "forecasting-evidence/forecast-weekly-v1-20260917/final-test-started.json"])
def test_bad_output_stops_before_inputs_and_consuming_guard(manifest, evidence_template, calibration_report, tmp_path, monkeypatch, relative):
    _patch_roots(tmp_path, monkeypatch)
    _, _, args = _files_and_args(tmp_path, manifest, evidence_template, calibration_report)
    args[-1] = str(tmp_path / relative)
    inputs = MagicMock()
    monkeypatch.setattr(script, "load_verified_selection", inputs)
    with pytest.raises(SystemExit):
        script.main(args)
    inputs.assert_not_called()
    assert not script._run_paths()[0].exists()


def test_provenance_mismatch_closes_read_only_db_before_guard_or_scoring(manifest, calibration_report, monkeypatch):
    engine, session, start, score = MagicMock(), MagicMock(), MagicMock(), MagicMock()
    records = tuple(SimpleNamespace(symbol=symbol, date=date(2024, 1, 1), adjusted_close=Decimal("100"), volume=None,
                                    source="synthetic") for symbol in script.USER_ASSET_SYMBOLS)
    @contextmanager
    def scope(_):
        yield session
    monkeypatch.setattr(script, "create_database_engine", lambda *a, **kw: engine)
    monkeypatch.setattr(script, "create_session_factory", lambda _: object())
    monkeypatch.setattr(script, "session_scope", scope)
    monkeypatch.setattr(script, "MarketDataService", lambda _: SimpleNamespace(get_range=lambda *a: records))
    monkeypatch.setattr(script, "evaluate_final_histories", score)
    arguments = dict(database_url="postgresql+psycopg://aura:private@127.0.0.1:5433/db", manifest=manifest,
        calibration_report=calibration_report, expected_calibration_sha256=calibration_report["calibration_sha256"], before_evaluation=start)
    with pytest.raises(script.SelectionProvenanceError, match="mismatch"):
        script.run_persisted_final_test(**arguments)
    engine.dispose.assert_called_once()
    start.assert_not_called()
    score.assert_not_called()
    assert str(session.execute.call_args.args[0]) == "SET TRANSACTION READ ONLY"
    fingerprint = build_market_data_fingerprint(records, evaluation_cutoff=date(2026, 9, 17), symbols=script.USER_ASSET_SYMBOLS)
    rebound = replace(manifest, market_data_fingerprint_sha256=fingerprint.sha256, market_data_row_count=fingerprint.total_row_count)
    base = freezer._manifest_base(rebound.source_selection_report_sha256, fingerprint.sha256, fingerprint.total_row_count, rebound.records)
    rebound = replace(rebound, manifest_sha256=sha256_bytes(canonical_json_bytes(base)))
    calibration_report.update(selection_manifest_sha256=rebound.manifest_sha256, approved_market_data_row_count=fingerprint.total_row_count,
        approved_market_data_fingerprint_sha256=fingerprint.sha256,
        data_provenance={"provenance_verified": True, "evaluation_cutoff": "2026-09-17", "symbol_count": 17,
                         "row_count": fingerprint.total_row_count, "market_data_fingerprint_sha256": fingerprint.sha256})
    calibration_report = _rehash(calibration_report)
    engine.dispose.reset_mock()
    events = []
    start.side_effect = lambda: events.append("start")
    def scoring(*a, **kw):
        engine.dispose.assert_called_once()
        assert events == ["start"]
        return {"stage": final.STAGE}
    score.side_effect = scoring
    report = script.run_persisted_final_test(**{**arguments, "manifest": rebound, "calibration_report": calibration_report,
        "expected_calibration_sha256": calibration_report["calibration_sha256"]})
    assert report["data_provenance"]["provenance_verified"] is True
    session.add.assert_not_called()
    session.delete.assert_not_called()


def test_final_workflow_never_recalibrates_or_creates_models():
    root = Path(script.__file__).resolve().parents[2]
    for module in (script, final):
        source = Path(module.__file__).read_text(encoding="utf-8")
        assert "train_deployment_artifact" not in source and "write_artifact_bundle" not in source
        assert "calibrate_frozen_selection" not in source
    for relative in ("backend/app/forecasting/inference.py", "backend/app/forecasting/registry.py", "backend/app/api/routes/forecasting.py"):
        assert "horizon_final_test" not in (root / relative).read_text(encoding="utf-8")
