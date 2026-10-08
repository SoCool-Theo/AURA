from contextlib import contextmanager
from datetime import date, timedelta
from decimal import Decimal
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

import backend.scripts.evaluate_forecasting_baselines as script


def _synthetic_history(count: int = 300):
    start = date(2024, 1, 1)
    records = [
        SimpleNamespace(
            symbol="AAPL",
            date=start + timedelta(days=index),
            adjusted_close=Decimal("100"),
        )
        for index in range(count)
    ]
    return script.build_price_histories(records)[0]


def _empty_report() -> script.BaselineEvaluationReport:
    return script.BaselineEvaluationReport(
        evaluation_cutoff=date(2026, 9, 17),
        evaluation_end_exclusive=date(2026, 9, 18),
        requested_symbols=("AAPL",),
        evaluated_symbols=("AAPL",),
        missing_symbols=(),
        results=(),
    )


def test_pure_script_evaluation_is_deterministic_on_synthetic_history() -> None:
    history = _synthetic_history()

    first = script.evaluate_histories(
        (history,),
        evaluation_cutoff=date(2026, 9, 17),
    )
    second = script.evaluate_histories(
        (history,),
        evaluation_cutoff=date(2026, 9, 17),
    )

    assert first == second
    assert first.evaluated_symbols == ("AAPL",)
    assert len(first.results) == 28
    assert all(result.prediction_available is False for result in first.results)


def test_report_json_is_strict_deterministic_and_date_serialized() -> None:
    payload = script.report_json(_empty_report())

    assert payload == script.report_json(_empty_report())
    decoded = json.loads(payload)
    assert decoded["evaluation_cutoff"] == "2026-09-17"
    assert decoded["evaluation_end_exclusive"] == "2026-09-18"
    assert decoded["results"] == []
    assert "NaN" not in payload
    assert "Infinity" not in payload


def test_persisted_evaluation_reads_market_data_without_commit() -> None:
    engine = MagicMock()
    session = MagicMock()
    session_factory = MagicMock()
    service = MagicMock()
    service.get_range.return_value = [SimpleNamespace(name="record")]
    histories = (_synthetic_history(1),)
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
        patch.object(script, "evaluate_histories", return_value=expected) as evaluate,
    ):
        result = script.run_persisted_baseline_evaluation(
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


def test_main_writes_user_selected_json_without_running_real_database(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output_path = tmp_path / "baseline-report.json"
    report = _empty_report()
    with patch.object(
        script,
        "run_persisted_baseline_evaluation",
        return_value=report,
    ) as evaluate:
        script.main(
            [
                "--evaluation-cutoff",
                "2026-09-17",
                "--output",
                str(output_path),
            ]
        )

    evaluate.assert_called_once_with(evaluation_cutoff=date(2026, 9, 17))
    assert output_path.read_text(encoding="utf-8") == script.report_json(report)
    output = capsys.readouterr().out
    assert "baseline evaluation completed" in output
    assert str(output_path) in output


def test_invalid_cli_date_is_rejected_before_evaluation() -> None:
    with pytest.raises(Exception, match="YYYY-MM-DD"):
        script._parse_date("not-a-date")


def test_script_has_no_provider_training_or_database_write_dependencies() -> None:
    source = Path(script.__file__).read_text(encoding="utf-8").lower()

    assert "yfinance" not in source
    assert "update_market_data" not in source
    assert "backfill" not in source
    assert "supabase" not in source
    assert "marketdatarepository" not in source
    assert ".commit(" not in source
    assert "sklearn" not in source
    assert "statsmodels" not in source
    assert ".fit(" not in source
