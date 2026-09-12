"""Core portfolio creation and retrieval endpoints."""

from collections.abc import Sequence
from uuid import UUID

from fastapi import APIRouter, HTTPException, Response, status

from app.api.dependencies import CurrentUser, DatabaseSession
from app.database.models import Holding, Portfolio
from app.schemas.portfolio import (
    PortfolioCreateRequest,
    PortfolioDuplicateRequest,
    PortfolioHoldingResponse,
    PortfolioHoldingValuationResponse,
    PortfolioHoldingsReplaceRequest,
    PortfolioListResponse,
    PortfolioResponse,
    PortfolioSummaryResponse,
    PortfolioUpdateRequest,
    PortfolioValuationFxResponse,
    PortfolioValuationResponse,
)
from app.services.market_data_service import MarketDataUnavailableError
from app.services.portfolio_service import PortfolioService
from app.services.portfolio_valuation_service import (
    InvalidHoldingModeError,
    InvalidPortfolioValueError,
    PortfolioDisplayCurrency,
    PortfolioValuationResult,
    PortfolioValuationService,
    UnsupportedHoldingInstrumentError,
)


router = APIRouter(prefix="/portfolios", tags=["Portfolios"])


def _to_portfolio_response(
    portfolio: Portfolio,
    *,
    holdings: Sequence[Holding] | None = None,
) -> PortfolioResponse:
    mapped_holdings = portfolio.holdings if holdings is None else holdings
    return PortfolioResponse(
        id=portfolio.id,
        name=portfolio.name,
        created_at=portfolio.created_at,
        updated_at=portfolio.updated_at,
        holdings=[
            PortfolioHoldingResponse.model_validate(holding)
            for holding in mapped_holdings
        ],
    )


def _to_portfolio_valuation_response(
    portfolio_id: UUID,
    valuation: PortfolioValuationResult,
) -> PortfolioValuationResponse:
    fx = (
        None
        if valuation.fx_context is None
        else PortfolioValuationFxResponse(
            pair=valuation.fx_context.pair,
            provider_symbol=valuation.fx_context.provider_symbol,
            rate=valuation.fx_context.rate,
            as_of=valuation.fx_context.as_of,
        )
    )
    return PortfolioValuationResponse(
        portfolio_id=portfolio_id,
        valuation_currency=valuation.display_currency.value,
        requested_date=valuation.requested_date,
        oldest_price_as_of=valuation.oldest_price_as_of,
        newest_price_as_of=valuation.newest_price_as_of,
        total_current_value_usd=valuation.total_current_value_usd,
        total_current_value=valuation.total_current_value,
        fx=fx,
        holdings=[
            PortfolioHoldingValuationResponse(
                id=holding.holding_id,
                symbol=holding.symbol,
                invested_amount=holding.invested_amount,
                invested_currency=holding.invested_currency,
                shares=holding.shares,
                purchase_date=holding.purchase_date,
                position=holding.position,
                asset_price=holding.asset_price,
                asset_quote_currency=holding.asset_quote_currency,
                price_as_of=holding.price_as_of,
                current_value_usd=holding.current_value_usd,
                current_value=holding.current_value,
                current_allocation=holding.current_allocation,
            )
            for holding in valuation.holdings
        ],
    )


def _to_portfolio_summary(
    portfolio: Portfolio,
) -> PortfolioSummaryResponse:
    return PortfolioSummaryResponse(
        id=portfolio.id,
        name=portfolio.name,
        created_at=portfolio.created_at,
        updated_at=portfolio.updated_at,
    )


def _internal_error(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=detail,
    )


def _portfolio_not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Portfolio not found",
    )


