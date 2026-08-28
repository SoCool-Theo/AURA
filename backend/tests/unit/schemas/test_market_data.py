from copy import deepcopy
from datetime import date

import pytest
from pydantic import ValidationError

from backend.app.schemas.market_data import (
    AssetPriceSeries,
    HistoricalMarketDataRequest,
    HistoricalMarketDataResponse,
    HistoricalPricePoint,
)


def _point(
    point_date: str,
    adjusted_close: int | float = 100.0,
    volume: int | None = 1_000,
) -> dict[str, object]:
    return {
        "date": point_date,
        "adjusted_close": adjusted_close,
        "volume": volume,
    }


def _series(
    symbol: str = "AAPL",
    *,
    source: str = "Synthetic",
    points: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "symbol": symbol,
        "source": source,
        "points": points
        if points is not None
        else [
            _point("2026-01-02", 100.0),
            _point("2026-01-05", 101.5),
        ],
    }


def _valid_response_data() -> dict[str, object]:
    return {
        "start_date": "2026-01-01",
        "end_date": "2026-01-31",
        "series": [_series()],
    }


def test_request_accepts_one_symbol() -> None:
    result = HistoricalMarketDataRequest(
        symbols=["AAPL"],
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
    )

    assert result.symbols == ["AAPL"]


def test_request_accepts_multiple_symbols() -> None:
    result = HistoricalMarketDataRequest(
        symbols=["AAPL", "MSFT", "BND"],
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
    )

    assert result.symbols == ["AAPL", "MSFT", "BND"]


def test_request_normalizes_symbols() -> None:
    result = HistoricalMarketDataRequest(
        symbols=[" aapl ", "msft"],
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
    )

    assert result.symbols == ["AAPL", "MSFT"]


def test_request_preserves_symbol_order() -> None:
    result = HistoricalMarketDataRequest(
        symbols=["BETA", "ALPHA", "CASH"],
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
    )

    assert result.symbols == ["BETA", "ALPHA", "CASH"]


def test_request_rejects_empty_symbol_list() -> None:
    with pytest.raises(ValidationError):
        HistoricalMarketDataRequest(
            symbols=[],
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
        )


@pytest.mark.parametrize(
    "symbols",
    [
        ["AAPL", "AAPL"],
        ["AAPL", "aapl"],
        ["AAPL", " AAPL "],
    ],
)
def test_request_rejects_duplicate_normalized_symbols(
    symbols: list[str],
) -> None:
    with pytest.raises(
        ValidationError,
        match="symbols must be unique after normalization",
    ):
        HistoricalMarketDataRequest(
            symbols=symbols,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
        )


def test_request_accepts_equal_dates() -> None:
    result = HistoricalMarketDataRequest(
        symbols=["AAPL"],
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 1),
    )

    assert result.start_date == result.end_date


def test_request_rejects_reversed_dates_through_analysis_period() -> None:
    with pytest.raises(
        ValidationError,
        match="start_date must be on or before end_date",
    ):
        HistoricalMarketDataRequest(
            symbols=["AAPL"],
            start_date=date(2026, 2, 1),
            end_date=date(2026, 1, 31),
        )


def test_request_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        HistoricalMarketDataRequest.model_validate(
            {
                "symbols": ["AAPL"],
                "start_date": "2026-01-01",
                "end_date": "2026-01-31",
                "provider": "Synthetic",
            }
        )


def test_request_does_not_mutate_caller_input() -> None:
    symbols = [" aapl ", "msft"]
    data = {
        "symbols": symbols,
        "start_date": "2026-01-01",
        "end_date": "2026-01-31",
    }
    original = deepcopy(data)

    result = HistoricalMarketDataRequest.model_validate(data)

    assert data == original
    assert data["symbols"] is symbols
    assert result.symbols == ["AAPL", "MSFT"]


def test_price_point_accepts_floating_adjusted_close() -> None:
    result = HistoricalPricePoint(
        date=date(2026, 1, 2),
        adjusted_close=100.5,
    )

    assert result.adjusted_close == pytest.approx(100.5)


def test_price_point_accepts_integer_adjusted_close() -> None:
    result = HistoricalPricePoint(
        date=date(2026, 1, 2),
        adjusted_close=100,
    )

    assert type(result.adjusted_close) is float
    assert result.adjusted_close == 100.0


