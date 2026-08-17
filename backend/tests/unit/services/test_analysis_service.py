from datetime import date
from decimal import Decimal

import pandas as pd
import pytest

from backend.app.database.models import MarketData
from backend.app.services.analysis_service import _build_price_frame


def _record(
    symbol: str,
    observation_date: str,
    adjusted_close: str,
    *,
    volume: int | None = None,
    source: str = "test-provider",
) -> MarketData:
    return MarketData(
        symbol=symbol,
        date=date.fromisoformat(observation_date),
        adjusted_close=Decimal(adjusted_close),
        volume=volume,
        source=source,
    )


def test_build_price_frame_converts_one_symbol_and_sorts_dates() -> None:
    records = [
        _record("AAPL", "2026-01-03", "103.125000000000"),
        _record("AAPL", "2026-01-01", "101.500000000000"),
        _record("AAPL", "2026-01-02", "102.250000000000"),
    ]

    result = _build_price_frame(records, ["AAPL"])

    expected = pd.DataFrame(
        {"AAPL": [101.5, 102.25, 103.125]},
        index=pd.DatetimeIndex(
            [
                date(2026, 1, 1),
                date(2026, 1, 2),
                date(2026, 1, 3),
            ]
        ),
        dtype=float,
    )
    pd.testing.assert_frame_equal(result, expected)
    assert result.index.is_monotonic_increasing
    assert result.index.is_unique


def test_build_price_frame_uses_request_order_not_repository_order() -> None:
    records = [
        _record("AAPL", "2026-01-01", "100.000000000000"),
        _record("AAPL", "2026-01-02", "101.000000000000"),
        _record("BND", "2026-01-01", "70.000000000000"),
        _record("BND", "2026-01-02", "71.000000000000"),
        _record("MSFT", "2026-01-01", "400.000000000000"),
        _record("MSFT", "2026-01-02", "404.000000000000"),
    ]

    result = _build_price_frame(records, ["MSFT", "AAPL", "BND"])

    assert list(result.columns) == ["MSFT", "AAPL", "BND"]
    assert result.to_dict(orient="list") == {
        "MSFT": [400.0, 404.0],
        "AAPL": [100.0, 101.0],
        "BND": [70.0, 71.0],
    }


def test_build_price_frame_is_independent_of_arbitrary_record_order() -> None:
    records = [
        _record("MSFT", "2026-01-03", "403.000000000000"),
        _record("AAPL", "2026-01-01", "101.000000000000"),
        _record("MSFT", "2026-01-01", "401.000000000000"),
        _record("AAPL", "2026-01-03", "103.000000000000"),
    ]

    result = _build_price_frame(records, ("AAPL", "MSFT"))

    assert list(result.index) == [
        pd.Timestamp("2026-01-01"),
        pd.Timestamp("2026-01-03"),
    ]
    assert result.to_dict(orient="list") == {
        "AAPL": [101.0, 103.0],
        "MSFT": [401.0, 403.0],
    }


def test_build_price_frame_uses_exact_stock_crypto_date_intersection() -> None:
    records = [
        _record("AAPL", "2026-01-02", "100.000000000000"),
        _record("AAPL", "2026-01-05", "102.000000000000"),
        _record("BTC-USD", "2026-01-02", "90000.000000000000"),
        _record("BTC-USD", "2026-01-03", "91000.000000000000"),
        _record("BTC-USD", "2026-01-04", "92000.000000000000"),
        _record("BTC-USD", "2026-01-05", "93000.000000000000"),
    ]

    result = _build_price_frame(records, ["BTC-USD", "AAPL"])

    assert list(result.index) == [
        pd.Timestamp("2026-01-02"),
        pd.Timestamp("2026-01-05"),
    ]
    assert result.to_dict(orient="list") == {
        "BTC-USD": [90000.0, 93000.0],
        "AAPL": [100.0, 102.0],
    }
    assert not result.isna().any().any()


@pytest.mark.parametrize(
    ("records", "symbols", "expected_message"),
    [
        (
            [],
            ["AAPL", "MSFT"],
            "market data is unavailable for requested symbols: AAPL, MSFT",
        ),
        (
            [_record("MSFT", "2026-01-01", "400.000000000000")],
            ["MSFT", "AAPL"],
            "market data is unavailable for requested symbols: AAPL",
        ),
        (
            [_record("AAPL", "2026-01-01", "100.000000000000")],
            ["MSFT", "AAPL", "BND"],
            "market data is unavailable for requested symbols: MSFT, BND",
        ),
    ],
)
def test_build_price_frame_reports_missing_symbols_in_request_order(
    records: list[MarketData],
    symbols: list[str],
    expected_message: str,
) -> None:
    with pytest.raises(ValueError) as raised:
        _build_price_frame(records, symbols)

    assert str(raised.value) == expected_message


@pytest.mark.parametrize("common_date_count", [0, 1, 2])
def test_build_price_frame_returns_insufficient_common_history(
    common_date_count: int,
) -> None:
    common_dates = ["2026-01-10", "2026-01-11"][:common_date_count]
    records = [
        *[
            _record("AAPL", observation_date, "100.000000000000")
            for observation_date in common_dates
        ],
        *[
            _record("MSFT", observation_date, "400.000000000000")
            for observation_date in common_dates
        ],
        _record("AAPL", "2026-01-01", "99.000000000000"),
        _record("MSFT", "2026-01-02", "399.000000000000"),
    ]

    result = _build_price_frame(records, ["AAPL", "MSFT"])

    assert result.shape == (common_date_count, 2)
    assert list(result.columns) == ["AAPL", "MSFT"]
    assert list(result.index) == [pd.Timestamp(value) for value in common_dates]
    assert not result.isna().any().any()


def test_build_price_frame_uses_only_adjusted_close_values() -> None:
    records = [
        _record(
            "AAPL",
            "2026-01-01",
            "101.125000000000",
            volume=123_456,
            source="ignored-source",
        )
    ]

    result = _build_price_frame(records, ["AAPL"])

    assert list(result.columns) == ["AAPL"]
    assert result.dtypes.to_dict() == {"AAPL": float}
    assert result.iloc[0, 0] == 101.125
    assert "volume" not in result.columns
    assert "source" not in result.columns


def test_build_price_frame_does_not_mutate_records_or_symbols() -> None:
    records = [
        _record(
            "MSFT",
            "2026-01-02",
            "402.500000000000",
            volume=2_000,
            source="provider-b",
        ),
        _record(
            "AAPL",
            "2026-01-02",
            "101.125000000000",
            source="provider-a",
        ),
    ]
    symbols = ["MSFT", "AAPL"]
    record_snapshot = [
        (
            record.symbol,
            record.date,
            record.adjusted_close,
            record.volume,
            record.source,
        )
        for record in records
    ]
    record_identities = [id(record) for record in records]
    symbols_snapshot = list(symbols)

    _build_price_frame(records, symbols)

    assert [id(record) for record in records] == record_identities
    assert [
        (
            record.symbol,
            record.date,
            record.adjusted_close,
            record.volume,
            record.source,
        )
        for record in records
    ] == record_snapshot
    assert symbols == symbols_snapshot
