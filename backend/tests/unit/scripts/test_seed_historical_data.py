from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pandas as pd
import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session

import backend.scripts.seed_historical_data as seed_module


def _canonical_data() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-01-02", "2026-01-03"]),
            "symbol": pd.Series(["AAPL", "AAPL"], dtype="string"),
            "adjusted_close": [100.25, 101.5],
            "volume": pd.Series([1_000, pd.NA], dtype="Int64"),
            "source": pd.Series(["provider", "provider"], dtype="string"),
        }
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


def test_load_processed_csv_restores_canonical_types_without_modifying_file(
    tmp_path: Path,
) -> None:
    input_path = tmp_path / "market_prices_clean.csv"
    pd.DataFrame(
        {
            "date": ["2026-01-02 14:30:00", "2026-01-03 09:15:00"],
            "symbol": ["AAPL", "NA"],
            "adjusted_close": [100.25, 101.5],
            "volume": [1_000, None],
            "source": ["provider", "NA"],
        }
    ).to_csv(input_path, index=False)
    original_bytes = input_path.read_bytes()

    data = seed_module._load_processed_market_data(input_path)

    assert data["date"].tolist() == [
        pd.Timestamp(date(2026, 1, 2)),
        pd.Timestamp(date(2026, 1, 3)),
    ]
    assert data["date"].dtype == "datetime64[us]"
    assert data["adjusted_close"].dtype == "float64"
    assert str(data["volume"].dtype) == "Int64"
    assert data.loc[0, "volume"] == 1_000
    assert pd.isna(data.loc[1, "volume"])
    assert data["symbol"].tolist() == ["AAPL", "NA"]
    assert data["source"].tolist() == ["provider", "NA"]
    assert input_path.read_bytes() == original_bytes


def test_seed_uses_default_path_validates_then_stores_and_commits_once() -> None:
    data = _canonical_data()
    engine, session, session_factory, service = _database_mocks()
    events: list[str] = []
    session.commit.side_effect = lambda: events.append("commit")
    service.store.side_effect = lambda stored_data: (
        events.append("store") or len(stored_data)
    )

    with (
        patch.object(
            seed_module,
            "_load_processed_market_data",
            return_value=data,
        ) as load_data,
        patch.object(
            seed_module,
            "raise_if_invalid",
            side_effect=lambda validated_data: events.append("validate"),
        ) as validate,
        patch.object(
            seed_module,
            "create_database_engine",
            return_value=engine,
        ),
        patch.object(
            seed_module,
            "create_session_factory",
            return_value=session_factory,
        ),
        patch.object(
            seed_module,
            "MarketDataService",
            return_value=service,
        ) as service_type,
    ):
        stored_count = seed_module.seed_historical_data()

    assert stored_count == 2
    load_data.assert_called_once_with(seed_module.PROCESSED_DATA_PATH)
    validate.assert_called_once_with(data)
    service_type.assert_called_once_with(session)
    service.store.assert_called_once_with(data)
    assert events == ["validate", "store", "commit"]
    session.commit.assert_called_once_with()
    session.rollback.assert_not_called()
    session.close.assert_called_once_with()
    engine.dispose.assert_called_once_with()


def test_invalid_data_prevents_database_setup_and_storage() -> None:
    data = _canonical_data()
    data.loc[0, "symbol"] = "aapl"

    with (
        patch.object(
            seed_module,
            "_load_processed_market_data",
            return_value=data,
        ),
        patch.object(seed_module, "create_database_engine") as create_engine,
        patch.object(seed_module, "MarketDataService") as service_type,
    ):
        with pytest.raises(ValueError, match="Market data validation failed"):
            seed_module.seed_historical_data(Path("invalid.csv"))

    create_engine.assert_not_called()
    service_type.assert_not_called()


def test_storage_failure_propagates_and_session_scope_rolls_back() -> None:
    data = _canonical_data()
    engine, session, session_factory, service = _database_mocks()
    failure = RuntimeError("storage failed")
    service.store.side_effect = failure

    with (
        patch.object(
            seed_module,
            "_load_processed_market_data",
            return_value=data,
        ),
        patch.object(
            seed_module,
            "create_database_engine",
            return_value=engine,
        ),
        patch.object(
            seed_module,
            "create_session_factory",
            return_value=session_factory,
        ),
        patch.object(
            seed_module,
            "MarketDataService",
            return_value=service,
        ),
    ):
        with pytest.raises(RuntimeError) as raised:
            seed_module.seed_historical_data(Path("processed.csv"))

    assert raised.value is failure
    session.commit.assert_not_called()
    session.rollback.assert_called_once_with()
    session.close.assert_called_once_with()
    engine.dispose.assert_called_once_with()


def test_missing_input_file_fails_clearly(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing.csv"

    with pytest.raises(
        FileNotFoundError,
        match="Processed market-data CSV not found",
    ):
        seed_module._load_processed_market_data(missing_path)


def test_cli_reports_input_path_and_stored_count(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    input_path = tmp_path / "processed.csv"

    with patch.object(
        seed_module,
        "seed_historical_data",
        return_value=1_234,
    ) as seed:
        seed_module.main(["--input-path", str(input_path)])

    seed.assert_called_once_with(input_path)
    output = capsys.readouterr().out
    assert "Aura historical market-data seed completed." in output
    assert f"Input file:  {input_path}" in output
    assert "Rows stored: 1,234" in output


def test_cli_reports_failure_without_success_message(
    capsys: pytest.CaptureFixture[str],
) -> None:
    failure = RuntimeError("storage failed")

    with patch.object(
        seed_module,
        "seed_historical_data",
        side_effect=failure,
    ):
        with pytest.raises(
            SystemExit,
            match="seed failed: storage failed",
        ) as raised:
            seed_module.main([])

    assert raised.value.__cause__ is failure
    assert "completed" not in capsys.readouterr().out


def test_seed_script_uses_service_without_update_network_or_table_clearing() -> None:
    source = Path(seed_module.__file__).read_text(encoding="utf-8").lower()

    assert "marketdataservice" in source
    assert "marketdatarepository" not in source
    assert "update_market_data" not in source
    assert "yfinance" not in source
    assert "marketdataprovider" not in source
    assert "truncate" not in source
    assert "delete(" not in source
