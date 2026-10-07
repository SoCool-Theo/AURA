"""Synthetic/mocked regressions; no live DB, provider, or estimator fitting."""

from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import date, timedelta
from decimal import Decimal
import json
import math
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import backend.scripts.evaluate_forecasting_horizons as script
from app.forecasting import multi_horizon as horizons
from app.forecasting.baselines import HistoricalMeanBaseline
from app.forecasting.data import AssetPriceHistory, ForecastPriceObservation, build_forecast_dataset
from app.forecasting.evaluation import ForecastTargetType
from app.forecasting.selection import CANDIDATE_SIMPLICITY_ORDER, VOLATILITY_CANDIDATE_SIMPLICITY_ORDER
from app.forecasting.splits import ChronologicalEvaluationPlan, EvaluationFold, EvaluationPlanConfig, FoldPurpose
from app.forecasting.targets import build_target_rows


def _history(values, symbol="AAPL"):
    return AssetPriceHistory(symbol, tuple(ForecastPriceObservation(day, float(price)) for day, price in values))


@pytest.mark.parametrize("horizon", [7, 14, 21, 30])
@pytest.mark.parametrize("slippage", [0, 1, 2, 3, 4])
def test_calendar_endpoint_and_allowed_slippage(horizon, slippage):
    start = date(2026, 1, 1)
    endpoint = start + timedelta(days=horizon + slippage)
    row, = horizons.build_horizon_targets(_history([(start, 100), (endpoint, 110)]), horizon_days=horizon)
    assert row.horizon_days == horizon
    assert row.requested_target_date == start + timedelta(days=horizon)
    assert row.endpoint_date == endpoint
    assert row.endpoint_slippage_days == slippage
    assert row.return_value == pytest.approx(.1)
    assert row.realized_volatility == pytest.approx(math.log(1.1))


@pytest.mark.parametrize("horizon", [7, 14, 21, 30])
def test_missing_late_endpoints_are_not_filled_or_backfilled(horizon):
    start = date(2026, 1, 1)
    history = _history([(start, 100), (start + timedelta(days=horizon - 1), 110),
                        (start + timedelta(days=horizon + 5), 120)])
    assert all(row.origin_date != start for row in horizons.build_horizon_targets(history, horizon_days=horizon))


@pytest.mark.parametrize("value", [True, False, 0, 5, 28, 31, 7.0, "7", None])
def test_unsupported_horizons_are_rejected(value):
    with pytest.raises(ValueError, match="horizon"):
        horizons.validate_horizon(value)


def test_horizon_returns_use_actual_endpoints_not_rescaled_thirty_day_output():
    start = date(2026, 1, 1)
    history = _history([(start + timedelta(days=day), price)
                        for day, price in [(0, 100), (7, 110), (14, 90), (21, 130), (30, 120)]])
    first = {day: horizons.build_horizon_targets(history, horizon_days=day)[0]
             for day in horizons.SUPPORTED_HORIZONS}
    assert [first[day].return_value for day in [7, 14, 21, 30]] == pytest.approx([.1, -.1, .3, .2])
    assert first[7].return_value != pytest.approx(first[30].return_value * 7 / 30)


def test_volatility_stops_at_endpoint_and_future_mutation_does_not_change_label():
    start = date(2026, 1, 1)
    points = [(start, 100), (start + timedelta(days=3), 110),
              (start + timedelta(days=7), 99), (start + timedelta(days=8), 999)]
    first = horizons.build_horizon_targets(_history(points), horizon_days=7)[0]
    changed = horizons.build_horizon_targets(_history([*points[:-1], (points[-1][0], 1)]), horizon_days=7)[0]
    assert first == changed
    assert first.realized_volatility == pytest.approx(math.sqrt(math.log(1.1) ** 2 + math.log(.9) ** 2))


