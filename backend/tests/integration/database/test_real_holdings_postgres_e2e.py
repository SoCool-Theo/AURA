"""Guarded end-to-end verification against the isolated Phase 12 database."""

from __future__ import annotations

from collections.abc import Iterator
from copy import deepcopy
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch
from uuid import UUID

from fastapi.testclient import TestClient
from pydantic import SecretStr
import pytest
from sqlalchemy import Engine, delete, inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload, sessionmaker

import app.api.routes.agent as agent_route_module
import app.api.routes.simulation as simulation_route_module
from app.agents.provider import ProviderRequest, ProviderResponse
from app.api.dependencies import get_database_session
from app.core.config import settings as app_settings
from app.database.connection import session_scope
from app.database.models import (
    Analysis,
    Holding,
    MarketData,
    Portfolio,
    Simulation,
)
from app.database.repositories import PortfolioRepository
from app.main import app
from app.schemas.portfolio import PortfolioResponse, PortfolioValuationResponse
from app.schemas.reporting import (
    PortfolioReportResponse,
    PortfolioReportV2Response,
    PortfolioReportV2Snapshot,
)
from app.schemas.simulation_history import (
    SimulationHistoryDetailResponse,
    SimulationHistoryV2DetailResponse,
)
from app.services.analysis_reporting_mapper import (
    PORTFOLIO_ANALYSIS_RESPONSE_SCHEMA_VERSION,
    PORTFOLIO_ANALYSIS_RESPONSE_V2_SCHEMA_VERSION,
)
import app.services.analysis_reporting_service as reporting_service_module
from app.services.simulation_history_mapper import (
    ALLOCATION_SIMULATION_RESPONSE_V2_SCHEMA_VERSION,
    COMBINED_SIMULATION_RESPONSE_V2_SCHEMA_VERSION,
    HISTORICAL_SCENARIO_SIMULATION_RESPONSE_SCHEMA_VERSION,
    HISTORICAL_SCENARIO_SIMULATION_RESPONSE_V2_SCHEMA_VERSION,
    restore_simulation_snapshot,
)
import app.services.portfolio_valuation_service as valuation_service_module

from backend.tests.integration.database.postgres_test_guard import (
    APPLICATION_TABLES,
    PHASE12_CURRENT_DATE,
    PHASE12_SYMBOLS,
    REAL_HOLDING_REVISION,
    create_guarded_engine,
    read_only_preflight,
    read_test_database_url,
)


OWNER_EMAIL = "phase12.owner.20260912@example.com"
OTHER_EMAIL = "phase12.other.20260912@example.com"
RESERVED_EMAILS = (OWNER_EMAIL, OTHER_EMAIL)
PASSWORD = "Phase12-Guarded-Local-Password-2026"
JWT_SECRET = "phase-12-guarded-local-jwt-secret-value"
REAL_PORTFOLIO_NAME = "Phase 12 Reserved REAL Portfolio"
REAL_RENAMED_NAME = "Phase 12 Reserved REAL Portfolio Renamed"
REAL_DUPLICATE_NAME = "Phase 12 Reserved REAL Portfolio Copy"
LEGACY_PORTFOLIO_NAME = "Phase 12 Reserved LEGACY Portfolio"
LEGACY_DUPLICATE_NAME = "Phase 12 Reserved LEGACY Portfolio Copy"
PHASE12_SOURCE = "phase-12-deterministic-fixture"
REPORT_PERIOD = {"start_date": "2020-01-01", "end_date": "2020-03-31"}
SCENARIO_ID = "covid-19-shock-2020"
MODIFIED_ALLOCATION = [
    {"symbol": "AAPL", "weight": 0.7},
    {"symbol": "MSFT", "weight": 0.3},
]


class _FrozenDateTime(datetime):
    @classmethod
    def now(cls, tz: object = None) -> _FrozenDateTime:
        return cls(2026, 9, 12, 12, 0, tzinfo=UTC)


class _FakeProvider:
    def __init__(self) -> None:
        self.requests: list[ProviderRequest] = []

    def generate(self, request: ProviderRequest) -> ProviderResponse:
        self.requests.append(request)
        return ProviderResponse("Aura explains the persisted portfolio risk context.")

    def reset(self) -> None:
        self.requests.clear()


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _register(client: TestClient, email: str) -> dict[str, object]:
    response = client.post(
        "/api/auth/register",
        json={"email": email, "password": PASSWORD},
    )
    assert response.status_code == 201
    return response.json()


def _login(client: TestClient, email: str) -> tuple[str, dict[str, str]]:
    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": PASSWORD},
    )
    assert response.status_code == 200
    token = str(response.json()["access_token"])
    return token, _headers(token)


def _row_counts(engine: Engine) -> dict[str, int]:
    with engine.connect() as connection:
        return {
            table: int(
                connection.scalar(text(f'SELECT count(*) FROM "{table}"'))
                or 0
            )
            for table in APPLICATION_TABLES
        }


