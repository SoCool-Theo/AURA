"""Live PostgreSQL verification for Aura's analysis-reporting workflow."""

from __future__ import annotations

from collections.abc import Iterator
from copy import deepcopy
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
import os
from pathlib import Path
import sys
from uuid import UUID


BACKEND_ROOT = Path(__file__).resolve().parents[3]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
import pandas as pd
import pytest
from pydantic import SecretStr
from sqlalchemy import Engine, func, inspect, select, text, update
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.api.dependencies import get_database_session
from app.core.config import settings as app_settings
from app.core.security import create_access_token
from app.database.connection import session_scope
from app.database.models import Analysis, Portfolio, User
from app.database.repositories import PortfolioRepository
from app.main import app
from app.schemas.analytics import PortfolioAnalysisResponse
from app.schemas.reporting import (
    PortfolioReportListResponse,
    PortfolioReportResponse,
)
from app.services.analysis_reporting_mapper import (
    PORTFOLIO_ANALYSIS_RESPONSE_SCHEMA_VERSION,
)
from app.services.market_data_service import MarketDataService
from backend.app.core.config import settings
from backend.app.database.connection import create_database_engine


ALEMBIC_CONFIG_PATH = BACKEND_ROOT / "alembic.ini"
APPLICATION_TABLES = {
    "analyses",
    "simulations",
    "holdings",
    "market_data",
    "portfolios",
    "users",
    "watchlist_items",
}

USER_A_ID = UUID("60000000-0000-0000-0000-000000000001")
USER_B_ID = UUID("60000000-0000-0000-0000-000000000002")
START_DATE = date(2062, 1, 2)
END_DATE = date(2062, 1, 7)
REPORT_PERIOD = {
    "start_date": START_DATE.isoformat(),
    "end_date": END_DATE.isoformat(),
}
JWT_SECRET = "phase-6-live-reporting-api-secret-value"


@dataclass(frozen=True)
class SeededPortfolios:
    owner_portfolio_id: UUID
    other_portfolio_id: UUID


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
    if (
        database_name != "aura_test"
        and not database_name.startswith("aura_test_")
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
                "TRUNCATE TABLE simulations, analyses, holdings, portfolios, users, "
                "market_data CASCADE"
            )
        )


@pytest.fixture(scope="module")
def postgres_engine() -> Iterator[Engine]:
    raw_url = _test_database_url()
    engine = create_database_engine(raw_url)
    original_database_url = settings.database_url
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

        settings.database_url = raw_url  # type: ignore[assignment]
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
            settings.database_url = original_database_url
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
def clean_application_rows(postgres_engine: Engine) -> Iterator[None]:
    _truncate_application_tables(postgres_engine)
    try:
        yield
    finally:
        _truncate_application_tables(postgres_engine)


def _headers(user_id: UUID) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user_id)}"}


def _canonical_market_data() -> pd.DataFrame:
    rows = [
        ("P6AAPL", "2062-01-02", 200.0, 1_001, "phase-6-live"),
        ("P6AAPL", "2062-01-03", 198.0, 1_002, "phase-6-live"),
        ("P6AAPL", "2062-01-04", 204.0, 1_003, "phase-6-live"),
        ("P6AAPL", "2062-01-05", 202.0, 1_004, "phase-6-live"),
        ("P6AAPL", "2062-01-06", 208.0, 1_005, "phase-6-live"),
        ("P6AAPL", "2062-01-07", 210.0, 1_006, "phase-6-live"),
        ("P6BND", "2062-01-02", 100.0, None, "phase-6-live"),
        ("P6BND", "2062-01-03", 101.0, None, "phase-6-live"),
        ("P6BND", "2062-01-04", 99.0, None, "phase-6-live"),
        ("P6BND", "2062-01-05", 103.0, None, "phase-6-live"),
        ("P6BND", "2062-01-06", 102.0, None, "phase-6-live"),
        ("P6BND", "2062-01-07", 104.0, None, "phase-6-live"),
    ]
    return pd.DataFrame(
        {
            "date": pd.to_datetime([row[1] for row in rows]),
            "symbol": pd.Series([row[0] for row in rows], dtype="string"),
            "adjusted_close": pd.Series(
                [row[2] for row in rows], dtype="float64"
            ),
            "volume": pd.Series([row[3] for row in rows], dtype="Int64"),
            "source": pd.Series([row[4] for row in rows], dtype="string"),
        }
    )