def test_thirty_day_labels_and_features_match_original_v1_without_changing_its_version():
    start = date(2020, 1, 1)
    history = _history([(start + timedelta(days=index), 100 + index) for index in range(320)])
    original = build_target_rows(history)
    new = horizons.build_horizon_targets(history, horizon_days=30)
    for old, row in zip(original, new, strict=True):
        assert row.return_value == old.return_30d
        assert row.realized_volatility == old.realized_volatility_30d
        assert row.endpoint_date == old.endpoint_date
    v1 = build_forecast_dataset(history)
    dataset = horizons.build_horizon_dataset(history, horizon_days=30)
    assert tuple(row.features for row in dataset.rows) == tuple(row.features for row in v1.rows)
    assert v1.target_set_version == "forecast-targets-v1"
    assert horizons.target_version(30) == "forecast-targets-30d-v1"


def test_dataset_is_chronological_joins_only_warmed_up_complete_labels_and_rejects_mixed_horizons():
    start = date(2020, 1, 1)
    history = _history([(start + timedelta(days=index), 100) for index in range(300)])
    observations = history.observations
    dataset = horizons.build_horizon_dataset(history, horizon_days=7)
    assert len(dataset.rows) == 300 - 252 - 7
    assert dataset.rows[0].features.origin_date == start + timedelta(days=252)
    assert history.observations is observations
    with pytest.raises(ValueError, match="mix"):
        replace(dataset, horizon_days=14)


def _purged_dataset():
    rows = []
    for origin, value in [(date(2025, 1, 1), .1), (date(2025, 1, 15), .3),
                          (date(2025, 5, 29), 99.), (date(2025, 6, 1), .4),
                          (date(2025, 6, 24), 999.)]:
        endpoint = origin + timedelta(days=7)
        rows.append(horizons.HorizonDatasetRow(
            SimpleNamespace(symbol="AAPL", origin_date=origin),
            horizons.HorizonTargetRow("AAPL", 7, origin, endpoint, endpoint, 0, value, value),
        ))
    return horizons.HorizonDataset("AAPL", 7, 300, 5, 5, tuple(rows))


@pytest.mark.parametrize("target_type", [ForecastTargetType.RETURN, ForecastTargetType.VOLATILITY])
def test_selection_purges_training_and_scored_endpoints_and_never_evaluates_later_folds(target_type):
    selection = EvaluationFold("selection-01", FoldPurpose.SELECTION, date(2025, 6, 1), date(2025, 7, 1))
    calibration = EvaluationFold("calibration-01", FoldPurpose.CALIBRATION, date(2025, 7, 1), date(2025, 8, 1))
    final = EvaluationFold("final-test-01", FoldPurpose.FINAL_TEST, date(2025, 8, 1), date(2025, 9, 1))
    plan = ChronologicalEvaluationPlan(EvaluationPlanConfig(date(2025, 9, 1), minimum_training_origins=2), (selection, calibration, final))
    results, _ = horizons.evaluate_horizon_selection(
        dataset=_purged_dataset(), plan=plan, target_type=target_type, candidates=(HistoricalMeanBaseline(),),
    )
    assert len(results) == 1
    result = results[0]
    assert result.fold_purpose is FoldPurpose.SELECTION
    assert result.training_observation_count == 2
    assert result.evaluated_observation_count == 1
    assert result.mae == pytest.approx(.2)  # Mean(.1,.3) versus actual .4; neither 99 nor 999 leaks.


def test_approved_candidate_order_is_reused_without_instantiating_fitted_estimators():
    assert tuple(candidate.candidate_id for candidate in horizons.horizon_candidates(ForecastTargetType.RETURN)) == CANDIDATE_SIMPLICITY_ORDER
    assert tuple(candidate.candidate_id for candidate in horizons.horizon_candidates(ForecastTargetType.VOLATILITY)) == VOLATILITY_CANDIDATE_SIMPLICITY_ORDER


@dataclass
class _Result:
    target_type: object
    fold_purpose: object
    training_cutoff: date
    negative_prediction_clipped_count: int = 0


@dataclass
class _Summary:
    symbol: str
    leading_selection_candidate_id: str = "historical_average"


