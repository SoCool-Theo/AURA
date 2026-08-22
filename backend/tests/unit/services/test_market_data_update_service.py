from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pandas as pd
import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session

import backend.app.services.market_data_update_service as service_module
from backend.app.data_pipeline.updater import MarketDataUpdateResult
from backend.app.services.market_data_update_service import (
    PersistedMarketDataUpdateResult,
    update_market_data_and_persist,
)


def _update_result(tmp_path: Path) -> MarketDataUpdateResult:
    return MarketDataUpdateResult(
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
    storage = MagicMock(spec=service_module.MarketDataService)
    storage.store.return_value = 2
    return engine, session, session_factory, storage


def test_success_preserves_pipeline_result_and_persists_exact_frame_once(
    tmp_path: Path,
) -> None:
    update_result = _update_result(tmp_path)
    data = pd.DataFrame({"canonical": [True, True]})
    symbols = ["AAPL", "MSFT"]
    symbols_before = list(symbols)
    provider = Mock()
    raw_path = tmp_path / "custom-raw.csv"
    processed_path = tmp_path / "custom-processed.csv"
    engine, session, session_factory, storage = _database_mocks()
    events: list[str] = []

    def run_pipeline(**kwargs):
        events.append("pipeline")
        return update_result, data

    def create_engine():
        events.append("engine")
        return engine

    storage.store.side_effect = lambda stored_data: (
        events.append("store") or 2
    )
    session.commit.side_effect = lambda: events.append("commit")

    with (
        patch.object(
            service_module,
            "_update_market_data_with_frame",
            side_effect=run_pipeline,
        ) as pipeline,
        patch.object(
            service_module,
            "create_database_engine",
            side_effect=create_engine,
        ),
        patch.object(
            service_module,
            "create_session_factory",
            return_value=session_factory,
        ) as create_factory,
        patch.object(
            service_module,
            "MarketDataService",
            return_value=storage,
        ) as storage_type,
    ):
        result = update_market_data_and_persist(
            symbols=symbols,
            start_date=date(2026, 1, 1),
            end_date="2026-01-31",
            provider=provider,
            raw_path=raw_path,
            processed_path=processed_path,
        )

    pipeline.assert_called_once_with(
        symbols=symbols,
        start_date=date(2026, 1, 1),
        end_date="2026-01-31",
        provider=provider,
        raw_path=raw_path,
        processed_path=processed_path,
    )
    assert pipeline.call_args.kwargs["symbols"] is symbols
    assert symbols == symbols_before
    create_factory.assert_called_once_with(engine)
    storage_type.assert_called_once_with(session)
    storage.store.assert_called_once_with(data)
    assert storage.store.call_args.args[0] is data
    session.commit.assert_called_once_with()
    session.rollback.assert_not_called()
    session.close.assert_called_once_with()
    engine.dispose.assert_called_once_with()
    assert events == ["pipeline", "engine", "store", "commit"]
    assert result == PersistedMarketDataUpdateResult(update_result, 2)
    assert result.update_result is update_result
    assert result.update_result.failed_symbols == ("MISSING",)
    assert result.stored_count == 2


def test_pipeline_failure_creates_no_database_resources(
    tmp_path: Path,
) -> None:
    failure = RuntimeError("pipeline failed")

    with (
        patch.object(
            service_module,
            "_update_market_data_with_frame",
            side_effect=failure,
        ),
        patch.object(
            service_module,
            "create_database_engine",
        ) as create_engine,
        patch.object(
            service_module,
            "create_session_factory",
        ) as create_factory,
        patch.object(service_module, "MarketDataService") as storage_type,
    ):
        with pytest.raises(RuntimeError) as raised:
            update_market_data_and_persist(
                raw_path=tmp_path / "raw.csv",
                processed_path=tmp_path / "processed.csv",
            )

    assert raised.value is failure
    create_engine.assert_not_called()
    create_factory.assert_not_called()
    storage_type.assert_not_called()


def test_storage_failure_rolls_back_closes_disposes_and_propagates(
    tmp_path: Path,
) -> None:
    update_result = _update_result(tmp_path)
    data = pd.DataFrame({"canonical": [True]})
    engine, session, session_factory, storage = _database_mocks()
    failure = RuntimeError("storage failed")
    storage.store.side_effect = failure

    with (
        patch.object(
            service_module,
            "_update_market_data_with_frame",
            return_value=(update_result, data),
        ),
        patch.object(
            service_module,
            "create_database_engine",
            return_value=engine,
        ),
        patch.object(
            service_module,
            "create_session_factory",
            return_value=session_factory,
        ),
        patch.object(
            service_module,
            "MarketDataService",
            return_value=storage,
        ),
    ):
        with pytest.raises(RuntimeError) as raised:
            update_market_data_and_persist()

    assert raised.value is failure
    storage.store.assert_called_once_with(data)
    session.commit.assert_not_called()
    session.rollback.assert_called_once_with()
    session.close.assert_called_once_with()
    engine.dispose.assert_called_once_with()


def test_commit_failure_rolls_back_closes_disposes_and_propagates(
    tmp_path: Path,
) -> None:
    update_result = _update_result(tmp_path)
    data = pd.DataFrame({"canonical": [True]})
    engine, session, session_factory, storage = _database_mocks()
    failure = RuntimeError("commit failed")
    session.commit.side_effect = failure

    with (
        patch.object(
            service_module,
            "_update_market_data_with_frame",
            return_value=(update_result, data),
        ),
        patch.object(
            service_module,
            "create_database_engine",
            return_value=engine,
        ),
        patch.object(
            service_module,
            "create_session_factory",
            return_value=session_factory,
        ),
        patch.object(
            service_module,
            "MarketDataService",
            return_value=storage,
        ),
    ):
        with pytest.raises(RuntimeError) as raised:
            update_market_data_and_persist()

    assert raised.value is failure
    storage.store.assert_called_once_with(data)
    session.commit.assert_called_once_with()
    session.rollback.assert_called_once_with()
    session.close.assert_called_once_with()
    engine.dispose.assert_called_once_with()
