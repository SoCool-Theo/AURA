"""Synthetic selection-freeze checks; no database or estimator execution."""

from copy import deepcopy
from dataclasses import asdict
from datetime import date, timedelta
import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import backend.scripts.freeze_forecasting_horizons as script
import backend.scripts.evaluate_forecasting_horizons as evaluator
from app.core.instruments import USER_ASSET_SYMBOLS
from app.forecasting import horizon_selection_manifest as freezer
from app.forecasting.evaluation import ForecastEvaluationResult, ForecastTargetType
from app.forecasting.features import FEATURE_SET_VERSION
from app.forecasting.fingerprints import canonical_json_bytes, sha256_bytes
from app.forecasting.models import ARIMA_FIT_CONVERGENCE_WARNING
from app.forecasting.multi_horizon import NEW_HORIZONS, target_name, target_version
from app.forecasting.selection import (
    CANDIDATE_SIMPLICITY_ORDER, VOLATILITY_CANDIDATE_SIMPLICITY_ORDER,
    summarize_symbol_selection, summarize_volatility_selection,
)
from app.forecasting.splits import EvaluationPlanConfig, FoldPurpose, build_chronological_plan


SOURCE_HASH = "a" * 64
FINGERPRINT = "b" * 64
ROW_COUNT = 69928


@pytest.fixture(scope="module")
def evidence_template():
    cutoff = date(2026, 9, 17)
    plan = build_chronological_plan(EvaluationPlanConfig(cutoff + timedelta(days=1)))
    folds = tuple(fold for fold in plan.folds if fold.purpose is FoldPurpose.SELECTION)
    groups = []
    for horizon in NEW_HORIZONS:
        for symbol in sorted(USER_ASSET_SYMBOLS):
            for target in ForecastTargetType:
                order = (CANDIDATE_SIMPLICITY_ORDER if target is ForecastTargetType.RETURN
                         else VOLATILITY_CANDIDATE_SIMPLICITY_ORDER)
                results = []
                for index, candidate in enumerate(order):
                    for fold in folds:
                        chosen_arima = symbol == "QQQ" and horizon == 21 and target is ForecastTargetType.VOLATILITY and index == 3
                        error = .07 if chosen_arima else (.1, .12, .14, .16, .18)[index]
                        results.append(ForecastEvaluationResult(
                            symbol=symbol, target_type=target, candidate_id=candidate,
                            fold_id=fold.fold_id, fold_purpose=FoldPurpose.SELECTION,
                            training_cutoff=fold.origin_start,
                            evaluation_origin_start=fold.origin_start, evaluation_origin_end=fold.origin_end,
                            training_observation_count=1000, candidate_training_value_count=900,
                            evaluated_observation_count=100, prediction_available=True,
                            mae=error, rmse=error * 1.1,
                            directional_accuracy=.5 if target is ForecastTargetType.RETURN else None,
                            directional_evaluated_count=100 if target is ForecastTargetType.RETURN else None,
                            return_mape=None,
                            warning=ARIMA_FIT_CONVERGENCE_WARNING if chosen_arima and fold.fold_id == "selection-05" else None,
                            negative_prediction_clipped_count=0 if target is ForecastTargetType.VOLATILITY else None,
                        ))
                summarize = summarize_symbol_selection if target is ForecastTargetType.RETURN else summarize_volatility_selection
                summary = summarize(symbol=symbol, results=tuple(results),
                                    expected_selection_fold_ids=tuple(fold.fold_id for fold in folds))
                groups.append({
                    "symbol": symbol, "horizon_days": horizon, "target_type": target_name(target, horizon),
                    "feature_set_version": FEATURE_SET_VERSION, "target_set_version": target_version(horizon),
                    "candidate_ids": list(order), "price_observation_count": 10000,
                    "feature_origin_count": 9748, "target_origin_count": 9970,
                    "label_complete_origin_count": 9700,
                    "results": [{**asdict(result), "horizon_days": horizon, "target_type": target_name(target, horizon)}
                                for result in results], "selection_summary": asdict(summary),
                })
    report = {
        "report_schema": evaluator.REPORT_SCHEMA, "stage": "selection_only_not_deployable",
        "evaluation_cutoff": cutoff, "evaluation_end_exclusive": plan.config.evaluation_end_exclusive,
        "horizons": list(NEW_HORIZONS), "horizon_unit": "calendar_days",
        "evaluation_plan": asdict(plan.config), "selection_folds": [asdict(fold) for fold in folds],
        "selection_policy": {"minimum_complex_model_improvement_percent": 5.0, "practical_tie_percent": 1.0},
        "target_definition": {"return": "endpoint_price / origin_price - 1",
                              "realized_volatility": "sqrt(sum(consecutive future log returns squared))",
                              "annualized": False, "endpoint": "first stored observation on or after origin plus horizon",
                              "maximum_endpoint_slippage_days": 4},
        "requested_symbols": list(USER_ASSET_SYMBOLS), "evaluated_symbols": sorted(USER_ASSET_SYMBOLS),
        "missing_symbols": [], "groups": groups,
        "data_provenance": {"provenance_verified": True, "evaluation_cutoff": cutoff,
                            "symbol_count": 17, "row_count": ROW_COUNT,
                            "market_data_fingerprint_sha256": FINGERPRINT},
    }
    return json.loads(evaluator.report_json(report))


