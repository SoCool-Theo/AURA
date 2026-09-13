from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.orm import Session

import app.api.dependencies as dependency_module
import app.api.routes.reporting as route_module
from app.core.config import settings
from app.core.security import create_access_token
from app.database.models import User
from app.main import app
from app.schemas.common import AnalysisPeriod
from app.schemas.reporting import (
    PortfolioReportListResponse,
    PortfolioReportResponse,
    PortfolioReportSummary,
    PortfolioReportV2Response,
)
from app.services.analysis_reporting_service import (
    ReportAnalysisUnprocessableError,
    ReportNotFoundError,
)
from app.services.market_data_service import MarketDataUnavailableError
from app.services.portfolio_analysis_composition import (
    PortfolioAnalysisCompositionError,
)
from app.services.portfolio_valuation_service import (
    InvalidHoldingModeError,
    PortfolioDisplayCurrency,
)
from backend.tests.unit.services.test_analysis_reporting_mapper import (
    _valid_v2_report,
)
from backend.tests.unit.schemas.test_reporting import (
    _valid_report_data,
    _valid_summary_data,
)


OWNER_ID = UUID("62a1279e-bc8d-4c89-876d-a09250b50395")
PORTFOLIO_ID = UUID("e6518442-58cb-408f-ae3f-bf47fb00b555")
REPORT_ID = UUID("10000000-0000-0000-0000-000000000001")
JWT_SECRET = "phase-6-reporting-api-test-secret-value"
REQUEST_HEADERS: dict[str, str] = {}
REPORT_PATH = f"/api/portfolios/{PORTFOLIO_ID}/reports"
DETAIL_PATH = f"{REPORT_PATH}/{REPORT_ID}"


@dataclass
class ApiHarness:
    client: TestClient
    session: MagicMock
    service: MagicMock


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


def _report() -> PortfolioReportResponse:
    data = _valid_report_data()
    data["id"] = str(REPORT_ID)
    data["portfolio_id"] = str(PORTFOLIO_ID)
    return PortfolioReportResponse.model_validate(data)


def _summary(
    report_id: str = "10000000-0000-0000-0000-000000000001",
) -> PortfolioReportSummary:
    data = _valid_summary_data(report_id=report_id)
    data["portfolio_id"] = str(PORTFOLIO_ID)
    return PortfolioReportSummary.model_validate(data)


