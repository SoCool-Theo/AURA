"""Authenticated current asset outlook from the internal inference service."""

from fastapi import APIRouter, HTTPException, status
from pydantic import ValidationError

from app.api.dependencies import CurrentUser, DatabaseSession
from app.core.instruments import USER_ASSET_SYMBOLS, get_instrument_metadata
from app.forecasting.inference import ForecastInferenceService
from app.forecasting.inference_errors import (
    ForecastDataStaleError,
    ForecastHistoryInsufficientError,
    ForecastInferenceError,
    ForecastSymbolUnsupportedError,
)
from app.schemas.forecasting import AssetOutlookResponse
from app.services.forecasting_response_mapper import map_asset_outlook


router = APIRouter(prefix="/forecasting", tags=["Forecasting"])


@router.get(
    "/assets/{symbol}/outlook",
    response_model=AssetOutlookResponse,
    responses={
        401: {"description": "Invalid or missing Bearer authentication"},
        404: {"description": "Unsupported asset symbol"},
        503: {"description": "Current forecast unavailable"},
    },
)
def get_asset_outlook(
    symbol: str,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> AssetOutlookResponse:
    """Return the current outlook; authentication does not require holdings."""
    try:
        normalized = get_instrument_metadata(symbol).provider_symbol
        if normalized not in USER_ASSET_SYMBOLS:
            raise ValueError()
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unsupported asset symbol",
        ) from None
    try:
        forecast = ForecastInferenceService(session).predict(normalized)
        return map_asset_outlook(forecast)
    except ForecastSymbolUnsupportedError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unsupported asset symbol",
        ) from None
    except ForecastDataStaleError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Forecast unavailable because current market data is stale.",
        ) from None
    except ForecastHistoryInsufficientError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Forecast unavailable because market history is insufficient.",
        ) from None
    except (ForecastInferenceError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Forecast is currently unavailable.",
        ) from None
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve asset outlook",
        ) from None
