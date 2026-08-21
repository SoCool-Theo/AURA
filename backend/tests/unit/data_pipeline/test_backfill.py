from datetime import date

import pandas as pd
import pytest

from backend.app.data_pipeline.backfill import (
    HistoricalCoverageAudit,
    HistoricalCoverageError,
    HistoricalSymbolCoverage,
    audit_historical_coverage,
)


def _canonical_data(
    rows: list[tuple[str, str]],
) -> pd.DataFrame:
    data = pd.DataFrame(rows, columns=["symbol", "date"])
    data["date"] = pd.to_datetime(data["date"])
    data["symbol"] = data["symbol"].astype("string")
    data["adjusted_close"] = pd.Series(
        [100.0 + index for index in range(len(data))],
        dtype="float64",
    )
    data["volume"] = pd.Series(range(len(data)), dtype="Int64")
    data["source"] = pd.Series(["provider"] * len(data), dtype="string")
    return data[
        ["date", "symbol", "adjusted_close", "volume", "source"]
    ]


def test_successful_multi_symbol_coverage_audit() -> None:
    data = _canonical_data(
        [
            ("AAPL", "2026-01-02"),
            ("AAPL", "2026-01-05"),
            ("MSFT", "2026-01-03"),
            ("MSFT", "2026-01-06"),
        ]
    )

    result = audit_historical_coverage(
        ["AAPL", "MSFT"],
        "2026-01-01",
        "2026-01-07",
        data,
    )

    assert result == HistoricalCoverageAudit(
        requested_start_date=date(2026, 1, 1),
        requested_end_date=date(2026, 1, 7),
        coverage=(
            HistoricalSymbolCoverage(
                symbol="AAPL",
                row_count=2,
                earliest_date=date(2026, 1, 2),
                latest_date=date(2026, 1, 5),
            ),
            HistoricalSymbolCoverage(
                symbol="MSFT",
                row_count=2,
                earliest_date=date(2026, 1, 3),
                latest_date=date(2026, 1, 6),
            ),
        ),
    )


def test_request_can_begin_at_year_2000() -> None:
    result = audit_historical_coverage(
        ["AAPL"],
        "2000-01-01",
        "2000-01-31",
        _canonical_data([("AAPL", "2000-01-03")]),
    )

    assert result.requested_start_date == date(2000, 1, 1)
    assert result.coverage[0].earliest_date == date(2000, 1, 3)


def test_later_starting_symbol_is_valid_and_reports_actual_first_date() -> None:
    result = audit_historical_coverage(
        ["BTC-USD"],
        "2000-01-01",
        "2026-01-31",
        _canonical_data(
            [
                ("BTC-USD", "2014-09-17"),
                ("BTC-USD", "2026-01-30"),
            ]
        ),
    )

    assert result.coverage[0].earliest_date == date(2014, 9, 17)
    assert result.coverage[0].row_count == 2


def test_symbol_ending_before_requested_end_is_valid() -> None:
    result = audit_historical_coverage(
        ["AAPL"],
        "2026-01-01",
        "2026-01-31",
        _canonical_data([("AAPL", "2026-01-20")]),
    )

    assert result.coverage[0].latest_date == date(2026, 1, 20)


def test_non_trading_endpoint_gaps_are_valid() -> None:
    result = audit_historical_coverage(
        ["AAPL"],
        "2022-01-01",
        "2022-01-09",
        _canonical_data(
            [
                ("AAPL", "2022-01-03"),
                ("AAPL", "2022-01-07"),
            ]
        ),
    )

    assert result.coverage[0].earliest_date == date(2022, 1, 3)
    assert result.coverage[0].latest_date == date(2022, 1, 7)


def test_zero_row_requested_symbol_is_unresolved() -> None:
    data = _canonical_data([("AAPL", "2026-01-02")])

    with pytest.raises(
        HistoricalCoverageError,
        match="Requested symbols with zero returned rows: MSFT",
    ):
        audit_historical_coverage(
            ["AAPL", "MSFT"],
            "2026-01-01",
            "2026-01-31",
            data,
        )


def test_provider_failed_symbol_is_unresolved() -> None:
    data = _canonical_data([("AAPL", "2026-01-02")])

    with pytest.raises(
        HistoricalCoverageError,
        match="Provider reported failures for requested symbols: AAPL",
    ):
        audit_historical_coverage(
            ["AAPL"],
            "2026-01-01",
            "2026-01-31",
            data,
            failed_symbols=[" aapl "],
        )


