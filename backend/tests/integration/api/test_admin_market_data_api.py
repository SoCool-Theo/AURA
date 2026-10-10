"""Synthetic SQLite acceptance for protected market inventory/history/status reads."""

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import patch
from uuid import UUID

from fastapi.testclient import TestClient
import jwt
from pydantic import SecretStr
import pytest
from sqlalchemy import JSON, MetaData, create_engine, delete
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.api.dependencies as dependencies
import app.api.routes.admin as routes
import app.services.admin_market_data_service as inventory_module
import app.services.market_data_status_service as status_module
from app.core.config import settings
from app.core.instruments import MARKET_UPDATE_SYMBOLS
from app.core.security import create_access_token
from app.database.models import MarketData, MarketDataRefreshState, User
from app.database.repositories.admin_market_data_repository import AdminMarketDataRepository
from app.main import app


SECRET = "admin-market-tests-secret-at-least-32-characters"
NOW = datetime(2026, 10, 10, 9, tzinfo=UTC)
ROOT = "/api/admin/market-data"
PATHS = [ROOT, ROOT + "/status", ROOT + "/observations"]


class FrozenDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return NOW if tz is not None else NOW.replace(tzinfo=None)


@dataclass
class Harness:
    client: TestClient
    factory: sessionmaker[Session]
    admin_id: UUID
    customer_id: UUID

    def headers(self, user_id: UUID | None = None):
        return {"Authorization": f"Bearer {create_access_token(user_id or self.admin_id)}"}


