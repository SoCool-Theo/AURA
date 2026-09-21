from datetime import date, timedelta
from decimal import Decimal
import math

import pytest

from backend.app.database.models import MarketData
from backend.app.forecasting.data import (
    MIN_LABEL_COMPLETE_TRAINING_ORIGINS,
    ForecastDataError,
    build_forecast_dataset,
    build_price_histories,
)


def _record(
    symbol: str,
    observation_date: date,
    price: Decimal | float | int | str,
    *,
    source: str = "test-provider",
) -> MarketData:
    return MarketData(
        symbol=symbol,
        date=observation_date,
        adjusted_close=price,  # type: ignore[arg-type]
        volume=None,
        source=source,
    )


def _daily_records(
    count: int,
    *,
    symbol: str = "AAPL",
    start: date = date(2025, 1, 1),
) -> list[MarketData]:
    return [
        _record(symbol, start + timedelta(days=index), Decimal("100"))
        for index in range(count)
    ]


def test_adapter_sorts_symbols_and_dates_deterministically() -> None:
    records = [
        _record("MSFT", date(2026, 1, 3), Decimal("303")),
        _record(" aapl ", date(2026, 1, 4), Decimal("104")),
        _record("AAPL", date(2026, 1, 2), Decimal("102")),
        _record("MSFT", date(2026, 1, 1), Decimal("301")),
    ]

    histories = build_price_histories(records)

    assert [history.symbol for history in histories] == ["AAPL", "MSFT"]
    assert [item.date for item in histories[0].observations] == [
        date(2026, 1, 2),
        date(2026, 1, 4),
    ]
    assert [item.adjusted_close for item in histories[1].observations] == [
        301.0,
        303.0,
    ]


def test_adapter_keeps_different_asset_calendars_independent() -> None:
    histories = build_price_histories(
        [
            _record("AAPL", date(2026, 1, 2), Decimal("100")),
            _record("AAPL", date(2026, 1, 5), Decimal("101")),
            _record("BTC-USD", date(2026, 1, 3), Decimal("90000")),
            _record("BTC-USD", date(2026, 1, 4), Decimal("91000")),
            _record("BTC-USD", date(2026, 1, 5), Decimal("92000")),
        ]
    )

    assert [item.date for item in histories[0].observations] == [
        date(2026, 1, 2),
        date(2026, 1, 5),
    ]
    assert [item.date for item in histories[1].observations] == [
        date(2026, 1, 3),
        date(2026, 1, 4),
        date(2026, 1, 5),
    ]


def test_adapter_rejects_duplicate_normalized_symbol_date() -> None:
    records = [
        _record("AAPL", date(2026, 1, 2), Decimal("100")),
        _record(" aapl ", date(2026, 1, 2), Decimal("101")),
    ]

    with pytest.raises(ForecastDataError, match="duplicate forecast observation"):
        build_price_histories(records)


@pytest.mark.parametrize(
    "price",
    [
        Decimal("0"),
        Decimal("-1"),
        Decimal("NaN"),
        Decimal("Infinity"),
        math.nan,
        math.inf,
    ],
)
def test_adapter_rejects_non_positive_or_non_finite_prices(
    price: Decimal | float,
) -> None:
    with pytest.raises(ForecastDataError, match="positive and finite"):
        build_price_histories([_record("AAPL", date(2026, 1, 2), price)])


def test_adapter_rejects_non_numeric_price() -> None:
    with pytest.raises(ForecastDataError, match="real numeric"):
        build_price_histories(
            [_record("AAPL", date(2026, 1, 2), "100")]
        )


@pytest.mark.parametrize("symbol", ["UNKNOWN", "THB=X"])
def test_adapter_allows_only_user_asset_symbols(symbol: str) -> None:
    with pytest.raises(ForecastDataError):
        build_price_histories(
            [_record(symbol, date(2026, 1, 2), Decimal("100"))]
        )


def test_adapter_does_not_mutate_caller_owned_records_or_list() -> None:
    records = [
        _record("MSFT", date(2026, 1, 3), Decimal("303")),
        _record("AAPL", date(2026, 1, 2), Decimal("102")),
    ]
    original_list = list(records)
    original_values = [
        (record.symbol, record.date, record.adjusted_close) for record in records
    ]

    build_price_histories(records)

    assert records == original_list
    assert [
        (record.symbol, record.date, record.adjusted_close) for record in records
    ] == original_values


def test_adapter_returns_empty_tuple_for_no_records() -> None:
    assert build_price_histories([]) == ()


def test_adapter_uses_canonical_price_even_when_source_marks_fallback() -> None:
    history = build_price_histories(
        [
            _record(
                "AAPL",
                date(2026, 1, 2),
                Decimal("99.25"),
                source="provider-close-fallback",
            )
        ]
    )[0]

    assert history.observations[0].adjusted_close == 99.25


def test_dataset_exposes_warmup_and_label_completion_metadata() -> None:
    history = build_price_histories(_daily_records(290))[0]

    dataset = build_forecast_dataset(history)

    assert dataset.symbol == "AAPL"
    assert dataset.feature_set_version == "forecast-features-v1"
    assert dataset.target_set_version == "forecast-targets-v1"
    assert dataset.max_feature_lookback == 252
    assert dataset.minimum_label_complete_training_origins == 756
    assert dataset.minimum_label_complete_training_origins == (
        MIN_LABEL_COMPLETE_TRAINING_ORIGINS
    )
    assert dataset.price_observation_count == 290
    assert dataset.feature_origin_count == 38
    assert dataset.target_origin_count == 260
    assert dataset.label_complete_origin_count == 8
    assert all(
        row.features.origin_date == row.target.origin_date
        for row in dataset.rows
    )
    assert all(
        row.target.label_completion_date == row.target.endpoint_date
        for row in dataset.rows
    )
