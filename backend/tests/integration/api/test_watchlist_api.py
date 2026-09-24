from collections.abc import Iterator
from datetime import UTC, date, datetime
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.orm import Session

import app.api.dependencies as dependency_module
import app.api.routes.watchlist as route_module
from app.core.config import settings
from app.core.security import create_access_token
from app.database.models import User
from app.main import app
from app.schemas.watchlist import (
    WatchlistItemResponse,
    WatchlistListResponse,
)
from app.services.watchlist_service import (
    DuplicateWatchlistItemError,
    UnsupportedWatchlistSymbolError,
    WatchlistItemNotFoundError,
)


USER_A_ID = UUID("72000000-0000-0000-0000-000000000001")
USER_B_ID = UUID("72000000-0000-0000-0000-000000000002")
ITEM_ID = UUID("73000000-0000-0000-0000-000000000001")
JWT_SECRET = "watchlist-api-test-secret-value-at-least-32-bytes"
CREATED_AT = datetime(2026, 9, 24, 2, tzinfo=UTC)


@pytest.fixture
def api_harness() -> Iterator[tuple[TestClient, MagicMock, MagicMock]]:
    session = MagicMock(spec=Session)
    session.get.side_effect = lambda model, user_id: User(id=user_id)
    session_factory = MagicMock(return_value=session)
    service = MagicMock(spec=route_module.WatchlistService)
    original_secret = settings.jwt_secret_key

    with (
        patch.object(
            dependency_module,
            "_get_session_factory",
            return_value=session_factory,
        ),
        patch.object(
            route_module,
            "WatchlistService",
            return_value=service,
        ),
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        settings.jwt_secret_key = SecretStr(JWT_SECRET)
        try:
            yield client, session, service
        finally:
            settings.jwt_secret_key = original_secret


def _headers(user_id: UUID = USER_A_ID) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user_id)}"}


def _item(symbol: str = "AAPL") -> WatchlistItemResponse:
    return WatchlistItemResponse(
        id=ITEM_ID,
        symbol=symbol,
        latest_price=126.0,
        latest_price_date=date(2026, 9, 21),
        daily_change_percent=5.0,
        ytd_change_percent=26.0,
        created_at=CREATED_AT,
    )


@pytest.mark.parametrize(
    "request_headers",
    [{}, {"X-User-ID": str(USER_A_ID)}],
    ids=["missing-auth", "x-user-id-only"],
)
def test_watchlist_requires_bearer_authentication(
    api_harness: tuple[TestClient, MagicMock, MagicMock],
    request_headers: dict[str, str],
) -> None:
    client, session, service = api_harness

    response = client.get("/api/watchlist", headers=request_headers)

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid or missing authentication credentials"
    }
    service.list_for_user.assert_not_called()
    session.commit.assert_not_called()


def test_authenticated_get_returns_only_public_watchlist_fields(
    api_harness: tuple[TestClient, MagicMock, MagicMock],
) -> None:
    client, session, service = api_harness
    service.list_for_user.return_value = WatchlistListResponse(
        items=[_item()]
    )

    response = client.get("/api/watchlist", headers=_headers())

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "id": str(ITEM_ID),
                "symbol": "AAPL",
                "latest_price": 126.0,
                "latest_price_date": "2026-09-21",
                "daily_change_percent": 5.0,
                "ytd_change_percent": 26.0,
                "created_at": CREATED_AT.isoformat().replace("+00:00", "Z"),
            }
        ]
    }
    assert "user_id" not in response.text
    service.list_for_user.assert_called_once_with(user_id=USER_A_ID)
    session.commit.assert_not_called()


def test_authenticated_post_normalizes_body_and_commits(
    api_harness: tuple[TestClient, MagicMock, MagicMock],
) -> None:
    client, session, service = api_harness
    service.add.return_value = _item()

    response = client.post(
        "/api/watchlist",
        headers=_headers(),
        json={"symbol": " aapl "},
    )

    assert response.status_code == 201
    assert response.json()["symbol"] == "AAPL"
    service.add.assert_called_once_with(user_id=USER_A_ID, symbol="AAPL")
    session.commit.assert_called_once_with()


def test_authenticated_delete_is_owner_scoped_and_commits(
    api_harness: tuple[TestClient, MagicMock, MagicMock],
) -> None:
    client, session, service = api_harness

    response = client.delete(
        "/api/watchlist/aapl",
        headers=_headers(USER_B_ID),
    )

    assert response.status_code == 204
    assert response.content == b""
    service.remove.assert_called_once_with(
        user_id=USER_B_ID,
        symbol="aapl",
    )
    session.commit.assert_called_once_with()


def test_duplicate_post_returns_sanitized_conflict(
    api_harness: tuple[TestClient, MagicMock, MagicMock],
) -> None:
    client, session, service = api_harness
    service.add.side_effect = DuplicateWatchlistItemError(
        "sensitive duplicate details"
    )

    response = client.post(
        "/api/watchlist",
        headers=_headers(),
        json={"symbol": "AAPL"},
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Watchlist item already exists"}
    assert "sensitive duplicate details" not in response.text
    session.commit.assert_not_called()
    session.rollback.assert_called_once_with()


def test_unsupported_post_returns_clean_validation_error(
    api_harness: tuple[TestClient, MagicMock, MagicMock],
) -> None:
    client, session, service = api_harness
    service.add.side_effect = UnsupportedWatchlistSymbolError

    response = client.post(
        "/api/watchlist",
        headers=_headers(),
        json={"symbol": "ASDF"},
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "Unsupported asset symbol"}
    session.commit.assert_not_called()


@pytest.mark.parametrize(
    "error",
    [WatchlistItemNotFoundError(), UnsupportedWatchlistSymbolError()],
)
def test_missing_or_unusable_delete_returns_same_sanitized_not_found(
    api_harness: tuple[TestClient, MagicMock, MagicMock],
    error: Exception,
) -> None:
    client, session, service = api_harness
    service.remove.side_effect = error

    response = client.delete(
        "/api/watchlist/AAPL",
        headers=_headers(),
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Watchlist item not found"}
    session.commit.assert_not_called()


def test_request_body_rejects_user_identity_and_unknown_fields(
    api_harness: tuple[TestClient, MagicMock, MagicMock],
) -> None:
    client, session, service = api_harness

    response = client.post(
        "/api/watchlist",
        headers=_headers(),
        json={"symbol": "AAPL", "user_id": str(USER_B_ID)},
    )

    assert response.status_code == 422
    service.add.assert_not_called()
    session.commit.assert_not_called()


def test_openapi_exposes_exact_watchlist_v1_surface() -> None:
    schema = app.openapi()

    assert set(schema["paths"]["/api/watchlist"]) == {"get", "post"}
    assert set(schema["paths"]["/api/watchlist/{symbol}"]) == {"delete"}
