"""Describe actual persisted inventory using the worker's existing freshness rule."""

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from ..core.instruments import MARKET_UPDATE_SYMBOLS, get_instrument_metadata
from ..database.repositories.admin_market_data_repository import AdminMarketDataRepository
from ..schemas.admin_market_data import (
    AdminMarketDataQuery,
    AdminMarketInstrument,
    AdminMarketInventoryResponse,
    AdminMarketObservation,
    AdminMarketObservationsResponse,
)
from .market_data_refresh_service import observation_is_current


class AdminMarketDataService:
    def __init__(self, session: Session) -> None:
        self._repository = AdminMarketDataRepository(session)

    def inventory(self) -> AdminMarketInventoryResponse:
        now = datetime.now(UTC)
        rows = self._repository.inventory()
        stored = {row["symbol"]: row for row in rows}
        unexpected = sorted(set(stored) - set(MARKET_UPDATE_SYMBOLS))
        instruments = []
        for symbol in [*MARKET_UPDATE_SYMBOLS, *unexpected]:
            row = stored.get(symbol)
            required = symbol in MARKET_UPDATE_SYMBOLS
            metadata = get_instrument_metadata(symbol) if required else None
            latest = row["latest_price_date"] if row else None
            age = (now.date() - latest).days if latest is not None else None
            freshness = (
                "unknown" if not required else "missing" if latest is None
                else "current" if observation_is_current(symbol, latest, now.date()) else "stale"
            )
            instruments.append(AdminMarketInstrument(
                symbol=symbol, required_for_refresh=required,
                kind=metadata.instrument_type.value if metadata else "unknown",
                quote_currency=metadata.quote_currency if metadata else None,
                base_currency=metadata.base_currency if metadata else None,
                total_records=row["total_records"] if row else 0,
                first_price_date=row["first_price_date"] if row else None,
                latest_price_date=latest,
                latest_adjusted_close=row["latest_adjusted_close"] if row else None,
                latest_volume=row["latest_volume"] if row else None,
                latest_source=row["latest_source"] if row else None,
                age_days=age if age is not None and age >= 0 else None,
                freshness=freshness,
            ))
        missing = sum(item.freshness == "missing" for item in instruments)
        return AdminMarketInventoryResponse(
            checked_at=now, total_records=sum(item.total_records for item in instruments),
            stored_symbols=len(stored), required_symbols=len(MARKET_UPDATE_SYMBOLS),
            present_required_symbols=len(MARKET_UPDATE_SYMBOLS) - missing,
            current_required_symbols=sum(item.freshness == "current" for item in instruments),
            stale_required_symbols=sum(item.freshness == "stale" for item in instruments),
            missing_required_symbols=missing, unexpected_symbols=len(unexpected),
            instruments=instruments,
        )

    def observations(self, query: AdminMarketDataQuery) -> AdminMarketObservationsResponse:
        validated = AdminMarketDataQuery.model_validate(query.model_dump())
        rows, total = self._repository.observations(**validated.model_dump())
        return AdminMarketObservationsResponse(
            items=[AdminMarketObservation(**{key: row[key] for key in (
                "symbol", "date", "adjusted_close", "volume", "source",
            )}) for row in rows],
            total=total, limit=validated.limit, offset=validated.offset,
        )
