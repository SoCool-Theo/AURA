from copy import deepcopy
from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.database.models import MarketData, WatchlistItem
import backend.app.services.watchlist_service as service_module
from backend.app.services.watchlist_service import (
    DuplicateWatchlistItemError,
    UnsupportedWatchlistSymbolError,
    WatchlistItemNotFoundError,
    WatchlistService,
)


USER_ID = UUID("71000000-0000-0000-0000-000000000001")
CREATED_AT = datetime(2026, 9, 24, 2, tzinfo=UTC)


def _service() -> tuple[WatchlistService, MagicMock, MagicMock, MagicMock]:
    session = MagicMock(spec=Session)
    repository = MagicMock(spec=service_module.WatchlistRepository)
    market_repository = MagicMock(
        spec=service_module.MarketDataRepository
    )
    with (
        patch.object(
            service_module,
            "WatchlistRepository",
            return_value=repository,
        ),
        patch.object(
            service_module,
            "MarketDataRepository",
            return_value=market_repository,
        ),
    ):
        service = WatchlistService(session)
    return service, session, repository, market_repository


def _item(symbol: str = "AAPL") -> WatchlistItem:
    return WatchlistItem(
        id=uuid4(),
        user_id=USER_ID,
        symbol=symbol,
        created_at=CREATED_AT,
    )


def _observation(day: date, price: str, symbol: str = "AAPL") -> MarketData:
    return MarketData(
        symbol=symbol,
        date=day,
        adjusted_close=Decimal(price),
        volume=None,
        source="watchlist-test",
    )


def _assert_lifecycle_untouched(session: MagicMock) -> None:
    session.commit.assert_not_called()
    session.rollback.assert_not_called()
    session.close.assert_not_called()


def test_add_normalizes_and_saves_supported_asset() -> None:
    service, session, repository, market_repository = _service()
    created = _item()
    repository.find_for_user_by_symbol.return_value = None
    repository.create.return_value = created
    market_repository.get_price_change_observations.return_value = []

    response = service.add(user_id=USER_ID, symbol=" aapl ")

    repository.find_for_user_by_symbol.assert_called_once_with(
        user_id=USER_ID,
        symbol="AAPL",
    )
    repository.create.assert_called_once_with(
        user_id=USER_ID,
        symbol="AAPL",
    )
    assert response.symbol == "AAPL"
    assert response.latest_price is None
    _assert_lifecycle_untouched(session)


def test_add_rejects_unsupported_asset_without_database_access() -> None:
    service, session, repository, market_repository = _service()

    with pytest.raises(UnsupportedWatchlistSymbolError):
        service.add(user_id=USER_ID, symbol="ASDF")

    repository.find_for_user_by_symbol.assert_not_called()
    repository.create.assert_not_called()
    market_repository.get_price_change_observations.assert_not_called()
    _assert_lifecycle_untouched(session)


def test_add_rejects_existing_normalized_duplicate() -> None:
    service, session, repository, _ = _service()
    repository.find_for_user_by_symbol.return_value = _item()

    with pytest.raises(DuplicateWatchlistItemError):
        service.add(user_id=USER_ID, symbol="aapl")

    repository.create.assert_not_called()
    _assert_lifecycle_untouched(session)


def test_database_duplicate_race_maps_without_service_rollback() -> None:
    service, session, repository, _ = _service()
    repository.find_for_user_by_symbol.return_value = None
    diagnostic = SimpleNamespace(
        constraint_name="uq_watchlist_items_user_symbol"
    )
    repository.create.side_effect = IntegrityError(
        "INSERT INTO watchlist_items",
        {},
        SimpleNamespace(diag=diagnostic),
    )

    with pytest.raises(DuplicateWatchlistItemError):
        service.add(user_id=USER_ID, symbol="AAPL")

    _assert_lifecycle_untouched(session)