@pytest.fixture
def api_harness() -> ApiHarness:
    session = MagicMock(spec=Session)
    session.get.return_value = User(id=OWNER_ID)
    session_factory = MagicMock(return_value=session)
    service = MagicMock(spec=route_module.AnalysisReportingService)

    with (
        patch.object(
            dependency_module,
            "_get_session_factory",
            return_value=session_factory,
        ),
        patch.object(
            route_module,
            "AnalysisReportingService",
            return_value=service,
        ),
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        yield ApiHarness(client=client, session=session, service=service)


def _registered_methods() -> set[tuple[str, str]]:
    return {
        (path, method.upper())
        for path, operations in app.openapi()["paths"].items()
        for method in operations
    }


def test_all_four_reporting_routes_are_registered() -> None:
    methods = _registered_methods()

    assert ("/api/portfolios/{portfolio_id}/reports", "POST") in methods
    assert ("/api/portfolios/{portfolio_id}/reports", "GET") in methods
    assert (
        "/api/portfolios/{portfolio_id}/reports/{report_id}",
        "GET",
    ) in methods
    assert (
        "/api/portfolios/{portfolio_id}/reports/{report_id}",
        "DELETE",
    ) in methods


def test_post_accepts_analysis_period_returns_report_and_commits_once(
    api_harness: ApiHarness,
) -> None:
    report = _report()
    api_harness.service.create_report.return_value = report

    response = api_harness.client.post(
        REPORT_PATH,
        headers=REQUEST_HEADERS,
        json={"start_date": "2026-01-01", "end_date": "2026-01-31"},
    )

    assert response.status_code == 201
    assert response.json() == report.model_dump(mode="json")
    assert PortfolioReportResponse.model_validate(response.json()) == report
    api_harness.service.create_report.assert_called_once()
    call_arguments = api_harness.service.create_report.call_args.kwargs
    assert call_arguments["user_id"] == OWNER_ID
    assert call_arguments["portfolio_id"] == PORTFOLIO_ID
    assert call_arguments["period"] == AnalysisPeriod(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
    )
    assert call_arguments["display_currency"] is PortfolioDisplayCurrency.USD
    api_harness.session.commit.assert_called_once_with()
    api_harness.session.rollback.assert_not_called()


@pytest.mark.parametrize(
    "body",
    [
        {"start_date": "2026-02-01", "end_date": "2026-01-01"},
        {
            "start_date": "2026-01-01",
            "end_date": "2026-01-31",
            "portfolio_name": "not accepted",
        },
    ],
)
def test_post_rejects_invalid_analysis_period_through_schema_validation(
    api_harness: ApiHarness,
    body: dict[str, str],
) -> None:
    response = api_harness.client.post(
        REPORT_PATH,
        headers=REQUEST_HEADERS,
        json=body,
    )

    assert response.status_code == 422
    api_harness.service.create_report.assert_not_called()
    api_harness.session.commit.assert_not_called()


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"X-User-ID": str(OWNER_ID)},
        {"Authorization": "Bearer not-a-jwt"},
    ],
)
def test_post_missing_invalid_or_x_user_id_only_is_unauthorized(
    api_harness: ApiHarness,
    headers: dict[str, str],
) -> None:
    response = api_harness.client.post(
        REPORT_PATH,
        headers=headers,
        json={"start_date": "2026-01-01", "end_date": "2026-01-31"},
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    api_harness.service.create_report.assert_not_called()
    api_harness.session.commit.assert_not_called()


def test_valid_token_for_unknown_user_is_unauthorized(
    api_harness: ApiHarness,
) -> None:
    api_harness.session.get.return_value = None

    response = api_harness.client.get(REPORT_PATH, headers=REQUEST_HEADERS)

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid or missing authentication credentials"
    }
    assert response.headers["www-authenticate"] == "Bearer"
    api_harness.service.list_reports.assert_not_called()
    api_harness.session.commit.assert_not_called()
    api_harness.session.rollback.assert_called_once_with()


def test_post_accepts_thb_and_returns_valid_v2_report(
    api_harness: ApiHarness,
) -> None:
    report = _valid_v2_report()
    api_harness.service.create_report.return_value = report

    response = api_harness.client.post(
        f"{REPORT_PATH}?currency=THB",
        headers=REQUEST_HEADERS,
        json={"start_date": "2022-01-01", "end_date": "2022-12-31"},
    )

    assert response.status_code == 201
    assert response.json() == report.model_dump(mode="json")
    PortfolioReportV2Response.model_validate(response.json())
    call_arguments = api_harness.service.create_report.call_args.kwargs
    assert call_arguments["display_currency"] is PortfolioDisplayCurrency.THB
    api_harness.session.commit.assert_called_once_with()


def test_post_rejects_unsupported_currency_before_service_call(
    api_harness: ApiHarness,
) -> None:
    response = api_harness.client.post(
        f"{REPORT_PATH}?currency=EUR",
        headers=REQUEST_HEADERS,
        json={"start_date": "2022-01-01", "end_date": "2022-12-31"},
    )

    assert response.status_code == 422
    api_harness.service.create_report.assert_not_called()
    api_harness.session.commit.assert_not_called()


