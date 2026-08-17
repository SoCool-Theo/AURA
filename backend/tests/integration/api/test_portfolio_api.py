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


def test_phase5_rename_returns_full_response_and_commits_once(
    api_harness: ApiHarness,
) -> None:
    renamed = _portfolio(name="Renamed Portfolio")
    api_harness.service.rename.return_value = renamed

    response = api_harness.client.patch(
        f"/api/portfolios/{PORTFOLIO_ID}",
        headers=REQUEST_HEADERS,
        json={"name": "  Renamed Portfolio  "},
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": str(PORTFOLIO_ID),
        "name": "Renamed Portfolio",
        "created_at": "2026-08-17T02:30:00Z",
        "updated_at": "2026-08-17T03:45:00Z",
        "holdings": [],
    }
    assert "user_id" not in response.json()
    api_harness.service.rename.assert_called_once_with(
        user_id=OWNER_ID,
        portfolio_id=PORTFOLIO_ID,
        name="Renamed Portfolio",
    )
    api_harness.session.commit.assert_called_once_with()
    api_harness.session.rollback.assert_not_called()
    api_harness.session.close.assert_called_once_with()


@pytest.mark.parametrize("resource_state", ["missing", "wrong-owner"])
def test_phase5_rename_missing_and_wrong_owner_have_identical_404(
    api_harness: ApiHarness,
    resource_state: str,
) -> None:
    api_harness.service.rename.return_value = None

    response = api_harness.client.patch(
        f"/api/portfolios/{PORTFOLIO_ID}",
        headers=REQUEST_HEADERS,
        json={"name": "Renamed Portfolio"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Portfolio not found"}
    api_harness.session.commit.assert_not_called()
    api_harness.session.rollback.assert_called_once_with()


@pytest.mark.parametrize("name", ["", "   "])
def test_phase5_rename_invalid_name_uses_schema_validation(
    api_harness: ApiHarness,
    name: str,
) -> None:
    response = api_harness.client.patch(
        f"/api/portfolios/{PORTFOLIO_ID}",
        headers=REQUEST_HEADERS,
        json={"name": name},
    )

    assert response.status_code == 422
    api_harness.service.rename.assert_not_called()
    api_harness.session.commit.assert_not_called()


def test_phase5_rename_failure_rolls_back_without_commit(
    api_harness: ApiHarness,
) -> None:
    api_harness.service.rename.side_effect = RuntimeError(
        "sensitive rename failure"
    )

    response = api_harness.client.patch(
        f"/api/portfolios/{PORTFOLIO_ID}",
        headers=REQUEST_HEADERS,
        json={"name": "Renamed Portfolio"},
    )

    assert response.status_code == 500
    assert response.json() == {"detail": "Unable to rename portfolio"}
    assert "sensitive rename failure" not in response.text
    api_harness.session.commit.assert_not_called()
    api_harness.session.rollback.assert_called_once_with()


def test_phase5_replace_holdings_uses_validated_order_and_commits_once(
    api_harness: ApiHarness,
) -> None:
    updated = _portfolio()
    updated.holdings.extend(
        [
            Holding(
                id=uuid4(),
                symbol="BETA",
                weight=Decimal("0.2"),
                position=0,
            ),
            Holding(
                id=uuid4(),
                symbol="ALPHA",
                weight=Decimal("0.5"),
                position=1,
            ),
            Holding(
                id=uuid4(),
                symbol="CASH",
                weight=Decimal("0.3"),
                position=2,
            ),
        ]
    )
    api_harness.service.replace_holdings.return_value = updated

    response = api_harness.client.put(
        f"/api/portfolios/{PORTFOLIO_ID}/holdings",
        headers=REQUEST_HEADERS,
        json={
            "holdings": [
                {"symbol": " beta ", "weight": 0.2},
                {"symbol": "alpha", "weight": 0.5},
                {"symbol": " cash ", "weight": 0.3},
            ]
        },
    )

    assert response.status_code == 200
    assert response.json()["holdings"] == [
        {"symbol": "BETA", "weight": 0.2, "position": 0},
        {"symbol": "ALPHA", "weight": 0.5, "position": 1},
        {"symbol": "CASH", "weight": 0.3, "position": 2},
    ]
    assert "user_id" not in response.json()
    api_harness.service.replace_holdings.assert_called_once_with(
        user_id=OWNER_ID,
        portfolio_id=PORTFOLIO_ID,
        holdings=[("BETA", 0.2), ("ALPHA", 0.5), ("CASH", 0.3)],
    )
    api_harness.session.commit.assert_called_once_with()
    api_harness.session.rollback.assert_not_called()


@pytest.mark.parametrize(
    "holdings",
    [
        [
            {"symbol": "AAPL", "weight": 0.5},
            {"symbol": " aapl ", "weight": 0.5},
        ],
        [
            {"symbol": "AAPL", "weight": 0.5},
            {"symbol": "MSFT", "weight": 0.499_999_998},
        ],
        [
            {"symbol": "AAPL", "weight": 0.5},
            {"symbol": "MSFT", "weight": 0.500_000_002},
        ],
        [],
    ],
    ids=["duplicate-symbol", "total-below", "total-above", "empty"],
)
def test_phase5_replace_holdings_invalid_body_stays_422(
    api_harness: ApiHarness,
    holdings: list[dict[str, object]],
) -> None:
    response = api_harness.client.put(
        f"/api/portfolios/{PORTFOLIO_ID}/holdings",
        headers=REQUEST_HEADERS,
        json={"holdings": holdings},
    )

    assert response.status_code == 422
    api_harness.service.replace_holdings.assert_not_called()
    api_harness.session.commit.assert_not_called()


@pytest.mark.parametrize("resource_state", ["missing", "wrong-owner"])
def test_phase5_replace_holdings_missing_and_wrong_owner_have_identical_404(
    api_harness: ApiHarness,
    resource_state: str,
) -> None:
    api_harness.service.replace_holdings.return_value = None

    response = api_harness.client.put(
        f"/api/portfolios/{PORTFOLIO_ID}/holdings",
        headers=REQUEST_HEADERS,
        json={"holdings": [{"symbol": "AAPL", "weight": 1.0}]},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Portfolio not found"}
    api_harness.session.commit.assert_not_called()
    api_harness.session.rollback.assert_called_once_with()


def test_phase5_replace_holdings_expected_defensive_error_is_400(
    api_harness: ApiHarness,
) -> None:
    message = "holding weights must sum to 1.0 within an absolute tolerance"
    api_harness.service.replace_holdings.side_effect = ValueError(message)

    response = api_harness.client.put(
        f"/api/portfolios/{PORTFOLIO_ID}/holdings",
        headers=REQUEST_HEADERS,
        json={"holdings": [{"symbol": "AAPL", "weight": 1.0}]},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": message}
    api_harness.session.commit.assert_not_called()
    api_harness.session.rollback.assert_called_once_with()


def test_phase5_replace_holdings_unexpected_failure_remains_500(
    api_harness: ApiHarness,
) -> None:
    api_harness.service.replace_holdings.side_effect = RuntimeError(
        "sensitive replacement failure"
    )

    response = api_harness.client.put(
        f"/api/portfolios/{PORTFOLIO_ID}/holdings",
        headers=REQUEST_HEADERS,
        json={"holdings": [{"symbol": "AAPL", "weight": 1.0}]},
    )

    assert response.status_code == 500
    assert response.json() == {
        "detail": "Unable to replace portfolio holdings"
    }
    assert "sensitive replacement failure" not in response.text
    api_harness.session.commit.assert_not_called()
    api_harness.session.rollback.assert_called_once_with()


def test_phase5_duplicate_returns_service_result_and_commits_once(
    api_harness: ApiHarness,
) -> None:
    duplicate_id = uuid4()
    duplicate = _portfolio(
        portfolio_id=duplicate_id,
        name="Core Portfolio Copy",
    )
    duplicate.holdings.extend(
        [
            Holding(
                id=uuid4(),
                symbol="FIRST",
                weight=Decimal("0.6"),
                position=0,
            ),
            Holding(
                id=uuid4(),
                symbol="SECOND",
                weight=Decimal("0.4"),
                position=1,
            ),
        ]
    )
    api_harness.service.duplicate.return_value = duplicate

    response = api_harness.client.post(
        f"/api/portfolios/{PORTFOLIO_ID}/duplicate",
        headers=REQUEST_HEADERS,
        json={"name": "  Core Portfolio Copy  "},
    )

    assert response.status_code == 201
    assert response.json()["id"] == str(duplicate_id)
    assert response.json()["name"] == "Core Portfolio Copy"
    assert response.json()["holdings"] == [
        {"symbol": "FIRST", "weight": 0.6, "position": 0},
        {"symbol": "SECOND", "weight": 0.4, "position": 1},
    ]
    assert "user_id" not in response.json()
    api_harness.service.duplicate.assert_called_once_with(
        user_id=OWNER_ID,
        portfolio_id=PORTFOLIO_ID,
        name="Core Portfolio Copy",
    )
    api_harness.session.commit.assert_called_once_with()
    api_harness.session.rollback.assert_not_called()


@pytest.mark.parametrize("resource_state", ["missing", "wrong-owner"])
def test_phase5_duplicate_missing_and_wrong_owner_have_identical_404(
    api_harness: ApiHarness,
    resource_state: str,
) -> None:
    api_harness.service.duplicate.return_value = None

    response = api_harness.client.post(
        f"/api/portfolios/{PORTFOLIO_ID}/duplicate",
        headers=REQUEST_HEADERS,
        json={"name": "Copy"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Portfolio not found"}
    api_harness.session.commit.assert_not_called()
    api_harness.session.rollback.assert_called_once_with()


def test_phase5_duplicate_invalid_name_uses_schema_validation(
    api_harness: ApiHarness,
) -> None:
    response = api_harness.client.post(
        f"/api/portfolios/{PORTFOLIO_ID}/duplicate",
        headers=REQUEST_HEADERS,
        json={"name": "   "},
    )

    assert response.status_code == 422
    api_harness.service.duplicate.assert_not_called()
    api_harness.session.commit.assert_not_called()


def test_phase5_duplicate_copy_failure_rolls_back_without_commit(
    api_harness: ApiHarness,
) -> None:
    api_harness.service.duplicate.side_effect = RuntimeError(
        "sensitive copy failure"
    )

    response = api_harness.client.post(
        f"/api/portfolios/{PORTFOLIO_ID}/duplicate",
        headers=REQUEST_HEADERS,
        json={"name": "Copy"},
    )

    assert response.status_code == 500
    assert response.json() == {"detail": "Unable to duplicate portfolio"}
    assert "sensitive copy failure" not in response.text
    api_harness.session.commit.assert_not_called()
    api_harness.session.rollback.assert_called_once_with()


def test_phase5_delete_success_returns_empty_204_and_commits_once(
    api_harness: ApiHarness,
) -> None:
    api_harness.service.delete.return_value = True

    response = api_harness.client.delete(
        f"/api/portfolios/{PORTFOLIO_ID}",
        headers=REQUEST_HEADERS,
    )

    assert response.status_code == 204
    assert response.content == b""
    api_harness.service.delete.assert_called_once_with(
        user_id=OWNER_ID,
        portfolio_id=PORTFOLIO_ID,
    )
    api_harness.session.commit.assert_called_once_with()
    api_harness.session.rollback.assert_not_called()
    api_harness.session.close.assert_called_once_with()


@pytest.mark.parametrize("resource_state", ["missing", "wrong-owner"])
def test_phase5_delete_missing_and_wrong_owner_have_identical_404(
    api_harness: ApiHarness,
    resource_state: str,
) -> None:
    api_harness.service.delete.return_value = False

    response = api_harness.client.delete(
        f"/api/portfolios/{PORTFOLIO_ID}",
        headers=REQUEST_HEADERS,
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Portfolio not found"}
    api_harness.session.commit.assert_not_called()
    api_harness.session.rollback.assert_called_once_with()


def test_phase5_delete_malformed_uuid_uses_normal_validation(
    api_harness: ApiHarness,
) -> None:
    response = api_harness.client.delete(
        "/api/portfolios/not-a-uuid",
        headers=REQUEST_HEADERS,
    )

    assert response.status_code == 422
    api_harness.service.delete.assert_not_called()
    api_harness.session.commit.assert_not_called()


def test_phase5_delete_failure_rolls_back_without_commit(
    api_harness: ApiHarness,
) -> None:
    api_harness.service.delete.side_effect = RuntimeError(
        "sensitive delete failure"
    )

    response = api_harness.client.delete(
        f"/api/portfolios/{PORTFOLIO_ID}",
        headers=REQUEST_HEADERS,
    )

    assert response.status_code == 500
    assert response.json() == {"detail": "Unable to delete portfolio"}
    assert "sensitive delete failure" not in response.text
    api_harness.session.commit.assert_not_called()
    api_harness.session.rollback.assert_called_once_with()
