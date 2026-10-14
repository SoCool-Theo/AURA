"""Global admin portfolio reads, with real permissions and synthetic storage."""

from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import patch
from uuid import UUID

import pytest
from sqlalchemy import JSON, MetaData, event, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database.models import Analysis, Holding, Portfolio, Simulation, User, AuditLog
from app.database.repositories.admin_portfolio_repository import AdminPortfolioRepository
from backend.tests.integration.api.test_admin_user_status_api import bearer, harness


@pytest.fixture
def directory(harness):
    client, factory = harness
    metadata = MetaData()
    for model in (User, Portfolio, Holding, Analysis, Simulation):
        copied = model.__table__.to_metadata(metadata)
        for column in copied.columns:
            if isinstance(column.type, JSONB):
                column.type = JSON()
    metadata.create_all(factory.kw["bind"])
    now = datetime(2026, 10, 14, tzinfo=UTC)
    with factory() as session:
        session.get(User, UUID(int=2)).display_name = "Portfolio Owner"
        session.get(User, UUID(int=2)).phone_number = "private-phone"
        session.get(User, UUID(int=3)).is_suspended = True
        session.add_all([
            Portfolio(id=UUID(int=100), user_id=UUID(int=2), name="100%_\\ literal", portfolio_type="CURRENT", created_at=now, updated_at=now),
            Portfolio(id=UUID(int=101), user_id=UUID(int=3), name="Planned allocation", portfolio_type="PLANNED", plan_currency="THB", created_at=now, updated_at=now),
            Portfolio(id=UUID(int=102), user_id=UUID(int=2), name="Legacy allocation", portfolio_type="LEGACY", created_at=now, updated_at=now),
            Portfolio(id=UUID(int=103), user_id=UUID(int=1), name="Empty current", portfolio_type="CURRENT", created_at=now, updated_at=now),
            *[Portfolio(id=UUID(int=i), user_id=UUID(int=2), name=f"Current {i}", created_at=now, updated_at=now) for i in range(104, 132)],
        ])
        session.flush()
        session.add_all([
            Holding(id=UUID(int=200), portfolio_id=UUID(int=100), symbol="MSFT", shares=Decimal("0.123456789012"), position=1),
            Holding(id=UUID(int=201), portfolio_id=UUID(int=100), symbol="AAPL", shares=Decimal("2.123456789012"), invested_amount=Decimal("123.456789012345"), invested_currency="USD", purchase_date=date(2026, 1, 2), position=0),
            Holding(id=UUID(int=202), portfolio_id=UUID(int=101), symbol="AAPL", proposed_amount=Decimal("1234567890.123456789012"), position=0),
            Holding(id=UUID(int=203), portfolio_id=UUID(int=102), symbol="AAPL", weight=Decimal("1"), position=0),
            *[Analysis(portfolio_id=UUID(int=100), start_date=date(2026, 1, 1), end_date=date(2026, 1, 2), schema_version="synthetic", result_snapshot={"private_snapshot": True}) for _ in range(2)],
            *[Simulation(portfolio_id=UUID(int=100), simulation_type="allocation", scenario_id=None, requested_start_date=date(2026, 1, 1), requested_end_date=date(2026, 1, 2), schema_version="synthetic", result_snapshot={"private_snapshot": True}) for _ in range(3)],
        ])
        session.commit()
    return client, factory


def test_directory_pagination_counts_owner_metadata_and_deterministic_ties(directory):
    client, _ = directory
    data = client.get("/api/admin/portfolios", headers=bearer()).json()
    assert (data["total"], data["limit"], data["offset"]) == (32, 25, 0)
    assert [item["id"] for item in data["items"]] == [str(UUID(int=i)) for i in range(131, 106, -1)]
    tail = client.get("/api/admin/portfolios", headers=bearer(), params={"offset": 25}).json()
    assert len(tail["items"]) == 7 and tail["total"] == 32
    current = next(item for item in tail["items"] if item["id"] == str(UUID(int=100)))
    assert (current["holding_count"], current["saved_report_count"], current["saved_simulation_count"]) == (2, 2, 3)
    assert current["owner"] == {"id": str(UUID(int=2)), "email": "customer@example.com", "display_name": "Portfolio Owner", "account_type": "REGISTERED", "status": "ACTIVE"}
    assert "holdings" not in current and "source_plan_id" not in current
    legacy_owner = next(item for item in tail["items"] if item["id"] == str(UUID(int=101)))["owner"]
    assert legacy_owner["account_type"] == "LEGACY" and legacy_owner["email"] is None and legacy_owner["status"] == "SUSPENDED"
    for private in ("password", "auth_version", "phone_number", "private-phone", "private_snapshot", "private-scenario", "access_token"):
        assert private not in str(data) + str(tail)


@pytest.mark.parametrize("query,total", [
    ({"portfolio_type": "PLANNED"}, 1), ({"portfolio_type": "LEGACY"}, 1),
    ({"owner_id": str(UUID(int=3))}, 1), ({"owner_id": str(UUID(int=999))}, 0),
    ({"q": " CUSTOMER@EXAMPLE.COM "}, 30), ({"q": "portfolio OWNER"}, 30),
    ({"q": "%"}, 1), ({"q": "_"}, 1), ({"q": "\\"}, 1),
    ({"q": "nothing matches"}, 0), ({"q": " "}, 32),
    ({"portfolio_type": "PLANNED", "owner_id": str(UUID(int=2))}, 0),
])
def test_literal_search_and_combined_filters(directory, query, total):
    client, _ = directory
    response = client.get("/api/admin/portfolios", headers=bearer(), params=query)
    assert response.status_code == 200 and response.json()["total"] == total


