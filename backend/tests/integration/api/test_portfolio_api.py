from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.orm import Session

import app.api.dependencies as dependency_module
import app.api.routes.portfolio as route_module
from app.core.config import settings
from app.core.security import create_access_token
from app.database.models import Holding, Portfolio, PortfolioType, User
from app.main import app
from app.services.market_data_service import MarketDataUnavailableError
from app.services.portfolio_planned_allocation_service import (
    InvalidPlannedPortfolioError,
    PlannedAllocationHolding,
    PlannedPortfolioAllocation,
)
from app.services.portfolio_planned_preview_service import (
    PlannedEstimateStatus,
    PlannedHoldingPreview,
    PlannedPortfolioPreview,
)
from app.services.portfolio_valuation_service import (
    HoldingValuationResult,
    InvalidHoldingModeError,
    PortfolioDisplayCurrency,
    PortfolioFxContext,
    PortfolioValuationResult,
)


OWNER_ID = UUID("62a1279e-bc8d-4c89-876d-a09250b50395")
PORTFOLIO_ID = UUID("e6518442-58cb-408f-ae3f-bf47fb00b555")
OTHER_PORTFOLIO_ID = UUID("100b15fb-9965-41e8-862e-c199cfaaee95")
JWT_SECRET = "phase-6-portfolio-api-test-secret-value"
REQUEST_HEADERS: dict[str, str] = {}
CREATED_AT = datetime(2026, 8, 17, 2, 30, tzinfo=UTC)
UPDATED_AT = datetime(2026, 8, 17, 3, 45, tzinfo=UTC)


@dataclass
class ApiHarness:
    client: TestClient
    session: MagicMock
    service: MagicMock
    valuation_service: MagicMock
    planned_allocation_service: MagicMock
    planned_preview_service: MagicMock
    session_factory: MagicMock


@pytest.fixture(autouse=True)
def bearer_request_headers() -> Iterator[None]:
    with patch.object(
        settings,
        "jwt_secret_key",
        SecretStr(JWT_SECRET),
    ):
        REQUEST_HEADERS["Authorization"] = (
            f"Bearer {create_access_token(OWNER_ID)}"
        )
        try:
            yield
        finally:
            REQUEST_HEADERS.clear()


def _portfolio(
    *,
    portfolio_id: UUID = PORTFOLIO_ID,
    name: str = "Core Portfolio",
    portfolio_type: PortfolioType | None = None,
    plan_currency: str | None = None,
) -> Portfolio:
    portfolio = Portfolio(
        id=portfolio_id,
        user_id=OWNER_ID,
        name=name,
        plan_currency=plan_currency,
        created_at=CREATED_AT,
        updated_at=UPDATED_AT,
    )
    if portfolio_type is not None:
        portfolio.portfolio_type = portfolio_type.value
    return portfolio


def _real_holding(
    symbol: str = "AAPL",
    *,
    position: int = 0,
    invested_currency: str = "USD",
) -> Holding:
    return Holding(
        id=UUID(f"42000000-0000-0000-0000-{position + 1:012d}"),
        portfolio_id=PORTFOLIO_ID,
        symbol=symbol,
        weight=None,
        invested_amount=Decimal("1500.000000000000"),
        invested_currency=invested_currency,
        shares=Decimal("10.250000000000"),
        purchase_date=date(2026, 1, 10),
        position=position,
    )


def _real_request_holding(
    symbol: str = "AAPL",
    *,
    invested_currency: str | None = "USD",
) -> dict[str, object]:
    result: dict[str, object] = {
        "symbol": symbol,
        "invested_amount": "1500.000000000000",
        "shares": "10.250000000000",
        "purchase_date": "2026-01-10",
    }
    if invested_currency is not None:
        result["invested_currency"] = invested_currency
    return result


def _planned_holding(
    symbol: str = "AAPL",
    *,
    position: int = 0,
    proposed_amount: str = "4000.000000000000",
) -> Holding:
    return Holding(
        id=UUID(f"43000000-0000-0000-0000-{position + 1:012d}"),
        portfolio_id=PORTFOLIO_ID,
        symbol=symbol,
        proposed_amount=Decimal(proposed_amount),
        position=position,
    )


def _valuation_result(
    *,
    currency: PortfolioDisplayCurrency = PortfolioDisplayCurrency.USD,
) -> PortfolioValuationResult:
    fx_context = None
    total_current_value = Decimal("250.000000000000")
    current_value = Decimal("250.000000000000")
    if currency is PortfolioDisplayCurrency.THB:
        fx_context = PortfolioFxContext(
            pair="USD/THB",
            provider_symbol="THB=X",
            rate=Decimal("32.500000000000"),
            as_of=date(2026, 9, 11),
        )
        total_current_value = Decimal("8125.000000000000000000000000")
        current_value = total_current_value
    return PortfolioValuationResult(
        display_currency=currency,
        requested_date=date(2026, 9, 12),
        oldest_price_as_of=date(2026, 9, 10),
        newest_price_as_of=date(2026, 9, 11),
        total_current_value_usd=Decimal("250.000000000000"),
        total_current_value=total_current_value,
        fx_context=fx_context,
        holdings=(
            HoldingValuationResult(
                holding_id=UUID("42000000-0000-0000-0000-000000000001"),
                symbol="AAPL",
                invested_amount=Decimal("1500.000000000000"),
                invested_currency="USD",
                shares=Decimal("2.000000000000"),
                purchase_date=date(2026, 1, 10),
                position=0,
                asset_price=Decimal("125.000000000000"),
                asset_quote_currency="USD",
                price_as_of=date(2026, 9, 11),
                current_value_usd=Decimal("250.000000000000"),
                current_value=current_value,
                current_allocation=Decimal("1"),
            ),
        ),
    )


