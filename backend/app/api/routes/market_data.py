"""Authenticated observation-only market-data health; no update trigger."""

from fastapi import APIRouter, HTTPException

from app.api.dependencies import CurrentUser, DatabaseSession
from app.schemas.market_data_status import MarketDataStatusResponse
from app.services.market_data_status_service import MarketDataStatusService

router = APIRouter(prefix="/market-data", tags=["Market data"])


@router.get("/status", response_model=MarketDataStatusResponse)
def market_data_status(session: DatabaseSession, current_user: CurrentUser) -> MarketDataStatusResponse:
    try:
        return MarketDataStatusService(session).get()
    except Exception as error:
        raise HTTPException(status_code=503, detail="Market-data status is temporarily unavailable") from error