def _seed_reporting_state(
    session_factory: sessionmaker[Session],
) -> SeededPortfolios:
    with session_factory.begin() as session:
        session.add_all([User(id=USER_A_ID), User(id=USER_B_ID)])
        portfolio_repository = PortfolioRepository(session)
        owner_portfolio = portfolio_repository.create(
            user_id=USER_A_ID,
            name="Phase 6 Owner Portfolio",
        )
        other_portfolio = portfolio_repository.create(
            user_id=USER_B_ID,
            name="Phase 6 Other Portfolio",
        )
        portfolio_repository.replace_holdings(
            owner_portfolio.id,
            [
                ("P6BND", Decimal("0.450000000000000000")),
                ("P6AAPL", Decimal("0.550000000000000000")),
            ],
        )
        portfolio_repository.replace_holdings(
            other_portfolio.id,
            [
                ("P6AAPL", Decimal("0.600000000000000000")),
                ("P6BND", Decimal("0.400000000000000000")),
            ],
        )
        assert MarketDataService(session).store(_canonical_market_data()) == 12

    return SeededPortfolios(
        owner_portfolio_id=owner_portfolio.id,
        other_portfolio_id=other_portfolio.id,
    )


def _reporting_state(
    session_factory: sessionmaker[Session],
) -> list[tuple[object, ...]]:
    with session_factory() as session:
        analyses = session.scalars(select(Analysis).order_by(Analysis.id)).all()
        return [
            (
                analysis.id,
                analysis.portfolio_id,
                analysis.start_date,
                analysis.end_date,
                analysis.schema_version,
                deepcopy(analysis.result_snapshot),
                analysis.created_at,
                analysis.updated_at,
            )
            for analysis in analyses
        ]


