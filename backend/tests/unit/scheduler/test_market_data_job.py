from pathlib import Path
from unittest.mock import patch

import pytest

from backend.app.data_pipeline.updater import MarketDataUpdateResult
import backend.app.scheduler.market_data_job as job_module
from backend.app.services.market_data_update_service import (
    PersistedMarketDataUpdateResult,
)


@pytest.fixture(autouse=True)
def _enable_job_logger(monkeypatch: pytest.MonkeyPatch) -> None:
    """Undo logging configurations that disable pre-collected loggers."""
    monkeypatch.setattr(job_module.logger, "disabled", False)
    monkeypatch.setattr(job_module.logger, "propagate", True)


def _persisted_result(
    tmp_path: Path,
    *,
    failed_symbols: tuple[str, ...] = (),
) -> PersistedMarketDataUpdateResult:
    update_result = MarketDataUpdateResult(
        raw_path=tmp_path / "raw.csv",
        processed_path=tmp_path / "processed.csv",
        row_count=2,
        symbols=("AAPL", "MSFT"),
        failed_symbols=failed_symbols,
        requested_start_date="2026-01-01",
        requested_end_date="2026-01-31",
        actual_start_date="2026-01-02",
        actual_end_date="2026-01-30",
    )
    return PersistedMarketDataUpdateResult(update_result, 2)


def test_success_calls_helper_once_and_logs_result(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    persisted_result = _persisted_result(tmp_path)

    with (
        patch.object(
            job_module,
            "update_market_data_and_persist",
            return_value=persisted_result,
        ) as update,
        caplog.at_level("INFO", logger=job_module.__name__),
    ):
        result = job_module.run_scheduled_market_data_update()

    assert result is None
    update.assert_called_once_with(symbols=job_module.MARKET_UPDATE_SYMBOLS)
    assert "Scheduled market-data update starting" in caplog.text
    assert "processed_rows=2" in caplog.text
    assert "stored_rows=2" in caplog.text
    assert "AAPL, MSFT" in caplog.text
    assert "provider failures" not in caplog.text


def test_partial_provider_failures_are_logged_as_warning(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    persisted_result = _persisted_result(
        tmp_path,
        failed_symbols=("MISSING", "UNAVAILABLE"),
    )

    with (
        patch.object(
            job_module,
            "update_market_data_and_persist",
            return_value=persisted_result,
        ),
        caplog.at_level("INFO", logger=job_module.__name__),
    ):
        job_module.run_scheduled_market_data_update()

    warning_records = [
        record for record in caplog.records if record.levelname == "WARNING"
    ]
    assert len(warning_records) == 1
    assert "MISSING, UNAVAILABLE" in warning_records[0].getMessage()


def test_helper_failure_is_logged_and_original_exception_is_reraised_once(
    caplog: pytest.LogCaptureFixture,
) -> None:
    failure = RuntimeError("database unavailable")

    with (
        patch.object(
            job_module,
            "update_market_data_and_persist",
            side_effect=failure,
        ) as update,
        caplog.at_level("ERROR", logger=job_module.__name__),
    ):
        with pytest.raises(RuntimeError) as raised:
            job_module.run_scheduled_market_data_update()

    assert raised.value is failure
    update.assert_called_once_with(symbols=job_module.MARKET_UPDATE_SYMBOLS)
    assert "Scheduled market-data update failed" in caplog.text