def _non_market_snapshot(engine: Engine) -> dict[str, tuple[tuple[object, ...], ...]]:
    snapshot: dict[str, tuple[tuple[object, ...], ...]] = {}
    with engine.connect() as connection:
        for table in (
            "users",
            "portfolios",
            "holdings",
            "analyses",
            "simulations",
        ):
            snapshot[table] = tuple(
                connection.execute(
                    text(f'SELECT * FROM "{table}" ORDER BY id')
                ).tuples()
            )
    return snapshot


def _reserved_market_rows(engine: Engine) -> tuple[tuple[object, ...], ...]:
    with engine.connect() as connection:
        return tuple(
            connection.execute(
                text(
                    "SELECT symbol, date, adjusted_close, volume, source "
                    "FROM market_data WHERE symbol = ANY(:symbols) "
                    "AND date = :date ORDER BY symbol"
                ),
                {
                    "symbols": list(PHASE12_SYMBOLS),
                    "date": PHASE12_CURRENT_DATE,
                },
            ).tuples()
        )


def _assert_reserved_identities_absent(engine: Engine) -> None:
    with engine.connect() as connection:
        reserved_users = connection.scalar(
            text("SELECT count(*) FROM users WHERE email = ANY(:emails)"),
            {"emails": list(RESERVED_EMAILS)},
        )
        reserved_portfolios = connection.scalar(
            text(
                "SELECT count(*) FROM portfolios WHERE name = ANY(:names)"
            ),
            {
                "names": [
                    REAL_PORTFOLIO_NAME,
                    REAL_RENAMED_NAME,
                    REAL_DUPLICATE_NAME,
                    LEGACY_PORTFOLIO_NAME,
                    LEGACY_DUPLICATE_NAME,
                ]
            },
        )
    assert reserved_users == 0
    assert reserved_portfolios == 0
    assert _reserved_market_rows(engine) == ()


def _historical_common_count(
    engine: Engine,
    *,
    start_date: date,
    end_date: date,
) -> int:
    with engine.connect() as connection:
        return int(
            connection.scalar(
                text(
                    "SELECT count(*) FROM ("
                    "SELECT date FROM market_data "
                    "WHERE symbol = ANY(:symbols) "
                    "AND date BETWEEN :start_date AND :end_date "
                    "GROUP BY date HAVING count(DISTINCT symbol) = 2"
                    ") AS common_dates"
                ),
                {
                    "symbols": ["AAPL", "MSFT"],
                    "start_date": start_date,
                    "end_date": end_date,
                },
            )
            or 0
        )


def _market_rows(*, changed: bool = False) -> list[MarketData]:
    prices = (
        {"AAPL": Decimal("300"), "MSFT": Decimal("150"), "THB=X": Decimal("35")}
        if changed
        else {"AAPL": Decimal("100"), "MSFT": Decimal("200"), "THB=X": Decimal("35")}
    )
    return [
        MarketData(
            symbol=symbol,
            date=PHASE12_CURRENT_DATE,
            adjusted_close=prices[symbol],
            volume=None,
            source=PHASE12_SOURCE,
        )
        for symbol in PHASE12_SYMBOLS
    ]


def _insert_market_rows(
    factory: sessionmaker[Session],
    *,
    symbols: tuple[str, ...] = PHASE12_SYMBOLS,
    changed: bool = False,
) -> None:
    selected = [row for row in _market_rows(changed=changed) if row.symbol in symbols]
    with factory.begin() as session:
        for row in selected:
            assert session.get(MarketData, (row.symbol, row.date)) is None
        session.add_all(selected)


def _delete_market_rows(
    factory: sessionmaker[Session],
    *,
    symbols: tuple[str, ...],
) -> None:
    with factory.begin() as session:
        session.execute(
            delete(MarketData).where(
                MarketData.symbol.in_(symbols),
                MarketData.date == PHASE12_CURRENT_DATE,
                MarketData.source == PHASE12_SOURCE,
            )
        )


def _change_asset_prices(factory: sessionmaker[Session]) -> None:
    changed = {row.symbol: row.adjusted_close for row in _market_rows(changed=True)}
    with factory.begin() as session:
        for symbol in ("AAPL", "MSFT"):
            row = session.get(MarketData, (symbol, PHASE12_CURRENT_DATE))
            assert row is not None
            assert row.source == PHASE12_SOURCE
            row.adjusted_close = changed[symbol]


def _portfolio_with_holdings(
    factory: sessionmaker[Session],
    portfolio_id: UUID,
) -> Portfolio:
    with factory() as session:
        portfolio = session.scalar(
            select(Portfolio)
            .options(selectinload(Portfolio.holdings))
            .where(Portfolio.id == portfolio_id)
        )
        assert portfolio is not None
        session.expunge_all()
        return portfolio


def _holding_snapshot(portfolio: Portfolio) -> tuple[tuple[object, ...], ...]:
    return tuple(
        (
            holding.id,
            holding.symbol,
            holding.weight,
            holding.invested_amount,
            holding.invested_currency,
            holding.shares,
            holding.purchase_date,
            holding.position,
        )
        for holding in portfolio.holdings
    )


