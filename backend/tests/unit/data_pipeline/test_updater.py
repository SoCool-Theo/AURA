from datetime import date
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

import backend.app.data_pipeline.updater as updater_module
from backend.app.data_pipeline.cleaner import OUTPUT_COLUMNS
from backend.app.data_pipeline.updater import (
    MarketDataUpdateResult,
    _update_market_data_with_frame,
    update_market_data,
)


class FakeProvider:
    source_name = "fake"

    def __init__(self) -> None:
        self.fetch_count = 0

    def fetch_historical_prices(self, symbols, start_date, end_date):
        self.fetch_count += 1
        selected = list(symbols)
        frame = pd.DataFrame(
            {
                "Date": ["2026-01-02", "2026-01-03"] * len(selected),
                "Adj Close": [100.0, 101.0] * len(selected),
                "Volume": [1000, 1100] * len(selected),
                "symbol": [symbol for symbol in selected for _ in range(2)],
                "source": [self.source_name] * (2 * len(selected)),
            }
        )
        frame.attrs["failed_symbols"] = ("MISSING",)
        return frame


def test_update_market_data_writes_raw_and_processed_files(tmp_path) -> None:
    raw_path = tmp_path / "raw.csv"
    processed_path = tmp_path / "processed.csv"
    provider = FakeProvider()

    result = update_market_data(
        symbols=["AAPL", "MSFT"],
        start_date="2026-01-01",
        end_date="2026-01-31",
        provider=provider,
        raw_path=raw_path,
        processed_path=processed_path,
    )

    assert isinstance(result, MarketDataUpdateResult)
    assert provider.fetch_count == 1
    assert raw_path.exists()
    assert processed_path.exists()
    assert result.raw_path == raw_path
    assert result.processed_path == processed_path
    assert result.row_count == 4
    assert result.symbols == ("AAPL", "MSFT")
    assert result.failed_symbols == ("MISSING",)
    assert result.requested_start_date == "2026-01-01"
    assert result.requested_end_date == "2026-01-31"
    assert result.actual_start_date == "2026-01-02"
    assert result.actual_end_date == "2026-01-03"

    processed = pd.read_csv(processed_path)
    assert list(processed.columns) == [
        "date",
        "symbol",
        "adjusted_close",
        "volume",
        "source",
    ]


def test_update_market_data_defaults_end_date_to_today(tmp_path) -> None:
    result = update_market_data(
        symbols=["AAPL"],
        start_date="2026-01-01",
        provider=FakeProvider(),
        raw_path=tmp_path / "raw.csv",
        processed_path=tmp_path / "processed.csv",
    )

    assert result.requested_end_date == date.today().isoformat()


def test_private_seam_returns_result_and_validated_canonical_frame(
    tmp_path: Path,
) -> None:
    raw_path = tmp_path / "raw.csv"
    processed_path = tmp_path / "processed.csv"
    symbols = ["MSFT", "AAPL"]
    original_symbols = list(symbols)
    provider = FakeProvider()

    result, data = _update_market_data_with_frame(
        symbols=symbols,
        start_date="2026-01-01",
        end_date="2026-01-31",
        provider=provider,
        raw_path=raw_path,
        processed_path=processed_path,
    )

    assert isinstance(result, MarketDataUpdateResult)
    assert result.row_count == 4
    assert result.symbols == ("AAPL", "MSFT")
    assert result.failed_symbols == ("MISSING",)
    assert provider.fetch_count == 1
    assert symbols == original_symbols
    assert tuple(data.columns) == OUTPUT_COLUMNS
    assert data["symbol"].tolist() == ["AAPL", "AAPL", "MSFT", "MSFT"]
    assert data["date"].dt.strftime("%Y-%m-%d").tolist() == [
        "2026-01-02",
        "2026-01-03",
        "2026-01-02",
        "2026-01-03",
    ]
    assert data["adjusted_close"].tolist() == [
        100.0,
        101.0,
        100.0,
        101.0,
    ]
    assert str(data["volume"].dtype) == "Int64"
    assert data["source"].tolist() == [
        "fake",
        "fake",
        "fake",
        "fake",
    ]
    assert "Date" not in data.columns
    assert "Adj Close" not in data.columns


