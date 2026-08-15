from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pandas as pd
import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session

import backend.scripts.update_market_data as update_script


def _result(tmp_path: Path) -> update_script.MarketDataUpdateResult:
    return update_script.MarketDataUpdateResult(
        raw_path=tmp_path / "raw.csv",
        processed_path=tmp_path / "processed.csv",
        row_count=2,
        symbols=("AAPL", "MSFT"),
        failed_symbols=("MISSING",),
        requested_start_date="2026-01-01",
        requested_end_date="2026-01-31",
        actual_start_date="2026-01-02",
        actual_end_date="2026-01-03",
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
    service = MagicMock()
    service.store.return_value = 2
    return engine, session, session_factory, service


def test_default_mode_preserves_csv_only_behavior_and_summary(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = _result(tmp_path)

    with (
        patch.object(
            update_script,
            "update_market_data",
            return_value=result,
        ) as update,
        patch.object(
            update_script,
            "_update_market_data_with_frame",
        ) as private_update,
        patch.object(
            update_script,
            "create_database_engine",
        ) as create_engine,
        patch.object(update_script, "MarketDataService") as service_type,
    ):
        update_script.main([])

    update.assert_called_once_with(
        symbols=update_script.DEFAULT_SYMBOLS,
        start_date=update_script.DEFAULT_START_DATE,
        end_date=None,
    )
    private_update.assert_not_called()
    create_engine.assert_not_called()
    service_type.assert_not_called()
    assert capsys.readouterr().out.splitlines() == [
        "Aura market-data update completed.",
        "----------------------------------",
        f"Raw file:       {result.raw_path}",
        f"Processed file: {result.processed_path}",
        "Rows:           2",
        "Symbols:        AAPL, MSFT",
        "Requested range: 2026-01-01 to 2026-01-31",
        "Actual range:    2026-01-02 to 2026-01-03",
        "Failed symbols: MISSING",
    ]


def test_existing_cli_arguments_remain_compatible(tmp_path: Path) -> None:
    result = _result(tmp_path)

    with patch.object(
        update_script,
        "update_market_data",
        return_value=result,
    ) as update:
        update_script.main(
            [
                "--symbols",
                "AAPL",
                "MSFT",
                "--start-date",
                "2026-01-01",
                "--end-date",
                "2026-01-31",
            ]
        )

    update.assert_called_once_with(
        symbols=["AAPL", "MSFT"],
        start_date="2026-01-01",
        end_date="2026-01-31",
    )


def test_persistence_mode_uses_private_handoff_once_and_reports_count(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = _result(tmp_path)
    data = pd.DataFrame({"validated": [True]})

    with (
        patch.object(
            update_script,
            "_update_market_data_with_frame",
            return_value=(result, data),
        ) as private_update,
        patch.object(update_script, "update_market_data") as public_update,
        patch.object(
            update_script,
            "_persist_market_data",
            return_value=2,
        ) as persist,
    ):
        update_script.main(["--persist-database"])

    private_update.assert_called_once_with(
        symbols=update_script.DEFAULT_SYMBOLS,
        start_date=update_script.DEFAULT_START_DATE,
        end_date=None,
    )
    public_update.assert_not_called()
    persist.assert_called_once_with(data)
    assert persist.call_args.args[0] is data
    output = capsys.readouterr().out
    assert output.index("Aura market-data update completed.") < output.index(
        "Database rows stored: 2"
    )


def test_database_setup_starts_after_pipeline_and_commits_once(
    tmp_path: Path,
) -> None:
    result = _result(tmp_path)
    data = pd.DataFrame({"validated": [True]})
    engine, session, session_factory, service = _database_mocks()
    events: list[str] = []

    def complete_pipeline(**kwargs):
        events.append("pipeline")
        return result, data

    def create_engine():
        events.append("database")
        return engine

    service.store.side_effect = lambda stored_data: (
        events.append("store") or len(stored_data)
    )
    session.commit.side_effect = lambda: events.append("commit")

    with (
        patch.object(
            update_script,
            "_update_market_data_with_frame",
            side_effect=complete_pipeline,
        ) as private_update,
        patch.object(
            update_script,
            "create_database_engine",
            side_effect=create_engine,
        ),
        patch.object(
            update_script,
            "create_session_factory",
            return_value=session_factory,
        ),
        patch.object(
            update_script,
            "MarketDataService",
            return_value=service,
        ) as service_type,
    ):
        update_script.main(["--persist-database"])

    private_update.assert_called_once()
    service_type.assert_called_once_with(session)
    service.store.assert_called_once_with(data)
    assert service.store.call_args.args[0] is data
    assert events == ["pipeline", "database", "store", "commit"]
    session.commit.assert_called_once_with()
    session.rollback.assert_not_called()
    session.close.assert_called_once_with()
    engine.dispose.assert_called_once_with()


def test_pipeline_failure_prevents_database_setup_and_success_output(
    capsys: pytest.CaptureFixture[str],
) -> None:
    failure = RuntimeError("pipeline failed")

    with (
        patch.object(
            update_script,
            "_update_market_data_with_frame",
            side_effect=failure,
        ),
        patch.object(
            update_script,
            "create_database_engine",
        ) as create_engine,
        patch.object(update_script, "MarketDataService") as service_type,
    ):
        with pytest.raises(
            SystemExit,
            match="update failed: pipeline failed",
        ) as raised:
            update_script.main(["--persist-database"])

    assert raised.value.__cause__ is failure
    create_engine.assert_not_called()
    service_type.assert_not_called()
    assert capsys.readouterr().out == ""


def test_storage_failure_rolls_back_and_propagates_without_commit(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = _result(tmp_path)
    data = pd.DataFrame({"validated": [True]})
    engine, session, session_factory, service = _database_mocks()
    failure = RuntimeError("storage failed")
    service.store.side_effect = failure

    with (
        patch.object(
            update_script,
            "_update_market_data_with_frame",
            return_value=(result, data),
        ),
        patch.object(
            update_script,
            "create_database_engine",
            return_value=engine,
        ),
        patch.object(
            update_script,
            "create_session_factory",
            return_value=session_factory,
        ),
        patch.object(
            update_script,
            "MarketDataService",
            return_value=service,
        ),
    ):
        with pytest.raises(
            SystemExit,
            match="update failed: storage failed",
        ) as raised:
            update_script.main(["--persist-database"])

    assert raised.value.__cause__ is failure
    session.commit.assert_not_called()
    session.rollback.assert_called_once_with()
    session.close.assert_called_once_with()
    engine.dispose.assert_called_once_with()
    assert "Database rows stored" not in capsys.readouterr().out


def test_commit_failure_is_rolled_back_and_not_reported_as_success(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = _result(tmp_path)
    data = pd.DataFrame({"validated": [True]})
    engine, session, session_factory, service = _database_mocks()
    failure = RuntimeError("commit failed")
    session.commit.side_effect = failure

    with (
        patch.object(
            update_script,
            "_update_market_data_with_frame",
            return_value=(result, data),
        ),
        patch.object(
            update_script,
            "create_database_engine",
            return_value=engine,
        ),
        patch.object(
            update_script,
            "create_session_factory",
            return_value=session_factory,
        ),
        patch.object(
            update_script,
            "MarketDataService",
            return_value=service,
        ),
    ):
        with pytest.raises(
            SystemExit,
            match="update failed: commit failed",
        ) as raised:
            update_script.main(["--persist-database"])

    assert raised.value.__cause__ is failure
    session.commit.assert_called_once_with()
    session.rollback.assert_called_once_with()
    session.close.assert_called_once_with()
    engine.dispose.assert_called_once_with()
    assert "Database rows stored" not in capsys.readouterr().out


def test_script_has_no_csv_reload_repository_or_hardcoded_credentials() -> None:
    source = Path(update_script.__file__).read_text(encoding="utf-8").lower()

    assert "read_csv" not in source
    assert "marketdatarepository" not in source
    assert "aura_test_database_url" not in source
    assert "database_url" not in source
    assert "localhost" not in source
    assert "postgresql+psycopg://" not in source
    assert "password" not in source