@pytest.fixture
def report(evidence_template):
    return deepcopy(evidence_template)


def _freeze(report, **overrides):
    return freezer.freeze_horizon_manifest(**{
        "report": report, "source_report_sha256": SOURCE_HASH,
        "expected_market_data_fingerprint": FINGERPRINT, "expected_row_count": ROW_COUNT,
        **overrides,
    })


def test_freeze_round_trip_is_deterministic_complete_and_not_deployable(report):
    original = deepcopy(report)
    manifest = _freeze(report)
    text = freezer.horizon_manifest_json(manifest)
    assert text == freezer.horizon_manifest_json(_freeze(report))
    assert freezer.horizon_manifest_from_dict(json.loads(text)) == manifest
    assert report == original
    payload = json.loads(text)
    assert payload["stage"] == "frozen_selection_not_deployable"
    assert payload["selection_count"] == len(manifest.records) == 102
    assert {(item["horizon_days"], item["symbol"], item["target_type"]) for item in payload["records"]} == {
        (horizon, symbol, target_name(target, horizon))
        for horizon in NEW_HORIZONS for symbol in USER_ASSET_SYMBOLS for target in ForecastTargetType
    }
    assert "return_30d" not in text and "realized_volatility_30d" not in text
    assert all(item["source_selection_report_sha256"] == SOURCE_HASH for item in payload["records"])
    assert payload["manifest_sha256"] == sha256_bytes(canonical_json_bytes({key: value for key, value in payload.items() if key != "manifest_sha256"}))
    warnings = [item for item in payload["records"] if item["selection_warning"]]
    assert len(warnings) == 1
    assert (warnings[0]["symbol"], warnings[0]["horizon_days"]) == ("QQQ", 21)
    assert warnings[0]["selection_warning"] == ARIMA_FIT_CONVERGENCE_WARNING


@pytest.mark.parametrize("field,value", [
    ("report_schema", "wrong"), ("stage", "deployable"), ("evaluation_cutoff", "2026-10-07"),
    ("evaluation_end_exclusive", "2026-09-17"), ("horizons", [7, 14, 30]),
    ("horizon_unit", "trading_days"), ("missing_symbols", ["AAPL"]),
    ("selection_folds", []), ("requested_symbols", []), ("evaluated_symbols", ["AAPL"] * 17),
])
def test_invalid_report_contract_is_rejected(report, field, value):
    report[field] = value
    with pytest.raises(freezer.HorizonSelectionError):
        _freeze(report)