def test_multiple_failed_and_unresolved_symbols_are_deterministic() -> None:
    data = _canonical_data([("NVDA", "2026-01-02")])

    with pytest.raises(HistoricalCoverageError) as raised:
        audit_historical_coverage(
            ["MSFT", "AAPL", "NVDA"],
            "2026-01-01",
            "2026-01-31",
            data,
            failed_symbols=["AAPL"],
        )

    assert str(raised.value) == (
        "Historical market-data coverage audit failed:\n"
        "- Provider reported failures for requested symbols: AAPL.\n"
        "- Requested symbols with zero returned rows: MSFT, AAPL."
    )


def test_unexpected_returned_symbol_is_rejected() -> None:
    data = _canonical_data(
        [
            ("AAPL", "2026-01-02"),
            ("UNEXPECTED", "2026-01-02"),
        ]
    )

    with pytest.raises(
        HistoricalCoverageError,
        match="Returned data contains unexpected symbols: UNEXPECTED",
    ):
        audit_historical_coverage(
            ["AAPL"],
            "2026-01-01",
            "2026-01-31",
            data,
        )


def test_early_out_of_range_observation_is_rejected() -> None:
    data = _canonical_data(
        [
            ("AAPL", "1999-12-31"),
            ("AAPL", "2000-01-03"),
        ]
    )

    with pytest.raises(
        HistoricalCoverageError,
        match="AAPL begin before requested start date 2000-01-01: 1999-12-31",
    ):
        audit_historical_coverage(
            ["AAPL"],
            "2000-01-01",
            "2000-01-31",
            data,
        )


def test_late_out_of_range_observation_is_rejected() -> None:
    data = _canonical_data(
        [
            ("AAPL", "2026-01-30"),
            ("AAPL", "2026-02-01"),
        ]
    )

    with pytest.raises(
        HistoricalCoverageError,
        match="AAPL end after requested end date 2026-01-31: 2026-02-01",
    ):
        audit_historical_coverage(
            ["AAPL"],
            "2026-01-01",
            "2026-01-31",
            data,
        )


def test_duplicate_symbol_date_identity_is_rejected() -> None:
    data = _canonical_data(
        [
            ("AAPL", "2026-01-02"),
            ("AAPL", "2026-01-02"),
        ]
    )

    with pytest.raises(ValueError, match="Found 1 duplicate date-symbol rows"):
        audit_historical_coverage(
            ["AAPL"],
            "2026-01-01",
            "2026-01-31",
            data,
        )


def test_requested_symbol_order_is_preserved() -> None:
    data = _canonical_data(
        [
            ("AAPL", "2026-01-02"),
            ("MSFT", "2026-01-02"),
        ]
    )

    result = audit_historical_coverage(
        ["MSFT", "AAPL"],
        "2026-01-01",
        "2026-01-31",
        data,
    )

    assert [item.symbol for item in result.coverage] == ["MSFT", "AAPL"]


def test_requested_symbol_normalization_uses_existing_convention() -> None:
    result = audit_historical_coverage(
        [" aapl ", "msft"],
        "2026-01-01",
        "2026-01-31",
        _canonical_data(
            [
                ("AAPL", "2026-01-02"),
                ("MSFT", "2026-01-02"),
            ]
        ),
    )

    assert [item.symbol for item in result.coverage] == ["AAPL", "MSFT"]


def test_caller_owned_inputs_are_not_mutated() -> None:
    requested_symbols = [" aapl ", "MSFT"]
    failed_symbols: list[str] = []
    data = _canonical_data(
        [
            ("AAPL", "2026-01-02"),
            ("MSFT", "2026-01-02"),
        ]
    )
    data.attrs["owner"] = "caller"
    requested_before = list(requested_symbols)
    failed_before = list(failed_symbols)
    data_before = data.copy(deep=True)
    attrs_before = dict(data.attrs)

    audit_historical_coverage(
        requested_symbols,
        "2026-01-01",
        "2026-01-31",
        data,
        failed_symbols=failed_symbols,
    )

    assert requested_symbols == requested_before
    assert failed_symbols == failed_before
    pd.testing.assert_frame_equal(data, data_before)
    assert data.attrs == attrs_before


def test_unrequested_provider_failure_metadata_is_rejected() -> None:
    with pytest.raises(
        HistoricalCoverageError,
        match="Provider failure metadata contains unrequested symbols: MSFT",
    ):
        audit_historical_coverage(
            ["AAPL"],
            "2026-01-01",
            "2026-01-31",
            _canonical_data([("AAPL", "2026-01-02")]),
            failed_symbols=["MSFT"],
        )


def test_start_date_must_not_follow_end_date() -> None:
    with pytest.raises(
        ValueError,
        match="start_date must be on or before end_date",
    ):
        audit_historical_coverage(
            ["AAPL"],
            "2026-02-01",
            "2026-01-31",
            _canonical_data([("AAPL", "2026-01-31")]),
        )