def test_public_update_delegates_to_private_seam_and_returns_only_result(
    tmp_path: Path,
) -> None:
    raw_path = tmp_path / "raw.csv"
    processed_path = tmp_path / "processed.csv"
    provider = FakeProvider()
    expected = MarketDataUpdateResult(
        raw_path=raw_path,
        processed_path=processed_path,
        row_count=1,
        symbols=("AAPL",),
        failed_symbols=(),
        requested_start_date="2026-01-01",
        requested_end_date="2026-01-31",
        actual_start_date="2026-01-02",
        actual_end_date="2026-01-02",
    )
    frame = pd.DataFrame()

    with patch.object(
        updater_module,
        "_update_market_data_with_frame",
        return_value=(expected, frame),
    ) as seam:
        result = update_market_data(
            symbols=["AAPL"],
            start_date="2026-01-01",
            end_date="2026-01-31",
            provider=provider,
            raw_path=raw_path,
            processed_path=processed_path,
        )

    assert result is expected
    seam.assert_called_once_with(
        symbols=["AAPL"],
        start_date="2026-01-01",
        end_date="2026-01-31",
        provider=provider,
        raw_path=raw_path,
        processed_path=processed_path,
    )


def test_private_seam_runs_each_stage_once_in_existing_order(
    tmp_path: Path,
) -> None:
    raw_path = tmp_path / "raw.csv"
    processed_path = tmp_path / "processed.csv"
    provider = FakeProvider()
    raw_data = pd.DataFrame({"provider_native": [1]})
    raw_data.attrs["failed_symbols"] = ("MISSING",)
    clean_data = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-01-02"]),
            "symbol": pd.Series(["AAPL"], dtype="string"),
            "adjusted_close": [100.0],
            "volume": pd.Series([1_000], dtype="Int64"),
            "source": pd.Series(["fake"], dtype="string"),
        }
    )
    events: list[str] = []

    def fetch_once(**kwargs) -> pd.DataFrame:
        events.append("fetch")
        return raw_data

    def clean_once(data: pd.DataFrame) -> pd.DataFrame:
        assert data is raw_data
        events.append("clean")
        return clean_data

    def validate_once(data: pd.DataFrame) -> None:
        assert data is clean_data
        events.append("validate")

    def write_once(data: pd.DataFrame, path: Path) -> None:
        if data is raw_data:
            assert path == raw_path
            events.append("write_raw")
        else:
            assert data is clean_data
            assert path == processed_path
            events.append("write_processed")

    with (
        patch.object(
            updater_module,
            "fetch_historical_prices",
            side_effect=fetch_once,
        ) as fetch,
        patch.object(
            updater_module,
            "clean_market_data",
            side_effect=clean_once,
        ) as clean,
        patch.object(
            updater_module,
            "raise_if_invalid",
            side_effect=validate_once,
        ) as validate,
        patch.object(
            updater_module,
            "_atomic_write_csv",
            side_effect=write_once,
        ) as write_csv,
    ):
        result, returned_data = _update_market_data_with_frame(
            symbols=["AAPL"],
            start_date="2026-01-01",
            end_date="2026-01-31",
            provider=provider,
            raw_path=raw_path,
            processed_path=processed_path,
        )

    assert result.failed_symbols == ("MISSING",)
    assert returned_data is clean_data
    assert events == [
        "fetch",
        "write_raw",
        "clean",
        "validate",
        "write_processed",
    ]
    fetch.assert_called_once()
    clean.assert_called_once_with(raw_data)
    validate.assert_called_once_with(clean_data)
    assert write_csv.call_count == 2


def test_validation_failure_writes_raw_but_not_processed_csv(
    tmp_path: Path,
) -> None:
    raw_path = tmp_path / "raw.csv"
    processed_path = tmp_path / "processed.csv"
    failure = ValueError("Market data validation failed:\n- invalid")

    with patch.object(
        updater_module,
        "raise_if_invalid",
        side_effect=failure,
    ) as validate:
        with pytest.raises(ValueError) as raised:
            update_market_data(
                symbols=["AAPL"],
                start_date="2026-01-01",
                end_date="2026-01-31",
                provider=FakeProvider(),
                raw_path=raw_path,
                processed_path=processed_path,
            )

    assert raised.value is failure
    validate.assert_called_once()
    assert raw_path.exists()
    assert not processed_path.exists()
