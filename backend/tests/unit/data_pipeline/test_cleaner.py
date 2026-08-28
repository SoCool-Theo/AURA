import pandas as pd
import pytest

from backend.app.data_pipeline.cleaner import OUTPUT_COLUMNS, clean_market_data


def _raw_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Date": ["2026-01-03", "2026-01-02"],
            "Adj Close": [102.0, 100.0],
            "Close": [999.0, 999.0],
            "Volume": [1_200, 1_000],
            "symbol": [" aapl ", "AAPL"],
            "source": ["yfinance", "yfinance"],
        }
    )


def test_clean_market_data_normalizes_and_orders_rows() -> None:
    result = clean_market_data(_raw_frame())

    assert tuple(result.columns) == OUTPUT_COLUMNS
    assert result["symbol"].tolist() == ["AAPL", "AAPL"]
    assert result["adjusted_close"].tolist() == [100.0, 102.0]
    assert result["volume"].tolist() == [1_000, 1_200]
    assert result["date"].dt.strftime("%Y-%m-%d").tolist() == [
        "2026-01-02",
        "2026-01-03",
    ]


def test_clean_market_data_prefers_adjusted_close_over_close() -> None:
    result = clean_market_data(_raw_frame())
    assert result["adjusted_close"].tolist() == [100.0, 102.0]


def test_clean_market_data_falls_back_to_close() -> None:
    raw = _raw_frame().drop(columns=["Adj Close"])
    raw["Close"] = [101.0, 99.0]

    result = clean_market_data(raw)

    assert result["adjusted_close"].tolist() == [99.0, 101.0]


def test_clean_market_data_drops_invalid_price_rows() -> None:
    raw = _raw_frame()
    raw.loc[0, "Adj Close"] = -1.0

    result = clean_market_data(raw)

    assert len(result) == 1
    assert result.iloc[0]["adjusted_close"] == 100.0


def test_clean_market_data_keeps_last_duplicate() -> None:
    raw = pd.DataFrame(
        {
            "Date": ["2026-01-02", "2026-01-02"],
            "Adj Close": [100.0, 101.0],
            "Volume": [100, 200],
            "symbol": ["AAPL", "AAPL"],
            "source": ["yfinance", "yfinance"],
        }
    )

    result = clean_market_data(raw)

    assert len(result) == 1
    assert result.iloc[0]["adjusted_close"] == 101.0
    assert result.iloc[0]["volume"] == 200


def test_clean_market_data_represents_invalid_volume_as_missing() -> None:
    raw = _raw_frame()
    raw.loc[0, "Volume"] = -5

    result = clean_market_data(raw)

    aapl_jan_3 = result[result["date"] == pd.Timestamp("2026-01-03")].iloc[0]
    assert pd.isna(aapl_jan_3["volume"])


def test_clean_market_data_does_not_mutate_input() -> None:
    raw = _raw_frame()
    original = raw.copy(deep=True)

    clean_market_data(raw)

    pd.testing.assert_frame_equal(raw, original)


def test_clean_market_data_rejects_empty_frame() -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        clean_market_data(pd.DataFrame())


def test_clean_market_data_requires_price_column() -> None:
    raw = _raw_frame().drop(columns=["Adj Close", "Close"])

    with pytest.raises(ValueError, match="adjusted_close"):
        clean_market_data(raw)