@pytest.fixture
def harness() -> Iterator[Harness]:
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    metadata = MetaData()
    for model in [User, MarketData, MarketDataRefreshState]:
        copied = model.__table__.to_metadata(metadata)
        for column in copied.columns:
            if isinstance(column.type, JSONB):
                column.type = JSON()
    metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with factory() as session:
        admin = User(id=UUID(int=1), email="admin@example.com", password_hash="private-hash", role="ADMIN")
        customer = User(id=UUID(int=2), email="customer@example.com", password_hash="private-hash", role="CUSTOMER")
        session.add_all([admin, customer])
        for symbol, day, price, volume, source in [
            ("AAPL", "2026-09-01", "100.25", 100, "Older synthetic source"),
            ("AAPL", "2026-10-06", "101.25", 200, "Synthetic"),
            ("AAPL", "2026-10-09", "102.25", 300, "Latest synthetic source"),
            ("MSFT", "2026-10-05", "200.25", 0, "Synthetic"),
            ("BTC-USD", "2026-10-08", "50000.25", 1000, "Synthetic"),
            ("ETH-USD", "2026-10-09", "3000.25", 2000, "Synthetic"),
            ("THB=X", "2026-10-06", "35.25", None, "Synthetic FX"),
            ("NVDA", "2026-10-10", "150.25", 400, "Synthetic"),
            ("TSLA", "2026-10-11", "300.25", 500, "Synthetic"),
            ("ODD", "2026-10-09", "1.25", None, "Unexpected synthetic source"),
        ]:
            session.add(MarketData(symbol=symbol, date=date.fromisoformat(day), adjusted_close=Decimal(price), volume=volume, source=source))
        session.commit()
    try:
        with (
            patch.object(dependencies, "_get_session_factory", return_value=factory),
            patch.object(settings, "jwt_secret_key", SecretStr(SECRET)),
            patch.object(inventory_module, "datetime", FrozenDatetime),
            patch.object(status_module, "datetime", FrozenDatetime),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            yield Harness(client, factory, admin.id, customer.id)
    finally:
        engine.dispose()


def test_inventory_counts_required_missing_and_unexpected_without_hiding_prices(harness):
    response = harness.client.get(ROOT, headers=harness.headers())
    assert response.status_code == 200
    payload = response.json()
    assert {key: value for key, value in payload.items() if key != "instruments"} == {
        "checked_at": "2026-10-10T09:00:00Z", "total_records": 10, "stored_symbols": 8,
        "required_symbols": 18, "present_required_symbols": 7, "current_required_symbols": 3,
        "stale_required_symbols": 4, "missing_required_symbols": 11, "unexpected_symbols": 1,
    }
    assert [item["symbol"] for item in payload["instruments"]] == [*MARKET_UPDATE_SYMBOLS, "ODD"]
    by_symbol = {item["symbol"]: item for item in payload["instruments"]}
    assert by_symbol["AAPL"] == {
        "symbol": "AAPL", "required_for_refresh": True, "kind": "asset", "quote_currency": "USD", "base_currency": None,
        "total_records": 3, "first_price_date": "2026-09-01", "latest_price_date": "2026-10-09",
        "latest_adjusted_close": "102.250000000000", "latest_volume": 300, "latest_source": "Latest synthetic source",
        "age_days": 1, "freshness": "current",
    }
    fx = by_symbol["THB=X"]
    assert (fx["kind"], fx["quote_currency"], fx["base_currency"], fx["age_days"], fx["freshness"], fx["latest_volume"]) == (
        "fx", "THB", "USD", 4, "current", None,
    )
    for symbol, age, freshness in [("MSFT", 5, "stale"), ("BTC-USD", 2, "stale"),
                                   ("ETH-USD", 1, "current"), ("NVDA", 0, "stale"), ("TSLA", None, "stale")]:
        assert (by_symbol[symbol]["age_days"], by_symbol[symbol]["freshness"]) == (age, freshness)
    missing = by_symbol["AMZN"]
    assert missing["freshness"] == "missing" and missing["total_records"] == 0
    assert all(missing[key] is None for key in ["first_price_date", "latest_price_date", "latest_adjusted_close", "latest_volume", "latest_source", "age_days"])
    odd = by_symbol["ODD"]
    assert (odd["required_for_refresh"], odd["kind"], odd["freshness"], odd["quote_currency"]) == (False, "unknown", "unknown", None)
    assert "private-hash" not in response.text and "Connected" not in response.text


def test_empty_inventory_retains_required_instruments_and_truthful_zero_counts(harness):
    with harness.factory() as session:
        session.execute(delete(MarketData))
        session.commit()
    payload = harness.client.get(ROOT, headers=harness.headers()).json()
    assert payload["total_records"] == payload["stored_symbols"] == payload["present_required_symbols"] == 0
    assert payload["required_symbols"] == payload["missing_required_symbols"] == 18
    assert payload["current_required_symbols"] == payload["stale_required_symbols"] == payload["unexpected_symbols"] == 0
    assert len(payload["instruments"]) == 18
    assert all(item["freshness"] == "missing" for item in payload["instruments"])


@pytest.mark.parametrize("params,expected", [
    ({"symbol": "  aapl  "}, [("AAPL", "2026-10-09"), ("AAPL", "2026-10-06"), ("AAPL", "2026-09-01")]),
    ({"symbol": "AAPL", "date_from": "2026-10-06", "date_to": "2026-10-09"}, [("AAPL", "2026-10-09"), ("AAPL", "2026-10-06")]),
    ({"date_from": "2026-10-09", "date_to": "2026-10-09"}, [("AAPL", "2026-10-09"), ("ETH-USD", "2026-10-09"), ("ODD", "2026-10-09")]),
    ({"symbol": "thb=x"}, [("THB=X", "2026-10-06")]),
    ({"symbol": "ODD"}, [("ODD", "2026-10-09")]),
    ({"symbol": "%"}, []), ({"symbol": "' OR 1=1 --"}, []),
    ({"symbol": "ABSENT"}, []), ({"date_to": "2000-01-01"}, []),
    ({"date_from": "2026-10-11"}, [("TSLA", "2026-10-11")]),
])
def test_observations_have_literal_symbol_and_inclusive_combined_date_filters(harness, params, expected):
    response = harness.client.get(PATHS[2], headers=harness.headers(), params=params)
    assert response.status_code == 200
    payload = response.json()
    assert [(item["symbol"], item["date"]) for item in payload["items"]] == expected
    assert payload["total"] == len(expected)
    assert (payload["limit"], payload["offset"]) == (25, 0)
    for item in payload["items"]:
        assert set(item) == {"symbol", "date", "adjusted_close", "volume", "source"}
        assert isinstance(item["adjusted_close"], str)
        assert Decimal(item["adjusted_close"]) > 0


def test_pages_use_stable_date_symbol_order_and_keep_total_beyond_last_page(harness):
    payload = harness.client.get(PATHS[2], headers=harness.headers(), params={"limit": 3, "offset": 2}).json()
    assert payload["total"] == 10
    assert [(item["symbol"], item["date"]) for item in payload["items"]] == [
        ("AAPL", "2026-10-09"), ("ETH-USD", "2026-10-09"), ("ODD", "2026-10-09"),
    ]
    payload = harness.client.get(PATHS[2], headers=harness.headers(), params={"symbol": "AAPL", "limit": 1, "offset": 10000}).json()
    assert payload == {"items": [], "total": 3, "limit": 1, "offset": 10000}


@pytest.mark.parametrize("params", [
    {"limit": 0}, {"limit": 101}, {"offset": -1}, {"offset": 10001},
    {"symbol": ""}, {"symbol": " "}, {"symbol": "x" * 65},
    {"date_from": "bad"}, {"date_to": "2026-02-30"},
    {"date_from": "2026-10-10", "date_to": "2026-10-09"},
])
def test_invalid_filters_rejected_before_service(harness, params):
    with patch.object(routes, "AdminMarketDataService") as service:
        response = harness.client.get(PATHS[2], headers=harness.headers(), params=params)
    assert response.status_code == 422
    service.assert_not_called()


def test_admin_status_reuses_shared_contract_and_reads_actual_partial_state(harness):
    with harness.factory() as session:
        session.add(MarketDataRefreshState(id=1, status="partial", attempt_count=2, stored_count=4,
            updated_symbols=["AAPL"], failed_symbols=["MSFT"], error_code="incomplete_coverage"))
        session.commit()
    response = harness.client.get(PATHS[1], headers=harness.headers())
    assert response.status_code == 200
    payload = response.json()
    customer = harness.client.get("/api/market-data/status", headers=harness.headers(harness.customer_id))
    assert customer.status_code == 200 and payload == customer.json()
    assert payload["last_run_status"] == "partial" and payload["worker_status"] == "unknown"
    assert payload["data_status"] == "missing" and payload["stored_count"] == 4
    assert payload["attempt_count"] == 2 and payload["failed_symbols"] == ["MSFT"]
    assert len(payload["observations"]) == 18
    assert payload["next_scheduled_at"] == "2026-10-11T02:00:00Z"


@pytest.mark.parametrize("path,queries", [(ROOT, 2), (PATHS[1], 3), (PATHS[2], 2)])
def test_reads_are_fixed_query_count_and_never_flush_commit_or_refresh(harness, path, queries):
    with (
        patch.object(Session, "execute", autospec=True, side_effect=Session.execute) as execute,
        patch.object(Session, "commit") as commit,
        patch.object(Session, "flush") as flush,
        patch("app.services.market_data_refresh_service.run_market_data_refresh") as refresh,
    ):
        response = harness.client.get(path, headers=harness.headers())
    assert response.status_code == 200
    assert execute.call_count == queries  # Includes one authorization query.
    commit.assert_not_called()
    flush.assert_not_called()
    refresh.assert_not_called()


@pytest.mark.parametrize("path", PATHS)
def test_missing_customer_forged_role_and_revoked_admin_cannot_query(harness, path):
    with patch.object(routes, "AdminMarketDataService") as market, patch.object(routes, "MarketDataStatusService") as status:
        assert harness.client.get(path).status_code == 401
        assert harness.client.get(path, headers={"X-User-ID": str(harness.admin_id)}).status_code == 401
        assert harness.client.get(path, headers=harness.headers(harness.customer_id)).status_code == 403
        claims = jwt.decode(create_access_token(harness.customer_id), SECRET, algorithms=["HS256"])
        claims["role"] = "ADMIN"
        forged = jwt.encode(claims, SECRET, algorithm="HS256")
        assert harness.client.get(path, headers={"Authorization": f"Bearer {forged}"}).status_code == 403
        with harness.factory() as session:
            session.get(User, harness.admin_id).role = "CUSTOMER"
            session.commit()
        assert harness.client.get(path, headers=harness.headers()).status_code == 403
    market.assert_not_called()
    status.assert_not_called()


@pytest.mark.parametrize("path,method,detail", [
    (ROOT, "inventory", "Admin market-data inventory unavailable"),
    (PATHS[2], "observations", "Admin market-data observations unavailable"),
])
def test_database_errors_are_sanitized_not_successful_empty_fallbacks(harness, path, method, detail):
    with patch.object(AdminMarketDataRepository, method, side_effect=SQLAlchemyError("private database credentials")):
        response = harness.client.get(path, headers=harness.headers())
    assert response.status_code == 503 and response.json() == {"detail": detail}


def test_invalid_persisted_price_fails_closed(harness):
    with patch.object(AdminMarketDataRepository, "observations", return_value=([
        {"symbol": "AAPL", "date": date(2026, 10, 9), "adjusted_close": Decimal("NaN"), "volume": None, "source": "Synthetic"},
    ], 1)):
        response = harness.client.get(PATHS[2], headers=harness.headers())
    assert response.status_code == 503
    assert response.json() == {"detail": "Admin market-data observations unavailable"}


def test_status_failure_is_sanitized(harness):
    with patch.object(routes.MarketDataStatusService, "get", side_effect=SQLAlchemyError("private database credentials")):
        response = harness.client.get(PATHS[1], headers=harness.headers())
    assert response.status_code == 503
    assert response.json() == {"detail": "Admin market-data status unavailable"}


def test_admin_market_surface_is_read_only_and_bearer_protected():
    paths = app.openapi()["paths"]
    for path in PATHS:
        assert set(paths[path]) == {"get"}
        assert paths[path]["get"]["security"] == [{"HTTPBearer": []}]
        assert "requestBody" not in paths[path]["get"]


@pytest.mark.parametrize("path", PATHS)
def test_http_mutations_are_not_supported(harness, path):
    for method in ["post", "put", "patch", "delete"]:
        assert harness.client.request(method, path, headers=harness.headers()).status_code == 405
