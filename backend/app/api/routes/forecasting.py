"""Authenticated current asset outlook from the internal inference service."""

from fastapi import APIRouter, HTTPException, status
from pydantic import ValidationError
from uuid import UUID

from app.api.dependencies import CurrentUser, DatabaseSession
from app.core.instruments import USER_ASSET_SYMBOLS, get_instrument_metadata
from app.forecasting.inference import ForecastInferenceService
from app.forecasting.inference_errors import (
    ForecastDataStaleError,
    ForecastHistoryInsufficientError,
    ForecastInferenceError,
    ForecastSymbolUnsupportedError,
)
from app.forecasting.portfolio import InvalidForecastPortfolioError, PortfolioForecastService
from app.schemas.forecasting import AssetOutlookResponse, PortfolioOutlookResponse
from app.services.forecasting_response_mapper import map_asset_outlook, map_portfolio_outlook
from app.services.market_data_service import MarketDataUnavailableError
from app.services.portfolio_service import PortfolioService
from app.services.portfolio_valuation_service import PortfolioValuationError


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


@router.get(
    "/portfolios/{portfolio_id}/outlook",
    response_model=PortfolioOutlookResponse,
    responses={
        401: {"description": "Invalid or missing Bearer authentication"},
        404: {"description": "Portfolio not found"},
        409: {"description": "Portfolio allocation is unusable"},
        503: {"description": "Current portfolio forecast unavailable"},
    },
)
def get_portfolio_outlook(
    portfolio_id: UUID,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> PortfolioOutlookResponse:
    """Use only the authenticated owner's backend-resolved current baseline."""
    try:
        portfolio = PortfolioService(session).get(
            user_id=current_user.id, portfolio_id=portfolio_id,
        )
    except Exception:
        raise HTTPException(status_code=500, detail="Unable to retrieve portfolio outlook") from None
    if portfolio is None:
        raise HTTPException(status_code=404, detail="Portfolio not found") from None
    try:
        return map_portfolio_outlook(PortfolioForecastService(session).predict(portfolio))
    except (InvalidForecastPortfolioError, PortfolioValuationError, ForecastSymbolUnsupportedError):
        raise HTTPException(status_code=409, detail="Portfolio cannot provide an outlook in its current holding state") from None
    except ForecastDataStaleError:
        raise HTTPException(status_code=503, detail="Forecast unavailable because current market data is stale.") from None
    except ForecastHistoryInsufficientError:
        raise HTTPException(status_code=503, detail="Forecast unavailable because market history is insufficient.") from None
    except (ForecastInferenceError, MarketDataUnavailableError, ValidationError):
        raise HTTPException(status_code=503, detail="Forecast is currently unavailable.") from None
    except Exception:
        raise HTTPException(status_code=500, detail="Unable to retrieve portfolio outlook") from None
