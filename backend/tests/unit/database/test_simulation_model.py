from datetime import date
from uuid import UUID

from sqlalchemy import CheckConstraint, Date, DateTime, Text, inspect
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.schema import CreateIndex, CreateTable
from sqlalchemy.types import Uuid

from backend.app.database import Base
from backend.app.database.models import Portfolio, Simulation


def test_simulation_uses_registered_base_and_only_approved_columns() -> None:
    assert issubclass(Simulation, Base)
    assert Simulation.__tablename__ == "simulations"
    assert Base.metadata.tables["simulations"] is Simulation.__table__
    assert tuple(Simulation.__table__.c.keys()) == (
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
    assert "updated_at" not in Simulation.__table__.c
    assert "user_id" not in Simulation.__table__.c


def test_simulation_id_and_portfolio_ownership_follow_uuid_conventions() -> None:
    id_column = Simulation.__table__.c.id
    portfolio_id = Simulation.__table__.c.portfolio_id
    foreign_key = next(iter(portfolio_id.foreign_keys))

    assert id_column.primary_key is True
    assert isinstance(id_column.type, Uuid)
    assert id_column.type.as_uuid is True
    assert callable(id_column.default.arg)
    assert isinstance(id_column.default.arg(None), UUID)
    assert portfolio_id.nullable is False
    assert foreign_key.target_fullname == "portfolios.id"
    assert foreign_key.ondelete == "CASCADE"


def test_simulation_columns_and_database_checks_match_contract() -> None:
    table = Simulation.__table__
    checks = {
        constraint.name: str(constraint.sqltext)
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert isinstance(table.c.simulation_type.type, Text)
    assert table.c.simulation_type.nullable is False
    assert isinstance(table.c.scenario_id.type, Text)
    assert table.c.scenario_id.nullable is True
    assert isinstance(table.c.requested_start_date.type, Date)
    assert isinstance(table.c.requested_end_date.type, Date)
    assert table.c.requested_start_date.nullable is False
    assert table.c.requested_end_date.nullable is False
    assert checks == {
        "ck_simulations_type": (
            "simulation_type IN ('historical-scenario', 'allocation', "
            "'combined')"
        ),
        "ck_simulations_scenario_by_type": (
            "(simulation_type = 'allocation' AND scenario_id IS NULL) OR "
            "(simulation_type <> 'allocation' AND scenario_id IS NOT NULL)"
        ),
        "ck_simulations_date_order": (
            "requested_start_date <= requested_end_date"
        ),
    }


def test_snapshot_schema_version_and_created_timestamp_are_immutable_fields() -> None:
    table = Simulation.__table__

    assert isinstance(table.c.schema_version.type, Text)
    assert table.c.schema_version.nullable is False
    assert table.c.schema_version.default is None
    assert isinstance(table.c.result_snapshot.type, JSONB)
    assert table.c.result_snapshot.nullable is False
    assert table.c.result_snapshot.default is None
    assert isinstance(table.c.created_at.type, DateTime)
    assert table.c.created_at.type.timezone is True
    assert table.c.created_at.nullable is False
    assert table.c.created_at.server_default is not None
    assert table.c.created_at.onupdate is None

    simulation = Simulation(
        portfolio_id=UUID(int=1),
        simulation_type="allocation",
        scenario_id=None,
        requested_start_date=date(2026, 1, 1),
        requested_end_date=date(2026, 1, 1),
        schema_version="1",
        result_snapshot={"ordered": [1, None, 3]},
    )
    assert simulation.result_snapshot == {"ordered": [1, None, 3]}


def test_portfolio_simulation_relationship_matches_owned_cascade_pattern() -> None:
    portfolio_simulations = inspect(Portfolio).relationships.simulations
    simulation_portfolio = inspect(Simulation).relationships.portfolio

    assert portfolio_simulations.back_populates == "portfolio"
    assert simulation_portfolio.back_populates == "simulations"
    assert "delete-orphan" in portfolio_simulations.cascade
    assert portfolio_simulations.passive_deletes is True


def test_simulation_has_expected_index_and_postgresql_ddl() -> None:
    indexes = {
        index.name: tuple(column.name for column in index.columns)
        for index in Simulation.__table__.indexes
    }
    assert indexes == {
        "ix_simulations_portfolio_created_at": (
            "portfolio_id",
            "created_at",
        )
    }

    dialect = postgresql.dialect()
    table_ddl = str(CreateTable(Simulation.__table__).compile(dialect=dialect))
    index = next(iter(Simulation.__table__.indexes))
    index_ddl = str(CreateIndex(index).compile(dialect=dialect))

    assert "JSONB" in table_ddl
    assert "TIMESTAMP WITH TIME ZONE" in table_ddl
    assert "REFERENCES portfolios (id) ON DELETE CASCADE" in table_ddl
    assert index_ddl == (
        "CREATE INDEX ix_simulations_portfolio_created_at "
        "ON simulations (portfolio_id, created_at)"
    )
