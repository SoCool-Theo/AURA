from datetime import date

import pandas as pd

from backend.app.data_pipeline.updater import update_market_data


class FakeProvider:
    source_name = "fake"

    def fetch_historical_prices(self, symbols, start_date, end_date):
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

    result = update_market_data(
        symbols=["AAPL", "MSFT"],
        start_date="2026-01-01",
        end_date="2026-01-31",
        provider=FakeProvider(),
        raw_path=raw_path,
        processed_path=processed_path,
    )

    assert raw_path.exists()
    assert processed_path.exists()
    assert result.row_count == 4
    assert result.symbols == ("AAPL", "MSFT")
    assert result.failed_symbols == ("MISSING",)
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
