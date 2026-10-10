"""Bounded price browsing and per-instrument inventory; no writes or providers."""

from collections.abc import Mapping
from datetime import date
from typing import Any

from sqlalchemy import and_, func, select, true
from sqlalchemy.orm import Session

from ..models.market_data import MarketData


class AdminMarketDataRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def inventory(self) -> list[Mapping[str, Any]]:
        counts = select(
            MarketData.symbol,
            func.count().label("total_records"),
            func.min(MarketData.date).label("first_price_date"),
            func.max(MarketData.date).label("latest_price_date"),
        ).group_by(MarketData.symbol).cte("admin_market_inventory")
        # The composite primary key guarantees one latest observation per symbol.
        statement = select(
            *counts.c,
            MarketData.adjusted_close.label("latest_adjusted_close"),
            MarketData.volume.label("latest_volume"),
            MarketData.source.label("latest_source"),
        ).select_from(counts.join(MarketData, and_(
            MarketData.symbol == counts.c.symbol,
            MarketData.date == counts.c.latest_price_date,
        ))).order_by(counts.c.symbol)
        return self._session.execute(statement).mappings().all()

    def observations(
        self, *, limit: int, offset: int, symbol: str | None = None,
        date_from: date | None = None, date_to: date | None = None,
    ) -> tuple[list[Mapping[str, Any]], int]:
        conditions = []
        if symbol is not None:
            conditions.append(MarketData.symbol == symbol)
        if date_from is not None:
            conditions.append(MarketData.date >= date_from)
        if date_to is not None:
            conditions.append(MarketData.date <= date_to)
        matching = select(
            MarketData.symbol, MarketData.date, MarketData.adjusted_close,
            MarketData.volume, MarketData.source,
        ).where(*conditions).cte("matching_admin_prices")
        page = select(matching).order_by(
            matching.c.date.desc(), matching.c.symbol.asc(),
        ).limit(limit).offset(offset).cte("admin_prices_page")
        total = select(func.count().label("total")).select_from(matching).cte("admin_prices_total")
        statement = select(*page.c, total.c.total).select_from(
            total.outerjoin(page, true()),
        ).order_by(page.c.date.desc(), page.c.symbol.asc())
        rows = self._session.execute(statement).mappings().all()
        return [row for row in rows if row["symbol"] is not None], rows[0]["total"]