@pytest.mark.parametrize("field,value", [("provenance_verified", False), ("row_count", 95488),
    ("row_count", True), ("symbol_count", 16), ("evaluation_cutoff", "2026-10-07"),
    ("market_data_fingerprint_sha256", "c" * 64)])
def test_unapproved_provenance_is_rejected(report, field, value):
    report["data_provenance"][field] = value
    with pytest.raises(freezer.HorizonSelectionError):
        _freeze(report)


@pytest.mark.parametrize("override", [{"source_report_sha256": "bad"},
    {"expected_market_data_fingerprint": "z" * 64}, {"expected_row_count": True}, {"expected_row_count": 0}])
def test_invalid_approval_arguments_are_rejected(report, override):
    with pytest.raises(freezer.HorizonSelectionError):
        _freeze(report, **override)


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "wrong-symbol", "mixed-target", "boolean-horizon"])
def test_group_coverage_is_exact(report, mutation):
    groups = report["groups"]
    if mutation == "missing":
        groups.pop()
    elif mutation == "duplicate":
        groups[-1] = deepcopy(groups[0])
    else:
        field, value = {"wrong-symbol": ("symbol", "UNSUPPORTED"), "mixed-target": ("target_type", "return_30d"),
                        "boolean-horizon": ("horizon_days", True)}[mutation]
        groups[0][field] = value
    with pytest.raises(freezer.HorizonSelectionError):
        _freeze(report)


@pytest.mark.parametrize("field,value", [("feature_set_version", "future"), ("target_set_version", "forecast-targets-v1"),
    ("candidate_ids", []), ("price_observation_count", True), ("feature_origin_count", 10001),
    ("target_origin_count", 0), ("label_complete_origin_count", 10001)])
def test_group_versions_candidates_and_counts_are_checked(report, field, value):
    report["groups"][0][field] = value
    with pytest.raises(freezer.HorizonSelectionError):
        _freeze(report)


@pytest.mark.parametrize("field,value", [
    ("symbol", "MSFT"), ("target_type", "return_30d"), ("horizon_days", 14),
    ("fold_id", "final-test-01"), ("fold_purpose", "calibration"), ("candidate_id", "unknown"),
    ("training_cutoff", "2023-03-18"), ("evaluation_origin_start", "2023-03-18"),
    ("evaluation_origin_end", "2025-09-18"), ("prediction_available", False),
    ("training_observation_count", 755), ("candidate_training_value_count", 1001),
    ("evaluated_observation_count", True), ("evaluated_observation_count", 101),
    ("mae", -1), ("mae", True), ("mae", float("nan")), ("rmse", float("inf")),
    ("directional_accuracy", 1.5), ("directional_evaluated_count", 99),
    ("negative_prediction_clipped_count", 0), ("warning", ARIMA_FIT_CONVERGENCE_WARNING),
])
def test_bad_candidate_results_are_rejected(report, field, value):
    report["groups"][0]["results"][0][field] = value
    with pytest.raises(freezer.HorizonSelectionError):
        _freeze(report)


def test_duplicate_fold_or_missing_result_is_rejected(report):
    results = report["groups"][0]["results"]
    results[-1] = deepcopy(results[0])
    with pytest.raises(freezer.HorizonSelectionError):
        _freeze(report)
    results.pop()
    with pytest.raises(freezer.HorizonSelectionError):
        _freeze(report)


@pytest.mark.parametrize("field,value", [("leading_selection_candidate_id", CANDIDATE_SIMPLICITY_ORDER[2]),
    ("best_baseline_mean_selection_mae", .001), ("baseline_remains_leading", False)])
def test_reported_winner_or_scores_cannot_override_policy(report, field, value):
    report["groups"][0]["selection_summary"][field] = value
    with pytest.raises(freezer.HorizonSelectionError, match="recomputed policy"):
        _freeze(report)


