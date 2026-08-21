from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from backend.app.data_pipeline.backfill import HistoricalSymbolCoverage
import backend.scripts.backfill_historical_market_data as backfill_script


def _result() -> backfill_script.MarketDataBackfillResult:
    return backfill_script.MarketDataBackfillResult(
        requested_symbols=("MSFT", "AAPL"),
        requested_start_date=date(2000, 1, 1),
        requested_end_date=date(2026, 1, 31),
        row_count=3,
        stored_count=3,
        coverage=(
            HistoricalSymbolCoverage(
                "MSFT",
                2,
                date(2000, 1, 3),
                date(2026, 1, 30),
            ),
            HistoricalSymbolCoverage(
                "AAPL",
                1,
                date(2000, 1, 4),
                date(2000, 1, 4),
            ),
        ),
    )


def _database_mocks() -> tuple[
    MagicMock,
    MagicMock,
    Mock,
    MagicMock,
]:
    engine = MagicMock(spec=Engine)
    session = MagicMock(spec=Session)
    session_factory = Mock(return_value=session)
    service = MagicMock(spec=backfill_script.MarketDataBackfillService)
    service.run.return_value = _result()
    return engine, session, session_factory, service


def test_parser_uses_approved_backfill_defaults() -> None:
    args = backfill_script._build_parser().parse_args([])

    assert args.start_date == "2000-01-01"
    assert args.end_date is None
    assert args.symbols is None


def test_default_end_date_and_aura_symbols_are_resolved_for_service() -> None:
    engine, session, session_factory, service = _database_mocks()
    with (
        patch.object(backfill_script, "date") as date_type,
        patch.object(
            backfill_script,
            "create_database_engine",
            return_value=engine,
        ),
        patch.object(
            backfill_script,
            "create_session_factory",
            return_value=session_factory,
        ),
        patch.object(
            backfill_script,
            "MarketDataBackfillService",
            return_value=service,
        ),
    ):
        date_type.today.return_value = date(2026, 8, 21)
        backfill_script.backfill_historical_market_data()

    service.run.assert_called_once_with(
        backfill_script.DEFAULT_SYMBOLS,
        date(2000, 1, 1),
        date(2026, 8, 21),
    )
    service.run.assert_called_once()
    assert service.run.call_args.args[0] is backfill_script.DEFAULT_SYMBOLS


def test_custom_arguments_are_handed_to_existing_service_workflow() -> None:
    engine, _, session_factory, service = _database_mocks()
    symbols = [" msft ", "aapl"]
    with (
        patch.object(
            backfill_script,
            "create_database_engine",
            return_value=engine,
        ),
        patch.object(
            backfill_script,
            "create_session_factory",
            return_value=session_factory,
        ),
        patch.object(
            backfill_script,
            "MarketDataBackfillService",
            return_value=service,
        ),
    ):
        backfill_script.backfill_historical_market_data(
            symbols=symbols,
            start_date="2001-01-01",
            end_date="2001-12-31",
        )

    service.run.assert_called_once_with(
        symbols,
        date(2001, 1, 1),
        date(2001, 12, 31),
    )
    assert service.run.call_args.args[0] is symbols
    assert symbols == [" msft ", "aapl"]


def test_success_commits_exactly_once_and_cleans_up_resources() -> None:
    engine, session, session_factory, service = _database_mocks()
    with (
        patch.object(
            backfill_script,
            "create_database_engine",
            return_value=engine,
        ),
        patch.object(
            backfill_script,
            "create_session_factory",
            return_value=session_factory,
        ),
        patch.object(
            backfill_script,
            "MarketDataBackfillService",
            return_value=service,
        ) as service_type,
    ):
        result = backfill_script.backfill_historical_market_data(
            symbols=["AAPL"],
            start_date="2000-01-01",
            end_date="2000-01-31",
        )

    assert result is service.run.return_value
    service_type.assert_called_once_with(session)
    service.run.assert_called_once()
    session.commit.assert_called_once_with()
    session.rollback.assert_not_called()
    session.close.assert_called_once_with()
    engine.dispose.assert_called_once_with()


