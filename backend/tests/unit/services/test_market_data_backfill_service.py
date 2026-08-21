from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from sqlalchemy.orm import Session

from backend.app.data_pipeline.backfill import (
    HistoricalCoverageAudit,
    HistoricalCoverageError,
    HistoricalSymbolCoverage,
)
import backend.app.services.market_data_backfill_service as service_module
from backend.app.services.market_data_backfill_service import (
    MarketDataBackfillResult,
    MarketDataBackfillService,
)


class FakeProvider:
    source_name = "fake"

    def __init__(
        self,
        data: pd.DataFrame,
        *,
        failed_symbols: tuple[str, ...] = (),
    ) -> None:
        self.data = data
        self.failed_symbols = failed_symbols
        self.data.attrs["failed_symbols"] = failed_symbols
        self.calls: list[tuple[tuple[str, ...], object, object]] = []

    def fetch_historical_prices(
        self,
        symbols,
        start_date,
        end_date,
    ) -> pd.DataFrame:
        self.calls.append((tuple(symbols), start_date, end_date))
        return self.data


def _raw_data(
    rows: list[tuple[str, str, float, int | None]],
) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Date": [row[1] for row in rows],
            "Adj Close": [row[2] for row in rows],
            "Volume": [row[3] for row in rows],
            "symbol": [row[0] for row in rows],
            "source": ["fake"] * len(rows),
        }
    )


def _canonical_data(
    rows: list[tuple[str, str, float, int | None]],
) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.to_datetime([row[1] for row in rows]),
            "symbol": pd.Series([row[0] for row in rows], dtype="string"),
            "adjusted_close": pd.Series(
                [row[2] for row in rows],
                dtype="float64",
            ),
            "volume": pd.Series(
                [row[3] for row in rows],
                dtype="Int64",
            ),
            "source": pd.Series(["fake"] * len(rows), dtype="string"),
        }
    )


def _service_with_storage() -> tuple[
    MarketDataBackfillService,
    MagicMock,
    MagicMock,
]:
    session = MagicMock(spec=Session)
    storage = MagicMock(spec=service_module.MarketDataService)
    storage.store.side_effect = lambda data: len(data)
    with patch.object(
        service_module,
        "MarketDataService",
        return_value=storage,
    ):
        service = MarketDataBackfillService(session)
    return service, session, storage


def test_successful_multi_symbol_orchestration() -> None:
    service, session, storage = _service_with_storage()
    provider = FakeProvider(
        _raw_data(
            [
                ("AAPL", "2026-01-02", 100.0, 1_000),
                ("AAPL", "2026-01-05", 101.0, 1_100),
                ("MSFT", "2026-01-02", 200.0, 2_000),
                ("MSFT", "2026-01-05", 201.0, None),
            ]
        )
    )

    result = service.run(
        ["AAPL", "MSFT"],
        "2026-01-01",
        "2026-01-06",
        provider=provider,
    )

    assert result == MarketDataBackfillResult(
        requested_symbols=("AAPL", "MSFT"),
        requested_start_date=date(2026, 1, 1),
        requested_end_date=date(2026, 1, 6),
        row_count=4,
        stored_count=4,
        coverage=(
            HistoricalSymbolCoverage(
                "AAPL",
                2,
                date(2026, 1, 2),
                date(2026, 1, 5),
            ),
            HistoricalSymbolCoverage(
                "MSFT",
                2,
                date(2026, 1, 2),
                date(2026, 1, 5),
            ),
        ),
    )
    assert provider.calls == [
        (("AAPL", "MSFT"), "2026-01-01", "2026-01-06")
    ]
    stored_data = storage.store.call_args.args[0]
    assert stored_data["symbol"].tolist() == [
        "AAPL",
        "AAPL",
        "MSFT",
        "MSFT",
    ]
    session.commit.assert_not_called()
    session.rollback.assert_not_called()
    session.close.assert_not_called()