def test_selected_warning_cannot_be_removed_from_summary(report):
    group = next(group for group in report["groups"] if group["symbol"] == "QQQ"
                 and group["horizon_days"] == 21 and group["target_type"] == "realized_volatility_21d")
    group["selection_summary"]["candidate_statistics"][3]["warning"] = None
    with pytest.raises(freezer.HorizonSelectionError, match="warnings"):
        _freeze(report)


def test_manifest_digest_binds_source_report_and_approved_provenance(report):
    first = _freeze(report)
    changed_source = _freeze(report, source_report_sha256="c" * 64)
    assert first.manifest_sha256 != changed_source.manifest_sha256
    report["data_provenance"]["market_data_fingerprint_sha256"] = "d" * 64
    changed_data = _freeze(report, expected_market_data_fingerprint="d" * 64)
    assert first.manifest_sha256 != changed_data.manifest_sha256


@pytest.mark.parametrize("field,value", [("selection_fold_count", 5.0), ("minimum_training_origins", True)])
def test_plan_integer_types_are_not_silently_coerced(report, field, value):
    report["evaluation_plan"][field] = value
    with pytest.raises(freezer.HorizonSelectionError):
        _freeze(report)


def test_nonfinite_unused_evidence_cannot_be_frozen(report):
    report["extra_evidence"] = float("inf")
    with pytest.raises(freezer.HorizonSelectionError):
        _freeze(report)


def test_selected_return_arima_warning_is_retained_even_when_v1_summary_omits_it(report):
    group = report["groups"][0]
    for item in group["results"]:
        if item["candidate_id"] == CANDIDATE_SIMPLICITY_ORDER[3]:
            item.update(mae=.07, rmse=.08, warning=ARIMA_FIT_CONVERGENCE_WARNING)
    parsed = tuple(freezer._parse_result({**item, "target_type": ForecastTargetType.RETURN.value},
                                       target_type=ForecastTargetType.RETURN) for item in group["results"])
    group["selection_summary"] = json.loads(json.dumps(asdict(summarize_symbol_selection(
        symbol=group["symbol"], results=parsed, expected_selection_fold_ids=tuple(f"selection-{index:02d}" for index in range(1, 6))))))
    record = next(record for record in _freeze(report).records if record.horizon_days == 7
                  and record.selection.symbol == group["symbol"] and record.selection.target_type is ForecastTargetType.RETURN)
    assert record.selection.selection_warning == ARIMA_FIT_CONVERGENCE_WARNING


@pytest.mark.parametrize("mutation", ["hash", "stage", "release", "order", "count", "record-source", "record-target", "record-model", "negative-mae", "warning", "extra"])
def test_manifest_reader_rejects_tampering_even_with_rehashed_metadata(report, mutation):
    payload = json.loads(freezer.horizon_manifest_json(_freeze(report)))
    if mutation == "hash":
        payload["manifest_sha256"] = "0" * 64
    else:
        if mutation in {"stage", "release", "count"}:
            payload[{"stage": "stage", "release": "release_version", "count": "selection_count"}[mutation]] = "wrong"
        elif mutation == "order":
            payload["records"].reverse()
        elif mutation == "extra":
            payload["unexpected"] = True
        else:
            field, value = {"record-source": ("source_selection_report_sha256", "c" * 64),
                            "record-target": ("target_type", "realized_volatility_30d"),
                            "record-model": ("selected_candidate_id", "unknown"),
                            "negative-mae": ("selected_candidate_mean_selection_mae", -.1),
                            "warning": ("selection_warning", ARIMA_FIT_CONVERGENCE_WARNING)}[mutation]
            payload["records"][0][field] = value
        payload["manifest_sha256"] = sha256_bytes(canonical_json_bytes({key: value for key, value in payload.items() if key != "manifest_sha256"}))
    with pytest.raises(freezer.HorizonSelectionError):
        freezer.horizon_manifest_from_dict(payload)


