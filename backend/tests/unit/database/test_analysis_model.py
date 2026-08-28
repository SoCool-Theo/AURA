from datetime import date
from uuid import UUID

from sqlalchemy import CheckConstraint, Date, DateTime, Text, inspect
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.schema import CreateIndex, CreateTable
from sqlalchemy.types import Uuid

from backend.app.database import (
    Analysis,
    Base,
    Holding,
    MarketData,
    Portfolio,
    User,
)


EXPECTED_TABLES = {
    "users",
    "portfolios",
    "holdings",
    "market_data",
    "analyses",
    "simulations",
}


def test_analysis_uses_existing_base_and_expected_table_name() -> None:
    assert issubclass(Analysis, Base)
    assert Analysis.__tablename__ == "analyses"
    assert set(Base.metadata.tables) == EXPECTED_TABLES
    assert User.__table__ is Base.metadata.tables["users"]
    assert Portfolio.__table__ is Base.metadata.tables["portfolios"]
    assert Holding.__table__ is Base.metadata.tables["holdings"]
    assert MarketData.__table__ is Base.metadata.tables["market_data"]


def test_analysis_has_only_approved_columns() -> None:
    assert tuple(Analysis.__table__.c.keys()) == (
        "id",
        "portfolio_id",
        "start_date",
        "end_date",
        "schema_version",
        "result_snapshot",
        "created_at",
        "updated_at",
    )

    disallowed_metric_columns = {
        "max_drawdown",
        "annualized_return",
        "annualized_volatility",
        "sharpe_ratio",
        "risk_score",
        "risk_level",
        "correlation_matrix",
        "portfolio_returns",
    }
    assert disallowed_metric_columns.isdisjoint(Analysis.__table__.c.keys())


def test_analysis_primary_key_is_application_generated_python_uuid() -> None:
    id_column = Analysis.__table__.c.id

    assert id_column.primary_key is True
    assert id_column.nullable is False
    assert isinstance(id_column.type, Uuid)
    assert id_column.type.as_uuid is True
    assert id_column.default is not None
    assert callable(id_column.default.arg)
    assert isinstance(id_column.default.arg(None), UUID)


def test_analysis_portfolio_foreign_key_cascades_on_delete() -> None:
    portfolio_id = Analysis.__table__.c.portfolio_id
    foreign_key = next(iter(portfolio_id.foreign_keys))

    assert portfolio_id.nullable is False
    assert foreign_key.target_fullname == "portfolios.id"
    assert foreign_key.ondelete == "CASCADE"


def test_portfolio_analysis_relationship_mirrors_ownership() -> None:
    portfolio_analyses = inspect(Portfolio).relationships.analyses
    analysis_portfolio = inspect(Analysis).relationships.portfolio

    assert portfolio_analyses.back_populates == "portfolio"
    assert analysis_portfolio.back_populates == "analyses"
    assert "delete-orphan" in portfolio_analyses.cascade
    assert portfolio_analyses.passive_deletes is True


def test_analysis_period_uses_required_dates_and_allows_equal_dates() -> None:
    start_date = Analysis.__table__.c.start_date
    end_date = Analysis.__table__.c.end_date
    constraints = {
        constraint.name: str(constraint.sqltext)
        for constraint in Analysis.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert isinstance(start_date.type, Date)
    assert start_date.nullable is False
    assert isinstance(end_date.type, Date)
    assert end_date.nullable is False
    assert constraints == {
        "ck_analyses_date_order": "start_date <= end_date"
    }

    same_date = date(2026, 8, 13)
    analysis = Analysis(
        portfolio_id=UUID(int=1),
        start_date=same_date,
        end_date=same_date,
        schema_version="1",
        result_snapshot={},
    )
    assert analysis.start_date == analysis.end_date


def test_schema_version_is_required_and_has_no_default() -> None:
    schema_version = Analysis.__table__.c.schema_version

    assert isinstance(schema_version.type, Text)
    assert schema_version.nullable is False
    assert schema_version.default is None
    assert schema_version.server_default is None


def test_result_snapshot_is_required_postgresql_jsonb() -> None:
    result_snapshot = Analysis.__table__.c.result_snapshot

    assert isinstance(result_snapshot.type, JSONB)
    assert result_snapshot.nullable is False
    assert result_snapshot.default is None
    assert result_snapshot.server_default is None


def test_snapshot_assignment_preserves_json_semantics_and_order() -> None:
    snapshot = {
        "max_drawdown": {"max_drawdown": -0.25},
        "risk_drivers": {
            "entries": [
                {"symbol": "FIRST", "component": -0.04},
                {"symbol": "SECOND", "component": 0.12},
            ]
        },
        "diversification": {"overall_score": None},
        "correlation_matrix": {
            "symbols": ["FIRST", "SECOND"],
            "values": [[1.0, None], [None, 1.0]],
        },
        "portfolio_returns": [
            {"date": "2026-01-02", "portfolio_return": -0.01},
            {"date": "2026-01-03", "portfolio_return": 0.02},
        ],
    }
    analysis = Analysis(
        portfolio_id=UUID(int=1),
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        schema_version="1",
        result_snapshot=snapshot,
    )

    assert analysis.result_snapshot is snapshot
    assert analysis.result_snapshot["max_drawdown"]["max_drawdown"] == -0.25
    assert analysis.result_snapshot["risk_drivers"]["entries"][0][
        "component"
    ] == -0.04
    assert analysis.result_snapshot["diversification"]["overall_score"] is None
    assert [
        point["date"] for point in analysis.result_snapshot["portfolio_returns"]
    ] == ["2026-01-02", "2026-01-03"]


def test_analysis_timestamps_are_timezone_capable_and_consistent() -> None:
    created_at = Analysis.__table__.c.created_at
    updated_at = Analysis.__table__.c.updated_at

    assert isinstance(created_at.type, DateTime)
    assert created_at.type.timezone is True
    assert created_at.nullable is False
    assert created_at.server_default is not None
    assert created_at.onupdate is None

    assert isinstance(updated_at.type, DateTime)
    assert updated_at.type.timezone is True
    assert updated_at.nullable is False
    assert updated_at.server_default is not None
    assert updated_at.onupdate is not None


def test_analysis_has_only_portfolio_created_at_index() -> None:
    indexes = {
        index.name: tuple(column.name for column in index.columns)
        for index in Analysis.__table__.indexes
    }

    assert indexes == {
        "ix_analyses_portfolio_created_at": ("portfolio_id", "created_at")
    }


def test_analysis_compiles_as_postgresql_ddl_without_connecting() -> None:
    dialect = postgresql.dialect()
    table_ddl = str(CreateTable(Analysis.__table__).compile(dialect=dialect))
    analysis_index = next(iter(Analysis.__table__.indexes))
    index_ddl = str(CreateIndex(analysis_index).compile(dialect=dialect))

    assert "UUID" in table_ddl
    assert "JSONB" in table_ddl
    assert "FOREIGN KEY(portfolio_id)" in table_ddl
    assert "REFERENCES portfolios (id) ON DELETE CASCADE" in table_ddl
    assert "CHECK (start_date <= end_date)" in table_ddl
    assert index_ddl == (
        "CREATE INDEX ix_analyses_portfolio_created_at "
        "ON analyses (portfolio_id, created_at)"
    )
