from datetime import UTC, datetime
import math
from uuid import uuid4

import pytest
from pydantic import ValidationError

from backend.app.schemas.watchlist import (
    WatchlistCreateRequest,
    WatchlistItemResponse,
    WatchlistListResponse,
)


def _response_data() -> dict[str, object]:
    return {
        "id": uuid4(),
        "symbol": "AAPL",
        "latest_price": 123.45,
        "latest_price_date": "2026-09-23",
        "daily_change_percent": 1.23,
        "ytd_change_percent": 14.56,
        "created_at": datetime(2026, 9, 23, tzinfo=UTC),
    }


def test_create_request_normalizes_whitespace_and_case() -> None:
    request = WatchlistCreateRequest.model_validate({"symbol": " aapl "})

    assert request.symbol == "AAPL"


def test_create_request_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        WatchlistCreateRequest.model_validate(
            {"symbol": "AAPL", "user_id": str(uuid4())}
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("latest_price", math.inf),
        ("latest_price", math.nan),
        ("daily_change_percent", -math.inf),
        ("ytd_change_percent", math.nan),
    ],
)
def test_response_rejects_non_finite_public_numbers(
    field: str,
    value: float,
) -> None:
    data = _response_data()
    data[field] = value

    with pytest.raises(ValidationError):
        WatchlistItemResponse.model_validate(data)


def test_response_accepts_intentionally_unavailable_market_data() -> None:
    data = _response_data()
    data.update(
        latest_price=None,
        latest_price_date=None,
        daily_change_percent=None,
        ytd_change_percent=None,
    )

    response = WatchlistItemResponse.model_validate(data)
    listed = WatchlistListResponse(items=[response])

    assert listed.items == [response]


def test_response_requires_price_and_date_context_together() -> None:
    data = _response_data()
    data["latest_price_date"] = None

    with pytest.raises(ValidationError):
        WatchlistItemResponse.model_validate(data)