def test_live_reporting_lifecycle_persistence_isolation_and_immutability(
    live_client: TestClient,
    session_factory: sessionmaker[Session],
) -> None:
    seeded = _seed_reporting_state(session_factory)
    owner_headers = _headers(USER_A_ID)
    other_headers = _headers(USER_B_ID)
    owner_report_path = (
        f"/api/portfolios/{seeded.owner_portfolio_id}/reports"
    )
    other_report_path = (
        f"/api/portfolios/{seeded.other_portfolio_id}/reports"
    )

    x_header_only_response = live_client.get(
        owner_report_path,
        headers={"X-User-ID": str(USER_A_ID)},
    )
    assert x_header_only_response.status_code == 401
    assert x_header_only_response.headers["www-authenticate"] == "Bearer"

    create_response = live_client.post(
        owner_report_path,
        headers=owner_headers,
        json=REPORT_PERIOD,
    )
    assert create_response.status_code == 201
    report_one = PortfolioReportResponse.model_validate(create_response.json())
    assert report_one.portfolio_id == seeded.owner_portfolio_id
    assert report_one.analysis.start_date == START_DATE
    assert report_one.analysis.end_date == END_DATE
    assert report_one.analysis.metadata.asset_count == 2
    assert [metric.symbol for metric in report_one.analysis.asset_metrics] == [
        "P6BND",
        "P6AAPL",
    ]
    assert report_one.analysis.correlation_matrix.symbols == [
        "P6BND",
        "P6AAPL",
    ]

    with session_factory() as session:
        persisted = session.get(Analysis, report_one.id)
        assert persisted is not None
        assert persisted.id == report_one.id
        assert persisted.portfolio_id == seeded.owner_portfolio_id
        assert persisted.start_date == START_DATE
        assert persisted.end_date == END_DATE
        assert (
            persisted.schema_version
            == PORTFOLIO_ANALYSIS_RESPONSE_SCHEMA_VERSION
            == "portfolio-analysis-response-v1"
        )
        assert persisted.created_at is not None
        assert persisted.created_at.tzinfo is not None
        stored_analysis = PortfolioAnalysisResponse.model_validate(
            persisted.result_snapshot
        )
        assert persisted.result_snapshot == stored_analysis.model_dump(
            mode="json"
        )
        assert stored_analysis == report_one.analysis
        assert persisted.start_date == stored_analysis.start_date
        assert persisted.end_date == stored_analysis.end_date

    fresh_detail_response = live_client.get(
        f"{owner_report_path}/{report_one.id}",
        headers=owner_headers,
    )
    assert fresh_detail_response.status_code == 200
    assert (
        PortfolioReportResponse.model_validate(fresh_detail_response.json())
        == report_one
    )

    original_analysis_payload = report_one.analysis.model_dump(mode="json")
    replacement_response = live_client.put(
        f"/api/portfolios/{seeded.owner_portfolio_id}/holdings",
        headers=owner_headers,
        json={
            "holdings": [
                {"symbol": "P6AAPL", "weight": 0.25},
                {"symbol": "P6BND", "weight": 0.75},
            ]
        },
    )
    assert replacement_response.status_code == 200

    immutable_detail_response = live_client.get(
        f"{owner_report_path}/{report_one.id}",
        headers=owner_headers,
    )
    assert immutable_detail_response.status_code == 200
    assert (
        immutable_detail_response.json()["analysis"]
        == original_analysis_payload
    )

    report_two_response = live_client.post(
        owner_report_path,
        headers=owner_headers,
        json=REPORT_PERIOD,
    )
    report_three_response = live_client.post(
        owner_report_path,
        headers=owner_headers,
        json=REPORT_PERIOD,
    )
    other_report_response = live_client.post(
        other_report_path,
        headers=other_headers,
        json=REPORT_PERIOD,
    )
    assert report_two_response.status_code == 201
    assert report_three_response.status_code == 201
    assert other_report_response.status_code == 201
    report_two = PortfolioReportResponse.model_validate(
        report_two_response.json()
    )
    report_three = PortfolioReportResponse.model_validate(
        report_three_response.json()
    )
    other_report = PortfolioReportResponse.model_validate(
        other_report_response.json()
    )

    tied_created_at = datetime(2062, 2, 1, tzinfo=timezone.utc)
    newest_created_at = datetime(2062, 2, 2, tzinfo=timezone.utc)
    with session_factory.begin() as session:
        session.execute(
            update(Analysis)
            .where(Analysis.id.in_([report_one.id, report_two.id]))
            .values(created_at=tied_created_at)
        )
        session.execute(
            update(Analysis)
            .where(Analysis.id == report_three.id)
            .values(created_at=newest_created_at)
        )

    state_before_gets = _reporting_state(session_factory)
    history_response = live_client.get(
        owner_report_path,
        headers=owner_headers,
    )
    assert history_response.status_code == 200
    history = PortfolioReportListResponse.model_validate(history_response.json())
    tied_ids = sorted([report_one.id, report_two.id], key=lambda value: value.int)
    assert [summary.id for summary in history.reports] == [
        report_three.id,
        *tied_ids,
    ]
    assert [summary.created_at for summary in history.reports] == [
        newest_created_at,
        tied_created_at,
        tied_created_at,
    ]

    read_only_detail_response = live_client.get(
        f"{owner_report_path}/{report_one.id}",
        headers=owner_headers,
    )
    assert read_only_detail_response.status_code == 200
    assert (
        read_only_detail_response.json()["analysis"]
        == original_analysis_payload
    )

    wrong_owner_response = live_client.get(
        owner_report_path,
        headers=other_headers,
    )
    assert wrong_owner_response.status_code == 404
    assert wrong_owner_response.json() == {"detail": "Portfolio not found"}

    unrelated_report_response = live_client.get(
        f"{owner_report_path}/{other_report.id}",
        headers=owner_headers,
    )
    assert unrelated_report_response.status_code == 404
    assert unrelated_report_response.json() == {"detail": "Report not found"}
    assert _reporting_state(session_factory) == state_before_gets


def test_live_failed_analysis_rolls_back_without_persisting_report(
    live_client: TestClient,
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory.begin() as session:
        session.add(User(id=USER_A_ID))
        portfolio_repository = PortfolioRepository(session)
        portfolio = portfolio_repository.create(
            user_id=USER_A_ID,
            name="Phase 6 Missing Market Data",
        )
        portfolio_repository.replace_holdings(
            portfolio.id,
            [("P6MISSING", Decimal("1.000000000000000000"))],
        )
        portfolio_id = portfolio.id

    with session_factory() as session:
        assert session.scalar(
            select(func.count()).select_from(Analysis)
        ) == 0

    response = live_client.post(
        f"/api/portfolios/{portfolio_id}/reports",
        headers=_headers(USER_A_ID),
        json=REPORT_PERIOD,
    )
    assert response.status_code == 500
    assert response.json() == {"detail": "Unable to create report"}

    with session_factory() as fresh_session:
        assert fresh_session.scalar(
            select(func.count()).select_from(Analysis)
        ) == 0
        assert fresh_session.get(Portfolio, portfolio_id) is not None