@pytest.fixture
def api_harness() -> ApiHarness:
    session = MagicMock(spec=Session)
    session.get.return_value = User(id=OWNER_ID)
    session_factory = MagicMock(return_value=session)
    service = MagicMock(spec=route_module.PortfolioService)
    valuation_service = MagicMock(
        spec=route_module.PortfolioValuationService
    )
    planned_allocation_service = MagicMock(
        spec=route_module.PortfolioPlannedAllocationService
    )
    planned_preview_service = MagicMock(
        spec=route_module.PortfolioPlannedPreviewService
    )

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
        patch.object(
            route_module,
            "PortfolioValuationService",
            return_value=valuation_service,
        ),
        patch.object(
            route_module,
            "PortfolioPlannedAllocationService",
            return_value=planned_allocation_service,
        ),
        patch.object(
            route_module,
            "PortfolioPlannedPreviewService",
            return_value=planned_preview_service,
        ),
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        yield ApiHarness(
            client=client,
            session=session,
            service=service,
            valuation_service=valuation_service,
            planned_allocation_service=planned_allocation_service,
            planned_preview_service=planned_preview_service,
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


def test_valid_bearer_identity_wins_without_requiring_x_user_id(
    api_harness: ApiHarness,
) -> None:
    api_harness.service.list_for_user.return_value = []

    response = api_harness.client.get(
        "/api/portfolios",
        headers={
            **REQUEST_HEADERS,
            "X-User-ID": str(OTHER_PORTFOLIO_ID),
        },
    )

    assert response.status_code == 200
    api_harness.session.get.assert_called_once_with(User, OWNER_ID)
    api_harness.service.list_for_user.assert_called_once_with(
        user_id=OWNER_ID
    )
    api_harness.session.close.assert_called_once_with()


@pytest.mark.parametrize(
    "headers",
    [{}, {"X-User-ID": str(OWNER_ID)}],
)
def test_missing_bearer_and_x_user_id_only_are_unauthorized(
    api_harness: ApiHarness,
    headers: dict[str, str],
) -> None:
    response = api_harness.client.get("/api/portfolios", headers=headers)

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    api_harness.service.list_for_user.assert_not_called()
    api_harness.session.commit.assert_not_called()


def test_malformed_bearer_token_is_unauthorized(
    api_harness: ApiHarness,
) -> None:
    response = api_harness.client.get(
        "/api/portfolios",
        headers={"Authorization": "Bearer not-a-jwt"},
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    api_harness.service.list_for_user.assert_not_called()
    api_harness.session.commit.assert_not_called()


def test_valid_token_for_unknown_user_returns_unauthorized_and_closes_session(
    api_harness: ApiHarness,
) -> None:
    api_harness.session.get.return_value = None

    response = api_harness.client.get(
        "/api/portfolios",
        headers=REQUEST_HEADERS,
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid or missing authentication credentials"
    }
    assert response.headers["www-authenticate"] == "Bearer"
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
        "portfolio_type": "CURRENT",
        "plan_currency": None,
        "source_plan_id": None,
        "created_at": "2026-08-17T02:30:00Z",
        "updated_at": "2026-08-17T03:45:00Z",
        "holdings": [],
    }
    assert "user_id" not in response.json()
    api_harness.service.create.assert_called_once_with(
        user_id=OWNER_ID,
        name="Core Portfolio",
        portfolio_type="CURRENT",
        plan_currency=None,
    )
    api_harness.session.commit.assert_called_once_with()
    api_harness.session.rollback.assert_not_called()
    api_harness.session.close.assert_called_once_with()


def test_step3_create_planned_portfolio_normalizes_type_and_currency(
    api_harness: ApiHarness,
) -> None:
    created = _portfolio(
        name="Future Plan",
        portfolio_type=PortfolioType.PLANNED,
        plan_currency="THB",
    )
    api_harness.service.create.return_value = created

    response = api_harness.client.post(
        "/api/portfolios",
        headers=REQUEST_HEADERS,
        json={
            "name": "  Future Plan  ",
            "portfolio_type": "planned",
            "plan_currency": " thb ",
        },
    )

    assert response.status_code == 201
    assert response.json() == {
        "id": str(PORTFOLIO_ID),
        "name": "Future Plan",
        "portfolio_type": "PLANNED",
        "plan_currency": "THB",
        "source_plan_id": None,
        "created_at": "2026-08-17T02:30:00Z",
        "updated_at": "2026-08-17T03:45:00Z",
        "holdings": [],
    }
    api_harness.service.create.assert_called_once_with(
        user_id=OWNER_ID,
        name="Future Plan",
        portfolio_type="PLANNED",
        plan_currency="THB",
    )
    api_harness.session.commit.assert_called_once_with()


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "Plan", "portfolio_type": "PLANNED"},
        {
            "name": "Current",
            "portfolio_type": "CURRENT",
            "plan_currency": "USD",
        },
        {"name": "Legacy", "portfolio_type": "LEGACY"},
    ],
)
def test_step3_create_rejects_invalid_or_legacy_type_context(
    api_harness: ApiHarness,
    payload: dict[str, object],
) -> None:
    response = api_harness.client.post(
        "/api/portfolios",
        headers=REQUEST_HEADERS,
        json=payload,
    )

    assert response.status_code == 422
    api_harness.service.create.assert_not_called()
    api_harness.session.commit.assert_not_called()


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


