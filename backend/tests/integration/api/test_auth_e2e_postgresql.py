"""Live end-to-end authentication and protected-resource verification."""

from __future__ import annotations

from collections.abc import Iterator
from copy import deepcopy
from datetime import date
from pathlib import Path
import os
from uuid import UUID

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
import pandas as pd
import pytest
from pydantic import SecretStr
from sqlalchemy import Engine, inspect, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, selectinload, sessionmaker

from app.api.dependencies import get_database_session
from app.core.config import settings as app_settings
from app.core.security import decode_access_token, verify_password
from app.database.connection import session_scope
from app.database.models import Analysis, Portfolio, User
from app.main import app
from app.schemas.reporting import (
    PortfolioReportListResponse,
    PortfolioReportResponse,
)
from app.services.market_data_service import MarketDataService
from backend.app.core.config import settings as backend_settings
from backend.app.database.connection import create_database_engine


BACKEND_ROOT = Path(__file__).resolve().parents[3]
ALEMBIC_CONFIG_PATH = BACKEND_ROOT / "alembic.ini"
APPLICATION_TABLES = {
    "analyses",
    "holdings",
    "market_data",
    "portfolios",
    "users",
}
JWT_SECRET = "phase-7-e2e-test-only-jwt-secret-value"
PASSWORD = "phase-7-valid-password"
START_DATE = date(2063, 1, 2)
END_DATE = date(2063, 1, 7)
REPORT_PERIOD = {
    "start_date": START_DATE.isoformat(),
    "end_date": END_DATE.isoformat(),
}


def _test_database_url() -> str:
    raw_url = os.getenv("AURA_TEST_DATABASE_URL")
    if not raw_url:
        pytest.skip(
            "AURA_TEST_DATABASE_URL is required for live PostgreSQL tests"
        )

    url = make_url(raw_url)
    if url.drivername != "postgresql+psycopg":
        pytest.fail(
            "AURA_TEST_DATABASE_URL must use postgresql+psycopg",
            pytrace=False,
        )

    database_name = url.database or ""
    if database_name != "aura_test" and not database_name.startswith(
        "aura_test_"
    ):
        pytest.fail(
            "AURA_TEST_DATABASE_URL must target aura_test or aura_test_*",
            pytrace=False,
        )
    return raw_url


def _alembic_config() -> Config:
    return Config(str(ALEMBIC_CONFIG_PATH))


def _table_names(engine: Engine) -> set[str]:
    return set(inspect(engine).get_table_names(schema="public"))


def _truncate_application_tables(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE TABLE analyses, holdings, portfolios, users, "
                "market_data CASCADE"
            )
        )


@pytest.fixture(scope="module")
def postgres_engine() -> Iterator[Engine]:
    raw_url = _test_database_url()
    engine = create_database_engine(raw_url)
    original_database_url = backend_settings.database_url
    upgraded = False
    initial_tables: set[str] = set()

    try:
        with engine.connect():
            initial_tables = _table_names(engine)

        unexpected_tables = initial_tables - {"alembic_version"}
        if unexpected_tables:
            pytest.fail(
                "Live test database must start empty; found tables: "
                f"{sorted(unexpected_tables)}",
                pytrace=False,
            )

        if "alembic_version" in initial_tables:
            with engine.connect() as connection:
                revision_count = connection.scalar(
                    text("SELECT COUNT(*) FROM alembic_version")
                )
            if revision_count:
                pytest.fail(
                    "Live test database must not have an applied revision",
                    pytrace=False,
                )

        backend_settings.database_url = raw_url  # type: ignore[assignment]
        command.upgrade(_alembic_config(), "head")
        upgraded = True
        yield engine
    finally:
        try:
            if upgraded:
                command.downgrade(_alembic_config(), "base")
                remaining_tables = _table_names(engine) & APPLICATION_TABLES
                if remaining_tables:
                    raise AssertionError(
                        "Live test cleanup left application tables behind: "
                        f"{sorted(remaining_tables)}"
                    )
                if not initial_tables.issubset(_table_names(engine)):
                    raise AssertionError(
                        "Live test cleanup removed a pre-existing table"
                    )
        finally:
            backend_settings.database_url = original_database_url
            engine.dispose()


@pytest.fixture(scope="module")
def session_factory(
    postgres_engine: Engine,
) -> sessionmaker[Session]:
    return sessionmaker(
        bind=postgres_engine,
        class_=Session,
        autoflush=False,
        expire_on_commit=False,
    )


@pytest.fixture(scope="module")
def live_client(
    session_factory: sessionmaker[Session],
) -> Iterator[TestClient]:
    def override_database_session() -> Iterator[Session]:
        with session_scope(session_factory) as session:
            yield session

    previous_override = app.dependency_overrides.get(get_database_session)
    original_jwt_secret = app_settings.jwt_secret_key
    app.dependency_overrides[get_database_session] = override_database_session
    app_settings.jwt_secret_key = SecretStr(JWT_SECRET)

    try:
        with TestClient(app) as client:
            yield client
    finally:
        app_settings.jwt_secret_key = original_jwt_secret
        if previous_override is None:
            app.dependency_overrides.pop(get_database_session, None)
        else:
            app.dependency_overrides[get_database_session] = previous_override