@pytest.mark.parametrize(
    ("failure", "expected_status", "expected_detail"),
    [
        (
            InvalidHoldingModeError("sensitive mixed state"),
            409,
            "Portfolio cannot be analyzed in its current holding state",
        ),
        (
            PortfolioAnalysisCompositionError("sensitive mismatch"),
            409,
            "Portfolio cannot be analyzed in its current holding state",
        ),
        (
            MarketDataUnavailableError("sensitive provider failure"),
            503,
            "Required market data is unavailable",
        ),
        (
            ReportAnalysisUnprocessableError("sensitive history failure"),
            422,
            "Historical analysis cannot process the requested period",
        ),
    ],
)
def test_post_maps_expected_real_report_failures_without_commit(
    api_harness: ApiHarness,
    failure: Exception,
    expected_status: int,
    expected_detail: str,
) -> None:
    api_harness.service.create_report.side_effect = failure

    response = api_harness.client.post(
        REPORT_PATH,
        headers=REQUEST_HEADERS,
        json={"start_date": "2022-01-01", "end_date": "2022-12-31"},
    )

    assert response.status_code == expected_status
    assert response.json() == {"detail": expected_detail}
    assert "sensitive" not in response.text
    api_harness.session.commit.assert_not_called()
    api_harness.session.rollback.assert_called_once_with()


def test_post_service_failure_does_not_commit_and_hides_details(
    api_harness: ApiHarness,
) -> None:
    api_harness.service.create_report.side_effect = RuntimeError(
        "sensitive analysis failure"
    )

    response = api_harness.client.post(
        REPORT_PATH,
        headers=REQUEST_HEADERS,
        json={"start_date": "2026-01-01", "end_date": "2026-01-31"},
    )

    assert response.status_code == 500
    assert response.json() == {"detail": "Unable to create report"}
    assert "sensitive analysis failure" not in response.text
    api_harness.session.commit.assert_not_called()
    api_harness.session.rollback.assert_called_once_with()


