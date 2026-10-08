"""Additive authenticated experimental weekly outlooks; 30-day routes unchanged."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path
from pydantic import ValidationError

from app.api.dependencies import CurrentUser, DatabaseSession
from app.core.instruments import USER_ASSET_SYMBOLS, get_instrument_metadata
from app.forecasting.inference_errors import (
    ForecastDataStaleError, ForecastHistoryInsufficientError,
    ForecastInferenceError, ForecastSymbolUnsupportedError,
)
from app.forecasting.portfolio import InvalidForecastPortfolioError
from app.forecasting.weekly_inference import WeeklyForecastInferenceService
from app.forecasting.weekly_portfolio import WeeklyPortfolioForecastService
from app.schemas.weekly_forecasting import WeeklyAssetOutlookResponse, WeeklyPortfolioOutlookResponse
from app.services.market_data_service import MarketDataUnavailableError
from app.services.portfolio_service import PortfolioService
from app.services.portfolio_valuation_service import PortfolioValuationError
from app.services.weekly_forecasting_response_mapper import map_weekly_asset_outlook, map_weekly_portfolio_outlook


router = APIRouter(prefix="/forecasting", tags=["Forecasting"])
HorizonPath = Annotated[int, Path(description="Experimental calendar-day horizon: 7, 14 or 21", ge=7, le=21)]


def _validate_horizon(horizon_days):
    if horizon_days not in (7, 14, 21):
        raise HTTPException(status_code=422, detail="Weekly horizon must be 7, 14 or 21 calendar days")


def _unavailable(error):
    if isinstance(error, ForecastDataStaleError):
        message = "Forecast unavailable because current market data is stale."
    elif isinstance(error, ForecastHistoryInsufficientError):
        message = "Forecast unavailable because market history is insufficient."
    else:
        message = "Forecast is currently unavailable."
    return HTTPException(status_code=503, detail=message)


@router.get("/assets/{symbol}/horizons/{horizon_days}/outlook", response_model=WeeklyAssetOutlookResponse,
    responses={401: {"description": "Bearer authentication required"},
               404: {"description": "Unsupported asset"}, 503: {"description": "Weekly outlook unavailable"}})
def get_weekly_asset_outlook(symbol: str, horizon_days: HorizonPath,
                             current_user: CurrentUser, session: DatabaseSession) -> WeeklyAssetOutlookResponse:
    _validate_horizon(horizon_days)
    try:
        normalized = get_instrument_metadata(symbol).provider_symbol
        if normalized not in USER_ASSET_SYMBOLS:
            raise ValueError()
    except (TypeError, ValueError):
        raise HTTPException(status_code=404, detail="Unsupported asset symbol") from None
    try:
        forecast = WeeklyForecastInferenceService(session).predict(normalized, horizon_days=horizon_days)
        if forecast.symbol != normalized or forecast.horizon_days != horizon_days:
            raise ForecastInferenceError("weekly response identity mismatch")
        return map_weekly_asset_outlook(forecast)
    except ForecastSymbolUnsupportedError:
        raise HTTPException(status_code=404, detail="Unsupported asset symbol") from None
    except (ForecastInferenceError, ValidationError) as error:
        raise _unavailable(error) from None
    except Exception:
        raise HTTPException(status_code=500, detail="Unable to retrieve asset outlook") from None


@router.get("/portfolios/{portfolio_id}/horizons/{horizon_days}/outlook", response_model=WeeklyPortfolioOutlookResponse,
    responses={401: {"description": "Bearer authentication required"},
               404: {"description": "Portfolio not found"}, 409: {"description": "Unusable allocation"},
               503: {"description": "Weekly outlook unavailable"}})
def get_weekly_portfolio_outlook(portfolio_id: UUID, horizon_days: HorizonPath,
                                 current_user: CurrentUser, session: DatabaseSession) -> WeeklyPortfolioOutlookResponse:
    _validate_horizon(horizon_days)
    try:
        portfolio = PortfolioService(session).get(user_id=current_user.id, portfolio_id=portfolio_id)
    except Exception:
        raise HTTPException(status_code=500, detail="Unable to retrieve portfolio outlook") from None
    if portfolio is None:
        raise HTTPException(status_code=404, detail="Portfolio not found") from None
    try:
        forecast = WeeklyPortfolioForecastService(session).predict(portfolio, horizon_days=horizon_days)
        if forecast.portfolio_id != portfolio_id or forecast.horizon_days != horizon_days:
            raise ForecastInferenceError("weekly response identity mismatch")
        return map_weekly_portfolio_outlook(forecast)
    except (InvalidForecastPortfolioError, PortfolioValuationError, ForecastSymbolUnsupportedError):
        raise HTTPException(status_code=409, detail="Portfolio cannot provide an outlook in its current holding state") from None
    except (ForecastInferenceError, MarketDataUnavailableError, ValidationError) as error:
        raise _unavailable(error) from None
    except Exception:
        raise HTTPException(status_code=500, detail="Unable to retrieve portfolio outlook") from None