def test_empty_page_retains_matching_total(directory):
    client, _ = directory
    data = client.get("/api/admin/portfolios", headers=bearer(), params={"offset": 10000}).json()
    assert data["items"] == [] and data["total"] == 32


@pytest.mark.parametrize("identifier,kind", [(100, "CURRENT"), (101, "PLANNED"), (102, "LEGACY"), (103, "CURRENT")])
def test_mode_aware_details_order_and_existing_serialization(directory, identifier, kind):
    client, _ = directory
    response = client.get(f"/api/admin/portfolios/{UUID(int=identifier)}", headers=bearer())
    assert response.status_code == 200
    data = response.json()
    assert data["portfolio_type"] == kind and data["holding_count"] == len(data["holdings"])
    assert data["created_at"].endswith("Z") and data["source_plan_id"] is None
    if identifier == 100:
        assert [item["symbol"] for item in data["holdings"]] == ["AAPL", "MSFT"]
        assert data["holdings"][0]["shares"] == "2.123456789012"
        assert data["holdings"][0]["invested_amount"] == "123.456789012345"
        assert data["saved_report_count"] == 2 and data["saved_simulation_count"] == 3
    elif identifier == 101:
        assert data["plan_currency"] == "THB" and Decimal(data["holdings"][0]["proposed_amount"]) > 0  # Exact large decimals are verified against PostgreSQL.
    elif identifier == 102:
        assert data["holdings"][0]["weight"] == 1
    else:
        assert data["holdings"] == []
    for private in ("password", "private_snapshot", "private-scenario", "auth_version", "phone_number", "valuation", "risk_score"):
        assert private not in response.text


@pytest.mark.parametrize("path", ["/api/admin/portfolios", f"/api/admin/portfolios/{UUID(int=100)}", f"/api/admin/portfolios/{UUID(int=999)}"])
def test_access_boundary_before_data_or_existence(directory, path):
    client, _ = directory
    assert client.get(path).status_code == 401
    assert client.get(path, headers=bearer(2)).status_code == 403
    assert client.get(path, headers=bearer(1, version=1)).status_code == 401
    assert client.get(path, headers={"X-User-ID": str(UUID(int=1))}).status_code == 401


def test_missing_and_malformed_ids_and_customer_ownership_are_preserved(directory):
    client, _ = directory
    assert client.get(f"/api/admin/portfolios/{UUID(int=999)}", headers=bearer()).status_code == 404
    assert client.get("/api/admin/portfolios/not-a-uuid", headers=bearer()).status_code == 422
    assert client.get(f"/api/portfolios/{UUID(int=100)}", headers=bearer()).status_code == 404


@pytest.mark.parametrize("query", [{"limit": 0}, {"limit": 101}, {"offset": -1}, {"offset": 10001}, {"portfolio_type": "REAL"}, {"owner_id": "invalid"}, {"q": "x" * 101}])
def test_invalid_queries(directory, query):
    assert directory[0].get("/api/admin/portfolios", headers=bearer(), params=query).status_code == 422


@pytest.mark.parametrize("method,path", [("list", "/api/admin/portfolios"), ("detail", f"/api/admin/portfolios/{UUID(int=100)}")])
def test_database_failure_is_sanitized(directory, method, path):
    with patch.object(AdminPortfolioRepository, method, side_effect=SQLAlchemyError("private DB credentials")):
        response = directory[0].get(path, headers=bearer())
    assert response.status_code == 503 and "private" not in response.text and "credentials" not in response.text


def test_invalid_saved_holding_state_fails_without_invented_data(directory):
    client, factory = directory
    original = AdminPortfolioRepository.detail
    def corrupted(repo, identifier):
        rows = [dict(row) for row in original(repo, identifier)]
        rows[0]["holding_shares"] = None
        return rows
    with patch.object(AdminPortfolioRepository, "detail", corrupted):
        assert client.get(f"/api/admin/portfolios/{UUID(int=100)}", headers=bearer()).status_code == 503


def test_reads_use_one_projection_statement_and_do_not_mutate(directory):
    client, factory = directory
    statements = []
    def capture(connection, cursor, statement, parameters, context, executemany):
        statements.append(statement)
    engine = factory.kw["bind"]
    event.listen(engine, "before_cursor_execute", capture)
    try:
        with patch.object(Session, "commit", side_effect=AssertionError("read committed")), patch.object(Session, "flush", side_effect=AssertionError("read wrote")):
            for path in ("/api/admin/portfolios", f"/api/admin/portfolios/{UUID(int=100)}"):
                statements.clear()
                assert client.get(path, headers=bearer()).status_code == 200
                assert len(statements) == 2  # Persisted actor authorization + one portfolio snapshot.
                assert all(private not in statements[-1] for private in ("password_hash", "result_snapshot", "scenario_name", "phone_number"))
    finally:
        event.remove(engine, "before_cursor_execute", capture)
    with factory() as session:
        assert len(session.scalars(select(AuditLog)).all()) == 0