def test_phase6_get_maps_legacy_ordered_orm_holdings_without_commit(
    api_harness: ApiHarness,
) -> None:
    portfolio = _portfolio()
    holding_ids = [uuid4(), uuid4(), uuid4()]
    portfolio.holdings.extend(
        [
            Holding(
                id=holding_ids[0],
                symbol="BETA",
                weight=Decimal("0.200000000000000000"),
                position=0,
            ),
            Holding(
                id=holding_ids[1],
                symbol="ALPHA",
                weight=Decimal("0.500000000000000000"),
                position=1,
            ),
            Holding(
                id=holding_ids[2],
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
        {
            "id": str(holding_ids[0]),
            "symbol": "BETA",
            "weight": 0.2,
            "invested_amount": None,
            "invested_currency": None,
            "shares": None,
            "purchase_date": None,
            "position": 0,
        },
        {
            "id": str(holding_ids[1]),
            "symbol": "ALPHA",
            "weight": 0.5,
            "invested_amount": None,
            "invested_currency": None,
            "shares": None,
            "purchase_date": None,
            "position": 1,
        },
        {
            "id": str(holding_ids[2]),
            "symbol": "CASH",
            "weight": 0.3,
            "invested_amount": None,
            "invested_currency": None,
            "shares": None,
            "purchase_date": None,
            "position": 2,
        },
    ]
    assert "user_id" not in response.json()
    api_harness.service.get.assert_called_once_with(
        user_id=OWNER_ID,
        portfolio_id=PORTFOLIO_ID,
    )
    api_harness.session.commit.assert_not_called()
    api_harness.session.rollback.assert_not_called()
    api_harness.session.close.assert_called_once_with()


def test_phase6_get_maps_real_holding_facts_without_float_coercion(
    api_harness: ApiHarness,
) -> None:
    portfolio = _portfolio()
    portfolio.holdings.extend(
        [
            _real_holding("MSFT", position=0, invested_currency="THB"),
            _real_holding("AAPL", position=1),
        ]
    )
    api_harness.service.get.return_value = portfolio

    response = api_harness.client.get(
        f"/api/portfolios/{PORTFOLIO_ID}",
        headers=REQUEST_HEADERS,
    )

    assert response.status_code == 200
    assert response.json()["holdings"] == [
        {
            "id": "42000000-0000-0000-0000-000000000001",
            "symbol": "MSFT",
            "weight": None,
            "invested_amount": "1500.000000000000",
            "invested_currency": "THB",
            "shares": "10.250000000000",
            "purchase_date": "2026-01-10",
            "position": 0,
        },
        {
            "id": "42000000-0000-0000-0000-000000000002",
            "symbol": "AAPL",
            "weight": None,
            "invested_amount": "1500.000000000000",
            "invested_currency": "USD",
            "shares": "10.250000000000",
            "purchase_date": "2026-01-10",
            "position": 1,
        },
    ]
    api_harness.session.commit.assert_not_called()


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


def test_step3_planned_allocation_returns_backend_derived_weights_read_only(
    api_harness: ApiHarness,
) -> None:
    portfolio = _portfolio(
        portfolio_type=PortfolioType.PLANNED,
        plan_currency="USD",
    )
    holdings = [
        _planned_holding("AAPL", position=0, proposed_amount="4000"),
        _planned_holding("BND", position=1, proposed_amount="1000"),
    ]
    portfolio.holdings.extend(holdings)
    api_harness.service.get.return_value = portfolio
    api_harness.planned_allocation_service.resolve.return_value = (
        PlannedPortfolioAllocation(
            portfolio_id=PORTFOLIO_ID,
            plan_currency="USD",
            total_proposed_amount=Decimal("5000"),
            holdings=(
                PlannedAllocationHolding(
                    holding_id=holdings[0].id,
                    symbol="AAPL",
                    proposed_amount=Decimal("4000"),
                    target_allocation=Decimal("0.800000000000000000"),
                    position=0,
                ),
                PlannedAllocationHolding(
                    holding_id=holdings[1].id,
                    symbol="BND",
                    proposed_amount=Decimal("1000"),
                    target_allocation=Decimal("0.200000000000000000"),
                    position=1,
                ),
            ),
        )
    )

    response = api_harness.client.get(
        f"/api/portfolios/{PORTFOLIO_ID}/planned-allocation",
        headers=REQUEST_HEADERS,
    )

    assert response.status_code == 200
    assert response.json() == {
        "portfolio_id": str(PORTFOLIO_ID),
        "portfolio_type": "PLANNED",
        "plan_currency": "USD",
        "total_proposed_amount": "5000",
        "holdings": [
            {
                "id": str(holdings[0].id),
                "symbol": "AAPL",
                "proposed_amount": "4000",
                "target_allocation": "0.800000000000000000",
                "position": 0,
            },
            {
                "id": str(holdings[1].id),
                "symbol": "BND",
                "proposed_amount": "1000",
                "target_allocation": "0.200000000000000000",
                "position": 1,
            },
        ],
    }
    api_harness.service.get.assert_called_once_with(
        user_id=OWNER_ID,
        portfolio_id=PORTFOLIO_ID,
    )
    api_harness.planned_allocation_service.resolve.assert_called_once_with(
        portfolio
    )
    api_harness.valuation_service.value.assert_not_called()
    api_harness.session.commit.assert_not_called()


@pytest.mark.parametrize("resource_state", ["missing", "wrong-owner"])
def test_step3_planned_allocation_preserves_owner_scoped_404(
    api_harness: ApiHarness,
    resource_state: str,
) -> None:
    api_harness.service.get.return_value = None

    response = api_harness.client.get(
        f"/api/portfolios/{PORTFOLIO_ID}/planned-allocation",
        headers=REQUEST_HEADERS,
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Portfolio not found"}
    api_harness.planned_allocation_service.resolve.assert_not_called()
    api_harness.session.commit.assert_not_called()


def test_step3_planned_allocation_invalid_mode_is_sanitized_conflict(
    api_harness: ApiHarness,
) -> None:
    portfolio = _portfolio(portfolio_type=PortfolioType.CURRENT)
    api_harness.service.get.return_value = portfolio
    api_harness.planned_allocation_service.resolve.side_effect = (
        InvalidPlannedPortfolioError("sensitive mixed holding detail")
    )

    response = api_harness.client.get(
        f"/api/portfolios/{PORTFOLIO_ID}/planned-allocation",
        headers=REQUEST_HEADERS,
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Portfolio cannot provide a planned allocation"
    }
    assert "sensitive mixed holding detail" not in response.text
    api_harness.session.commit.assert_not_called()


def test_step3_planned_allocation_unexpected_failure_is_sanitized_500(
    api_harness: ApiHarness,
) -> None:
    api_harness.service.get.return_value = _portfolio(
        portfolio_type=PortfolioType.PLANNED,
        plan_currency="USD",
    )
    api_harness.planned_allocation_service.resolve.side_effect = RuntimeError(
        "sensitive resolver failure"
    )

    response = api_harness.client.get(
        f"/api/portfolios/{PORTFOLIO_ID}/planned-allocation",
        headers=REQUEST_HEADERS,
    )

    assert response.status_code == 500
    assert response.json() == {
        "detail": "Unable to resolve planned allocation"
    }
    assert "sensitive resolver failure" not in response.text
    api_harness.session.commit.assert_not_called()


def test_step4_planned_preview_maps_optional_estimates_without_commit(
    api_harness: ApiHarness,
) -> None:
    portfolio = _portfolio(
        portfolio_type=PortfolioType.PLANNED,
        plan_currency="THB",
    )
    holdings = [
        _planned_holding("AAPL", position=0, proposed_amount="6500"),
        _planned_holding("BND", position=1, proposed_amount="3250"),
    ]
    portfolio.holdings.extend(holdings)
    api_harness.service.get.return_value = portfolio
    api_harness.planned_preview_service.preview.return_value = (
        PlannedPortfolioPreview(
            portfolio_id=PORTFOLIO_ID,
            plan_currency="THB",
            requested_date=date(2026, 9, 12),
            total_proposed_amount=Decimal("9750"),
            fx_context=PortfolioFxContext(
                pair="USD/THB",
                provider_symbol="THB=X",
                rate=Decimal("32.5"),
                as_of=date(2026, 9, 11),
            ),
            holdings=(
                PlannedHoldingPreview(
                    holding_id=holdings[0].id,
                    symbol="AAPL",
                    proposed_amount=Decimal("6500"),
                    target_allocation=Decimal("0.666666666666666666"),
                    position=0,
                    estimate_status=PlannedEstimateStatus.AVAILABLE,
                    estimated_shares=Decimal("1"),
                    asset_price=Decimal("200"),
                    asset_quote_currency="USD",
                    price_as_of=date(2026, 9, 11),
                ),
                PlannedHoldingPreview(
                    holding_id=holdings[1].id,
                    symbol="BND",
                    proposed_amount=Decimal("3250"),
                    target_allocation=Decimal("0.333333333333333334"),
                    position=1,
                    estimate_status=PlannedEstimateStatus.PRICE_UNAVAILABLE,
                    estimated_shares=None,
                    asset_price=None,
                    asset_quote_currency=None,
                    price_as_of=None,
                ),
            ),
        )
    )

    with patch.object(
        route_module,
        "_current_utc_date",
        return_value=date(2026, 9, 12),
    ):
        response = api_harness.client.get(
            f"/api/portfolios/{PORTFOLIO_ID}/planned-preview",
            headers=REQUEST_HEADERS,
        )

    assert response.status_code == 200
    body = response.json()
    assert body["portfolio_type"] == "PLANNED"
    assert body["plan_currency"] == "THB"
    assert body["requested_date"] == "2026-09-12"
    assert body["total_proposed_amount"] == "9750"
    assert body["fx"] == {
        "pair": "USD/THB",
        "provider_symbol": "THB=X",
        "rate": "32.5",
        "as_of": "2026-09-11",
    }
    assert body["holdings"][0]["estimated_shares"] == "1"
    assert body["holdings"][0]["estimate_status"] == "AVAILABLE"
    assert body["holdings"][1]["estimated_shares"] is None
    assert body["holdings"][1]["estimate_status"] == "PRICE_UNAVAILABLE"
    api_harness.planned_preview_service.preview.assert_called_once_with(
        portfolio=portfolio,
        requested_date=date(2026, 9, 12),
    )
    api_harness.valuation_service.value.assert_not_called()
    api_harness.session.commit.assert_not_called()


@pytest.mark.parametrize("resource_state", ["missing", "wrong-owner"])
def test_step4_planned_preview_preserves_owner_scoped_404(
    api_harness: ApiHarness,
    resource_state: str,
) -> None:
    api_harness.service.get.return_value = None

    response = api_harness.client.get(
        f"/api/portfolios/{PORTFOLIO_ID}/planned-preview",
        headers=REQUEST_HEADERS,
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Portfolio not found"}
    api_harness.planned_preview_service.preview.assert_not_called()
    api_harness.session.commit.assert_not_called()


def test_step4_planned_preview_invalid_mode_is_sanitized_conflict(
    api_harness: ApiHarness,
) -> None:
    api_harness.service.get.return_value = _portfolio(
        portfolio_type=PortfolioType.CURRENT
    )
    api_harness.planned_preview_service.preview.side_effect = (
        InvalidPlannedPortfolioError("sensitive invalid plan detail")
    )

    response = api_harness.client.get(
        f"/api/portfolios/{PORTFOLIO_ID}/planned-preview",
        headers=REQUEST_HEADERS,
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Portfolio cannot provide a planned preview"
    }
    assert "sensitive invalid plan detail" not in response.text
    api_harness.session.commit.assert_not_called()


def test_step4_planned_preview_unexpected_failure_is_sanitized_500(
    api_harness: ApiHarness,
) -> None:
    api_harness.service.get.return_value = _portfolio(
        portfolio_type=PortfolioType.PLANNED,
        plan_currency="USD",
    )
    api_harness.planned_preview_service.preview.side_effect = RuntimeError(
        "sensitive preview failure"
    )

    response = api_harness.client.get(
        f"/api/portfolios/{PORTFOLIO_ID}/planned-preview",
        headers=REQUEST_HEADERS,
    )

    assert response.status_code == 500
    assert response.json() == {
        "detail": "Unable to preview planned portfolio"
    }
    assert "sensitive preview failure" not in response.text
    api_harness.session.commit.assert_not_called()


def test_phase6_valuation_requires_bearer_authentication(
    api_harness: ApiHarness,
) -> None:
    response = api_harness.client.get(
        f"/api/portfolios/{PORTFOLIO_ID}/valuation"
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    api_harness.service.get.assert_not_called()
    api_harness.valuation_service.value.assert_not_called()


def test_phase6_valuation_defaults_to_usd_and_delegates_all_math(
    api_harness: ApiHarness,
) -> None:
    portfolio = _portfolio()
    portfolio.holdings.extend(
        [_real_holding("AAPL", position=0)]
    )
    original_facts = [
        (
            holding.id,
            holding.symbol,
            holding.invested_amount,
            holding.invested_currency,
            holding.shares,
            holding.purchase_date,
            holding.weight,
            holding.position,
        )
        for holding in portfolio.holdings
    ]
    valuation = _valuation_result()
    api_harness.service.get.return_value = portfolio
    api_harness.valuation_service.value.return_value = valuation

    response = api_harness.client.get(
        f"/api/portfolios/{PORTFOLIO_ID}/valuation",
        headers=REQUEST_HEADERS,
    )

    assert response.status_code == 200
    assert response.json() == {
        "portfolio_id": str(PORTFOLIO_ID),
        "valuation_currency": "USD",
        "requested_date": "2026-09-12",
        "oldest_price_as_of": "2026-09-10",
        "newest_price_as_of": "2026-09-11",
        "total_current_value_usd": "250.000000000000",
        "total_current_value": "250.000000000000",
        "fx": None,
        "holdings": [
            {
                "id": "42000000-0000-0000-0000-000000000001",
                "symbol": "AAPL",
                "invested_amount": "1500.000000000000",
                "invested_currency": "USD",
                "shares": "2.000000000000",
                "purchase_date": "2026-01-10",
                "position": 0,
                "asset_price": "125.000000000000",
                "asset_quote_currency": "USD",
                "price_as_of": "2026-09-11",
                "current_value_usd": "250.000000000000",
                "current_value": "250.000000000000",
                "current_allocation": "1",
            }
        ],
    }
    api_harness.service.get.assert_called_once_with(
        user_id=OWNER_ID,
        portfolio_id=PORTFOLIO_ID,
    )
    api_harness.valuation_service.value.assert_called_once_with(
        portfolio.holdings,
        display_currency=PortfolioDisplayCurrency.USD,
    )
    assert original_facts == [
        (
            holding.id,
            holding.symbol,
            holding.invested_amount,
            holding.invested_currency,
            holding.shares,
            holding.purchase_date,
            holding.weight,
            holding.position,
        )
        for holding in portfolio.holdings
    ]
    api_harness.session.commit.assert_not_called()
    api_harness.session.rollback.assert_not_called()


def test_phase6_valuation_accepts_normalized_thb_and_maps_fx_once(
    api_harness: ApiHarness,
) -> None:
    portfolio = _portfolio()
    portfolio.holdings.append(_real_holding())
    api_harness.service.get.return_value = portfolio
    api_harness.valuation_service.value.return_value = _valuation_result(
        currency=PortfolioDisplayCurrency.THB
    )

    response = api_harness.client.get(
        f"/api/portfolios/{PORTFOLIO_ID}/valuation?currency=thb",
        headers=REQUEST_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["valuation_currency"] == "THB"
    assert body["total_current_value"] == (
        "8125.000000000000000000000000"
    )
    assert body["fx"] == {
        "pair": "USD/THB",
        "provider_symbol": "THB=X",
        "rate": "32.500000000000",
        "as_of": "2026-09-11",
    }
    assert body["holdings"][0]["current_allocation"] == "1"
    api_harness.valuation_service.value.assert_called_once_with(
        portfolio.holdings,
        display_currency=PortfolioDisplayCurrency.THB,
    )
    api_harness.session.commit.assert_not_called()


def test_phase6_thb_unavailability_does_not_block_usd_valuation(
    api_harness: ApiHarness,
) -> None:
    portfolio = _portfolio()
    portfolio.holdings.append(_real_holding())
    api_harness.service.get.return_value = portfolio

    def value_by_currency(
        holdings: list[Holding],
        *,
        display_currency: PortfolioDisplayCurrency,
    ) -> PortfolioValuationResult:
        assert holdings is portfolio.holdings
        if display_currency is PortfolioDisplayCurrency.THB:
            raise MarketDataUnavailableError("THB=X is unavailable")
        return _valuation_result()

    api_harness.valuation_service.value.side_effect = value_by_currency

    thb_response = api_harness.client.get(
        f"/api/portfolios/{PORTFOLIO_ID}/valuation?currency=THB",
        headers=REQUEST_HEADERS,
    )
    usd_response = api_harness.client.get(
        f"/api/portfolios/{PORTFOLIO_ID}/valuation",
        headers=REQUEST_HEADERS,
    )

    assert thb_response.status_code == 503
    assert usd_response.status_code == 200
    assert usd_response.json()["valuation_currency"] == "USD"
    api_harness.session.commit.assert_not_called()


@pytest.mark.parametrize("resource_state", ["missing", "wrong-owner"])
def test_phase6_valuation_missing_and_wrong_owner_are_same_404(
    api_harness: ApiHarness,
    resource_state: str,
) -> None:
    api_harness.service.get.return_value = None

    response = api_harness.client.get(
        f"/api/portfolios/{PORTFOLIO_ID}/valuation",
        headers=REQUEST_HEADERS,
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Portfolio not found"}
    api_harness.valuation_service.value.assert_not_called()
    api_harness.session.commit.assert_not_called()


@pytest.mark.parametrize(
    "message",
    [
        "legacy weight-based holdings cannot be valued",
        "mixed legacy and real holdings cannot be valued",
        "incomplete real holding AAPL: missing shares",
    ],
)
def test_phase6_valuation_invalid_holding_states_are_conflicts(
    api_harness: ApiHarness,
    message: str,
) -> None:
    portfolio = _portfolio()
    portfolio.holdings.append(_real_holding())
    api_harness.service.get.return_value = portfolio
    api_harness.valuation_service.value.side_effect = InvalidHoldingModeError(
        message
    )

    response = api_harness.client.get(
        f"/api/portfolios/{PORTFOLIO_ID}/valuation",
        headers=REQUEST_HEADERS,
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Portfolio cannot be valued in its current holding state"
    }
    assert message not in response.text
    api_harness.session.commit.assert_not_called()


@pytest.mark.parametrize(
    "message",
    ["latest market data is unavailable for AAPL", "FX data is stale"],
)
def test_phase6_valuation_missing_or_stale_market_data_is_503(
    api_harness: ApiHarness,
    message: str,
) -> None:
    portfolio = _portfolio()
    portfolio.holdings.append(_real_holding())
    api_harness.service.get.return_value = portfolio
    api_harness.valuation_service.value.side_effect = (
        MarketDataUnavailableError(message)
    )

    response = api_harness.client.get(
        f"/api/portfolios/{PORTFOLIO_ID}/valuation?currency=THB",
        headers=REQUEST_HEADERS,
    )

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Required market data is unavailable"
    }
    assert message not in response.text
    api_harness.session.commit.assert_not_called()


def test_phase6_valuation_rejects_unsupported_currency_before_service(
    api_harness: ApiHarness,
) -> None:
    response = api_harness.client.get(
        f"/api/portfolios/{PORTFOLIO_ID}/valuation?currency=EUR",
        headers=REQUEST_HEADERS,
    )

    assert response.status_code == 422
    api_harness.service.get.assert_not_called()
    api_harness.valuation_service.value.assert_not_called()
    api_harness.session.commit.assert_not_called()


def test_phase6_valuation_unexpected_failure_is_sanitized_500(
    api_harness: ApiHarness,
) -> None:
    portfolio = _portfolio()
    portfolio.holdings.append(_real_holding())
    api_harness.service.get.return_value = portfolio
    api_harness.valuation_service.value.side_effect = RuntimeError(
        "provider credentials leaked"
    )

    response = api_harness.client.get(
        f"/api/portfolios/{PORTFOLIO_ID}/valuation",
        headers=REQUEST_HEADERS,
    )

    assert response.status_code == 500
    assert response.json() == {"detail": "Unable to value portfolio"}
    assert "provider credentials leaked" not in response.text
    api_harness.session.commit.assert_not_called()


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
        "portfolio_type": "CURRENT",
        "plan_currency": None,
        "source_plan_id": None,
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


def test_phase6_replace_holdings_uses_real_facts_order_and_commits_once(
    api_harness: ApiHarness,
) -> None:
    updated = _portfolio()
    updated.holdings.extend(
        [
            _real_holding("MSFT", position=0, invested_currency="THB"),
            _real_holding("AAPL", position=1),
        ]
    )
    api_harness.service.replace_holdings.return_value = updated

    response = api_harness.client.put(
        f"/api/portfolios/{PORTFOLIO_ID}/holdings",
        headers=REQUEST_HEADERS,
        json={
            "holdings": [
                _real_request_holding(
                    " msft ", invested_currency=" thb "
                ),
                _real_request_holding("aapl", invested_currency=None),
            ]
        },
    )

    assert response.status_code == 200
    assert response.json()["holdings"] == [
        {
            "id": "42000000-0000-0000-0000-000000000001",
            "symbol": "MSFT",
            "weight": None,
            "invested_amount": "1500.000000000000",
            "invested_currency": "THB",
            "shares": "10.250000000000",
            "purchase_date": "2026-01-10",
            "position": 0,
        },
        {
            "id": "42000000-0000-0000-0000-000000000002",
            "symbol": "AAPL",
            "weight": None,
            "invested_amount": "1500.000000000000",
            "invested_currency": "USD",
            "shares": "10.250000000000",
            "purchase_date": "2026-01-10",
            "position": 1,
        },
    ]
    assert "user_id" not in response.json()
    api_harness.service.replace_holdings.assert_called_once_with(
        user_id=OWNER_ID,
        portfolio_id=PORTFOLIO_ID,
        holdings=[
            (
                "MSFT",
                Decimal("1500.000000000000"),
                "THB",
                Decimal("10.250000000000"),
                date(2026, 1, 10),
            ),
            (
                "AAPL",
                Decimal("1500.000000000000"),
                "USD",
                Decimal("10.250000000000"),
                date(2026, 1, 10),
            ),
        ],
    )
    api_harness.session.commit.assert_called_once_with()
    api_harness.session.rollback.assert_not_called()


def test_replace_holdings_accepts_quantity_only_contract(
    api_harness: ApiHarness,
) -> None:
    updated = _portfolio(portfolio_type=PortfolioType.CURRENT)
    updated.holdings.append(
        Holding(
            id=UUID("42000000-0000-0000-0000-000000000001"),
            portfolio_id=PORTFOLIO_ID,
            symbol="AAPL",
            weight=None,
            invested_amount=None,
            invested_currency=None,
            shares=Decimal("5.250000000000"),
            purchase_date=None,
            position=0,
        )
    )
    api_harness.service.replace_holdings.return_value = updated

    response = api_harness.client.put(
        f"/api/portfolios/{PORTFOLIO_ID}/holdings",
        headers=REQUEST_HEADERS,
        json={"holdings": [{"symbol": " aapl ", "shares": "5.25"}]},
    )

    assert response.status_code == 200
    assert response.json()["holdings"] == [
        {
            "id": "42000000-0000-0000-0000-000000000001",
            "symbol": "AAPL",
            "weight": None,
            "invested_amount": None,
            "invested_currency": None,
            "shares": "5.250000000000",
            "purchase_date": None,
            "position": 0,
        }
    ]
    api_harness.service.replace_holdings.assert_called_once_with(
        user_id=OWNER_ID,
        portfolio_id=PORTFOLIO_ID,
        holdings=[("AAPL", None, None, Decimal("5.25"), None)],
    )
    api_harness.session.commit.assert_called_once_with()


def test_step3_replace_planned_holdings_uses_proposed_amounts_only(
    api_harness: ApiHarness,
) -> None:
    updated = _portfolio(
        portfolio_type=PortfolioType.PLANNED,
        plan_currency="USD",
    )
    updated.holdings.extend(
        [
            _planned_holding("AAPL", position=0, proposed_amount="4000"),
            _planned_holding("BND", position=1, proposed_amount="1000"),
        ]
    )
    api_harness.service.replace_planned_holdings.return_value = updated

    response = api_harness.client.put(
        f"/api/portfolios/{PORTFOLIO_ID}/holdings",
        headers=REQUEST_HEADERS,
        json={
            "holdings": [
                {"symbol": " aapl ", "proposed_amount": "4000"},
                {"symbol": "bnd", "proposed_amount": "1000"},
            ]
        },
    )

    assert response.status_code == 200
    assert response.json()["portfolio_type"] == "PLANNED"
    assert response.json()["plan_currency"] == "USD"
    assert response.json()["holdings"] == [
        {
            "id": "43000000-0000-0000-0000-000000000001",
            "symbol": "AAPL",
            "weight": None,
            "proposed_amount": "4000",
            "position": 0,
        },
        {
            "id": "43000000-0000-0000-0000-000000000002",
            "symbol": "BND",
            "weight": None,
            "proposed_amount": "1000",
            "position": 1,
        },
    ]
    api_harness.service.replace_planned_holdings.assert_called_once_with(
        user_id=OWNER_ID,
        portfolio_id=PORTFOLIO_ID,
        holdings=[
            ("AAPL", Decimal("4000")),
            ("BND", Decimal("1000")),
        ],
    )
    api_harness.service.replace_holdings.assert_not_called()
    api_harness.session.commit.assert_called_once_with()


@pytest.mark.parametrize("request_mode", ["current", "planned"])
def test_step3_replace_holdings_reports_type_conflict_without_details(
    api_harness: ApiHarness,
    request_mode: str,
) -> None:
    error = route_module.PortfolioTypeConflictError(
        "sensitive persisted portfolio mode"
    )
    if request_mode == "planned":
        api_harness.service.replace_planned_holdings.side_effect = error
        payload = {
            "holdings": [{"symbol": "AAPL", "proposed_amount": "1000"}]
        }
    else:
        api_harness.service.replace_holdings.side_effect = error
        payload = {"holdings": [_real_request_holding()]}

    response = api_harness.client.put(
        f"/api/portfolios/{PORTFOLIO_ID}/holdings",
        headers=REQUEST_HEADERS,
        json=payload,
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Holding input does not match portfolio type"
    }
    assert "sensitive persisted portfolio mode" not in response.text
    api_harness.session.commit.assert_not_called()
    api_harness.session.rollback.assert_called_once_with()


@pytest.mark.parametrize(
    "holdings",
    [
        [
            _real_request_holding("AAPL"),
            _real_request_holding(" aapl "),
        ],
        [{**_real_request_holding(), "weight": 1.0}],
        [{**_real_request_holding(), "current_value": "1500"}],
        [],
    ],
    ids=["duplicate-symbol", "manual-weight", "computed-field", "empty"],
)
def test_phase6_replace_holdings_invalid_body_stays_422(
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
def test_phase6_replace_holdings_missing_and_wrong_owner_have_identical_404(
    api_harness: ApiHarness,
    resource_state: str,
) -> None:
    api_harness.service.replace_holdings.return_value = None

    response = api_harness.client.put(
        f"/api/portfolios/{PORTFOLIO_ID}/holdings",
        headers=REQUEST_HEADERS,
        json={"holdings": [_real_request_holding()]},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Portfolio not found"}
    api_harness.session.commit.assert_not_called()
    api_harness.session.rollback.assert_called_once_with()


def test_phase6_replace_holdings_expected_defensive_error_is_400(
    api_harness: ApiHarness,
) -> None:
    message = "holding symbols must be unique after normalization"
    api_harness.service.replace_holdings.side_effect = ValueError(message)

    response = api_harness.client.put(
        f"/api/portfolios/{PORTFOLIO_ID}/holdings",
        headers=REQUEST_HEADERS,
        json={"holdings": [_real_request_holding()]},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": message}
    api_harness.session.commit.assert_not_called()
    api_harness.session.rollback.assert_called_once_with()


def test_phase6_replace_holdings_unexpected_failure_remains_500(
    api_harness: ApiHarness,
) -> None:
    api_harness.service.replace_holdings.side_effect = RuntimeError(
        "sensitive replacement failure"
    )

    response = api_harness.client.put(
        f"/api/portfolios/{PORTFOLIO_ID}/holdings",
        headers=REQUEST_HEADERS,
        json={"holdings": [_real_request_holding()]},
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
    holding_ids = [uuid4(), uuid4()]
    duplicate.holdings.extend(
        [
            Holding(
                id=holding_ids[0],
                symbol="FIRST",
                weight=Decimal("0.6"),
                position=0,
            ),
            Holding(
                id=holding_ids[1],
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
        {
            "id": str(holding_ids[0]),
            "symbol": "FIRST",
            "weight": 0.6,
            "invested_amount": None,
            "invested_currency": None,
            "shares": None,
            "purchase_date": None,
            "position": 0,
        },
        {
            "id": str(holding_ids[1]),
            "symbol": "SECOND",
            "weight": 0.4,
            "invested_amount": None,
            "invested_currency": None,
            "shares": None,
            "purchase_date": None,
            "position": 1,
        },
    ]
    assert "user_id" not in response.json()
    api_harness.service.duplicate.assert_called_once_with(
        user_id=OWNER_ID,
        portfolio_id=PORTFOLIO_ID,
        name="Core Portfolio Copy",
    )
    api_harness.session.commit.assert_called_once_with()
    api_harness.session.rollback.assert_not_called()


def test_phase6_duplicate_maps_real_mode_without_fabricated_fields(
    api_harness: ApiHarness,
) -> None:
    duplicate = _portfolio(portfolio_id=uuid4(), name="Real Copy")
    duplicate.holdings.extend(
        [
            _real_holding("MSFT", position=0, invested_currency="THB"),
            _real_holding("AAPL", position=1),
        ]
    )
    api_harness.service.duplicate.return_value = duplicate

    response = api_harness.client.post(
        f"/api/portfolios/{PORTFOLIO_ID}/duplicate",
        headers=REQUEST_HEADERS,
        json={"name": "Real Copy"},
    )

    assert response.status_code == 201
    holdings = response.json()["holdings"]
    assert [holding["symbol"] for holding in holdings] == ["MSFT", "AAPL"]
    assert all(holding["weight"] is None for holding in holdings)
    assert [holding["invested_currency"] for holding in holdings] == [
        "THB",
        "USD",
    ]
    assert all("current_value" not in holding for holding in holdings)
    api_harness.session.commit.assert_called_once_with()


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


def test_phase6_openapi_exposes_only_approved_portfolio_contract_changes() -> None:
    schema = app.openapi()
    expected_crud_operations = {
        "/api/portfolios": {"get", "post"},
        "/api/portfolios/{portfolio_id}": {"delete", "get", "patch"},
        "/api/portfolios/{portfolio_id}/planned-allocation": {"get"},
        "/api/portfolios/{portfolio_id}/planned-preview": {"get"},
        "/api/portfolios/{portfolio_id}/valuation": {"get"},
        "/api/portfolios/{portfolio_id}/holdings": {"put"},
        "/api/portfolios/{portfolio_id}/duplicate": {"post"},
    }
    for path, methods in expected_crud_operations.items():
        assert set(schema["paths"][path]) == methods
    replace_operation = schema["paths"][
        "/api/portfolios/{portfolio_id}/holdings"
    ]["put"]
    assert replace_operation["requestBody"]["content"][
        "application/json"
    ]["schema"] == {
        "anyOf": [
            {
                "$ref": (
                    "#/components/schemas/"
                    "PortfolioHoldingsReplaceRequest"
                )
            },
            {
                "$ref": (
                    "#/components/schemas/"
                    "PortfolioPlannedHoldingsReplaceRequest"
                )
            },
        ],
        "title": "Request",
    }
    replacement_schema = schema["components"]["schemas"][
        "PortfolioHoldingsReplaceRequest"
    ]
    assert replacement_schema["properties"]["holdings"]["items"] == {
        "$ref": "#/components/schemas/PortfolioRealHoldingInput"
    }
    real_holding_schema = schema["components"]["schemas"][
        "PortfolioRealHoldingInput"
    ]
    assert set(real_holding_schema["properties"]) == {
        "symbol",
        "invested_amount",
        "invested_currency",
        "shares",
        "purchase_date",
    }
    planned_replacement_schema = schema["components"]["schemas"][
        "PortfolioPlannedHoldingsReplaceRequest"
    ]
    assert planned_replacement_schema["properties"]["holdings"][
        "items"
    ] == {
        "$ref": "#/components/schemas/PortfolioPlannedHoldingInput"
    }
    planned_holding_schema = schema["components"]["schemas"][
        "PortfolioPlannedHoldingInput"
    ]
    assert set(planned_holding_schema["properties"]) == {
        "symbol",
        "proposed_amount",
    }
    planned_allocation_operation = schema["paths"][
        "/api/portfolios/{portfolio_id}/planned-allocation"
    ]["get"]
    assert planned_allocation_operation["responses"]["200"]["content"][
        "application/json"
    ]["schema"] == {
        "$ref": "#/components/schemas/PortfolioPlannedAllocationResponse"
    }
    planned_preview_operation = schema["paths"][
        "/api/portfolios/{portfolio_id}/planned-preview"
    ]["get"]
    assert planned_preview_operation["responses"]["200"]["content"][
        "application/json"
    ]["schema"] == {
        "$ref": "#/components/schemas/PortfolioPlannedPreviewResponse"
    }
    valuation_operation = schema["paths"][
        "/api/portfolios/{portfolio_id}/valuation"
    ]["get"]
    assert valuation_operation["responses"]["200"]["content"][
        "application/json"
    ]["schema"] == {
        "$ref": "#/components/schemas/PortfolioValuationResponse"
    }