def test_report_horizon_identity_is_explicit_strict_deterministic_and_not_deployable(monkeypatch):
    calls = []
    def fake_evaluate(*, dataset, plan, target_type, candidates):
        calls.append((dataset.horizon_days, target_type))
        return ((_Result(target_type, FoldPurpose.SELECTION, plan.folds[0].origin_start),), _Summary(dataset.symbol))
    monkeypatch.setattr(script, "evaluate_horizon_selection", fake_evaluate)
    history = _history([(date(2020, 1, 1) + timedelta(days=index), 100) for index in range(300)])
    report = script.evaluate_histories((history,), evaluation_cutoff=date(2026, 9, 17))
    payload = script.report_json(report)
    assert payload == script.report_json(report)
    decoded = json.loads(payload)
    assert decoded["horizons"] == [7, 14, 21]
    assert decoded["stage"] == "selection_only_not_deployable"
    assert decoded["data_provenance"]["provenance_verified"] is False
    assert len(calls) == len(decoded["groups"]) == 6
    assert "return_30d" not in payload and "realized_volatility_30d" not in payload
    assert all(result["target_type"] == group["target_type"]
               for group in decoded["groups"] for result in group["results"])
    report["invalid"] = float("nan")
    with pytest.raises(ValueError):
        script.report_json(report)


def test_invalid_horizon_lists_and_future_history_fail_before_evaluation(monkeypatch):
    evaluate = MagicMock()
    monkeypatch.setattr(script, "evaluate_horizon_selection", evaluate)
    history = _history([(date(2026, 10, 1), 100)])
    for days in [(), (7, 7), (7, 9)]:
        with pytest.raises(ValueError):
            script.evaluate_histories((history,), evaluation_cutoff=date(2026, 10, 1), horizons=days)
    with pytest.raises(ValueError, match="cutoff"):
        script.evaluate_histories((history,), evaluation_cutoff=date(2026, 9, 17))
    evaluate.assert_not_called()


@pytest.mark.parametrize("url", ["", "postgresql+psycopg://user:private@remote.example:5433/db",
    "postgresql+psycopg://user:private@127.0.0.1:5432/db", "sqlite://",
    "postgresql+psycopg://user:private@127.0.0.1:5433/db?host=remote.example"])
def test_remote_implicit_or_redirected_database_urls_are_rejected_safely(url):
    with pytest.raises(script.SelectionProvenanceError) as error:
        script.validate_local_database_url(url)
    assert "private" not in str(error.value)


def _persisted_mocks(monkeypatch):
    engine, session, evaluate = MagicMock(), MagicMock(), MagicMock(return_value={})
    records = tuple(SimpleNamespace(symbol=symbol, date=date(2020, 1, 1),
                                    adjusted_close=Decimal("100"), volume=None, source="synthetic")
                    for symbol in script.USER_ASSET_SYMBOLS)
    @contextmanager
    def scope(_):
        yield session
    monkeypatch.setattr(script, "create_database_engine", lambda *args, **kwargs: engine)
    monkeypatch.setattr(script, "create_session_factory", lambda _: object())
    monkeypatch.setattr(script, "session_scope", scope)
    monkeypatch.setattr(script, "MarketDataService", lambda _: SimpleNamespace(get_range=lambda *args: records))
    monkeypatch.setattr(script, "evaluate_histories", evaluate)
    from app.forecasting.fingerprints import build_market_data_fingerprint
    fingerprint = build_market_data_fingerprint(records, evaluation_cutoff=date(2026, 9, 17), symbols=script.USER_ASSET_SYMBOLS)
    return engine, session, evaluate, fingerprint


def test_fingerprint_mismatch_stops_before_fitting_and_disposes_database(monkeypatch):
    engine, session, evaluate, fingerprint = _persisted_mocks(monkeypatch)
    with pytest.raises(script.SelectionProvenanceError, match="mismatch"):
        script.run_persisted_evaluation(database_url="postgresql+psycopg://user:private@127.0.0.1:5433/db",
            evaluation_cutoff=date(2026, 9, 17), horizons=(7,),
            expected_market_data_fingerprint="0" * 64, expected_row_count=fingerprint.total_row_count)
    evaluate.assert_not_called()
    engine.dispose.assert_called_once()
    session.commit.assert_not_called()
    assert str(session.execute.call_args.args[0]) == "SET TRANSACTION READ ONLY"