def test_list_maps_latest_previous_available_and_first_ytd_observations() -> None:
    service, session, repository, market_repository = _service()
    item = _item()
    observations = [
        _observation(date(2026, 1, 2), "100"),
        _observation(date(2026, 9, 18), "120"),
        _observation(date(2026, 9, 21), "126"),
    ]
    original = deepcopy(
        [(row.date, row.adjusted_close) for row in observations]
    )
    repository.list_for_user.return_value = [item]
    market_repository.get_price_change_observations.return_value = observations

    response = service.list_for_user(user_id=USER_ID)

    assert len(response.items) == 1
    mapped = response.items[0]
    assert mapped.latest_price == 126.0
    assert mapped.latest_price_date == date(2026, 9, 21)
    assert mapped.daily_change_percent == 5.0
    assert mapped.ytd_change_percent == 26.0
    assert [(row.date, row.adjusted_close) for row in observations] == original
    _assert_lifecycle_untouched(session)


def test_list_preserves_negative_changes() -> None:
    service, _, repository, market_repository = _service()
    repository.list_for_user.return_value = [_item()]
    market_repository.get_price_change_observations.return_value = [
        _observation(date(2026, 1, 2), "100"),
        _observation(date(2026, 9, 18), "120"),
        _observation(date(2026, 9, 21), "90"),
    ]

    item = service.list_for_user(user_id=USER_ID).items[0]

    assert item.daily_change_percent == -25.0
    assert item.ytd_change_percent == -10.0


@pytest.mark.parametrize(
    "observations",
    [
        [],
        [_observation(date(2026, 9, 21), "126")],
    ],
    ids=["no-market-data", "single-observation"],
)
def test_list_never_fabricates_missing_change_data(
    observations: list[MarketData],
) -> None:
    service, _, repository, market_repository = _service()
    repository.list_for_user.return_value = [_item()]
    market_repository.get_price_change_observations.return_value = observations

    item = service.list_for_user(user_id=USER_ID).items[0]

    if observations:
        assert item.latest_price == 126.0
        assert item.latest_price_date == date(2026, 9, 21)
    else:
        assert item.latest_price is None
        assert item.latest_price_date is None
    assert item.daily_change_percent is None
    assert item.ytd_change_percent is None


def test_zero_denominators_return_null_instead_of_fabricated_zero() -> None:
    service, _, repository, market_repository = _service()
    repository.list_for_user.return_value = [_item()]
    market_repository.get_price_change_observations.return_value = [
        _observation(date(2026, 1, 2), "0"),
        _observation(date(2026, 9, 18), "0"),
        _observation(date(2026, 9, 21), "90"),
    ]

    item = service.list_for_user(user_id=USER_ID).items[0]

    assert item.latest_price == 90.0
    assert item.daily_change_percent is None
    assert item.ytd_change_percent is None


def test_list_groups_multiple_symbols_without_per_item_market_queries() -> None:
    service, _, repository, market_repository = _service()
    repository.list_for_user.return_value = [_item("AAPL"), _item("MSFT")]
    market_repository.get_price_change_observations.return_value = [
        _observation(date(2026, 9, 21), "126", "AAPL"),
        _observation(date(2026, 9, 21), "350", "MSFT"),
    ]

    response = service.list_for_user(user_id=USER_ID)

    assert [item.symbol for item in response.items] == ["AAPL", "MSFT"]
    market_repository.get_price_change_observations.assert_called_once_with(
        ["AAPL", "MSFT"]
    )


def test_remove_normalizes_symbol_and_is_owner_scoped() -> None:
    service, session, repository, _ = _service()
    repository.delete_for_user_by_symbol.return_value = True

    service.remove(user_id=USER_ID, symbol=" aapl ")

    repository.delete_for_user_by_symbol.assert_called_once_with(
        user_id=USER_ID,
        symbol="AAPL",
    )
    _assert_lifecycle_untouched(session)


def test_remove_missing_item_uses_sanitizable_not_found_error() -> None:
    service, session, repository, _ = _service()
    repository.delete_for_user_by_symbol.return_value = False

    with pytest.raises(WatchlistItemNotFoundError):
        service.remove(user_id=USER_ID, symbol="AAPL")

    _assert_lifecycle_untouched(session)
