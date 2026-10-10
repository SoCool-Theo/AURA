"""Caller-owned transactions for refresh state and bounded coverage queries."""

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from ..models.market_data import MarketData
from ..models.market_data_refresh import MarketDataRefreshState


class MarketDataRefreshRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self) -> MarketDataRefreshState | None:
        return self._session.get(MarketDataRefreshState, 1, populate_existing=True)

    def save(self, **values: object) -> None:
        statement = insert(MarketDataRefreshState).values(id=1, **values)
        self._session.execute(statement.on_conflict_do_update(index_elements=["id"], set_=values))
        self._session.flush()

    def latest_dates(self, symbols: tuple[str, ...]) -> dict[str, date]:
        rows = self._session.execute(select(MarketData.symbol, func.max(MarketData.date))
            .where(MarketData.symbol.in_(symbols)).group_by(MarketData.symbol)).all()
        return dict(rows)