def test_price_point_accepts_positive_volume() -> None:
    result = HistoricalPricePoint(
        date=date(2026, 1, 2),
        adjusted_close=100.0,
        volume=1_000,
    )

    assert result.volume == 1_000


def test_price_point_accepts_zero_volume() -> None:
    result = HistoricalPricePoint(
        date=date(2026, 1, 2),
        adjusted_close=100.0,
        volume=0,
    )

    assert result.volume == 0


def test_price_point_accepts_none_volume() -> None:
    result = HistoricalPricePoint(
        date=date(2026, 1, 2),
        adjusted_close=100.0,
        volume=None,
    )

    assert result.volume is None


@pytest.mark.parametrize(
    "adjusted_close",
    [0.0, -0.01, float("nan"), float("inf"), -float("inf")],
)
def test_price_point_rejects_invalid_adjusted_close(
    adjusted_close: float,
) -> None:
    with pytest.raises(ValidationError):
        HistoricalPricePoint(
            date=date(2026, 1, 2),
            adjusted_close=adjusted_close,
        )


def test_price_point_rejects_boolean_adjusted_close() -> None:
    with pytest.raises(ValidationError):
        HistoricalPricePoint(
            date=date(2026, 1, 2),
            adjusted_close=True,
        )


def test_price_point_rejects_numeric_string_adjusted_close() -> None:
    with pytest.raises(ValidationError):
        HistoricalPricePoint(
            date=date(2026, 1, 2),
            adjusted_close="100.5",
        )


@pytest.mark.parametrize("volume", [-1, True, 1.5, "100"])
def test_price_point_rejects_invalid_volume(volume: object) -> None:
    with pytest.raises(ValidationError):
        HistoricalPricePoint(
            date=date(2026, 1, 2),
            adjusted_close=100.0,
            volume=volume,
        )


def test_price_point_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        HistoricalPricePoint.model_validate(
            {
                "date": "2026-01-02",
                "adjusted_close": 100.0,
                "close": 99.0,
            }
        )


def test_price_point_serializes_date_as_json_safe_string() -> None:
    result = HistoricalPricePoint(
        date=date(2026, 1, 2),
        adjusted_close=100.0,
        volume=1_000,
    )

    assert result.model_dump(mode="json") == {
        "date": "2026-01-02",
        "adjusted_close": 100.0,
        "volume": 1_000,
    }


def test_price_point_does_not_mutate_input_mapping() -> None:
    data = {
        "date": "2026-01-02",
        "adjusted_close": 100,
        "volume": 1_000,
    }
    original = data.copy()

    result = HistoricalPricePoint.model_validate(data)

    assert data == original
    assert result.adjusted_close == 100.0


def test_asset_series_accepts_normalized_symbol_source_and_points() -> None:
    result = AssetPriceSeries.model_validate(
        _series(symbol=" aapl ", source=" Synthetic ")
    )

    assert result.symbol == "AAPL"
    assert result.source == "Synthetic"
    assert [point.date for point in result.points] == [
        date(2026, 1, 2),
        date(2026, 1, 5),
    ]


def test_asset_series_preserves_symbol_punctuation() -> None:
    result = AssetPriceSeries.model_validate(_series(symbol=" brk.b "))

    assert result.symbol == "BRK.B"


@pytest.mark.parametrize("source", ["", " \t "])
def test_asset_series_rejects_empty_normalized_source(source: str) -> None:
    with pytest.raises(
        ValidationError,
        match="source cannot be empty after normalization",
    ):
        AssetPriceSeries.model_validate(_series(source=source))


def test_asset_series_rejects_non_string_source() -> None:
    data = _series()
    data["source"] = 123

    with pytest.raises(ValidationError):
        AssetPriceSeries.model_validate(data)


def test_asset_series_rejects_empty_points() -> None:
    with pytest.raises(ValidationError):
        AssetPriceSeries.model_validate(_series(points=[]))


def test_asset_series_rejects_duplicate_point_dates() -> None:
    points = [
        _point("2026-01-02", 100.0),
        _point("2026-01-02", 101.0),
    ]

    with pytest.raises(ValidationError, match="point dates must be unique"):
        AssetPriceSeries.model_validate(_series(points=points))