def test_orchestration_runs_stages_once_in_required_order() -> None:
    service, _, storage = _service_with_storage()
    raw_data = pd.DataFrame({"raw": [True]})
    raw_data.attrs["failed_symbols"] = ("FAILED",)
    clean_data = _canonical_data(
        [("AAPL", "2026-01-02", 100.0, 1_000)]
    )
    audit = HistoricalCoverageAudit(
        requested_start_date=date(2026, 1, 1),
        requested_end_date=date(2026, 1, 31),
        coverage=(
            HistoricalSymbolCoverage(
                "AAPL",
                1,
                date(2026, 1, 2),
                date(2026, 1, 2),
            ),
        ),
    )
    events: list[str] = []

    def fetch(**kwargs) -> pd.DataFrame:
        events.append("fetch")
        return raw_data

    def clean(data: pd.DataFrame) -> pd.DataFrame:
        assert data is raw_data
        events.append("clean")
        return clean_data

    def validate(data: pd.DataFrame) -> None:
        assert data is clean_data
        events.append("validate")

    def audit_coverage(*args, **kwargs) -> HistoricalCoverageAudit:
        assert args == (
            ("AAPL",),
            "2026-01-01",
            "2026-01-31",
            clean_data,
        )
        assert kwargs == {"failed_symbols": ("FAILED",)}
        events.append("audit")
        return audit

    storage.store.side_effect = lambda data: events.append("store") or 1
    with (
        patch.object(
            service_module,
            "fetch_historical_prices",
            side_effect=fetch,
        ),
        patch.object(service_module, "clean_market_data", side_effect=clean),
        patch.object(service_module, "raise_if_invalid", side_effect=validate),
        patch.object(
            service_module,
            "audit_historical_coverage",
            side_effect=audit_coverage,
        ),
    ):
        service.run(
            ["AAPL"],
            "2026-01-01",
            "2026-01-31",
        )

    assert events == ["fetch", "clean", "validate", "audit", "store"]


def test_request_can_begin_at_year_2000() -> None:
    service, _, _ = _service_with_storage()

    result = service.run(
        ["AAPL"],
        "2000-01-01",
        "2000-01-31",
        provider=FakeProvider(
            _raw_data([("AAPL", "2000-01-03", 1.0, 100)])
        ),
    )

    assert result.requested_start_date == date(2000, 1, 1)


def test_later_starting_partial_history_symbol_succeeds() -> None:
    service, _, _ = _service_with_storage()

    result = service.run(
        ["BTC-USD"],
        "2000-01-01",
        "2026-01-31",
        provider=FakeProvider(
            _raw_data(
                [
                    ("BTC-USD", "2014-09-17", 1.0, 100),
                    ("BTC-USD", "2026-01-30", 2.0, 200),
                ]
            )
        ),
    )

    assert result.coverage[0].earliest_date == date(2014, 9, 17)


def test_normalized_requested_order_is_preserved() -> None:
    service, _, _ = _service_with_storage()

    result = service.run(
        [" msft ", "aapl"],
        "2026-01-01",
        "2026-01-31",
        provider=FakeProvider(
            _raw_data(
                [
                    ("AAPL", "2026-01-02", 100.0, 100),
                    ("MSFT", "2026-01-02", 200.0, 200),
                ]
            )
        ),
    )

    assert result.requested_symbols == ("MSFT", "AAPL")
    assert [item.symbol for item in result.coverage] == ["MSFT", "AAPL"]


