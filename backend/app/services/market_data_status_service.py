"""Describe persisted observations and worker liveness without initiating writes."""

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from ..core.config import settings
from ..core.instruments import MARKET_UPDATE_SYMBOLS
from ..database.repositories.market_data_refresh_repository import MarketDataRefreshRepository
from ..schemas.market_data_status import MarketDataStatusResponse, MarketObservationStatus
from .market_data_refresh_service import latest_schedule_slot, observation_is_current


class MarketDataStatusService:
    def __init__(self, session: Session) -> None:
        self.repository = MarketDataRefreshRepository(session)

    def get(self, *, now: datetime | None = None) -> MarketDataStatusResponse:
        now = (now or datetime.now(UTC)).astimezone(UTC)
        state = self.repository.get()
        dates = self.repository.latest_dates(MARKET_UPDATE_SYMBOLS)
        observations = []
        for symbol in MARKET_UPDATE_SYMBOLS:
            observed = dates.get(symbol)
            age = (now.date() - observed).days if observed else None
            observations.append(MarketObservationStatus(symbol=symbol, kind="fx" if symbol == "THB=X" else "asset",
                latest_price_date=observed, age_days=age if age is not None and age >= 0 else None,
                is_current=observation_is_current(symbol, observed, now.date())))
        heartbeat = state.worker_heartbeat_at if state else None
        worker_status = "unknown" if heartbeat is None else "offline"
        if heartbeat and state.worker_running and 0 <= (now - heartbeat).total_seconds() <= 180:
            worker_status = "online"
        return MarketDataStatusResponse(checked_at=now,
            update_time_utc=settings.market_data_update_time_utc.strftime("%H:%M"),
            next_scheduled_at=latest_schedule_slot(now) + timedelta(days=1),
            worker_status=worker_status, worker_last_seen_at=heartbeat,
            last_run_status=state.status if state else "never",
            last_attempt_at=state.last_attempt_at if state else None,
            last_finished_at=state.last_finished_at if state else None,
            last_complete_at=state.last_complete_at if state else None,
            attempt_count=state.attempt_count if state else 0,
            stored_count=state.stored_count if state else 0,
            updated_symbols=state.updated_symbols if state else [],
            failed_symbols=state.failed_symbols if state else [],
            error_code=state.error_code if state else None,
            data_status="missing" if any(item.latest_price_date is None for item in observations)
                else "current" if all(item.is_current for item in observations) else "stale",
            observations=observations)
