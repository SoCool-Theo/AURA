from pathlib import Path
from unittest.mock import patch

import pytest

import backend.scripts.update_market_data as update_script
from backend.app.services.market_data_update_service import (
    PersistedMarketDataUpdateResult,
)


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
            "update_market_data_and_persist",
        ) as persist_update,
    ):
        update_script.main([])

    update.assert_called_once_with(
        symbols=update_script.MARKET_UPDATE_SYMBOLS,
        start_date=update_script.DEFAULT_START_DATE,
        end_date=None,
    )
    assert len(update_script.DEFAULT_SYMBOLS) == 17
    assert "THB=X" not in update_script.DEFAULT_SYMBOLS
    assert update_script.MARKET_UPDATE_SYMBOLS[-1] == "THB=X"
    persist_update.assert_not_called()
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

    with (
        patch.object(
            update_script,
            "update_market_data",
            return_value=result,
        ) as update,
        patch.object(
            update_script,
            "update_market_data_and_persist",
        ) as persist_update,
    ):
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
    persist_update.assert_not_called()


def test_persistence_mode_delegates_once_and_preserves_output(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = _result(tmp_path)
    persisted_result = PersistedMarketDataUpdateResult(result, 2)

    with (
        patch.object(
            update_script,
            "update_market_data_and_persist",
            return_value=persisted_result,
        ) as persist_update,
        patch.object(update_script, "update_market_data") as public_update,
    ):
        update_script.main(
            [
                "--symbols",
                "AAPL",
                "MSFT",
                "--start-date",
                "2026-01-01",
                "--end-date",
                "2026-01-31",
                "--persist-database",
            ]
        )

    persist_update.assert_called_once_with(
        symbols=["AAPL", "MSFT"],
        start_date="2026-01-01",
        end_date="2026-01-31",
    )
    public_update.assert_not_called()
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
        "Database rows stored: 2",
    ]


def test_default_persistence_mode_includes_internal_fx(tmp_path: Path) -> None:
    result = _result(tmp_path)
    persisted_result = PersistedMarketDataUpdateResult(result, 2)

    with patch.object(
        update_script,
        "update_market_data_and_persist",
        return_value=persisted_result,
    ) as persist_update:
        update_script.main(["--persist-database"])

    persist_update.assert_called_once_with(
        symbols=update_script.MARKET_UPDATE_SYMBOLS,
        start_date=update_script.DEFAULT_START_DATE,
        end_date=None,
    )


@pytest.mark.parametrize(
    ("message", "failure"),
    [
        ("pipeline failed", RuntimeError("pipeline failed")),
        ("storage failed", RuntimeError("storage failed")),
    ],
)
def test_persistence_failure_preserves_cli_error_behavior(
    message: str,
    failure: RuntimeError,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with patch.object(
        update_script,
        "update_market_data_and_persist",
        side_effect=failure,
    ):
        with pytest.raises(
            SystemExit,
            match=f"update failed: {message}",
        ) as raised:
            update_script.main(["--persist-database"])

    assert raised.value.__cause__ is failure
    assert capsys.readouterr().out == ""


def test_script_has_no_csv_reload_repository_or_hardcoded_credentials() -> None:
    source = Path(update_script.__file__).read_text(encoding="utf-8").lower()

    assert "read_csv" not in source
    assert "marketdatarepository" not in source
    assert "aura_test_database_url" not in source
    assert "database_url" not in source
    assert "localhost" not in source
    assert "postgresql+psycopg://" not in source
    assert "password" not in source
    assert "_update_market_data_with_frame" not in source
    assert "_persist_market_data" not in source
    assert "create_database_engine" not in source
    assert "create_session_factory" not in source
    assert "session_scope" not in source
    assert "marketdataservice" not in source
    assert ".commit(" not in source