@router.post(
    "",
    response_model=PortfolioResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_portfolio(
    request: PortfolioCreateRequest,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> PortfolioResponse:
    try:
        portfolio = PortfolioService(session).create(
            user_id=current_user.id,
            name=request.name,
        )
        response = _to_portfolio_response(portfolio, holdings=())
        session.commit()
    except Exception as error:
        raise _internal_error("Unable to create portfolio") from error
    return response


@router.get(
    "",
    response_model=PortfolioListResponse,
    status_code=status.HTTP_200_OK,
)
def list_portfolios(
    session: DatabaseSession,
    current_user: CurrentUser,
) -> PortfolioListResponse:
    try:
        portfolios = PortfolioService(session).list_for_user(
            user_id=current_user.id
        )
        return PortfolioListResponse(
            portfolios=[
                _to_portfolio_summary(portfolio)
                for portfolio in portfolios
            ]
        )
    except Exception as error:
        raise _internal_error("Unable to list portfolios") from error


@router.get(
    "/{portfolio_id}",
    response_model=PortfolioResponse,
    status_code=status.HTTP_200_OK,
)
def get_portfolio(
    portfolio_id: UUID,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> PortfolioResponse:
    try:
        portfolio = PortfolioService(session).get(
            user_id=current_user.id,
            portfolio_id=portfolio_id,
        )
    except Exception as error:
        raise _internal_error("Unable to retrieve portfolio") from error

    if portfolio is None:
        raise _portfolio_not_found()

    try:
        return _to_portfolio_response(portfolio)
    except Exception as error:
        raise _internal_error("Unable to retrieve portfolio") from error


@router.get(
    "/{portfolio_id}/valuation",
    response_model=PortfolioValuationResponse,
    status_code=status.HTTP_200_OK,
)
def get_portfolio_valuation(
    portfolio_id: UUID,
    session: DatabaseSession,
    current_user: CurrentUser,
    currency: PortfolioDisplayCurrency = PortfolioDisplayCurrency.USD,
) -> PortfolioValuationResponse:
    try:
        portfolio = PortfolioService(session).get(
            user_id=current_user.id,
            portfolio_id=portfolio_id,
        )
    except Exception as error:
        raise _internal_error("Unable to value portfolio") from error

    if portfolio is None:
        raise _portfolio_not_found()

    try:
        valuation = PortfolioValuationService(session).value(
            portfolio.holdings,
            display_currency=currency,
        )
        return _to_portfolio_valuation_response(portfolio.id, valuation)
    except MarketDataUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Required market data is unavailable",
        ) from error
    except (
        InvalidHoldingModeError,
        InvalidPortfolioValueError,
        UnsupportedHoldingInstrumentError,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Portfolio cannot be valued in its current holding state",
        ) from error
    except Exception as error:
        raise _internal_error("Unable to value portfolio") from error


@router.patch(
    "/{portfolio_id}",
    response_model=PortfolioResponse,
    status_code=status.HTTP_200_OK,
)
def rename_portfolio(
    portfolio_id: UUID,
    request: PortfolioUpdateRequest,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> PortfolioResponse:
    try:
        portfolio = PortfolioService(session).rename(
            user_id=current_user.id,
            portfolio_id=portfolio_id,
            name=request.name,
        )
    except Exception as error:
        raise _internal_error("Unable to rename portfolio") from error

    if portfolio is None:
        raise _portfolio_not_found()

    try:
        response = _to_portfolio_response(portfolio)
        session.commit()
    except Exception as error:
        raise _internal_error("Unable to rename portfolio") from error
    return response


@router.put(
    "/{portfolio_id}/holdings",
    response_model=PortfolioResponse,
    status_code=status.HTTP_200_OK,
)
def replace_portfolio_holdings(
    portfolio_id: UUID,
    request: PortfolioHoldingsReplaceRequest,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> PortfolioResponse:
    holdings = [
        (
            holding.symbol,
            holding.invested_amount,
            holding.invested_currency,
            holding.shares,
            holding.purchase_date,
        )
        for holding in request.holdings
    ]
    try:
        portfolio = PortfolioService(session).replace_holdings(
            user_id=current_user.id,
            portfolio_id=portfolio_id,
            holdings=holdings,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error
    except Exception as error:
        raise _internal_error("Unable to replace portfolio holdings") from error

    if portfolio is None:
        raise _portfolio_not_found()

    try:
        response = _to_portfolio_response(portfolio)
        session.commit()
    except Exception as error:
        raise _internal_error("Unable to replace portfolio holdings") from error
    return response


@router.post(
    "/{portfolio_id}/duplicate",
    response_model=PortfolioResponse,
    status_code=status.HTTP_201_CREATED,
)
def duplicate_portfolio(
    portfolio_id: UUID,
    request: PortfolioDuplicateRequest,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> PortfolioResponse:
    try:
        portfolio = PortfolioService(session).duplicate(
            user_id=current_user.id,
            portfolio_id=portfolio_id,
            name=request.name,
        )
    except Exception as error:
        raise _internal_error("Unable to duplicate portfolio") from error

    if portfolio is None:
        raise _portfolio_not_found()

    try:
        response = _to_portfolio_response(portfolio)
        session.commit()
    except Exception as error:
        raise _internal_error("Unable to duplicate portfolio") from error
    return response


@router.delete(
    "/{portfolio_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def delete_portfolio(
    portfolio_id: UUID,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> Response:
    try:
        deleted = PortfolioService(session).delete(
            user_id=current_user.id,
            portfolio_id=portfolio_id,
        )
    except Exception as error:
        raise _internal_error("Unable to delete portfolio") from error

    if not deleted:
        raise _portfolio_not_found()

    try:
        session.commit()
    except Exception as error:
        raise _internal_error("Unable to delete portfolio") from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
