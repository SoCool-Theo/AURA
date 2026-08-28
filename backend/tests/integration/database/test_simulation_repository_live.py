"""Live PostgreSQL verification for simulation-history persistence."""

from collections.abc import Iterator
from datetime import UTC, date, datetime
import os
from pathlib import Path
from uuid import UUID, uuid4

from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
import pytest
import sqlalchemy as sa
from sqlalchemy import inspect, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from backend.app.core.config import settings
from backend.app.database.connection import create_database_engine
from backend.app.database.models import Portfolio, Simulation, User
from backend.app.database.repositories import (
    PortfolioRepository,
    SimulationRepository,
)


BACKEND_ROOT = Path(__file__).resolve().parents[3]
ALEMBIC_CONFIG_PATH = BACKEND_ROOT / "alembic.ini"
AUTHENTICATION_REVISION = "2b6e5d4a9c81"
SIMULATION_REVISION = "7c1e2f4a6b90"
APPLICATION_TABLES = {
    "users",
    "portfolios",
    "holdings",
    "market_data",
    "analyses",
    "simulations",
}


def _test_database_url() -> str:
    raw_url = os.getenv("AURA_TEST_DATABASE_URL")
    if not raw_url:
        pytest.skip("AURA_TEST_DATABASE_URL is not configured")
    url = make_url(raw_url)
    database_name = url.database or ""
    if url.drivername != "postgresql+psycopg":
        pytest.fail(
            "AURA_TEST_DATABASE_URL must use postgresql+psycopg",
            pytrace=False,
        )
    if database_name != "aura_test" and not database_name.startswith(
        "aura_test_"
    ):
        pytest.fail(
            "AURA_TEST_DATABASE_URL must target aura_test or aura_test_*",
            pytrace=False,
        )
    return raw_url


def _alembic_config() -> Config:
    return Config(ALEMBIC_CONFIG_PATH)


@pytest.fixture(scope="module")
def postgres_engine() -> Iterator[Engine]:
    raw_url = _test_database_url()
    engine = create_database_engine(raw_url)
    original_database_url = settings.database_url
    owns_schema = False

    try:
        with engine.connect() as connection:
            initial_tables = set(
                inspect(connection).get_table_names(schema="public")
            )
            unexpected = initial_tables - APPLICATION_TABLES - {
                "alembic_version"
            }
            if unexpected:
                pytest.fail(
                    "isolated test database contains unexpected public "
                    f"tables: {sorted(unexpected)}",
                    pytrace=False,
                )
            revision = MigrationContext.configure(
                connection
            ).get_current_revision()

        existing_application_tables = initial_tables & APPLICATION_TABLES
        if existing_application_tables:
            if existing_application_tables != APPLICATION_TABLES:
                pytest.fail(
                    "isolated test database has an incomplete application "
                    "schema",
                    pytrace=False,
                )
            if revision != SIMULATION_REVISION:
                pytest.fail(
                    "isolated test database migrations are not current",
                    pytrace=False,
                )
            with engine.connect() as connection:
                populated = {
                    table: int(
                        connection.scalar(
                            sa.text(f'SELECT COUNT(*) FROM "{table}"')
                        )
                        or 0
                    )
                    for table in APPLICATION_TABLES
                }
            if any(populated.values()):
                pytest.fail(
                    "isolated test database contains application rows",
                    pytrace=False,
                )
        else:
            if revision is not None:
                pytest.fail(
                    "isolated test database is not at Alembic base",
                    pytrace=False,
                )
        settings.database_url = raw_url  # type: ignore[assignment]
        if not existing_application_tables:
            command.upgrade(_alembic_config(), "head")
            owns_schema = True
        yield engine
    finally:
        try:
            if owns_schema:
                command.downgrade(_alembic_config(), "base")
        finally:
            settings.database_url = original_database_url
            engine.dispose()