def test_verified_snapshot_is_read_only_closed_before_evaluation_and_never_exposes_credentials(monkeypatch):
    engine, session, evaluate, fingerprint = _persisted_mocks(monkeypatch)
    def fake_evaluate(*args, **kwargs):
        engine.dispose.assert_called_once()
        assert len(args[0]) == 17
        return {"stage": "selection_only_not_deployable"}
    evaluate.side_effect = fake_evaluate
    report = script.run_persisted_evaluation(database_url="postgresql+psycopg://user:private@127.0.0.1:5433/db",
        evaluation_cutoff=date(2026, 9, 17), horizons=(7, 14, 21),
        expected_market_data_fingerprint=fingerprint.sha256, expected_row_count=fingerprint.total_row_count)
    assert report["data_provenance"]["provenance_verified"] is True
    assert "private" not in script.report_json(report)
    session.commit.assert_not_called()
    session.add.assert_not_called()
    session.delete.assert_not_called()


def test_output_requires_new_evidence_and_protects_frozen_files_before_database_access(tmp_path, monkeypatch):
    monkeypatch.setattr(script, "REPOSITORY_ROOT", tmp_path)
    evidence = tmp_path / "forecasting-evidence"
    evidence.mkdir()
    existing = evidence / "existing.json"
    existing.write_text("keep", encoding="utf-8")
    for output in [existing, evidence / "forecast-v1-20260917" / "new.json", tmp_path / "backend/artifacts/forecasting/new.json", evidence / "new.txt"]:
        with pytest.raises(ValueError):
            script.validate_output_path(output)
    assert existing.read_text(encoding="utf-8") == "keep"
    assert script.validate_output_path(evidence / "new-run/selection.json") == (evidence / "new-run/selection.json").resolve()
    run = MagicMock()
    monkeypatch.setattr(script, "run_persisted_evaluation", run)
    with pytest.raises(SystemExit):
        script.main(["--env-file", "absent.env", "--evaluation-cutoff", "2026-09-17",
                     "--expected-market-data-fingerprint", "0" * 64, "--expected-row-count", "17", "--output", str(existing)])
    run.assert_not_called()


def test_manual_main_writes_only_a_new_report_without_database_or_model_execution(tmp_path, monkeypatch):
    monkeypatch.setattr(script, "REPOSITORY_ROOT", tmp_path)
    output = tmp_path / "forecasting-evidence/new-run/selection.json"
    monkeypatch.setattr(script, "database_url_from_env_file", lambda *args, **kwargs: "mock-url")
    run = MagicMock(return_value={"stage": "selection_only_not_deployable"})
    monkeypatch.setattr(script, "run_persisted_evaluation", run)
    script.main(["--env-file", "selected.env", "--evaluation-cutoff", "2026-09-17",
                 "--expected-market-data-fingerprint", "0" * 64, "--expected-row-count", "17", "--output", str(output)])
    assert json.loads(output.read_text(encoding="utf-8"))["stage"] == "selection_only_not_deployable"
    assert run.call_args.kwargs["horizons"] == horizons.NEW_HORIZONS
    assert run.call_args.kwargs["evaluation_cutoff"] == date(2026, 9, 17)


def test_new_selection_workflow_is_not_on_api_inference_path_and_has_no_artifact_writer():
    root = Path(script.__file__).resolve().parents[2]
    for relative in ["backend/app/forecasting/inference.py", "backend/app/forecasting/registry.py",
                     "backend/app/api/routes/forecasting.py"]:
        assert "multi_horizon" not in (root / relative).read_text(encoding="utf-8")
    source = Path(script.__file__).read_text(encoding="utf-8")
    assert "write_artifact_bundle" not in source
    assert "train_deployment_artifact" not in source
    assert "calibrate_frozen_selection" not in source
    assert "evaluate_frozen_final_test" not in source