def _simulation_ids(client: TestClient, path: str, headers: dict[str, str]) -> set[UUID]:
    response = client.get(path, headers=headers)
    assert response.status_code == 200
    return {UUID(item["id"]) for item in response.json()["simulations"]}


def _run_and_get_simulation(
    client: TestClient,
    *,
    post_path: str,
    history_path: str,
    detail_base_path: str,
    headers: dict[str, str],
    payload: dict[str, object],
) -> tuple[dict[str, object], UUID, dict[str, object]]:
    before = _simulation_ids(client, history_path, headers)
    response = client.post(post_path, headers=headers, json=payload)
    assert response.status_code == 200
    after = _simulation_ids(client, history_path, headers)
    created = after - before
    assert len(created) == 1
    simulation_id = created.pop()
    detail_response = client.get(
        f"{detail_base_path}/{simulation_id}",
        headers=headers,
    )
    assert detail_response.status_code == 200
    return response.json(), simulation_id, detail_response.json()


def _count_for_portfolio(
    factory: sessionmaker[Session],
    model: type[Analysis] | type[Simulation],
    portfolio_id: UUID,
) -> int:
    with factory() as session:
        return len(
            tuple(
                session.scalars(
                    select(model.id).where(model.portfolio_id == portfolio_id)
                )
            )
        )