def test_service_failure_rolls_back_without_successful_commit() -> None:
    engine, session, session_factory, service = _database_mocks()
    failure = ValueError("unresolved symbol")
    service.run.side_effect = failure
    with (
        patch.object(
            backfill_script,
            "create_database_engine",
            return_value=engine,
        ),
        patch.object(
            backfill_script,
            "create_session_factory",
            return_value=session_factory,
        ),
        patch.object(
            backfill_script,
            "MarketDataBackfillService",
            return_value=service,
        ),
    ):
        with pytest.raises(ValueError) as raised:
            backfill_script.backfill_historical_market_data(
                symbols=["AAPL", "MISSING"],
                end_date="2026-01-31",
            )

    assert raised.value is failure
    session.commit.assert_not_called()
    session.rollback.assert_called_once_with()
    session.close.assert_called_once_with()
    engine.dispose.assert_called_once_with()


def test_main_reports_service_failure_without_success_output(
    capsys: pytest.CaptureFixture[str],
) -> None:
    failure = RuntimeError("storage failed")
    with patch.object(
        backfill_script,
        "backfill_historical_market_data",
        side_effect=failure,
    ):
        with pytest.raises(
            SystemExit,
            match="backfill failed: storage failed",
        ) as raised:
            backfill_script.main([])

    assert raised.value.__cause__ is failure
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize(
    ("start_date", "end_date", "message"),
    [
        (
            "2026-02-01",
            "2026-01-31",
            "start_date must be on or before end_date",
        ),
        (
            "not-a-date",
            "2026-01-31",
            "start_date must use YYYY-MM-DD format",
        ),
    ],
)
def test_invalid_date_arguments_fail_before_database_or_service_setup(
    start_date: str,
    end_date: str,
    message: str,
) -> None:
    with (
        patch.object(backfill_script, "create_database_engine") as engine,
        patch.object(backfill_script, "MarketDataBackfillService") as service,
    ):
        with pytest.raises(ValueError, match=message):
            backfill_script.backfill_historical_market_data(
                start_date=start_date,
                end_date=end_date,
            )

    engine.assert_not_called()
    service.assert_not_called()


def test_main_passes_cli_arguments_to_backfill_once() -> None:
    result = _result()
    with patch.object(
        backfill_script,
        "backfill_historical_market_data",
        return_value=result,
    ) as backfill:
        backfill_script.main(
            [
                "--symbols",
                "MSFT",
                "AAPL",
                "--start-date",
                "2001-01-01",
                "--end-date",
                "2001-12-31",
            ]
        )

    backfill.assert_called_once_with(
        symbols=["MSFT", "AAPL"],
        start_date="2001-01-01",
        end_date="2001-12-31",
    )


def test_success_output_is_deterministic_and_uses_coverage_language(
    capsys: pytest.CaptureFixture[str],
) -> None:
    backfill_script._print_result(_result())

    lines = capsys.readouterr().out.splitlines()
    assert lines == [
        "Aura historical market-data backfill completed.",
        "------------------------------------------------",
        "Requested range: 2000-01-01 to 2026-01-31",
        "Symbols:         MSFT, AAPL",
        "Rows processed:  3",
        "Rows stored:     3",
        "Per-symbol coverage:",
        "  MSFT",
        "    rows: 2",
        "    earliest available observation: 2000-01-03",
        "    latest available observation: 2026-01-30",
        "  AAPL",
        "    rows: 1",
        "    earliest available observation: 2000-01-04",
        "    latest available observation: 2000-01-04",
    ]
    output = "\n".join(lines).lower()
    assert "inception" not in output
    assert "password" not in output
    assert "database_url" not in output
    assert "postgresql" not in output


def test_script_is_thin_and_has_no_csv_or_direct_storage_dependency() -> None:
    source = Path(backfill_script.__file__).read_text(encoding="utf-8").lower()

    assert "to_csv" not in source
    assert "read_csv" not in source
    assert "market_prices_raw" not in source
    assert "market_prices_clean" not in source
    assert "marketdatarepository" not in source
    assert "marketdataservice(" not in source
    assert "update_market_data" not in source
    assert "seed_historical_data" not in source
    assert "database_url" not in source
    assert "localhost" not in source
    assert "postgresql+psycopg://" not in source
    assert "password" not in source
