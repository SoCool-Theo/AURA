from datetime import date
from decimal import Decimal

import numpy as np
import pandas as pd
import pytest

from backend.app.services.market_data_service import _to_market_data_records


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