@pytest.fixture(autouse=True)
def isolated_live_rows(postgres_engine: Engine) -> Iterator[None]:
    _truncate_application_tables(postgres_engine)
    try:
        yield
    finally:
        _truncate_application_tables(postgres_engine)


def _canonical_market_data() -> pd.DataFrame:
    rows = [
        ("E2EA", "2063-01-02", 200.0, 1_001),
        ("E2EA", "2063-01-03", 198.0, 1_002),
        ("E2EA", "2063-01-04", 204.0, 1_003),
        ("E2EA", "2063-01-05", 202.0, 1_004),
        ("E2EA", "2063-01-06", 208.0, 1_005),
        ("E2EA", "2063-01-07", 210.0, 1_006),
        ("E2EB", "2063-01-02", 100.0, None),
        ("E2EB", "2063-01-03", 101.0, None),
        ("E2EB", "2063-01-04", 99.0, None),
        ("E2EB", "2063-01-05", 103.0, None),
        ("E2EB", "2063-01-06", 102.0, None),
        ("E2EB", "2063-01-07", 104.0, None),
    ]
    return pd.DataFrame(
        {
            "date": pd.to_datetime([row[1] for row in rows]),
            "symbol": pd.Series([row[0] for row in rows], dtype="string"),
            "adjusted_close": pd.Series(
                [row[2] for row in rows], dtype="float64"
            ),
            "volume": pd.Series([row[3] for row in rows], dtype="Int64"),
            "source": pd.Series(
                ["phase-7-e2e"] * len(rows), dtype="string"
            ),
        }
    )


def _seed_market_data(session_factory: sessionmaker[Session]) -> None:
    with session_factory.begin() as session:
        assert MarketDataService(session).store(_canonical_market_data()) == 12


def _register(
    client: TestClient,
    *,
    email: str,
    password: str = PASSWORD,
) -> dict[str, object]:
    response = client.post(
        "/api/auth/register",
        json={"email": email, "password": password},
    )
    assert response.status_code == 201
    return response.json()


def _login(
    client: TestClient,
    *,
    email: str,
    password: str = PASSWORD,
) -> tuple[str, dict[str, str]]:
    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["token_type"] == "bearer"
    token = payload["access_token"]
    return token, {"Authorization": f"Bearer {token}"}


def _create_reportable_portfolio(
    client: TestClient,
    headers: dict[str, str],
    *,
    name: str,
) -> dict[str, object]:
    create_response = client.post(
        "/api/portfolios",
        headers=headers,
        json={"name": name},
    )
    assert create_response.status_code == 201
    created = create_response.json()

    holdings_response = client.put(
        f"/api/portfolios/{created['id']}/holdings",
        headers=headers,
        json={
            "holdings": [
                {"symbol": "E2EA", "weight": 0.55},
                {"symbol": "E2EB", "weight": 0.45},
            ]
        },
    )
    assert holdings_response.status_code == 200
    return holdings_response.json()


