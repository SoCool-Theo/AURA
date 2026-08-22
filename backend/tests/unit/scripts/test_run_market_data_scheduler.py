from datetime import datetime, time, timezone
import importlib
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

import backend.scripts.run_market_data_scheduler as runner


@pytest.fixture(autouse=True)
def _enable_runner_logger(monkeypatch: pytest.MonkeyPatch) -> None:
    """Undo logging configurations that disable pre-collected loggers."""
    monkeypatch.setattr(runner.logger, "disabled", False)
    monkeypatch.setattr(runner.logger, "propagate", True)


def _scheduler_mock() -> MagicMock:
    scheduler = MagicMock()
    scheduler.running = False
    job = MagicMock()
    job.trigger.get_next_fire_time.return_value = datetime(
        2026,
        8,
        23,
        2,
        tzinfo=timezone.utc,
    )
    scheduler.get_jobs.return_value = [job]
    return scheduler


def test_runner_configures_constructs_logs_and_starts_once(
    caplog: pytest.LogCaptureFixture,
) -> None:
    scheduler = _scheduler_mock()
    scheduled_job = Mock()

    with (
        patch.object(runner, "configure_logging") as configure,
        patch.object(
            runner,
            "create_market_data_scheduler",
            return_value=scheduler,
        ) as create_scheduler,
        patch.object(
            runner,
            "run_scheduled_market_data_update",
            scheduled_job,
        ),
        patch.object(
            runner.settings,
            "market_data_update_time_utc",
            time(hour=2),
        ),
        caplog.at_level("INFO", logger=runner.__name__),
    ):
        runner.main()

    configure.assert_called_once_with()
    create_scheduler.assert_called_once_with(scheduled_job)
    scheduler.start.assert_called_once_with()
    scheduler.shutdown.assert_not_called()
    scheduled_job.assert_not_called()
    assert "02:00 UTC" in caplog.text
    assert "Next scheduled market-data update" in caplog.text
    assert "scheduler stopped" in caplog.text


@pytest.mark.parametrize("interruption", [KeyboardInterrupt(), SystemExit()])
def test_runner_handles_normal_interruption_and_shuts_down(
    interruption: BaseException,
) -> None:
    scheduler = _scheduler_mock()
    scheduler.running = True
    scheduler.start.side_effect = interruption
    scheduled_job = Mock()

    with (
        patch.object(runner, "configure_logging"),
        patch.object(
            runner,
            "create_market_data_scheduler",
            return_value=scheduler,
        ),
        patch.object(
            runner,
            "run_scheduled_market_data_update",
            scheduled_job,
        ),
    ):
        runner.main()

    scheduler.start.assert_called_once_with()
    scheduler.shutdown.assert_called_once_with(wait=True)
    scheduled_job.assert_not_called()


def test_runner_startup_failure_propagates_without_substitution() -> None:
    scheduler = _scheduler_mock()
    failure = RuntimeError("scheduler startup failed")
    scheduler.start.side_effect = failure

    with (
        patch.object(runner, "configure_logging"),
        patch.object(
            runner,
            "create_market_data_scheduler",
            return_value=scheduler,
        ),
        pytest.raises(RuntimeError) as raised,
    ):
        runner.main()

    assert raised.value is failure
    scheduler.shutdown.assert_not_called()


def test_module_import_is_safe_and_runner_has_no_fastapi_integration() -> None:
    with patch("apscheduler.schedulers.blocking.BlockingScheduler.start") as start:
        importlib.reload(runner)

    start.assert_not_called()
    source = Path(runner.__file__).read_text(encoding="utf-8").lower()
    assert "fastapi" not in source
    assert "lifespan" not in source
    assert "startup" not in source
    assert "update_market_data_and_persist" not in source