def test_asset_series_rejects_descending_point_dates() -> None:
    points = [
        _point("2026-01-05", 101.0),
        _point("2026-01-02", 100.0),
    ]

    with pytest.raises(
        ValidationError,
        match="point dates must be strictly increasing",
    ):
        AssetPriceSeries.model_validate(_series(points=points))


def test_asset_series_accepts_non_consecutive_dates() -> None:
    points = [
        _point("2026-01-02", 100.0),
        _point("2026-01-20", 105.0),
    ]

    result = AssetPriceSeries.model_validate(_series(points=points))

    assert [point.date for point in result.points] == [
        date(2026, 1, 2),
        date(2026, 1, 20),
    ]


def test_asset_series_preserves_point_order() -> None:
    points = [
        _point("2026-01-02", 100.0),
        _point("2026-01-05", 101.0),
        _point("2026-01-20", 105.0),
    ]

    result = AssetPriceSeries.model_validate(_series(points=points))

    assert [point.adjusted_close for point in result.points] == [
        100.0,
        101.0,
        105.0,
    ]


def test_asset_series_rejects_unknown_field() -> None:
    data = _series()
    data["currency"] = "USD"

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        AssetPriceSeries.model_validate(data)


def test_asset_series_does_not_mutate_caller_owned_inputs() -> None:
    first_point = _point("2026-01-02", 100)
    second_point = _point("2026-01-05", 101.5)
    points = [first_point, second_point]
    data = {
        "symbol": " aapl ",
        "source": " Synthetic ",
        "points": points,
    }
    original = deepcopy(data)

    result = AssetPriceSeries.model_validate(data)

    assert data == original
    assert data["points"] is points
    assert points[0] is first_point
    assert points[1] is second_point
    assert result.symbol == "AAPL"
    assert result.source == "Synthetic"


def test_response_accepts_one_series() -> None:
    result = HistoricalMarketDataResponse.model_validate(
        _valid_response_data()
    )

    assert len(result.series) == 1
    assert result.series[0].symbol == "AAPL"


def test_response_accepts_multiple_series() -> None:
    data = _valid_response_data()
    data["series"] = [
        _series("AAPL"),
        _series("MSFT"),
    ]

    result = HistoricalMarketDataResponse.model_validate(data)

    assert [asset_series.symbol for asset_series in result.series] == [
        "AAPL",
        "MSFT",
    ]


def test_response_accepts_different_trading_dates_across_assets() -> None:
    data = _valid_response_data()
    data["series"] = [
        _series(
            "AAPL",
            points=[
                _point("2026-01-02", 100.0),
                _point("2026-01-05", 101.0),
            ],
        ),
        _series(
            "MSFT",
            points=[
                _point("2026-01-03", 200.0),
                _point("2026-01-06", 202.0),
            ],
        ),
    ]

    result = HistoricalMarketDataResponse.model_validate(data)

    assert result.series[0].points[0].date == date(2026, 1, 2)
    assert result.series[1].points[0].date == date(2026, 1, 3)


def test_response_accepts_different_point_counts() -> None:
    data = _valid_response_data()
    data["series"] = [
        _series("AAPL"),
        _series(
            "MSFT",
            points=[_point("2026-01-03", 200.0)],
        ),
    ]

    result = HistoricalMarketDataResponse.model_validate(data)

    assert len(result.series[0].points) == 2
    assert len(result.series[1].points) == 1


def test_response_preserves_series_order() -> None:
    data = _valid_response_data()
    data["series"] = [
        _series("BETA"),
        _series("ALPHA"),
        _series("CASH"),
    ]

    result = HistoricalMarketDataResponse.model_validate(data)

    assert [asset_series.symbol for asset_series in result.series] == [
        "BETA",
        "ALPHA",
        "CASH",
    ]


def test_response_rejects_empty_series() -> None:
    data = _valid_response_data()
    data["series"] = []

    with pytest.raises(ValidationError):
        HistoricalMarketDataResponse.model_validate(data)


