from contextlib import contextmanager
from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

import backend.scripts.evaluate_forecasting_volatility_models as script
from backend.app.forecasting.models import (
    ARIMA_FIT_CONVERGENCE_WARNING,
    VOLATILITY_ARIMA_CANDIDATE_ID,
)
from backend.app.forecasting.selection import (
    VOLATILITY_CANDIDATE_SIMPLICITY_ORDER,
)


def _synthetic_history(count: int = 1):
    start = date(2020, 1, 1)
    records = [
        SimpleNamespace(
            symbol="AAPL",
            date=start + timedelta(days=index),
            adjusted_close=Decimal("100"),
        )
        for index in range(count)
    ]
    return script.build_price_histories(records)[0]


def _result(candidate_id: str, fold, mae: float = 0.1):
    return script.ForecastEvaluationResult(
        symbol="AAPL",
        target_type=script.ForecastTargetType.VOLATILITY,
        candidate_id=candidate_id,
        fold_id=fold.fold_id,
        fold_purpose=fold.purpose,
        training_cutoff=fold.training_cutoff,
        evaluation_origin_start=fold.origin_start,
        evaluation_origin_end=fold.origin_end,
        training_observation_count=756,
        candidate_training_value_count=756,
        evaluated_observation_count=20,
        prediction_available=True,
        mae=mae,
        rmse=mae,
        directional_accuracy=None,
        directional_evaluated_count=None,
        return_mape=None,
        warning=None,
        negative_prediction_clipped_count=1,
    )


def _empty_report() -> script.VolatilityModelEvaluationReport:
    return script.VolatilityModelEvaluationReport(
        evaluation_cutoff=date(2026, 9, 17),
        evaluation_end_exclusive=date(2026, 9, 18),
        requested_symbols=("AAPL",),
        evaluated_symbols=(),
        missing_symbols=("AAPL",),
        selection_fold_ids=tuple(
            f"selection-{index:02d}" for index in range(1, 6)
        ),
        candidate_ids=VOLATILITY_CANDIDATE_SIMPLICITY_ORDER,
        results=(),
        selection_summaries=(),
    )


def test_script_executes_only_five_selection_folds_without_fitting() -> None:
    history = _synthetic_history()
    seen_purposes: list[tuple[script.FoldPurpose, ...]] = []

    def fake_evaluate_candidate(
        *,
        dataset,
        plan,
        target_type,
        candidate,
        fold_purposes,
    ):
        assert target_type is script.ForecastTargetType.VOLATILITY
        seen_purposes.append(tuple(fold_purposes))
        return tuple(
            _result(candidate.candidate_id, fold)
            for fold in plan.folds
            if fold.purpose in fold_purposes
        )

    with patch.object(
        script,
        "evaluate_candidate",
        side_effect=fake_evaluate_candidate,
    ):
        first = script.evaluate_histories(
            (history,),
            evaluation_cutoff=date(2026, 9, 17),
        )
        second = script.evaluate_histories(
            (history,),
            evaluation_cutoff=date(2026, 9, 17),
        )

    assert first == second
    assert first.candidate_ids == VOLATILITY_CANDIDATE_SIMPLICITY_ORDER
    assert len(first.selection_fold_ids) == 5
    assert len(first.results) == 25
    assert all(
        result.fold_purpose is script.FoldPurpose.SELECTION
        for result in first.results
    )
    assert seen_purposes == [(script.FoldPurpose.SELECTION,)] * 10


def test_persisted_path_is_read_only_and_uses_user_assets() -> None:
    engine = MagicMock()
    session = MagicMock()
    session_factory = MagicMock()
    service = MagicMock()
    service.get_range.return_value = [SimpleNamespace(name="record")]
    histories = (_synthetic_history(),)
    expected = _empty_report()

    @contextmanager
    def fake_session_scope(factory):
        assert factory is session_factory
        yield session

    with (
        patch.object(script, "create_database_engine", return_value=engine),
        patch.object(
            script,
            "create_session_factory",
            return_value=session_factory,
        ),
        patch.object(script, "session_scope", side_effect=fake_session_scope),
        patch.object(script, "MarketDataService", return_value=service),
        patch.object(script, "build_price_histories", return_value=histories),
        patch.object(
            script,
            "evaluate_histories",
            return_value=expected,
        ) as evaluate,
    ):
        result = script.run_persisted_volatility_model_evaluation(
            evaluation_cutoff=date(2026, 9, 17)
        )

    assert result is expected
    service.get_range.assert_called_once_with(
        script.USER_ASSET_SYMBOLS,
        date.min,
        date(2026, 9, 17),
    )
    evaluate.assert_called_once_with(
        histories,
        evaluation_cutoff=date(2026, 9, 17),
    )
    session.commit.assert_not_called()
    session.add.assert_not_called()
    session.delete.assert_not_called()
    engine.dispose.assert_called_once_with()


def test_report_json_is_strict_deterministic_and_preserves_metadata() -> None:
    fold = SimpleNamespace(
        fold_id="selection-01",
        purpose=script.FoldPurpose.SELECTION,
        training_cutoff=date(2023, 3, 18),
        origin_start=date(2023, 3, 18),
        origin_end=date(2023, 9, 18),
    )
    result = replace(
        _result(VOLATILITY_ARIMA_CANDIDATE_ID, fold),
        warning=ARIMA_FIT_CONVERGENCE_WARNING,
    )
    report = replace(
        _empty_report(),
        evaluated_symbols=("AAPL",),
        missing_symbols=(),
        results=(result,),
    )

    payload = script.report_json(report)
    decoded = json.loads(payload)

    assert payload == script.report_json(report)
    assert decoded["results"][0]["negative_prediction_clipped_count"] == 1
    assert decoded["results"][0]["directional_accuracy"] is None
    assert decoded["results"][0]["return_mape"] is None
    assert (
        decoded["results"][0]["warning"]
        == ARIMA_FIT_CONVERGENCE_WARNING
    )
    assert "NaN" not in payload
    assert "Infinity" not in payload


def test_main_writes_selected_output_without_real_evaluation(tmp_path: Path) -> None:
    output = tmp_path / "volatility-selection.json"
    report = _empty_report()

    with patch.object(
        script,
        "run_persisted_volatility_model_evaluation",
        return_value=report,
    ) as run:
        script.main(
            [
                "--evaluation-cutoff",
                "2026-09-17",
                "--output",
                str(output),
            ]
        )

    run.assert_called_once_with(evaluation_cutoff=date(2026, 9, 17))
    assert output.read_text(encoding="utf-8") == script.report_json(report)


def test_invalid_date_is_rejected_before_evaluation() -> None:
    with pytest.raises(Exception, match="YYYY-MM-DD"):
        script._parse_date("not-a-date")


def test_script_source_has_no_provider_write_or_artifact_workflow() -> None:
    source = Path(script.__file__).read_text(encoding="utf-8").lower()

    assert "yfinance" not in source
    assert "update_market_data" not in source
    assert "backfill" not in source
    assert "supabase" not in source
    assert "marketdatarepository" not in source
    assert ".commit(" not in source
    assert ".add(" not in source
    assert ".delete(" not in source
    assert "calibration-01" not in source
    assert "final-test-01" not in source
