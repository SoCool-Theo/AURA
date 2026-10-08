from dataclasses import fields
from datetime import date, timedelta
from decimal import Decimal
import math

import pytest

from backend.app.database.models import MarketData
from backend.app.forecasting.data import build_price_histories
from backend.app.forecasting.features import (
    FEATURE_NAMES,
    FEATURE_SET_VERSION,
    ForecastFeatureRow,
    build_feature_rows,
)
from backend.app.forecasting.targets import build_target_rows


def _geometric_records(
    count: int,
    *,
    daily_log_return: float = 0.01,
    scale: float = 1.0,
    start: date = date(2025, 1, 1),
) -> list[MarketData]:
    return [
        MarketData(
            symbol="AAPL",
            date=start + timedelta(days=index),
            adjusted_close=Decimal(
                str(scale * 100.0 * math.exp(daily_log_return * index))
            ),
            volume=None,
            source="test-provider",
        )
        for index in range(count)
    ]


def _history(records: list[MarketData]):
    return build_price_histories(records)[0]


def _row_for_origin(rows, origin_date: date):
    return next(row for row in rows if row.origin_date == origin_date)


def test_feature_version_and_exact_v1_names_are_stable() -> None:
    assert FEATURE_SET_VERSION == "forecast-features-v1"
    assert FEATURE_NAMES == tuple(
        field.name
        for field in fields(ForecastFeatureRow)
        if field.name not in {"symbol", "origin_date"}
    )
    assert all("price" not in name for name in FEATURE_NAMES)


def test_feature_warmup_excludes_first_252_observations() -> None:
    assert build_feature_rows(_history(_geometric_records(252))) == ()

    rows = build_feature_rows(_history(_geometric_records(253)))

    assert len(rows) == 1
    assert rows[0].origin_date == date(2025, 1, 1) + timedelta(days=252)


def test_geometric_prices_produce_documented_feature_formulas() -> None:
    rows = build_feature_rows(_history(_geometric_records(253)))
    row = rows[0]

    assert row.log_return_1 == pytest.approx(0.01)
    assert row.cumulative_return_5 == pytest.approx(math.exp(0.05) - 1.0)
    assert row.cumulative_return_21 == pytest.approx(math.exp(0.21) - 1.0)
    assert row.cumulative_return_63 == pytest.approx(math.exp(0.63) - 1.0)
    assert row.cumulative_return_126 == pytest.approx(math.exp(1.26) - 1.0)
    assert row.cumulative_return_252 == pytest.approx(math.exp(2.52) - 1.0)
    assert row.rolling_mean_log_return_5 == pytest.approx(0.01)
    assert row.rolling_mean_log_return_21 == pytest.approx(0.01)
    assert row.rolling_mean_log_return_63 == pytest.approx(0.01)
    assert row.rolling_volatility_log_return_5 == pytest.approx(0.0, abs=1e-14)
    assert row.rolling_volatility_log_return_21 == pytest.approx(0.0, abs=1e-14)
    assert row.rolling_volatility_log_return_63 == pytest.approx(0.0, abs=1e-14)
    assert row.rolling_volatility_log_return_126 == pytest.approx(0.0, abs=1e-14)
    assert row.rolling_volatility_log_return_252 == pytest.approx(0.0, abs=1e-14)


def test_changing_price_after_origin_does_not_change_origin_features() -> None:
    records = _geometric_records(270)
    origin_date = records[252].date
    changed_records = list(records)
    changed_records[253] = MarketData(
        symbol="AAPL",
        date=records[253].date,
        adjusted_close=records[253].adjusted_close * Decimal("50"),
        volume=None,
        source="test-provider",
    )

    original = _row_for_origin(
        build_feature_rows(_history(records)), origin_date
    )
    changed = _row_for_origin(
        build_feature_rows(_history(changed_records)), origin_date
    )

    assert changed == original


def test_changing_target_window_changes_target_not_origin_features() -> None:
    records = _geometric_records(290)
    origin_date = records[252].date
    changed_records = list(records)
    changed_records[260] = MarketData(
        symbol="AAPL",
        date=records[260].date,
        adjusted_close=records[260].adjusted_close * Decimal("1.5"),
        volume=None,
        source="test-provider",
    )

    original_history = _history(records)
    changed_history = _history(changed_records)
    original_feature = _row_for_origin(
        build_feature_rows(original_history), origin_date
    )
    changed_feature = _row_for_origin(
        build_feature_rows(changed_history), origin_date
    )
    original_target = _row_for_origin(
        build_target_rows(original_history), origin_date
    )
    changed_target = _row_for_origin(
        build_target_rows(changed_history), origin_date
    )

    assert changed_feature == original_feature
    assert changed_target.realized_volatility_30d != pytest.approx(
        original_target.realized_volatility_30d
    )


def test_252_observation_feature_uses_past_and_current_prices_only() -> None:
    records = _geometric_records(254)
    origin_date = records[252].date
    past_changed = list(records)
    future_changed = list(records)
    past_changed[0] = MarketData(
        symbol="AAPL",
        date=records[0].date,
        adjusted_close=records[0].adjusted_close * Decimal("0.5"),
        volume=None,
        source="test-provider",
    )
    future_changed[253] = MarketData(
        symbol="AAPL",
        date=records[253].date,
        adjusted_close=records[253].adjusted_close * Decimal("2"),
        volume=None,
        source="test-provider",
    )

    original = _row_for_origin(build_feature_rows(_history(records)), origin_date)
    changed_past = _row_for_origin(
        build_feature_rows(_history(past_changed)), origin_date
    )
    changed_future = _row_for_origin(
        build_feature_rows(_history(future_changed)), origin_date
    )

    assert changed_past.cumulative_return_252 != pytest.approx(
        original.cumulative_return_252
    )
    assert changed_future == original


def test_features_are_scale_invariant_and_not_globally_standardized() -> None:
    original = build_feature_rows(_history(_geometric_records(253)))[0]
    scaled = build_feature_rows(
        _history(_geometric_records(253, scale=1_000.0))
    )[0]

    for name in FEATURE_NAMES:
        assert getattr(scaled, name) == pytest.approx(getattr(original, name))


def test_feature_generation_does_not_mutate_history() -> None:
    history = _history(_geometric_records(260))
    observations_before = history.observations

    build_feature_rows(history)

    assert history.observations is observations_before
    assert history.observations == observations_before


def test_every_feature_value_is_finite() -> None:
    rows = build_feature_rows(_history(_geometric_records(260, daily_log_return=-0.001)))

    assert rows
    assert all(
        math.isfinite(getattr(row, name))
        for row in rows
        for name in FEATURE_NAMES
    )