@pytest.mark.parametrize("resource_state", ["missing", "wrong-owner"])
def test_post_missing_and_wrong_owner_portfolio_are_identical_not_found(
    api_harness: ApiHarness,
    resource_state: str,
) -> None:
    api_harness.service.create_report.return_value = None

    response = api_harness.client.post(
        REPORT_PATH,
        headers=REQUEST_HEADERS,
        json={"start_date": "2026-01-01", "end_date": "2026-01-31"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Portfolio not found"}
    api_harness.session.commit.assert_not_called()
    api_harness.session.rollback.assert_called_once_with()


def test_get_history_passes_ownership_and_preserves_response_order(
    api_harness: ApiHarness,
) -> None:
    second = _summary("10000000-0000-0000-0000-000000000002")
    first = _summary("10000000-0000-0000-0000-000000000001")
    history = PortfolioReportListResponse(reports=[second, first])
    api_harness.service.list_reports.return_value = history

    response = api_harness.client.get(REPORT_PATH, headers=REQUEST_HEADERS)

    assert response.status_code == 200
    assert response.json() == history.model_dump(mode="json")
    assert PortfolioReportListResponse.model_validate(response.json()) == history
    assert [item["id"] for item in response.json()["reports"]] == [
        str(second.id),
        str(first.id),
    ]
    api_harness.service.list_reports.assert_called_once_with(
        user_id=OWNER_ID,
        portfolio_id=PORTFOLIO_ID,
    )
    api_harness.session.commit.assert_not_called()
    api_harness.session.rollback.assert_not_called()


def test_get_history_allows_empty_history_without_commit(
    api_harness: ApiHarness,
) -> None:
    api_harness.service.list_reports.return_value = PortfolioReportListResponse(
        reports=[]
    )

    response = api_harness.client.get(REPORT_PATH, headers=REQUEST_HEADERS)

    assert response.status_code == 200
    assert response.json() == {"reports": []}
    api_harness.session.commit.assert_not_called()


def test_get_history_unowned_portfolio_maps_to_portfolio_not_found(
    api_harness: ApiHarness,
) -> None:
    api_harness.service.list_reports.return_value = None

    response = api_harness.client.get(REPORT_PATH, headers=REQUEST_HEADERS)

    assert response.status_code == 404
    assert response.json() == {"detail": "Portfolio not found"}
    api_harness.session.commit.assert_not_called()


def test_get_detail_passes_all_ids_and_returns_valid_report_without_commit(
    api_harness: ApiHarness,
) -> None:
    report = _report()
    api_harness.service.get_report.return_value = report

    response = api_harness.client.get(DETAIL_PATH, headers=REQUEST_HEADERS)

    assert response.status_code == 200
    assert response.json() == report.model_dump(mode="json")
    assert PortfolioReportResponse.model_validate(response.json()) == report
    api_harness.service.get_report.assert_called_once_with(
        user_id=OWNER_ID,
        portfolio_id=PORTFOLIO_ID,
        report_id=REPORT_ID,
    )
    api_harness.service.list_reports.assert_not_called()
    api_harness.session.commit.assert_not_called()
    api_harness.session.rollback.assert_not_called()


def test_get_detail_returns_saved_v2_without_write(
    api_harness: ApiHarness,
) -> None:
    report = _valid_v2_report()
    api_harness.service.get_report.return_value = report

    response = api_harness.client.get(DETAIL_PATH, headers=REQUEST_HEADERS)

    assert response.status_code == 200
    assert response.json() == report.model_dump(mode="json")
    PortfolioReportV2Response.model_validate(response.json())
    api_harness.service.get_report.assert_called_once_with(
        user_id=OWNER_ID,
        portfolio_id=PORTFOLIO_ID,
        report_id=REPORT_ID,
    )
    api_harness.session.commit.assert_not_called()


@pytest.mark.parametrize("report_state", ["missing", "wrong-associated"])
def test_get_detail_missing_and_wrong_association_are_identical_not_found(
    api_harness: ApiHarness,
    report_state: str,
) -> None:
    api_harness.service.get_report.side_effect = ReportNotFoundError

    response = api_harness.client.get(DETAIL_PATH, headers=REQUEST_HEADERS)

    assert response.status_code == 404
    assert response.json() == {"detail": "Report not found"}
    api_harness.service.get_report.assert_called_once_with(
        user_id=OWNER_ID,
        portfolio_id=PORTFOLIO_ID,
        report_id=REPORT_ID,
    )
    api_harness.service.list_reports.assert_not_called()
    api_harness.session.commit.assert_not_called()


@pytest.mark.parametrize("portfolio_state", ["missing", "wrong-owner"])
def test_get_detail_unowned_parent_maps_to_portfolio_not_found(
    api_harness: ApiHarness,
    portfolio_state: str,
) -> None:
    api_harness.service.get_report.return_value = None

    response = api_harness.client.get(DETAIL_PATH, headers=REQUEST_HEADERS)

    assert response.status_code == 404
    assert response.json() == {"detail": "Portfolio not found"}
    api_harness.service.list_reports.assert_not_called()
    api_harness.session.commit.assert_not_called()


def test_delete_report_returns_empty_204_commits_once_and_removes_access(
    api_harness: ApiHarness,
) -> None:
    api_harness.service.delete_report.return_value = True

    response = api_harness.client.delete(
        DETAIL_PATH,
        headers=REQUEST_HEADERS,
    )

    assert response.status_code == 204
    assert response.content == b""
    api_harness.service.delete_report.assert_called_once_with(
        user_id=OWNER_ID,
        portfolio_id=PORTFOLIO_ID,
        report_id=REPORT_ID,
    )
    api_harness.session.commit.assert_called_once_with()
    api_harness.session.rollback.assert_not_called()

    api_harness.service.get_report.side_effect = ReportNotFoundError
    detail_response = api_harness.client.get(
        DETAIL_PATH,
        headers=REQUEST_HEADERS,
    )
    assert detail_response.status_code == 404
    assert detail_response.json() == {"detail": "Report not found"}

    api_harness.service.list_reports.return_value = PortfolioReportListResponse(
        reports=[]
    )
    history_response = api_harness.client.get(
        REPORT_PATH,
        headers=REQUEST_HEADERS,
    )
    assert history_response.status_code == 200
    assert history_response.json() == {"reports": []}
    api_harness.session.commit.assert_called_once_with()


@pytest.mark.parametrize("report_state", ["missing", "wrong-associated"])
def test_delete_report_missing_and_wrong_association_are_not_found(
    api_harness: ApiHarness,
    report_state: str,
) -> None:
    api_harness.service.delete_report.side_effect = ReportNotFoundError

    response = api_harness.client.delete(
        DETAIL_PATH,
        headers=REQUEST_HEADERS,
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Report not found"}
    api_harness.service.delete_report.assert_called_once_with(
        user_id=OWNER_ID,
        portfolio_id=PORTFOLIO_ID,
        report_id=REPORT_ID,
    )
    api_harness.session.commit.assert_not_called()
    api_harness.session.rollback.assert_called_once_with()


@pytest.mark.parametrize("portfolio_state", ["missing", "wrong-owner"])
def test_delete_report_unowned_parent_is_portfolio_not_found(
    api_harness: ApiHarness,
    portfolio_state: str,
) -> None:
    api_harness.service.delete_report.return_value = None

    response = api_harness.client.delete(
        DETAIL_PATH,
        headers=REQUEST_HEADERS,
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Portfolio not found"}
    api_harness.session.commit.assert_not_called()
    api_harness.session.rollback.assert_called_once_with()


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"X-User-ID": str(OWNER_ID)},
        {"Authorization": "Bearer not-a-jwt"},
    ],
)
def test_delete_report_requires_valid_bearer_authentication(
    api_harness: ApiHarness,
    headers: dict[str, str],
) -> None:
    response = api_harness.client.delete(DETAIL_PATH, headers=headers)

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    api_harness.service.delete_report.assert_not_called()
    api_harness.session.commit.assert_not_called()


def test_delete_report_failure_does_not_commit_and_hides_details(
    api_harness: ApiHarness,
) -> None:
    api_harness.service.delete_report.side_effect = RuntimeError(
        "sensitive database failure"
    )

    response = api_harness.client.delete(
        DETAIL_PATH,
        headers=REQUEST_HEADERS,
    )

    assert response.status_code == 500
    assert response.json() == {"detail": "Unable to delete report"}
    assert "sensitive database failure" not in response.text
    api_harness.session.commit.assert_not_called()
    api_harness.session.rollback.assert_called_once_with()
    api_harness.service.create_report.assert_not_called()


def test_delete_report_commit_failure_is_sanitized(
    api_harness: ApiHarness,
) -> None:
    api_harness.service.delete_report.return_value = True
    api_harness.session.commit.side_effect = RuntimeError(
        "sensitive commit failure"
    )

    response = api_harness.client.delete(
        DETAIL_PATH,
        headers=REQUEST_HEADERS,
    )

    assert response.status_code == 500
    assert response.json() == {"detail": "Unable to delete report"}
    assert "sensitive commit failure" not in response.text
    api_harness.session.commit.assert_called_once_with()
    api_harness.session.rollback.assert_called_once_with()


def test_existing_portfolio_routes_and_health_remain_available(
    api_harness: ApiHarness,
) -> None:
    methods = _registered_methods()

    assert ("/api/portfolios", "GET") in methods
    assert ("/api/portfolios", "POST") in methods
    assert ("/api/portfolios/{portfolio_id}", "GET") in methods
    response = api_harness.client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "app_name": settings.app_name,
        "environment": settings.app_env,
    }


def test_openapi_exposes_all_reporting_operations(
    api_harness: ApiHarness,
) -> None:
    schema = api_harness.client.get("/openapi.json").json()
    collection = schema["paths"]["/api/portfolios/{portfolio_id}/reports"]
    detail = schema["paths"][
        "/api/portfolios/{portfolio_id}/reports/{report_id}"
    ]

    assert {"post", "get"}.issubset(collection)
    assert {"get", "delete"}.issubset(detail)
    post_operation = collection["post"]
    currency_parameter = next(
        parameter
        for parameter in post_operation["parameters"]
        if parameter["name"] == "currency"
    )
    assert currency_parameter["in"] == "query"
    assert currency_parameter["required"] is False
    response_schema = post_operation["responses"]["201"]["content"][
        "application/json"
    ]["schema"]
    assert response_schema["anyOf"] == [
        {"$ref": "#/components/schemas/PortfolioReportResponse"},
        {"$ref": "#/components/schemas/PortfolioReportV2Response"},
    ]
    methods = _registered_methods()
    assert len(methods) == 24
    assert (
        "/api/portfolios/{portfolio_id}/planned-allocation",
        "GET",
    ) in methods