def _cleanup_reserved_rows(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(
            text("DELETE FROM users WHERE email = ANY(:emails)"),
            {"emails": list(RESERVED_EMAILS)},
        )
        connection.execute(
            text(
                "DELETE FROM market_data WHERE symbol = ANY(:symbols) "
                "AND date = :date AND source = :source"
            ),
            {
                "symbols": list(PHASE12_SYMBOLS),
                "date": PHASE12_CURRENT_DATE,
                "source": PHASE12_SOURCE,
            },
        )


def test_phase12_complete_guarded_postgresql_e2e() -> None:
    preflight = read_only_preflight()
    assert preflight.alembic_revision == REAL_HOLDING_REVISION
    raw_url = read_test_database_url()
    engine = create_guarded_engine(raw_url)
    factory = sessionmaker(
        bind=engine,
        class_=Session,
        autoflush=False,
        expire_on_commit=False,
    )
    baseline_counts = _row_counts(engine)
    baseline_non_market = _non_market_snapshot(engine)
    baseline_overlap = _reserved_market_rows(engine)
    _assert_reserved_identities_absent(engine)
    assert baseline_overlap == ()
    assert _historical_common_count(
        engine,
        start_date=date(2020, 1, 1),
        end_date=date(2020, 3, 31),
    ) >= 3
    assert _historical_common_count(
        engine,
        start_date=date(2020, 2, 1),
        end_date=date(2020, 4, 30),
    ) >= 3

    fake_provider = _FakeProvider()

    def override_database_session() -> Iterator[Session]:
        with session_scope(factory) as session:
            yield session

    previous_database_override = app.dependency_overrides.get(
        get_database_session
    )
    previous_provider_override = app.dependency_overrides.get(
        agent_route_module.get_agent_provider
    )
    original_jwt_secret = app_settings.jwt_secret_key
    app.dependency_overrides[get_database_session] = override_database_session
    app.dependency_overrides[agent_route_module.get_agent_provider] = (
        lambda: fake_provider
    )
    app_settings.jwt_secret_key = SecretStr(JWT_SECRET)

    try:
        _insert_market_rows(factory)
        with (
            patch.object(
                valuation_service_module,
                "datetime",
                _FrozenDateTime,
            ),
            patch.object(
                reporting_service_module,
                "datetime",
                _FrozenDateTime,
            ),
            patch.object(
                simulation_route_module,
                "_current_utc_date",
                return_value=PHASE12_CURRENT_DATE,
            ),
            patch.object(
                agent_route_module,
                "_current_utc_date",
                return_value=PHASE12_CURRENT_DATE,
            ),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            owner_registration = _register(client, OWNER_EMAIL)
            other_registration = _register(client, OTHER_EMAIL)
            owner_id = UUID(str(owner_registration["id"]))
            other_id = UUID(str(other_registration["id"]))
            assert owner_id != other_id

            owner_token, owner_headers = _login(client, OWNER_EMAIL.upper())
            other_token, other_headers = _login(client, OTHER_EMAIL.upper())
            assert owner_token != other_token
            me_response = client.get("/api/auth/me", headers=owner_headers)
            assert me_response.status_code == 200
            assert me_response.json() == owner_registration

            create_response = client.post(
                "/api/portfolios",
                headers=owner_headers,
                json={"name": REAL_PORTFOLIO_NAME},
            )
            assert create_response.status_code == 201
            portfolio_id = UUID(create_response.json()["id"])
            holdings_payload = {
                "holdings": [
                    {
                        "symbol": "AAPL",
                        "invested_amount": "150.25",
                        "invested_currency": "USD",
                        "shares": "2",
                        "purchase_date": "2025-01-02",
                    },
                    {
                        "symbol": "MSFT",
                        "invested_amount": "10000",
                        "invested_currency": "THB",
                        "shares": "4",
                        "purchase_date": "2025-02-03",
                    },
                ]
            }
            replace_response = client.put(
                f"/api/portfolios/{portfolio_id}/holdings",
                headers=owner_headers,
                json=holdings_payload,
            )
            assert replace_response.status_code == 200
            replaced = PortfolioResponse.model_validate(replace_response.json())
            assert [holding.symbol for holding in replaced.holdings] == [
                "AAPL",
                "MSFT",
            ]
            assert [holding.position for holding in replaced.holdings] == [0, 1]
            assert all(holding.weight is None for holding in replaced.holdings)

            fresh_portfolio = _portfolio_with_holdings(factory, portfolio_id)
            original_holding_snapshot = _holding_snapshot(fresh_portfolio)
            assert [holding.invested_amount for holding in fresh_portfolio.holdings] == [
                Decimal("150.250000000000"),
                Decimal("10000.000000000000"),
            ]
            assert [holding.invested_currency for holding in fresh_portfolio.holdings] == [
                "USD",
                "THB",
            ]
            assert [holding.shares for holding in fresh_portfolio.holdings] == [
                Decimal("2.000000000000"),
                Decimal("4.000000000000"),
            ]
            assert all(holding.weight is None for holding in fresh_portfolio.holdings)
            holding_column_names = {
                column["name"] for column in inspect(engine).get_columns("holdings")
            }
            assert "current_value" not in holding_column_names
            assert "current_allocation" not in holding_column_names

            detail_response = client.get(
                f"/api/portfolios/{portfolio_id}",
                headers=owner_headers,
            )
            assert detail_response.status_code == 200
            assert PortfolioResponse.model_validate(
                detail_response.json()
            ) == replaced

            rename_response = client.patch(
                f"/api/portfolios/{portfolio_id}",
                headers=owner_headers,
                json={"name": REAL_RENAMED_NAME},
            )
            assert rename_response.status_code == 200
            assert rename_response.json()["name"] == REAL_RENAMED_NAME

            duplicate_response = client.post(
                f"/api/portfolios/{portfolio_id}/duplicate",
                headers=owner_headers,
                json={"name": REAL_DUPLICATE_NAME},
            )
            assert duplicate_response.status_code == 201
            duplicate = PortfolioResponse.model_validate(duplicate_response.json())
            assert duplicate.id != portfolio_id
            assert [holding.id for holding in duplicate.holdings] != [
                holding.id for holding in replaced.holdings
            ]
            assert [
                (
                    holding.symbol,
                    holding.invested_amount,
                    holding.invested_currency,
                    holding.shares,
                    holding.purchase_date,
                    holding.position,
                    holding.weight,
                )
                for holding in duplicate.holdings
            ] == [
                (
                    holding.symbol,
                    holding.invested_amount,
                    holding.invested_currency,
                    holding.shares,
                    holding.purchase_date,
                    holding.position,
                    holding.weight,
                )
                for holding in replaced.holdings
            ]

            counts_before_valuation = _row_counts(engine)
            usd_response = client.get(
                f"/api/portfolios/{portfolio_id}/valuation",
                headers=owner_headers,
            )
            assert usd_response.status_code == 200
            usd = PortfolioValuationResponse.model_validate(usd_response.json())
            assert usd.valuation_currency == "USD"
            assert usd.requested_date == PHASE12_CURRENT_DATE
            assert usd.total_current_value_usd == Decimal("1000")
            assert usd.total_current_value == Decimal("1000")
            assert usd.fx is None
            assert [holding.current_value_usd for holding in usd.holdings] == [
                Decimal("200"),
                Decimal("800"),
            ]
            assert [holding.current_allocation for holding in usd.holdings] == [
                Decimal("0.2"),
                Decimal("0.8"),
            ]

            thb_response = client.get(
                f"/api/portfolios/{portfolio_id}/valuation?currency=THB",
                headers=owner_headers,
            )
            assert thb_response.status_code == 200
            thb = PortfolioValuationResponse.model_validate(thb_response.json())
            assert thb.valuation_currency == "THB"
            assert thb.total_current_value_usd == Decimal("1000")
            assert thb.total_current_value == Decimal("35000")
            assert thb.fx is not None
            assert thb.fx.provider_symbol == "THB=X"
            assert thb.fx.rate == Decimal("35")
            assert thb.fx.as_of == PHASE12_CURRENT_DATE
            assert [holding.current_value for holding in thb.holdings] == [
                Decimal("7000"),
                Decimal("28000"),
            ]
            assert [holding.current_allocation for holding in thb.holdings] == [
                Decimal("0.2"),
                Decimal("0.8"),
            ]
            assert _row_counts(engine) == counts_before_valuation

            report_path = f"/api/portfolios/{portfolio_id}/reports"
            usd_report_response = client.post(
                report_path,
                headers=owner_headers,
                json=REPORT_PERIOD,
            )
            assert usd_report_response.status_code == 201
            usd_report_payload = deepcopy(usd_report_response.json())
            usd_report = PortfolioReportV2Response.model_validate(
                usd_report_payload
            )
            assert usd_report.schema_version == (
                PORTFOLIO_ANALYSIS_RESPONSE_V2_SCHEMA_VERSION
            )
            assert usd_report.valuation.valuation_currency == "USD"
            assert usd_report.valuation.total_current_value_usd == Decimal("1000")
            assert [holding.current_allocation for holding in usd_report.holdings] == [
                Decimal("0.2"),
                Decimal("0.8"),
            ]
            assert [holding.symbol for holding in usd_report.holdings] == [
                "AAPL",
                "MSFT",
            ]
            assert [holding.asset_price for holding in usd_report.holdings] == [
                Decimal("100"),
                Decimal("200"),
            ]
            assert [
                holding.current_value_usd for holding in usd_report.holdings
            ] == [Decimal("200"), Decimal("800")]
            assert [
                (
                    holding.invested_amount,
                    holding.invested_currency,
                    holding.shares,
                    holding.purchase_date,
                    holding.position,
                )
                for holding in usd_report.holdings
            ] == [
                (
                    Decimal("150.25"),
                    "USD",
                    Decimal("2"),
                    date(2025, 1, 2),
                    0,
                ),
                (
                    Decimal("10000"),
                    "THB",
                    Decimal("4"),
                    date(2025, 2, 3),
                    1,
                ),
            ]
            assert all(holding.asset_metrics is not None for holding in usd_report.holdings)
            assert all(holding.risk_driver.rank >= 1 for holding in usd_report.holdings)

            thb_report_response = client.post(
                f"{report_path}?currency=THB",
                headers=owner_headers,
                json=REPORT_PERIOD,
            )
            assert thb_report_response.status_code == 201
            thb_report_payload = deepcopy(thb_report_response.json())
            thb_report = PortfolioReportV2Response.model_validate(
                thb_report_payload
            )
            assert thb_report.valuation.valuation_currency == "THB"
            assert thb_report.valuation.total_current_value == Decimal("35000")
            assert thb_report.valuation.fx is not None
            assert thb_report.valuation.fx.rate == Decimal("35")

            with factory() as session:
                raw_report = session.get(Analysis, usd_report.id)
                raw_thb_report = session.get(Analysis, thb_report.id)
                assert raw_report is not None
                assert raw_thb_report is not None
                assert raw_report.schema_version == (
                    PORTFOLIO_ANALYSIS_RESPONSE_V2_SCHEMA_VERSION
                )
                PortfolioReportV2Snapshot.model_validate(raw_report.result_snapshot)
                PortfolioReportV2Snapshot.model_validate(
                    raw_thb_report.result_snapshot
                )
                assert isinstance(
                    raw_report.result_snapshot["valuation"]["total_current_value_usd"],
                    str,
                )
                assert isinstance(
                    raw_report.result_snapshot["valuation"]["requested_date"],
                    str,
                )

            usd_report_get = client.get(
                f"{report_path}/{usd_report.id}",
                headers=owner_headers,
            )
            assert usd_report_get.status_code == 200
            assert usd_report_get.json() == usd_report_payload

            history_path = f"/api/portfolios/{portfolio_id}/simulations"
            historical_post = f"{history_path}/historical-scenarios"
            allocation_post = f"{history_path}/allocations"
            combined_post = f"{history_path}/combined"
            simulation_specs = [
                (
                    "historical-scenario",
                    historical_post,
                    {"scenario_id": SCENARIO_ID},
                    HISTORICAL_SCENARIO_SIMULATION_RESPONSE_V2_SCHEMA_VERSION,
                ),
                (
                    "allocation",
                    allocation_post,
                    {**REPORT_PERIOD, "modified_allocation": MODIFIED_ALLOCATION},
                    ALLOCATION_SIMULATION_RESPONSE_V2_SCHEMA_VERSION,
                ),
                (
                    "combined",
                    combined_post,
                    {
                        "scenario_id": SCENARIO_ID,
                        "modified_allocation": MODIFIED_ALLOCATION,
                    },
                    COMBINED_SIMULATION_RESPONSE_V2_SCHEMA_VERSION,
                ),
            ]
            saved_simulations: dict[str, tuple[UUID, dict[str, object]]] = {}
            for simulation_type, post_path, payload, expected_version in simulation_specs:
                _, simulation_id, detail_payload = _run_and_get_simulation(
                    client,
                    post_path=post_path,
                    history_path=history_path,
                    detail_base_path=history_path,
                    headers=owner_headers,
                    payload=payload,
                )
                detail = SimulationHistoryV2DetailResponse.model_validate(
                    detail_payload
                )
                assert detail.simulation_type == simulation_type
                assert detail.schema_version == expected_version
                assert detail.baseline.valuation_date == PHASE12_CURRENT_DATE
                assert detail.baseline.total_current_value_usd == Decimal("1000")
                assert [holding.symbol for holding in detail.baseline.holdings] == [
                    "AAPL",
                    "MSFT",
                ]
                assert [
                    holding.current_allocation for holding in detail.baseline.holdings
                ] == [Decimal("0.2"), Decimal("0.8")]
                assert [
                    holding.asset_price for holding in detail.baseline.holdings
                ] == [Decimal("100"), Decimal("200")]
                assert [
                    holding.current_value_usd
                    for holding in detail.baseline.holdings
                ] == [Decimal("200"), Decimal("800")]
                assert [
                    (
                        holding.invested_amount,
                        holding.invested_currency,
                        holding.shares,
                        holding.purchase_date,
                        holding.position,
                    )
                    for holding in detail.baseline.holdings
                ] == [
                    (
                        Decimal("150.25"),
                        "USD",
                        Decimal("2"),
                        date(2025, 1, 2),
                        0,
                    ),
                    (
                        Decimal("10000"),
                        "THB",
                        Decimal("4"),
                        date(2025, 2, 3),
                        1,
                    ),
                ]
                saved_simulations[simulation_type] = (
                    simulation_id,
                    deepcopy(detail_payload),
                )

                with factory() as session:
                    raw_simulation = session.get(Simulation, simulation_id)
                    assert raw_simulation is not None
                    assert raw_simulation.schema_version == expected_version
                    restored = restore_simulation_snapshot(
                        simulation_type=simulation_type,
                        schema_version=raw_simulation.schema_version,
                        snapshot=raw_simulation.result_snapshot,
                    )
                    assert restored.baseline is not None
                    assert isinstance(
                        raw_simulation.result_snapshot["baseline"][
                            "total_current_value_usd"
                        ],
                        str,
                    )
                    assert isinstance(
                        raw_simulation.result_snapshot["baseline"]["valuation_date"],
                        str,
                    )

            _change_asset_prices(factory)
            changed_usd_response = client.get(
                f"/api/portfolios/{portfolio_id}/valuation",
                headers=owner_headers,
            )
            assert changed_usd_response.status_code == 200
            changed_usd = PortfolioValuationResponse.model_validate(
                changed_usd_response.json()
            )
            assert changed_usd.total_current_value_usd == Decimal("1200")
            assert [holding.current_value_usd for holding in changed_usd.holdings] == [
                Decimal("600"),
                Decimal("600"),
            ]
            assert [holding.current_allocation for holding in changed_usd.holdings] == [
                Decimal("0.5"),
                Decimal("0.5"),
            ]
            assert client.get(
                f"{report_path}/{usd_report.id}", headers=owner_headers
            ).json() == usd_report_payload
            assert client.get(
                f"{report_path}/{thb_report.id}", headers=owner_headers
            ).json() == thb_report_payload
            for simulation_id, original_detail in saved_simulations.values():
                unchanged = client.get(
                    f"{history_path}/{simulation_id}",
                    headers=owner_headers,
                )
                assert unchanged.status_code == 200
                assert unchanged.json() == original_detail

            before_rollback = _holding_snapshot(
                _portfolio_with_holdings(factory, portfolio_id)
            )
            assert before_rollback == original_holding_snapshot
            with factory() as session:
                repository = PortfolioRepository(session)
                with pytest.raises(IntegrityError):
                    repository.replace_real_holdings(
                        portfolio_id,
                        (
                            (
                                "AAPL",
                                Decimal("1"),
                                "EUR",
                                Decimal("1"),
                                date(2025, 1, 1),
                            ),
                        ),
                    )
                session.rollback()
            assert _holding_snapshot(
                _portfolio_with_holdings(factory, portfolio_id)
            ) == before_rollback

            _delete_market_rows(factory, symbols=("AAPL", "MSFT"))
            with factory() as session:
                latest_asset_dates = tuple(
                    session.execute(
                        text(
                            "SELECT symbol, max(date) FROM market_data "
                            "WHERE symbol = ANY(:symbols) GROUP BY symbol "
                            "ORDER BY symbol"
                        ),
                        {"symbols": ["AAPL", "MSFT"]},
                    ).tuples()
                )
            assert latest_asset_dates
            assert all(
                PHASE12_CURRENT_DATE - latest_date > timedelta(days=4)
                for _, latest_date in latest_asset_dates
            )

            stale_valuation = client.get(
                f"/api/portfolios/{portfolio_id}/valuation",
                headers=owner_headers,
            )
            assert stale_valuation.status_code == 503
            fake_provider.reset()
            live_ai_stale = client.post(
                "/api/agent/explain",
                headers=owner_headers,
                json={
                    "portfolio_id": str(portfolio_id),
                    "message": "Explain my current portfolio risk.",
                },
            )
            assert live_ai_stale.status_code == 503
            assert fake_provider.requests == []

            analysis_count_before_failure = _count_for_portfolio(
                factory,
                Analysis,
                portfolio_id,
            )
            failed_report = client.post(
                report_path,
                headers=owner_headers,
                json=REPORT_PERIOD,
            )
            assert failed_report.status_code == 503
            assert _count_for_portfolio(factory, Analysis, portfolio_id) == (
                analysis_count_before_failure
            )

            simulation_count_before_failure = _count_for_portfolio(
                factory,
                Simulation,
                portfolio_id,
            )
            failed_simulation = client.post(
                allocation_post,
                headers=owner_headers,
                json={**REPORT_PERIOD, "modified_allocation": MODIFIED_ALLOCATION},
            )
            assert failed_simulation.status_code == 503
            assert _count_for_portfolio(factory, Simulation, portfolio_id) == (
                simulation_count_before_failure
            )

            assert client.get(
                f"{report_path}/{usd_report.id}", headers=owner_headers
            ).json() == usd_report_payload
            for simulation_id, original_detail in saved_simulations.values():
                response = client.get(
                    f"{history_path}/{simulation_id}",
                    headers=owner_headers,
                )
                assert response.status_code == 200
                assert response.json() == original_detail

            fake_provider.reset()
            saved_report_ai = client.post(
                "/api/agent/explain",
                headers=owner_headers,
                json={
                    "portfolio_id": str(portfolio_id),
                    "report_id": str(usd_report.id),
                    "message": "Explain this saved report.",
                },
            )
            assert saved_report_ai.status_code == 200
            assert len(fake_provider.requests) == 1
            assert fake_provider.requests[0].grounded_context["report"][
                "schema_version"
            ] == PORTFOLIO_ANALYSIS_RESPONSE_V2_SCHEMA_VERSION
            assert "holdings" not in fake_provider.requests[0].grounded_context[
                "portfolio"
            ]

            historical_id = saved_simulations["historical-scenario"][0]
            fake_provider.reset()
            saved_simulation_ai = client.post(
                "/api/agent/explain",
                headers=owner_headers,
                json={
                    "portfolio_id": str(portfolio_id),
                    "simulation_id": str(historical_id),
                    "message": "Explain this saved simulation.",
                },
            )
            assert saved_simulation_ai.status_code == 200
            assert len(fake_provider.requests) == 1
            assert fake_provider.requests[0].grounded_context["simulation"][
                "schema_version"
            ] == HISTORICAL_SCENARIO_SIMULATION_RESPONSE_V2_SCHEMA_VERSION

            fake_provider.reset()
            advice_refusal = client.post(
                "/api/agent/explain",
                headers=owner_headers,
                json={
                    "portfolio_id": str(portfolio_id),
                    "message": "Should I buy AAPL?",
                },
            )
            assert advice_refusal.status_code == 200
            assert fake_provider.requests == []

            _insert_market_rows(
                factory,
                symbols=("AAPL", "MSFT"),
                changed=True,
            )
            _delete_market_rows(factory, symbols=("THB=X",))

            usd_without_fx = client.get(
                f"/api/portfolios/{portfolio_id}/valuation",
                headers=owner_headers,
            )
            assert usd_without_fx.status_code == 200
            assert usd_without_fx.json()["fx"] is None
            assert client.get(
                f"/api/portfolios/{portfolio_id}/valuation?currency=THB",
                headers=owner_headers,
            ).status_code == 503

            analysis_count_before_fx_failure = _count_for_portfolio(
                factory,
                Analysis,
                portfolio_id,
            )
            usd_without_fx_report = client.post(
                report_path,
                headers=owner_headers,
                json=REPORT_PERIOD,
            )
            assert usd_without_fx_report.status_code == 201
            assert client.post(
                f"{report_path}?currency=THB",
                headers=owner_headers,
                json=REPORT_PERIOD,
            ).status_code == 503
            assert _count_for_portfolio(factory, Analysis, portfolio_id) == (
                analysis_count_before_fx_failure + 1
            )

            for _, post_path, payload, _ in simulation_specs:
                response = client.post(
                    post_path,
                    headers=owner_headers,
                    json=payload,
                )
                assert response.status_code == 200

            fake_provider.reset()
            live_ai_without_fx = client.post(
                "/api/agent/explain",
                headers=owner_headers,
                json={
                    "portfolio_id": str(portfolio_id),
                    "message": "Explain my current portfolio risk.",
                },
            )
            assert live_ai_without_fx.status_code == 200
            assert len(fake_provider.requests) == 1
            live_context = fake_provider.requests[0].grounded_context["portfolio"]
            assert live_context["valuation"]["valuation_currency"] == "USD"
            assert "fx" not in live_context["valuation"]
            assert [holding["current_allocation"] for holding in live_context["holdings"]] == [
                "0.5",
                "0.5",
            ]
            assert client.get(
                f"{report_path}/{thb_report.id}", headers=owner_headers
            ).json() == thb_report_payload
            _insert_market_rows(factory, symbols=("THB=X",), changed=True)

            wrong_owner_responses = [
                client.get(
                    f"/api/portfolios/{portfolio_id}", headers=other_headers
                ),
                client.get(
                    f"/api/portfolios/{portfolio_id}/valuation",
                    headers=other_headers,
                ),
                client.get(
                    f"{report_path}/{usd_report.id}", headers=other_headers
                ),
                client.get(
                    f"{history_path}/{historical_id}", headers=other_headers
                ),
            ]
            assert all(response.status_code == 404 for response in wrong_owner_responses)
            assert all(
                response.json() == {"detail": "Portfolio not found"}
                for response in wrong_owner_responses
            )
            assert client.get(
                f"/api/portfolios/{portfolio_id}"
            ).status_code == 401
            fake_provider.reset()
            wrong_owner_ai = client.post(
                "/api/agent/explain",
                headers=other_headers,
                json={
                    "portfolio_id": str(portfolio_id),
                    "report_id": str(usd_report.id),
                    "message": "Explain this saved report.",
                },
            )
            assert wrong_owner_ai.status_code == 404
            assert fake_provider.requests == []

            legacy_create = client.post(
                "/api/portfolios",
                headers=owner_headers,
                json={"name": LEGACY_PORTFOLIO_NAME},
            )
            assert legacy_create.status_code == 201
            legacy_portfolio_id = UUID(legacy_create.json()["id"])
            with factory.begin() as session:
                legacy_rows = PortfolioRepository(session).replace_holdings(
                    legacy_portfolio_id,
                    (
                        ("AAPL", Decimal("0.4")),
                        ("MSFT", Decimal("0.6")),
                    ),
                )
                assert legacy_rows is not None

            legacy_detail_response = client.get(
                f"/api/portfolios/{legacy_portfolio_id}",
                headers=owner_headers,
            )
            assert legacy_detail_response.status_code == 200
            legacy_detail = PortfolioResponse.model_validate(
                legacy_detail_response.json()
            )
            assert [holding.weight for holding in legacy_detail.holdings] == [
                0.4,
                0.6,
            ]
            assert all(
                holding.invested_amount is None
                and holding.invested_currency is None
                and holding.shares is None
                and holding.purchase_date is None
                for holding in legacy_detail.holdings
            )
            assert client.get(
                f"/api/portfolios/{legacy_portfolio_id}/valuation",
                headers=owner_headers,
            ).status_code == 409

            legacy_report_path = (
                f"/api/portfolios/{legacy_portfolio_id}/reports"
            )
            legacy_report_response = client.post(
                legacy_report_path,
                headers=owner_headers,
                json=REPORT_PERIOD,
            )
            assert legacy_report_response.status_code == 201
            legacy_report = PortfolioReportResponse.model_validate(
                legacy_report_response.json()
            )
            with factory() as session:
                raw_legacy_report = session.get(Analysis, legacy_report.id)
                assert raw_legacy_report is not None
                assert raw_legacy_report.schema_version == (
                    PORTFOLIO_ANALYSIS_RESPONSE_SCHEMA_VERSION
                )

            legacy_history_path = (
                f"/api/portfolios/{legacy_portfolio_id}/simulations"
            )
            _, legacy_simulation_id, legacy_simulation_payload = (
                _run_and_get_simulation(
                    client,
                    post_path=f"{legacy_history_path}/historical-scenarios",
                    history_path=legacy_history_path,
                    detail_base_path=legacy_history_path,
                    headers=owner_headers,
                    payload={"scenario_id": SCENARIO_ID},
                )
            )
            legacy_simulation = SimulationHistoryDetailResponse.model_validate(
                legacy_simulation_payload
            )
            assert legacy_simulation.simulation_type == "historical-scenario"
            with factory() as session:
                raw_legacy_simulation = session.get(
                    Simulation,
                    legacy_simulation_id,
                )
                assert raw_legacy_simulation is not None
                assert raw_legacy_simulation.schema_version == (
                    HISTORICAL_SCENARIO_SIMULATION_RESPONSE_SCHEMA_VERSION
                )

            legacy_duplicate_response = client.post(
                f"/api/portfolios/{legacy_portfolio_id}/duplicate",
                headers=owner_headers,
                json={"name": LEGACY_DUPLICATE_NAME},
            )
            assert legacy_duplicate_response.status_code == 201
            legacy_duplicate = PortfolioResponse.model_validate(
                legacy_duplicate_response.json()
            )
            assert legacy_duplicate.id != legacy_portfolio_id
            assert [holding.id for holding in legacy_duplicate.holdings] != [
                holding.id for holding in legacy_detail.holdings
            ]
            assert [holding.weight for holding in legacy_duplicate.holdings] == [
                0.4,
                0.6,
            ]
            assert all(
                holding.invested_amount is None
                and holding.invested_currency is None
                and holding.shares is None
                and holding.purchase_date is None
                for holding in legacy_duplicate.holdings
            )

            with factory() as session:
                real_holding_count = len(
                    tuple(
                        session.scalars(
                            select(Holding.id).where(
                                Holding.portfolio_id == portfolio_id,
                                Holding.weight.is_(None),
                            )
                        )
                    )
                )
                assert real_holding_count == 2
    finally:
        app_settings.jwt_secret_key = original_jwt_secret
        if previous_database_override is None:
            app.dependency_overrides.pop(get_database_session, None)
        else:
            app.dependency_overrides[get_database_session] = (
                previous_database_override
            )
        if previous_provider_override is None:
            app.dependency_overrides.pop(
                agent_route_module.get_agent_provider,
                None,
            )
        else:
            app.dependency_overrides[agent_route_module.get_agent_provider] = (
                previous_provider_override
            )
        _cleanup_reserved_rows(engine)
        assert _row_counts(engine) == baseline_counts
        assert _non_market_snapshot(engine) == baseline_non_market
        assert _reserved_market_rows(engine) == baseline_overlap
        _assert_reserved_identities_absent(engine)
        engine.dispose()
