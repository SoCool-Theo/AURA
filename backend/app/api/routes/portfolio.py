"""Core portfolio creation and retrieval endpoints."""

from collections.abc import Sequence
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import DatabaseSession, TemporaryOwnerId
from app.database.models import Holding, Portfolio
from app.schemas.portfolio import (
    PortfolioCreateRequest,
    PortfolioHoldingResponse,
    PortfolioListResponse,
    PortfolioResponse,
    PortfolioSummaryResponse,
)
from app.services.portfolio_service import PortfolioService


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
            PortfolioHoldingResponse(
                symbol=holding.symbol,
                weight=float(holding.weight),
                position=holding.position,
            )
            for holding in mapped_holdings
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


@router.post(
    "",
    response_model=PortfolioResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_portfolio(
    request: PortfolioCreateRequest,
    session: DatabaseSession,
    user_id: TemporaryOwnerId,
) -> PortfolioResponse:
    try:
        portfolio = PortfolioService(session).create(
            user_id=user_id,
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
    user_id: TemporaryOwnerId,
) -> PortfolioListResponse:
    try:
        portfolios = PortfolioService(session).list_for_user(user_id=user_id)
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
    user_id: TemporaryOwnerId,
) -> PortfolioResponse:
    try:
        portfolio = PortfolioService(session).get(
            user_id=user_id,
            portfolio_id=portfolio_id,
        )
    except Exception as error:
        raise _internal_error("Unable to retrieve portfolio") from error

    if portfolio is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found",
        )

    try:
        return _to_portfolio_response(portfolio)
    except Exception as error:
        raise _internal_error("Unable to retrieve portfolio") from error