@pytest.mark.parametrize(
    ("symbols", "rows", "failed_symbols", "message"),
    [
        (
            ["AAPL", "MSFT"],
            [("AAPL", "2026-01-02", 100.0, 100)],
            ("MSFT",),
            "Provider reported failures for requested symbols: MSFT",
        ),
        (
            ["AAPL", "MSFT"],
            [("AAPL", "2026-01-02", 100.0, 100)],
            (),
            "Requested symbols with zero returned rows: MSFT",
        ),
        (
            ["AAPL"],
            [
                ("AAPL", "2026-01-02", 100.0, 100),
                ("MSFT", "2026-01-02", 200.0, 200),
            ],
            (),
            "Returned data contains unexpected symbols: MSFT",
        ),
        (
            ["AAPL"],
            [("AAPL", "2025-12-31", 100.0, 100)],
            (),
            "begin before requested start date",
        ),
    ],
)
def test_coverage_failure_prevents_any_persistence(
    symbols: list[str],
    rows: list[tuple[str, str, float, int | None]],
    failed_symbols: tuple[str, ...],
    message: str,
) -> None:
    service, session, storage = _service_with_storage()

    with pytest.raises(HistoricalCoverageError, match=message):
        service.run(
            symbols,
            "2026-01-01",
            "2026-01-31",
            provider=FakeProvider(
                _raw_data(rows),
                failed_symbols=failed_symbols,
            ),
        )

    storage.store.assert_not_called()
    session.commit.assert_not_called()
    session.rollback.assert_not_called()
    session.close.assert_not_called()


def test_canonical_validation_failure_prevents_audit_and_persistence() -> None:
    service, _, storage = _service_with_storage()
    failure = ValueError("Market data validation failed")
    with (
        patch.object(
            service_module,
            "raise_if_invalid",
            side_effect=failure,
        ),
        patch.object(
            service_module,
            "audit_historical_coverage",
        ) as audit,
    ):
        with pytest.raises(ValueError) as raised:
            service.run(
                ["AAPL"],
                "2026-01-01",
                "2026-01-31",
                provider=FakeProvider(
                    _raw_data([("AAPL", "2026-01-02", 100.0, 100)])
                ),
            )

    assert raised.value is failure
    audit.assert_not_called()
    storage.store.assert_not_called()


def test_storage_failure_propagates_without_owning_transaction() -> None:
    service, session, storage = _service_with_storage()
    failure = RuntimeError("storage failed")
    storage.store.side_effect = failure

    with pytest.raises(RuntimeError) as raised:
        service.run(
            ["AAPL"],
            "2026-01-01",
            "2026-01-31",
            provider=FakeProvider(
                _raw_data([("AAPL", "2026-01-02", 100.0, 100)])
            ),
        )

    assert raised.value is failure
    session.commit.assert_not_called()
    session.rollback.assert_not_called()
    session.close.assert_not_called()


def test_caller_inputs_and_source_frames_are_not_mutated() -> None:
    service, _, storage = _service_with_storage()
    symbols = [" aapl "]
    start = date(2026, 1, 1)
    end = date(2026, 1, 31)
    raw_data = _raw_data([("AAPL", "2026-01-02", 100.0, 100)])
    raw_data.attrs["owner"] = "caller"
    clean_data = _canonical_data(
        [("AAPL", "2026-01-02", 100.0, 100)]
    )
    provider = FakeProvider(raw_data)
    symbols_before = list(symbols)
    raw_before = raw_data.copy(deep=True)
    raw_attrs_before = dict(raw_data.attrs)
    clean_before = clean_data.copy(deep=True)

    with patch.object(
        service_module,
        "clean_market_data",
        return_value=clean_data,
    ):
        service.run(
            symbols,
            start,
            end,
            provider=provider,
        )

    assert symbols == symbols_before
    assert start == date(2026, 1, 1)
    assert end == date(2026, 1, 31)
    pd.testing.assert_frame_equal(raw_data, raw_before)
    assert raw_data.attrs == raw_attrs_before
    pd.testing.assert_frame_equal(clean_data, clean_before)
    assert storage.store.call_args.args[0] is clean_data


def test_service_has_no_csv_or_updater_dependency() -> None:
    source = Path(service_module.__file__).read_text(encoding="utf-8").lower()

    assert "updater" not in source
    assert "to_csv" not in source
    assert "raw_data_path" not in source
    assert "processed_data_path" not in source
    assert "commit(" not in source
    assert "rollback(" not in source
    assert "close(" not in source