@pytest.fixture
def session_factory(postgres_engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(
        bind=postgres_engine,
        class_=Session,
        autoflush=False,
        expire_on_commit=False,
    )


@pytest.fixture(autouse=True)
def clean_rows(postgres_engine: Engine) -> Iterator[None]:
    yield
    with postgres_engine.begin() as connection:
        connection.execute(
            sa.text(
                "TRUNCATE TABLE simulations, analyses, holdings, portfolios, "
                "users, market_data CASCADE"
            )
        )


def _create_portfolio(session: Session, name: str = "Core") -> Portfolio:
    user = User()
    session.add(user)
    session.flush()
    return PortfolioRepository(session).create(user_id=user.id, name=name)


def _create_simulation(
    repository: SimulationRepository,
    *,
    portfolio_id: UUID,
    simulation_type: str = "historical-scenario",
    scenario_id: str | None = "covid-19-shock-2020",
    start: date = date(2020, 2, 1),
    end: date = date(2020, 4, 30),
    snapshot: dict[str, object] | None = None,
) -> Simulation:
    return repository.create(
        portfolio_id=portfolio_id,
        simulation_type=simulation_type,
        scenario_id=scenario_id,
        requested_start_date=start,
        requested_end_date=end,
        schema_version="1.0",
        result_snapshot=snapshot or {"metrics": {"drawdown": -0.25}},
    )


def test_live_migration_has_exact_simulation_structure(
    postgres_engine: Engine,
) -> None:
    with postgres_engine.connect() as connection:
        inspector = inspect(connection)
        assert set(inspector.get_table_names(schema="public")) >= (
            APPLICATION_TABLES
        )
        columns = {
            column["name"]: column
            for column in inspector.get_columns("simulations", schema="public")
        }
        assert tuple(columns) == (
            "id",
            "portfolio_id",
            "simulation_type",
            "scenario_id",
            "requested_start_date",
            "requested_end_date",
            "schema_version",
            "result_snapshot",
            "created_at",
        )
        assert isinstance(columns["id"]["type"], postgresql.UUID)
        assert isinstance(columns["result_snapshot"]["type"], postgresql.JSONB)
        assert columns["scenario_id"]["nullable"] is True
        assert columns["created_at"]["type"].timezone is True

        checks = {
            constraint["name"]
            for constraint in inspector.get_check_constraints(
                "simulations", schema="public"
            )
        }
        assert checks == {
            "ck_simulations_type",
            "ck_simulations_scenario_by_type",
            "ck_simulations_date_order",
        }
        foreign_keys = inspector.get_foreign_keys(
            "simulations", schema="public"
        )
        assert len(foreign_keys) == 1
        assert foreign_keys[0]["referred_table"] == "portfolios"
        assert foreign_keys[0]["constrained_columns"] == ["portfolio_id"]
        assert foreign_keys[0]["options"]["ondelete"] == "CASCADE"
        indexes = {
            index["name"]: tuple(index["column_names"])
            for index in inspector.get_indexes("simulations", schema="public")
        }
        assert indexes["ix_simulations_portfolio_created_at"] == (
            "portfolio_id",
            "created_at",
        )
        revision = MigrationContext.configure(connection).get_current_revision()

    script = ScriptDirectory.from_config(_alembic_config())
    assert revision == SIMULATION_REVISION == script.get_current_head()
    assert len(list(script.walk_revisions())) == 3


@pytest.mark.parametrize(
    ("simulation_type", "scenario_id"),
    [
        ("historical-scenario", "covid-19-shock-2020"),
        ("allocation", None),
        ("combined", "covid-19-shock-2020"),
    ],
)
def test_live_repository_accepts_types_and_round_trips_fresh_session(
    session_factory: sessionmaker[Session],
    simulation_type: str,
    scenario_id: str | None,
) -> None:
    snapshot = {"kind": simulation_type, "values": [1.0, None, -0.2]}
    with session_factory.begin() as session:
        portfolio = _create_portfolio(session)
        created = _create_simulation(
            SimulationRepository(session),
            portfolio_id=portfolio.id,
            simulation_type=simulation_type,
            scenario_id=scenario_id,
            snapshot=snapshot,
        )
        simulation_id = created.id
        portfolio_id = portfolio.id

    snapshot["kind"] = "caller-mutated"
    with session_factory() as session:
        loaded = SimulationRepository(session).get_for_portfolio(
            portfolio_id=portfolio_id,
            simulation_id=simulation_id,
        )

    assert loaded is not None
    assert loaded.simulation_type == simulation_type
    assert loaded.scenario_id == scenario_id
    assert loaded.schema_version == "1.0"
    assert loaded.result_snapshot == {
        "kind": simulation_type,
        "values": [1.0, None, -0.2],
    }
    assert loaded.created_at.tzinfo is not None


@pytest.mark.parametrize(
    ("simulation_type", "scenario_id", "start", "end", "constraint"),
    [
        (
            "unsupported",
            "scenario",
            date(2020, 1, 1),
            date(2020, 1, 2),
            "ck_simulations_type",
        ),
        (
            "allocation",
            "scenario",
            date(2020, 1, 1),
            date(2020, 1, 2),
            "ck_simulations_scenario_by_type",
        ),
        (
            "historical-scenario",
            None,
            date(2020, 1, 1),
            date(2020, 1, 2),
            "ck_simulations_scenario_by_type",
        ),
        (
            "combined",
            None,
            date(2020, 1, 1),
            date(2020, 1, 2),
            "ck_simulations_scenario_by_type",
        ),
        (
            "allocation",
            None,
            date(2020, 1, 2),
            date(2020, 1, 1),
            "ck_simulations_date_order",
        ),
    ],
)
def test_live_database_rejects_invalid_simulation_rows(
    session_factory: sessionmaker[Session],
    simulation_type: str,
    scenario_id: str | None,
    start: date,
    end: date,
    constraint: str,
) -> None:
    with session_factory() as session:
        portfolio = _create_portfolio(session)
        with pytest.raises(IntegrityError) as raised:
            _create_simulation(
                SimulationRepository(session),
                portfolio_id=portfolio.id,
                simulation_type=simulation_type,
                scenario_id=scenario_id,
                start=start,
                end=end,
            )
        assert raised.value.orig.diag.constraint_name == constraint
        session.rollback()


def test_live_duplicate_records_ordering_and_portfolio_scope(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory.begin() as session:
        first_portfolio = _create_portfolio(session, "First")
        second_portfolio = _create_portfolio(session, "Second")
        repository = SimulationRepository(session)
        duplicate_one = _create_simulation(
            repository, portfolio_id=first_portfolio.id
        )
        duplicate_two = _create_simulation(
            repository, portfolio_id=first_portfolio.id
        )
        newest = _create_simulation(
            repository,
            portfolio_id=first_portfolio.id,
            simulation_type="allocation",
            scenario_id=None,
        )
        other = _create_simulation(
            repository, portfolio_id=second_portfolio.id
        )
        tied_ids = sorted([duplicate_one.id, duplicate_two.id])
        session.execute(
            sa.update(Simulation)
            .where(Simulation.id.in_(tied_ids))
            .values(created_at=datetime(2026, 1, 1, tzinfo=UTC))
        )
        session.execute(
            sa.update(Simulation)
            .where(Simulation.id == newest.id)
            .values(created_at=datetime(2026, 2, 1, tzinfo=UTC))
        )
        first_portfolio_id = first_portfolio.id
        second_portfolio_id = second_portfolio.id
        newest_id = newest.id
        other_id = other.id

    assert duplicate_one.id != duplicate_two.id
    with session_factory() as session:
        repository = SimulationRepository(session)
        listed = repository.list_for_portfolio(first_portfolio_id)
        assert [row.id for row in listed] == [newest_id, *tied_ids]
        assert {row.portfolio_id for row in listed} == {first_portfolio_id}
        assert repository.get_for_portfolio(
            portfolio_id=first_portfolio_id,
            simulation_id=other_id,
        ) is None
        assert repository.get_for_portfolio(
            portfolio_id=second_portfolio_id,
            simulation_id=uuid4(),
        ) is None


def test_live_portfolio_delete_cascades_simulations(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory.begin() as session:
        portfolio = _create_portfolio(session)
        simulation = _create_simulation(
            SimulationRepository(session), portfolio_id=portfolio.id
        )
        portfolio_id = portfolio.id
        simulation_id = simulation.id

    with session_factory.begin() as session:
        assert PortfolioRepository(session).delete(portfolio_id) is True

    with session_factory() as session:
        assert session.get(Simulation, simulation_id) is None
        assert session.scalar(select(sa.func.count()).select_from(Simulation)) == 0


def test_live_new_revision_downgrades_to_previous_head_and_reupgrades(
    postgres_engine: Engine,
) -> None:
    command.downgrade(_alembic_config(), AUTHENTICATION_REVISION)
    with postgres_engine.connect() as connection:
        inspector = inspect(connection)
        table_names = set(inspector.get_table_names(schema="public"))
        assert "simulations" not in table_names
        assert APPLICATION_TABLES - {"simulations"} <= table_names
        assert (
            MigrationContext.configure(connection).get_current_revision()
            == AUTHENTICATION_REVISION
        )

    command.upgrade(_alembic_config(), "head")
    with postgres_engine.connect() as connection:
        assert "simulations" in inspect(connection).get_table_names(
            schema="public"
        )
        assert (
            MigrationContext.configure(connection).get_current_revision()
            == SIMULATION_REVISION
        )
