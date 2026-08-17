from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import app.api.dependencies as dependency_module
import app.api.routes.portfolio as route_module
from app.core.config import settings
from app.database.models import Holding, Portfolio, User
from app.main import app


OWNER_ID = UUID("62a1279e-bc8d-4c89-876d-a09250b50395")
PORTFOLIO_ID = UUID("e6518442-58cb-408f-ae3f-bf47fb00b555")
OTHER_PORTFOLIO_ID = UUID("100b15fb-9965-41e8-862e-c199cfaaee95")
REQUEST_HEADERS = {"X-User-ID": str(OWNER_ID)}
CREATED_AT = datetime(2026, 8, 17, 2, 30, tzinfo=UTC)
UPDATED_AT = datetime(2026, 8, 17, 3, 45, tzinfo=UTC)


@dataclass
class ApiHarness:
    client: TestClient
    session: MagicMock
    service: MagicMock
    session_factory: MagicMock


def _portfolio(
    *,
    portfolio_id: UUID = PORTFOLIO_ID,
    name: str = "Core Portfolio",
) -> Portfolio:
    return Portfolio(
        id=portfolio_id,
        user_id=OWNER_ID,
        name=name,
        created_at=CREATED_AT,
        updated_at=UPDATED_AT,
    )


@pytest.fixture
def api_harness() -> ApiHarness:
    session = MagicMock(spec=Session)
    session.get.return_value = User(id=OWNER_ID)
    session_factory = MagicMock(return_value=session)
    service = MagicMock(spec=route_module.PortfolioService)

    with (
        patch.object(
            dependency_module,
            "_get_session_factory",
            return_value=session_factory,
        ),
        patch.object(
            route_module,
            "PortfolioService",
            return_value=service,
        ),
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        yield ApiHarness(
            client=client,
            session=session,
            service=service,
            session_factory=session_factory,
        )


def test_phase4_app_import_keeps_database_factory_lazy_and_health_works() -> None:
    assert dependency_module._get_session_factory.cache_info().currsize == 0

    with patch.object(
        dependency_module,
        "create_database_engine",
    ) as create_engine:
        with TestClient(app) as client:
            response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "app_name": settings.app_name,
        "environment": settings.app_env,
    }
    create_engine.assert_not_called()


def test_phase4_valid_owner_header_is_resolved_for_request(
    api_harness: ApiHarness,
) -> None:
    api_harness.service.list_for_user.return_value = []

    response = api_harness.client.get(
        "/api/portfolios",
        headers=REQUEST_HEADERS,
    )

    assert response.status_code == 200
    api_harness.session.get.assert_called_once_with(User, OWNER_ID)
    api_harness.service.list_for_user.assert_called_once_with(
        user_id=OWNER_ID
    )
    api_harness.session.close.assert_called_once_with()


def test_phase4_missing_owner_header_uses_normal_validation(
    api_harness: ApiHarness,
) -> None:
    response = api_harness.client.get("/api/portfolios")

    assert response.status_code == 422
    api_harness.service.list_for_user.assert_not_called()
    api_harness.session.commit.assert_not_called()


def test_phase4_malformed_owner_header_uses_normal_validation(
    api_harness: ApiHarness,
) -> None:
    response = api_harness.client.get(
        "/api/portfolios",
        headers={"X-User-ID": "not-a-uuid"},
    )

    assert response.status_code == 422
    api_harness.service.list_for_user.assert_not_called()
    api_harness.session.commit.assert_not_called()


def test_phase4_unknown_valid_owner_returns_404_and_closes_session(
    api_harness: ApiHarness,
) -> None:
    api_harness.session.get.return_value = None

    response = api_harness.client.get(
        "/api/portfolios",
        headers=REQUEST_HEADERS,
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "User not found"}
    api_harness.service.list_for_user.assert_not_called()
    api_harness.session.commit.assert_not_called()
    api_harness.session.rollback.assert_called_once_with()
    api_harness.session.close.assert_called_once_with()