def _arguments(source, output, digest):
    return ["--selection-report", str(source), "--expected-selection-report-sha256", digest,
            "--expected-market-data-fingerprint", FINGERPRINT, "--expected-row-count", str(ROW_COUNT), "--output", str(output)]


def test_cli_writes_only_new_manifest_and_preserves_source_without_fitting(report, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(evaluator, "REPOSITORY_ROOT", tmp_path)
    source = tmp_path / "selection.json"
    original = evaluator.report_json(report).encode()
    source.write_bytes(original)
    output = tmp_path / "forecasting-evidence/new/selection-manifest.json"
    database = MagicMock()
    fitting = MagicMock()
    monkeypatch.setattr(evaluator, "run_persisted_evaluation", database)
    monkeypatch.setattr(evaluator, "evaluate_horizon_selection", fitting)
    script.main(_arguments(source, output, sha256_bytes(original)))
    manifest = freezer.horizon_manifest_from_dict(json.loads(output.read_text(encoding="utf-8")))
    assert len(manifest.records) == 102
    assert source.read_bytes() == original
    database.assert_not_called()
    fitting.assert_not_called()
    assert "Selected-model warnings retained: 1" in capsys.readouterr().out
    saved = output.read_bytes()
    with pytest.raises(SystemExit, match="already exists"):
        script.main(_arguments(source, output, sha256_bytes(original)))
    assert output.read_bytes() == saved


@pytest.mark.parametrize("raw", [b'{"groups":[],"groups":[]}', b'{"value":NaN}', b'{"value":Infinity}', b'invalid', b'\xff'])
def test_cli_rejects_ambiguous_or_malformed_json_before_output(raw, tmp_path, monkeypatch):
    monkeypatch.setattr(evaluator, "REPOSITORY_ROOT", tmp_path)
    source = tmp_path / "source.json"
    source.write_bytes(raw)
    output = tmp_path / "forecasting-evidence/new/manifest.json"
    with pytest.raises(SystemExit):
        script.main(_arguments(source, output, sha256_bytes(raw)))
    assert not output.exists()


def test_changed_source_hash_stops_before_parsing_or_output(tmp_path, monkeypatch):
    monkeypatch.setattr(evaluator, "REPOSITORY_ROOT", tmp_path)
    source = tmp_path / "changed.json"
    source.write_bytes(b'not even valid JSON')
    output = tmp_path / "forecasting-evidence/new/manifest.json"
    with pytest.raises(SystemExit, match="reviewed report"):
        script.main(_arguments(source, output, SOURCE_HASH))
    assert not output.exists()


@pytest.mark.parametrize("relative", ["forecasting-evidence/forecast-v1-20260917/manifest.json",
    "backend/artifacts/forecasting/forecast-v1-20260917/manifest.json", "manifest.json", "forecasting-evidence/new.txt"])
def test_cli_cannot_write_frozen_v1_artifacts_or_outside_evidence(tmp_path, monkeypatch, relative):
    monkeypatch.setattr(evaluator, "REPOSITORY_ROOT", tmp_path)
    output = tmp_path / relative
    with pytest.raises(SystemExit, match="output must"):
        script.main(_arguments(tmp_path / "absent.json", output, SOURCE_HASH))
    assert not output.exists()


def test_freezer_is_not_connected_to_runtime_or_artifact_training():
    root = Path(script.__file__).resolve().parents[2]
    for relative in ["backend/app/forecasting/inference.py", "backend/app/forecasting/registry.py", "backend/app/api/routes/forecasting.py"]:
        assert "horizon_selection_manifest" not in (root / relative).read_text(encoding="utf-8")
    source = Path(script.__file__).read_text(encoding="utf-8")
    assert "train_deployment_artifact" not in source
    assert "calibrate_frozen_selection" not in source
    assert "evaluate_frozen_final_test" not in source
    assert "create_database_engine" not in source