@pytest.mark.parametrize(
    "symbols",
    [
        ("AAPL", "AAPL"),
        ("AAPL", "aapl"),
        ("AAPL", " AAPL "),
    ],
)
def test_response_rejects_duplicate_normalized_series_symbols(
    symbols: tuple[str, str],
) -> None:
    data = _valid_response_data()
    data["series"] = [
        _series(symbols[0]),
        _series(symbols[1]),
    ]

    with pytest.raises(
        ValidationError,
        match="series symbols must be unique after normalization",
    ):
        HistoricalMarketDataResponse.model_validate(data)


def test_response_accepts_point_on_start_boundary() -> None:
    data = _valid_response_data()
    data["series"] = [
        _series(points=[_point("2026-01-01", 100.0)])
    ]

    result = HistoricalMarketDataResponse.model_validate(data)

    assert result.series[0].points[0].date == result.start_date


def test_response_accepts_point_on_end_boundary() -> None:
    data = _valid_response_data()
    data["series"] = [
        _series(points=[_point("2026-01-31", 100.0)])
    ]

    result = HistoricalMarketDataResponse.model_validate(data)

    assert result.series[0].points[0].date == result.end_date


@pytest.mark.parametrize("point_date", ["2025-12-31", "2026-02-01"])
def test_response_rejects_point_outside_period(point_date: str) -> None:
    data = _valid_response_data()
    data["series"] = [_series(points=[_point(point_date, 100.0)])]

    with pytest.raises(
        ValidationError,
        match="point dates must fall within the inclusive response period",
    ):
        HistoricalMarketDataResponse.model_validate(data)


def test_response_accepts_equal_dates_when_points_use_that_date() -> None:
    data = _valid_response_data()
    data["start_date"] = "2026-01-15"
    data["end_date"] = "2026-01-15"
    data["series"] = [
        _series(points=[_point("2026-01-15", 100.0)])
    ]

    result = HistoricalMarketDataResponse.model_validate(data)

    assert result.start_date == result.end_date
    assert result.series[0].points[0].date == result.start_date


def test_response_rejects_reversed_dates_through_analysis_period() -> None:
    data = _valid_response_data()
    data["start_date"] = "2026-02-01"
    data["end_date"] = "2026-01-31"

    with pytest.raises(
        ValidationError,
        match="start_date must be on or before end_date",
    ):
        HistoricalMarketDataResponse.model_validate(data)


def test_response_rejects_unknown_field() -> None:
    data = _valid_response_data()
    data["provider"] = "Synthetic"

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        HistoricalMarketDataResponse.model_validate(data)


def test_response_rejects_nested_unknown_field() -> None:
    data = _valid_response_data()
    series = data["series"]
    assert isinstance(series, list)
    points = series[0]["points"]
    assert isinstance(points, list)
    points[0]["currency"] = "USD"

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        HistoricalMarketDataResponse.model_validate(data)


def test_response_model_dump_json_mode_is_json_safe() -> None:
    data = {
        "start_date": "2026-01-01",
        "end_date": "2026-01-02",
        "series": [
            _series(
                " aapl ",
                source=" Synthetic ",
                points=[_point("2026-01-02", 100, None)],
            )
        ],
    }

    result = HistoricalMarketDataResponse.model_validate(data)

    assert result.model_dump(mode="json") == {
        "start_date": "2026-01-01",
        "end_date": "2026-01-02",
        "series": [
            {
                "symbol": "AAPL",
                "source": "Synthetic",
                "points": [
                    {
                        "date": "2026-01-02",
                        "adjusted_close": 100.0,
                        "volume": None,
                    }
                ],
            }
        ],
    }


def test_response_does_not_mutate_caller_owned_inputs() -> None:
    point = _point("2026-01-02", 100)
    points = [point]
    asset_series = {
        "symbol": " aapl ",
        "source": " Synthetic ",
        "points": points,
    }
    series = [asset_series]
    data = {
        "start_date": "2026-01-01",
        "end_date": "2026-01-31",
        "series": series,
    }
    original = deepcopy(data)

    result = HistoricalMarketDataResponse.model_validate(data)

    assert data == original
    assert data["series"] is series
    assert series[0] is asset_series
    assert asset_series["points"] is points
    assert points[0] is point
    assert result.series[0].symbol == "AAPL"
