from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest
from sqlalchemy.orm import Session

import backend.app.services.market_data_service as service_module
from backend.app.services.market_data_service import (
    MarketDataService,
    _to_market_data_records,
)


def _canonical_data() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-01-03", "2026-01-02"]),
            "symbol": pd.Series(["MSFT", "AAPL"], dtype="string"),
            "adjusted_close": np.array(
                [402.5000000000004, 101.125],
                dtype=np.float64,
            ),
            "volume": pd.Series([np.int64(2_000), pd.NA], dtype="Int64"),
            "source": pd.Series(["provider-b", "provider-a"], dtype="string"),
        }
    )


def _canonical_rows(row_count: int) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.date_range("2026-01-01", periods=row_count),
            "symbol": pd.Series(["AAPL"] * row_count, dtype="string"),
            "adjusted_close": np.arange(
                100.0,
                100.0 + row_count,
                dtype=np.float64,
            ),
            "volume": pd.Series(range(row_count), dtype="Int64"),
            "source": pd.Series(["provider"] * row_count, dtype="string"),
        }
    )


def _service_with_repository() -> tuple[
    MarketDataService,
    MagicMock,
    MagicMock,
    MagicMock,
]:
    session = MagicMock(spec=Session)
    repository = MagicMock(spec=service_module.MarketDataRepository)
    repository.upsert_many.side_effect = lambda records: len(records)

    with patch.object(
        service_module,
        "MarketDataRepository",
        return_value=repository,
    ) as repository_type:
        service = MarketDataService(session)

    return service, session, repository, repository_type


def test_mapper_preserves_fields_and_row_order_with_python_storage_types() -> None:
    records = _to_market_data_records(_canonical_data())

    assert records == [
        {
            "symbol": "MSFT",
            "date": date(2026, 1, 3),
            "adjusted_close": Decimal("402.500000000000"),
            "volume": 2_000,
            "source": "provider-b",
        },
        {
            "symbol": "AAPL",
            "date": date(2026, 1, 2),
            "adjusted_close": Decimal("101.125000000000"),
            "volume": None,
            "source": "provider-a",
        },
    ]
    assert type(records[0]["date"]) is date
    assert type(records[0]["adjusted_close"]) is Decimal
    assert type(records[0]["volume"]) is int
    assert records[1]["volume"] is None


@pytest.mark.parametrize("price", [1.25, np.float64(1.25)])
def test_mapper_converts_python_and_numpy_floats_to_quantized_decimal(
    price: float | np.float64,
) -> None:
    data = _canonical_data().iloc[[0]].copy()
    data["adjusted_close"] = pd.Series([price], index=data.index, dtype=object)

    record = _to_market_data_records(data)[0]

    assert record["adjusted_close"] == Decimal("1.250000000000")
    assert record["adjusted_close"].as_tuple().exponent == -12


def test_mapper_uses_round_half_up_at_twelve_fractional_places() -> None:
    data = _canonical_data().iloc[[0]].copy()
    data["adjusted_close"] = np.float64("1.2345678901235")

    record = _to_market_data_records(data)[0]

    assert record["adjusted_close"] == Decimal("1.234567890124")


def test_mapper_is_deterministic_and_does_not_mutate_input() -> None:
    data = _canonical_data()
    original = data.copy(deep=True)

    first_result = _to_market_data_records(data)
    second_result = _to_market_data_records(data)

    assert first_result == second_result
    assert first_result is not second_result
    assert all(
        first is not second
        for first, second in zip(first_result, second_result)
    )
    pd.testing.assert_frame_equal(data, original)


def test_mapper_returns_empty_list_for_empty_canonical_data() -> None:
    empty_data = _canonical_data().iloc[0:0]

    assert _to_market_data_records(empty_data) == []


def test_mapper_preserves_duplicate_rows_in_their_original_order() -> None:
    data = _canonical_data().iloc[[1, 1]].copy()
    data.iloc[1, data.columns.get_loc("adjusted_close")] = 102.0

    records = _to_market_data_records(data)

    assert [(record["symbol"], record["date"]) for record in records] == [
        ("AAPL", date(2026, 1, 2)),
        ("AAPL", date(2026, 1, 2)),
    ]
    assert [record["adjusted_close"] for record in records] == [
        Decimal("101.125000000000"),
        Decimal("102.000000000000"),
    ]


def test_service_uses_caller_owned_session() -> None:
    _, session, _, repository_type = _service_with_repository()

    repository_type.assert_called_once_with(session)


def test_store_uses_existing_mapper_output() -> None:
    service, _, repository, _ = _service_with_repository()
    data = _canonical_data()
    prepared_records = [
        {
            "symbol": "UNCHANGED",
            "date": date(2026, 2, 1),
            "adjusted_close": Decimal("10.000000000000"),
            "volume": None,
            "source": " source ",
        }
    ]

    with patch.object(
        service_module,
        "_to_market_data_records",
        return_value=prepared_records,
    ) as mapper:
        stored_count = service.store(data)

    assert stored_count == 1
    mapper.assert_called_once_with(data)
    repository.upsert_many.assert_called_once_with(prepared_records)


@pytest.mark.parametrize("row_count", [999, 1_000])
def test_store_uses_one_repository_write_up_to_batch_limit(
    row_count: int,
) -> None:
    service, session, repository, _ = _service_with_repository()

    stored_count = service.store(_canonical_rows(row_count))

    assert stored_count == row_count
    repository.upsert_many.assert_called_once()
    assert len(repository.upsert_many.call_args.args[0]) == row_count
    session.commit.assert_not_called()
    session.rollback.assert_not_called()
    session.close.assert_not_called()


def test_store_splits_large_input_and_handles_final_partial_batch() -> None:
    service, _, repository, _ = _service_with_repository()

    stored_count = service.store(_canonical_rows(2_001))

    assert stored_count == 2_001
    batches = [call.args[0] for call in repository.upsert_many.call_args_list]
    assert [len(batch) for batch in batches] == [1_000, 1_000, 1]


def test_store_empty_data_returns_zero_without_repository_write() -> None:
    service, session, repository, _ = _service_with_repository()

    stored_count = service.store(_canonical_rows(0))

    assert stored_count == 0
    repository.upsert_many.assert_not_called()
    session.commit.assert_not_called()
    session.rollback.assert_not_called()
    session.close.assert_not_called()


def test_store_propagates_failure_and_stops_later_batches() -> None:
    service, session, repository, _ = _service_with_repository()
    failure = RuntimeError("repository write failed")
    repository.upsert_many.side_effect = [1_000, failure]

    with pytest.raises(RuntimeError) as raised:
        service.store(_canonical_rows(2_001))

    assert raised.value is failure
    assert repository.upsert_many.call_count == 2
    assert [
        len(call.args[0])
        for call in repository.upsert_many.call_args_list
    ] == [1_000, 1_000]
    session.commit.assert_not_called()
    session.rollback.assert_not_called()
    session.close.assert_not_called()


def test_get_range_delegates_without_transforming_inputs_or_results() -> None:
    service, session, repository, _ = _service_with_repository()
    symbols = [" aapl ", "AAPL", " aapl "]
    start_date = date(2026, 1, 31)
    end_date = date(2026, 1, 1)
    expected_rows = [MagicMock(), MagicMock()]
    repository.get_range.return_value = expected_rows

    result = service.get_range(symbols, start_date, end_date)

    assert result is expected_rows
    repository.get_range.assert_called_once_with(
        symbols,
        start_date,
        end_date,
    )
    assert repository.get_range.call_args.args[0] is symbols
    session.commit.assert_not_called()
    session.rollback.assert_not_called()
    session.close.assert_not_called()
