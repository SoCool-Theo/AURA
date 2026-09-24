"""Caller-transaction-owned Watchlist persistence operations."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import WatchlistItem


class WatchlistRepository:
    """Persist user-scoped Watchlist items without managing transactions."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, *, user_id: UUID, symbol: str) -> WatchlistItem:
        """Add and flush one Watchlist item without committing."""
        item = WatchlistItem(user_id=user_id, symbol=symbol)
        self._session.add(item)
        self._session.flush()
        return item

    def list_for_user(self, user_id: UUID) -> list[WatchlistItem]:
        """Return one user's items in deterministic add order."""
        statement = (
            select(WatchlistItem)
            .where(WatchlistItem.user_id == user_id)
            .order_by(WatchlistItem.created_at, WatchlistItem.id)
        )
        return list(self._session.scalars(statement).all())

    def find_for_user_by_symbol(
        self,
        *,
        user_id: UUID,
        symbol: str,
    ) -> WatchlistItem | None:
        """Return only the owner's matching Watchlist item when present."""
        statement = select(WatchlistItem).where(
            WatchlistItem.user_id == user_id,
            WatchlistItem.symbol == symbol,
        )
        return self._session.scalars(statement).one_or_none()

    def delete_for_user_by_symbol(
        self,
        *,
        user_id: UUID,
        symbol: str,
    ) -> bool:
        """Delete only the owner's matching item without committing."""
        item = self.find_for_user_by_symbol(
            user_id=user_id,
            symbol=symbol,
        )
        if item is None:
            return False
        self._session.delete(item)
        self._session.flush()
        return True
