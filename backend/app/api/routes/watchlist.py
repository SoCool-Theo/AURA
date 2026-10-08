"""Authenticated Aura Watchlist Backend V1 endpoints."""

from fastapi import APIRouter, HTTPException, Response, status

from app.api.dependencies import CurrentUser, DatabaseSession
from app.schemas.watchlist import (
    WatchlistCreateRequest,
    WatchlistItemResponse,
    WatchlistListResponse,
)
from app.services.watchlist_service import (
    DuplicateWatchlistItemError,
    UnsupportedWatchlistSymbolError,
    WatchlistItemNotFoundError,
    WatchlistService,
)


router = APIRouter(prefix="/watchlist", tags=["Watchlist"])


def _internal_error(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=detail,
    )


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Watchlist item not found",
    )


@router.get(
    "",
    response_model=WatchlistListResponse,
    status_code=status.HTTP_200_OK,
)
def list_watchlist(
    session: DatabaseSession,
    current_user: CurrentUser,
) -> WatchlistListResponse:
    """Return only the authenticated user's enriched Watchlist."""
    try:
        return WatchlistService(session).list_for_user(user_id=current_user.id)
    except Exception as error:
        raise _internal_error("Unable to list Watchlist") from error


@router.post(
    "",
    response_model=WatchlistItemResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_watchlist_item(
    request: WatchlistCreateRequest,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> WatchlistItemResponse:
    """Save one supported asset for the authenticated user."""
    try:
        response = WatchlistService(session).add(
            user_id=current_user.id,
            symbol=request.symbol,
        )
        session.commit()
        return response
    except DuplicateWatchlistItemError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Watchlist item already exists",
        ) from error
    except UnsupportedWatchlistSymbolError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Unsupported asset symbol",
        ) from error
    except Exception as error:
        raise _internal_error("Unable to add Watchlist item") from error


@router.delete(
    "/{symbol}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def delete_watchlist_item(
    symbol: str,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> Response:
    """Remove one owned Watchlist item without affecting other resources."""
    try:
        WatchlistService(session).remove(
            user_id=current_user.id,
            symbol=symbol,
        )
        session.commit()
    except (
        UnsupportedWatchlistSymbolError,
        WatchlistItemNotFoundError,
    ) as error:
        raise _not_found() from error
    except Exception as error:
        raise _internal_error("Unable to delete Watchlist item") from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
