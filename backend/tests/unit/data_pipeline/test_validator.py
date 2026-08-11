import pandas as pd
import pytest

from backend.app.data_pipeline.validator import raise_if_invalid, validate_market_data


def _valid_data() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-01-02", "2026-01-03"]),
            "symbol": ["AAPL", "AAPL"],
            "adjusted_close": [100.0, 101.0],
            "volume": pd.Series([1000, pd.NA], dtype="Int64"),
            "source": ["yfinance", "yfinance"],
        }
    )


def test_validate_market_data_accepts_canonical_rows() -> None:
    assert validate_market_data(_valid_data()) == []


def test_raise_if_invalid_accepts_canonical_rows() -> None:
    raise_if_invalid(_valid_data())


def test_validate_market_data_reports_missing_column() -> None:
    data = _valid_data().drop(columns=["source"])

    errors = validate_market_data(data)

    assert errors == ["Missing required columns: ['source']"]


def test_validate_market_data_rejects_non_positive_prices() -> None:
    data = _valid_data()
    data.loc[0, "adjusted_close"] = 0.0

    errors = validate_market_data(data)

    assert "Some adjusted_close values are zero or negative." in errors


def test_validate_market_data_rejects_duplicate_symbol_date() -> None:
    data = _valid_data()
    data.loc[1, "date"] = data.loc[0, "date"]

    errors = validate_market_data(data)

    assert "Found 1 duplicate date-symbol rows." in errors


def test_validate_market_data_rejects_unsorted_dates_per_symbol() -> None:
    data = _valid_data().iloc[::-1].reset_index(drop=True)

    errors = validate_market_data(data)

    assert "Dates for AAPL are not in increasing order." in errors


def test_validate_market_data_rejects_non_normalized_symbol() -> None:
    data = _valid_data()
    data.loc[0, "symbol"] = " aapl "

    errors = validate_market_data(data)

    assert "Symbols must be trimmed and uppercase." in errors


def test_validate_market_data_rejects_fractional_volume() -> None:
    data = _valid_data().astype({"volume": "Float64"})
    data.loc[0, "volume"] = 1.5

    errors = validate_market_data(data)

    assert "Some volume values are not whole numbers." in errors


def test_raise_if_invalid_includes_all_errors() -> None:
    data = _valid_data()
    data.loc[0, "adjusted_close"] = -1.0
    data.loc[0, "symbol"] = " aapl "

    with pytest.raises(ValueError, match="Market data validation failed") as exc:
        raise_if_invalid(data)

    assert "Symbols must be trimmed and uppercase." in str(exc.value)
    assert "zero or negative" in str(exc.value)