def test_phase4_invalid_portfolio_path_uses_normal_validation(
    api_harness: ApiHarness,
) -> None:
    response = api_harness.client.get(
        "/api/portfolios/not-a-uuid",
        headers=REQUEST_HEADERS,
    )

    assert response.status_code == 422
    api_harness.service.get.assert_not_called()
    api_harness.session.commit.assert_not_called()


def test_phase4_create_returns_valid_empty_portfolio_and_commits_once(
    api_harness: ApiHarness,
) -> None:
    created = _portfolio()
    api_harness.service.create.return_value = created

    response = api_harness.client.post(
        "/api/portfolios",
        headers=REQUEST_HEADERS,
        json={"name": "  Core Portfolio  "},
    )

    assert response.status_code == 201
    assert response.json() == {
        "id": str(PORTFOLIO_ID),
        "name": "Core Portfolio",
        "created_at": "2026-08-17T02:30:00Z",
        "updated_at": "2026-08-17T03:45:00Z",
        "holdings": [],
    }
    assert "user_id" not in response.json()
    api_harness.service.create.assert_called_once_with(
        user_id=OWNER_ID,
        name="Core Portfolio",
    )
    api_harness.session.commit.assert_called_once_with()
    api_harness.session.rollback.assert_not_called()
    api_harness.session.close.assert_called_once_with()


def test_phase4_create_body_validation_prevents_service_write(
    api_harness: ApiHarness,
) -> None:
    response = api_harness.client.post(
        "/api/portfolios",
        headers=REQUEST_HEADERS,
        json={"name": "   "},
    )

    assert response.status_code == 422
    api_harness.service.create.assert_not_called()
    api_harness.session.commit.assert_not_called()


def test_phase4_create_service_failure_rolls_back_without_commit(
    api_harness: ApiHarness,
) -> None:
    api_harness.service.create.side_effect = RuntimeError(
        "sensitive service failure"
    )

    response = api_harness.client.post(
        "/api/portfolios",
        headers=REQUEST_HEADERS,
        json={"name": "Core Portfolio"},
    )

    assert response.status_code == 500
    assert response.json() == {"detail": "Unable to create portfolio"}
    assert "sensitive service failure" not in response.text
    api_harness.session.commit.assert_not_called()
    api_harness.session.rollback.assert_called_once_with()
    api_harness.session.close.assert_called_once_with()


def test_phase4_create_commit_failure_rolls_back_and_hides_details(
    api_harness: ApiHarness,
) -> None:
    api_harness.service.create.return_value = _portfolio()
    api_harness.session.commit.side_effect = RuntimeError(
        "sensitive database failure"
    )

    response = api_harness.client.post(
        "/api/portfolios",
        headers=REQUEST_HEADERS,
        json={"name": "Core Portfolio"},
    )

    assert response.status_code == 500
    assert response.json() == {"detail": "Unable to create portfolio"}
    assert "sensitive database failure" not in response.text
    api_harness.session.commit.assert_called_once_with()
    api_harness.session.rollback.assert_called_once_with()
    api_harness.session.close.assert_called_once_with()


def test_phase4_list_returns_empty_ordered_collection_without_commit(
    api_harness: ApiHarness,
) -> None:
    api_harness.service.list_for_user.return_value = []

    response = api_harness.client.get(
        "/api/portfolios",
        headers=REQUEST_HEADERS,
    )

    assert response.status_code == 200
    assert response.json() == {"portfolios": []}
    api_harness.session.commit.assert_not_called()
    api_harness.session.rollback.assert_not_called()
    api_harness.session.close.assert_called_once_with()


