"""Authenticated Watchlist workflows and persisted price enrichment."""

from collections import defaultdict
from collections.abc import Sequence
from decimal import Decimal
import math
from uuid import UUID

from pydantic import TypeAdapter, ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..core.instruments import is_user_asset_symbol
from ..database.models import MarketData, WatchlistItem
from ..database.repositories import (
    MarketDataRepository,
    WatchlistRepository,
)
from ..schemas.common import AssetSymbol
from ..schemas.watchlist import (
    WatchlistItemResponse,
    WatchlistListResponse,
)


_SYMBOL_ADAPTER = TypeAdapter(AssetSymbol)
_WATCHLIST_UNIQUE_CONSTRAINT = "uq_watchlist_items_user_symbol"
_ONE_HUNDRED = Decimal("100")


class UnsupportedWatchlistSymbolError(ValueError):
    """Raised when a symbol is not in Aura's supported asset universe."""


class DuplicateWatchlistItemError(ValueError):
    """Raised when one user already observes the normalized symbol."""


class WatchlistItemNotFoundError(ValueError):
    """Raised when an owned Watchlist item cannot be found."""


class WatchlistService:
    """Coordinate Watchlist operations without managing transactions."""

    def __init__(self, session: Session) -> None:
        self._repository = WatchlistRepository(session)
        self._market_data_repository = MarketDataRepository(session)

    def add(self, *, user_id: UUID, symbol: str) -> WatchlistItemResponse:
        """Save one supported normalized symbol and return its current view."""
        normalized_symbol = _normalize_supported_symbol(symbol)
        if self._repository.find_for_user_by_symbol(
            user_id=user_id,
            symbol=normalized_symbol,
        ) is not None:
            raise DuplicateWatchlistItemError

        try:
            item = self._repository.create(
                user_id=user_id,
                symbol=normalized_symbol,
            )
        except IntegrityError as error:
            if _constraint_name(error) == _WATCHLIST_UNIQUE_CONSTRAINT:
                raise DuplicateWatchlistItemError from error
            raise

        observations = self._market_data_repository.get_price_change_observations(
            [normalized_symbol]
        )
        return _to_response(item, observations)

    def list_for_user(self, *, user_id: UUID) -> WatchlistListResponse:
        """Return the user's ordered Watchlist with persisted price context."""
        items = self._repository.list_for_user(user_id)
        observations = (
            self._market_data_repository.get_price_change_observations(
                [item.symbol for item in items]
            )
        )
        observations_by_symbol: dict[str, list[MarketData]] = defaultdict(list)
        for observation in observations:
            observations_by_symbol[observation.symbol].append(observation)
        return WatchlistListResponse(
            items=[
                _to_response(item, observations_by_symbol[item.symbol])
                for item in items
            ]
        )

    def remove(self, *, user_id: UUID, symbol: str) -> None:
        """Remove only the authenticated user's normalized Watchlist item."""
        normalized_symbol = _normalize_supported_symbol(symbol)
        deleted = self._repository.delete_for_user_by_symbol(
            user_id=user_id,
            symbol=normalized_symbol,
        )
        if not deleted:
            raise WatchlistItemNotFoundError


def _normalize_supported_symbol(symbol: str) -> str:
    try:
        normalized = _SYMBOL_ADAPTER.validate_python(symbol)
    except ValidationError as error:
        raise UnsupportedWatchlistSymbolError from error
    if not is_user_asset_symbol(normalized):
        raise UnsupportedWatchlistSymbolError
    return normalized


def _to_response(
    item: WatchlistItem,
    observations: Sequence[MarketData],
) -> WatchlistItemResponse:
    ordered = sorted(observations, key=lambda observation: observation.date)
    if not ordered:
        return WatchlistItemResponse(
            id=item.id,
            symbol=item.symbol,
            latest_price=None,
            latest_price_date=None,
            daily_change_percent=None,
            ytd_change_percent=None,
            created_at=item.created_at,
        )

    latest = ordered[-1]
    latest_price = _valid_price(latest.adjusted_close)
    if latest_price is None:
        return WatchlistItemResponse(
            id=item.id,
            symbol=item.symbol,
            latest_price=None,
            latest_price_date=None,
            daily_change_percent=None,
            ytd_change_percent=None,
            created_at=item.created_at,
        )

    previous = ordered[-2] if len(ordered) >= 2 else None
    first_of_year = next(
        (
            observation
            for observation in ordered
            if observation.date.year == latest.date.year
        ),
        None,
    )
    daily_change = (
        None
        if previous is None
        else _percent_change(latest_price, previous.adjusted_close)
    )
    ytd_change = (
        None
        if first_of_year is None or first_of_year.date == latest.date
        else _percent_change(latest_price, first_of_year.adjusted_close)
    )
    return WatchlistItemResponse(
        id=item.id,
        symbol=item.symbol,
        latest_price=float(latest_price),
        latest_price_date=latest.date,
        daily_change_percent=daily_change,
        ytd_change_percent=ytd_change,
        created_at=item.created_at,
    )


def _valid_price(value: object) -> Decimal | None:
    if not isinstance(value, Decimal) or not value.is_finite() or value <= 0:
        return None
    return value


def _percent_change(
    latest_price: Decimal,
    baseline_value: object,
) -> float | None:
    baseline = _valid_price(baseline_value)
    if baseline is None:
        return None
    result = ((latest_price - baseline) / baseline) * _ONE_HUNDRED
    converted = float(result)
    return converted if math.isfinite(converted) else None


def _constraint_name(error: IntegrityError) -> str | None:
    diagnostic = getattr(error.orig, "diag", None)
    return getattr(diagnostic, "constraint_name", None)
