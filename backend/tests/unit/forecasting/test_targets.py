from datetime import date, timedelta
from decimal import Decimal
import math

import pytest

from backend.app.database.models import MarketData
from backend.app.forecasting.data import build_price_histories
from backend.app.forecasting.targets import (
    FORECAST_HORIZON_DAYS,
    MAX_ENDPOINT_SLIPPAGE_DAYS,
    TARGET_SET_VERSION,
    build_target_rows,
)


def _history(
    observations: list[tuple[date, str]],
    *,
    symbol: str = "AAPL",
):
    records = [
        MarketData(
            symbol=symbol,
            date=observation_date,
            adjusted_close=Decimal(price),
            volume=None,
            source="test-provider",
        )
        for observation_date, price in observations
    ]
    return build_price_histories(records)[0]


def test_target_contract_versions_and_horizon_are_stable() -> None:
    assert TARGET_SET_VERSION == "forecast-targets-v1"
    assert FORECAST_HORIZON_DAYS == 30
    assert MAX_ENDPOINT_SLIPPAGE_DAYS == 4


@pytest.mark.parametrize("slippage_days", [0, 1, 2, 3, 4])
def test_endpoint_at_day_30_through_day_34_is_accepted(
    slippage_days: int,
) -> None:
    origin = date(2026, 1, 1)
    endpoint = origin + timedelta(days=30 + slippage_days)
    rows = build_target_rows(_history([(origin, "100"), (endpoint, "110")]))

    assert len(rows) == 1
    assert rows[0].origin_date == origin
    assert rows[0].requested_target_date == origin + timedelta(days=30)
    assert rows[0].endpoint_date == endpoint
    assert rows[0].endpoint_slippage_days == slippage_days
    assert rows[0].label_completion_date == endpoint
    assert rows[0].return_30d == pytest.approx(0.1)


def test_endpoint_after_day_34_is_rejected() -> None:
    origin = date(2026, 1, 1)
    rows = build_target_rows(
        _history([(origin, "100"), (origin + timedelta(days=35), "110")])
    )

    assert rows == ()


def test_earlier_observation_is_not_used_as_endpoint_fallback() -> None:
    origin = date(2026, 1, 1)
    rows = build_target_rows(
        _history(
            [
                (origin, "100"),
                (origin + timedelta(days=29), "105"),
                (origin + timedelta(days=35), "110"),
            ]
        )
    )

    assert rows == ()


def test_weekend_target_date_is_not_synthesized() -> None:
    origin = date(2026, 1, 2)  # Friday; day 30 is Sunday, 2026-02-01.
    observed_monday = date(2026, 2, 2)
    rows = build_target_rows(
        _history(
            [
                (origin, "100"),
                (date(2026, 1, 30), "104"),
                (observed_monday, "105"),
            ]
        )
    )

    assert rows[0].requested_target_date == date(2026, 2, 1)
    assert rows[0].endpoint_date == observed_monday
    assert rows[0].endpoint_slippage_days == 1


def test_realized_volatility_uses_only_consecutive_future_window_returns() -> None:
    origin = date(2026, 1, 1)
    observations = [
        (origin, "100"),
        (date(2026, 1, 10), "110"),
        (date(2026, 1, 20), "99"),
        (date(2026, 1, 31), "108"),
        (date(2026, 2, 5), "999"),
    ]
    row = build_target_rows(_history(observations))[0]
    expected_log_returns = (
        math.log(110.0 / 100.0),
        math.log(99.0 / 110.0),
        math.log(108.0 / 99.0),
    )
    expected = math.sqrt(
        math.fsum(value * value for value in expected_log_returns)
    )

    assert row.endpoint_date == date(2026, 1, 31)
    assert row.return_30d == pytest.approx(0.08)
    assert row.realized_volatility_30d == pytest.approx(expected)


def test_observation_after_endpoint_does_not_change_target() -> None:
    origin = date(2026, 1, 1)
    base = [
        (origin, "100"),
        (date(2026, 1, 15), "105"),
        (date(2026, 1, 31), "110"),
        (date(2026, 2, 5), "115"),
    ]
    changed = [*base[:-1], (date(2026, 2, 5), "9999")]

    original_row = build_target_rows(_history(base))[0]
    changed_row = build_target_rows(_history(changed))[0]

    assert changed_row == original_row


def test_origin_price_is_used_for_first_future_log_return() -> None:
    origin = date(2026, 1, 1)
    row = build_target_rows(
        _history(
            [
                (origin, "100"),
                (date(2026, 1, 15), "120"),
                (date(2026, 1, 31), "120"),
            ]
        )
    )[0]

    assert row.realized_volatility_30d == pytest.approx(math.log(1.2))


def test_zero_movement_has_zero_unannualized_realized_volatility() -> None:
    origin = date(2026, 1, 1)
    row = build_target_rows(
        _history(
            [
                (origin, "100"),
                (date(2026, 1, 10), "100"),
                (date(2026, 1, 20), "100"),
                (date(2026, 1, 31), "100"),
            ]
        )
    )[0]

    assert row.return_30d == 0.0
    assert row.realized_volatility_30d == 0.0


def test_target_output_is_finite_and_origin_ordered() -> None:
    start = date(2026, 1, 1)
    history = _history(
        [
            (start + timedelta(days=index), str(100 + index))
            for index in range(70)
        ]
    )
    rows = build_target_rows(history)

    assert [row.origin_date for row in rows] == sorted(
        row.origin_date for row in rows
    )
    assert all(
        math.isfinite(row.return_30d)
        and math.isfinite(row.realized_volatility_30d)
        for row in rows
    )


def test_target_generation_does_not_mutate_history() -> None:
    origin = date(2026, 1, 1)
    history = _history(
        [(origin, "100"), (origin + timedelta(days=30), "110")]
    )
    observations_before = history.observations

    build_target_rows(history)

    assert history.observations is observations_before
    assert history.observations == observations_before