def test_phase4_list_preserves_service_order_and_uses_summaries(
    api_harness: ApiHarness,
) -> None:
    second_id_first = _portfolio(
        portfolio_id=OTHER_PORTFOLIO_ID,
        name="Second ID First",
    )
    first_id_second = _portfolio(
        portfolio_id=PORTFOLIO_ID,
        name="First ID Second",
    )
    api_harness.service.list_for_user.return_value = [
        second_id_first,
        first_id_second,
    ]

    response = api_harness.client.get(
        "/api/portfolios",
        headers=REQUEST_HEADERS,
    )

    assert response.status_code == 200
    portfolios = response.json()["portfolios"]
    assert [portfolio["name"] for portfolio in portfolios] == [
        "Second ID First",
        "First ID Second",
    ]
    assert all("holdings" not in portfolio for portfolio in portfolios)
    assert all("user_id" not in portfolio for portfolio in portfolios)
    api_harness.session.commit.assert_not_called()


def test_phase4_list_failure_is_internal_and_rolls_back(
    api_harness: ApiHarness,
) -> None:
    api_harness.service.list_for_user.side_effect = RuntimeError(
        "sensitive read failure"
    )

    response = api_harness.client.get(
        "/api/portfolios",
        headers=REQUEST_HEADERS,
    )

    assert response.status_code == 500
    assert response.json() == {"detail": "Unable to list portfolios"}
    assert "sensitive read failure" not in response.text
    api_harness.session.commit.assert_not_called()
    api_harness.session.rollback.assert_called_once_with()


def test_phase4_get_maps_real_ordered_orm_holdings_without_commit(
    api_harness: ApiHarness,
) -> None:
    portfolio = _portfolio()
    portfolio.holdings.extend(
        [
            Holding(
                id=uuid4(),
                symbol="BETA",
                weight=Decimal("0.200000000000000000"),
                position=0,
            ),
            Holding(
                id=uuid4(),
                symbol="ALPHA",
                weight=Decimal("0.500000000000000000"),
                position=1,
            ),
            Holding(
                id=uuid4(),
                symbol="CASH",
                weight=Decimal("0.300000000000000000"),
                position=2,
            ),
        ]
    )
    api_harness.service.get.return_value = portfolio

    response = api_harness.client.get(
        f"/api/portfolios/{PORTFOLIO_ID}",
        headers=REQUEST_HEADERS,
    )

    assert response.status_code == 200
    assert response.json()["holdings"] == [
        {"symbol": "BETA", "weight": 0.2, "position": 0},
        {"symbol": "ALPHA", "weight": 0.5, "position": 1},
        {"symbol": "CASH", "weight": 0.3, "position": 2},
    ]
    assert "user_id" not in response.json()
    api_harness.service.get.assert_called_once_with(
        user_id=OWNER_ID,
        portfolio_id=PORTFOLIO_ID,
    )
    api_harness.session.commit.assert_not_called()
    api_harness.session.rollback.assert_not_called()
    api_harness.session.close.assert_called_once_with()


@pytest.mark.parametrize("resource_state", ["missing", "wrong-owner"])
def test_phase4_get_missing_and_wrong_owner_have_identical_404(
    api_harness: ApiHarness,
    resource_state: str,
) -> None:
    api_harness.service.get.return_value = None

    response = api_harness.client.get(
        f"/api/portfolios/{PORTFOLIO_ID}",
        headers=REQUEST_HEADERS,
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Portfolio not found"}
    api_harness.session.commit.assert_not_called()
    api_harness.session.rollback.assert_called_once_with()


def test_phase4_get_failure_is_not_relabelled_as_missing(
    api_harness: ApiHarness,
) -> None:
    api_harness.service.get.side_effect = RuntimeError(
        "sensitive retrieval failure"
    )

    response = api_harness.client.get(
        f"/api/portfolios/{PORTFOLIO_ID}",
        headers=REQUEST_HEADERS,
    )

    assert response.status_code == 500
    assert response.json() == {"detail": "Unable to retrieve portfolio"}
    assert "sensitive retrieval failure" not in response.text
    api_harness.session.commit.assert_not_called()
    api_harness.session.rollback.assert_called_once_with()