def test_live_complete_authentication_to_report_workflow(
    live_client: TestClient,
    session_factory: sessionmaker[Session],
) -> None:
    _seed_market_data(session_factory)
    registration_input = {
        "email": "  Phase.Seven@Example.COM  ",
        "password": PASSWORD,
    }
    original_registration_input = deepcopy(registration_input)

    health_response = live_client.get("/api/health")
    assert health_response.status_code == 200

    registered = _register(
        live_client,
        email=registration_input["email"],
        password=registration_input["password"],
    )
    assert registration_input == original_registration_input
    assert registered["email"] == "phase.seven@example.com"
    assert set(registered) == {"id", "email", "created_at", "updated_at"}
    assert "password" not in registered
    assert "password_hash" not in registered
    user_id = UUID(str(registered["id"]))

    with session_factory() as session:
        persisted_user = session.get(User, user_id)
        assert persisted_user is not None
        assert persisted_user.email == "phase.seven@example.com"
        assert persisted_user.password_hash is not None
        assert persisted_user.password_hash != PASSWORD
        assert PASSWORD not in persisted_user.password_hash
        assert verify_password(PASSWORD, persisted_user.password_hash)

    token, headers = _login(
        live_client,
        email=" PHASE.SEVEN@example.com ",
    )
    assert decode_access_token(token) == user_id

    me_response = live_client.get("/api/auth/me", headers=headers)
    assert me_response.status_code == 200
    assert me_response.json() == registered

    portfolio = _create_reportable_portfolio(
        live_client,
        headers,
        name="Phase 7 Portfolio",
    )
    portfolio_id = UUID(str(portfolio["id"]))
    assert set(portfolio) == {
        "id",
        "name",
        "created_at",
        "updated_at",
        "holdings",
    }
    assert portfolio["holdings"] == [
        {"symbol": "E2EA", "weight": 0.55, "position": 0},
        {"symbol": "E2EB", "weight": 0.45, "position": 1},
    ]

    retrieved_portfolio = live_client.get(
        f"/api/portfolios/{portfolio_id}",
        headers=headers,
    )
    assert retrieved_portfolio.status_code == 200
    assert retrieved_portfolio.json() == portfolio

    report_path = f"/api/portfolios/{portfolio_id}/reports"
    report_response = live_client.post(
        report_path,
        headers=headers,
        json=REPORT_PERIOD,
    )
    assert report_response.status_code == 201
    report = PortfolioReportResponse.model_validate(report_response.json())
    report_id = report.id
    original_analysis = report.analysis.model_dump(mode="json")

    list_response = live_client.get(report_path, headers=headers)
    assert list_response.status_code == 200
    reports = PortfolioReportListResponse.model_validate(list_response.json())
    assert [summary.id for summary in reports.reports] == [report_id]

    mutation_response = live_client.put(
        f"/api/portfolios/{portfolio_id}/holdings",
        headers=headers,
        json={
            "holdings": [
                {"symbol": "E2EB", "weight": 0.60},
                {"symbol": "E2EA", "weight": 0.40},
            ]
        },
    )
    assert mutation_response.status_code == 200

    detail_response = live_client.get(
        f"{report_path}/{report_id}",
        headers=headers,
    )
    assert detail_response.status_code == 200
    assert detail_response.json()["analysis"] == original_analysis

    with session_factory() as fresh_session:
        fresh_user = fresh_session.get(User, user_id)
        fresh_portfolio = fresh_session.scalar(
            select(Portfolio)
            .options(selectinload(Portfolio.holdings))
            .where(Portfolio.id == portfolio_id)
        )
        fresh_report = fresh_session.get(Analysis, report_id)

        assert fresh_user is not None
        assert fresh_user.email == "phase.seven@example.com"
        assert fresh_portfolio is not None
        assert fresh_portfolio.user_id == user_id
        assert [holding.symbol for holding in fresh_portfolio.holdings] == [
            "E2EB",
            "E2EA",
        ]
        assert fresh_report is not None
        assert fresh_report.portfolio_id == portfolio_id
        assert fresh_report.result_snapshot == original_analysis


def test_live_two_user_privacy_and_x_user_id_rejection(
    live_client: TestClient,
    session_factory: sessionmaker[Session],
) -> None:
    _seed_market_data(session_factory)
    user_a = _register(live_client, email="owner.a@example.com")
    user_b = _register(live_client, email="owner.b@example.com")
    user_a_id = UUID(str(user_a["id"]))
    user_b_id = UUID(str(user_b["id"]))
    token_a, headers_a = _login(live_client, email="OWNER.A@example.com")
    token_b, headers_b = _login(live_client, email="OWNER.B@example.com")
    assert decode_access_token(token_a) == user_a_id
    assert decode_access_token(token_b) == user_b_id

    portfolio = _create_reportable_portfolio(
        live_client,
        headers_a,
        name="User A Private Portfolio",
    )
    portfolio_id = UUID(str(portfolio["id"]))
    report_path = f"/api/portfolios/{portfolio_id}/reports"
    report_response = live_client.post(
        report_path,
        headers=headers_a,
        json=REPORT_PERIOD,
    )
    assert report_response.status_code == 201
    report_id = UUID(report_response.json()["id"])

    wrong_owner_portfolio = live_client.get(
        f"/api/portfolios/{portfolio_id}",
        headers=headers_b,
    )
    assert wrong_owner_portfolio.status_code == 404
    assert wrong_owner_portfolio.json() == {"detail": "Portfolio not found"}

    wrong_owner_report = live_client.get(
        f"{report_path}/{report_id}",
        headers=headers_b,
    )
    assert wrong_owner_report.status_code == 404
    assert wrong_owner_report.json() == {"detail": "Portfolio not found"}

    x_header_only = live_client.get(
        f"/api/portfolios/{portfolio_id}",
        headers={"X-User-ID": str(user_a_id)},
    )
    assert x_header_only.status_code == 401
    assert x_header_only.headers["www-authenticate"] == "Bearer"

    bearer_with_conflicting_x_header = live_client.get(
        f"/api/portfolios/{portfolio_id}",
        headers={**headers_a, "X-User-ID": str(user_b_id)},
    )
    assert bearer_with_conflicting_x_header.status_code == 200
    assert UUID(bearer_with_conflicting_x_header.json()["id"]) == portfolio_id

    owner_report = live_client.get(
        f"{report_path}/{report_id}",
        headers=headers_a,
    )
    assert owner_report.status_code == 200

    with session_factory() as fresh_session:
        assert fresh_session.get(User, user_a_id) is not None
        assert fresh_session.get(User, user_b_id) is not None
        assert fresh_session.get(Portfolio, portfolio_id) is not None
        assert fresh_session.get(Analysis, report_id) is not None
