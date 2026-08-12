from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Numeric,
    UniqueConstraint,
    inspect,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable
from sqlalchemy.types import Uuid

from backend.app.database import Base, Holding, Portfolio, User


EXPECTED_TABLES = {"users", "portfolios", "holdings"}


def test_models_use_existing_aura_base_and_expected_tables() -> None:
    assert issubclass(User, Base)
    assert issubclass(Portfolio, Base)
    assert issubclass(Holding, Base)
    assert User.__tablename__ == "users"
    assert Portfolio.__tablename__ == "portfolios"
    assert Holding.__tablename__ == "holdings"
    assert set(Base.metadata.tables) == EXPECTED_TABLES


def test_primary_keys_are_application_generated_python_uuids() -> None:
    generated_values: list[UUID] = []

    for model in (User, Portfolio, Holding):
        id_column = model.__table__.c.id
        assert id_column.primary_key is True
        assert id_column.nullable is False
        assert isinstance(id_column.type, Uuid)
        assert id_column.type.as_uuid is True
        assert id_column.default is not None
        assert callable(id_column.default.arg)
        generated_values.append(id_column.default.arg(None))

    assert all(isinstance(value, UUID) for value in generated_values)
    assert len(set(generated_values)) == len(generated_values)


def test_required_model_columns_are_not_nullable() -> None:
    for column_name in ("id", "created_at", "updated_at"):
        assert User.__table__.c[column_name].nullable is False

    for column_name in (
        "id",
        "user_id",
        "name",
        "created_at",
        "updated_at",
    ):
        assert Portfolio.__table__.c[column_name].nullable is False

    for column_name in (
        "id",
        "portfolio_id",
        "symbol",
        "weight",
        "position",
        "created_at",
        "updated_at",
    ):
        assert Holding.__table__.c[column_name].nullable is False


def test_foreign_keys_target_owners_and_cascade_on_delete() -> None:
    portfolio_user_fk = next(iter(Portfolio.__table__.c.user_id.foreign_keys))
    holding_portfolio_fk = next(
        iter(Holding.__table__.c.portfolio_id.foreign_keys)
    )

    assert portfolio_user_fk.target_fullname == "users.id"
    assert portfolio_user_fk.ondelete == "CASCADE"
    assert holding_portfolio_fk.target_fullname == "portfolios.id"
    assert holding_portfolio_fk.ondelete == "CASCADE"


def test_ownership_relationships_mirror_delete_semantics() -> None:
    user_portfolios = inspect(User).relationships.portfolios
    portfolio_user = inspect(Portfolio).relationships.user
    portfolio_holdings = inspect(Portfolio).relationships.holdings
    holding_portfolio = inspect(Holding).relationships.portfolio

    assert user_portfolios.back_populates == "user"
    assert portfolio_user.back_populates == "portfolios"
    assert "delete-orphan" in user_portfolios.cascade
    assert user_portfolios.passive_deletes is True

    assert portfolio_holdings.back_populates == "portfolio"
    assert holding_portfolio.back_populates == "holdings"
    assert "delete-orphan" in portfolio_holdings.cascade
    assert portfolio_holdings.passive_deletes is True
    assert list(portfolio_holdings.order_by) == [Holding.__table__.c.position]


def test_relationships_link_owned_objects_without_database_access() -> None:
    user = User()
    portfolio = Portfolio(name="Long-term portfolio")
    holding = Holding(
        symbol="AAPL",
        weight=Decimal("1.000000000000000000"),
        position=0,
    )

    user.portfolios.append(portfolio)
    portfolio.holdings.append(holding)

    assert portfolio.user is user
    assert holding.portfolio is portfolio
    assert holding.symbol == "AAPL"


def test_holding_uses_exact_weight_and_integer_position_types() -> None:
    weight_type = Holding.__table__.c.weight.type

    assert isinstance(weight_type, Numeric)
    assert weight_type.precision == 20
    assert weight_type.scale == 18
    assert Holding.__table__.c.position.type.python_type is int


def test_holding_check_constraints_cover_only_row_level_bounds() -> None:
    checks = {
        constraint.name: str(constraint.sqltext)
        for constraint in Holding.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert checks == {
        "ck_holdings_weight_range": "weight >= 0 AND weight <= 1",
        "ck_holdings_position_non_negative": "position >= 0",
    }
    assert all("sum" not in expression.lower() for expression in checks.values())


def test_holding_has_approved_composite_unique_constraints() -> None:
    unique_columns = {
        tuple(column.name for column in constraint.columns)
        for constraint in Holding.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    }

    assert unique_columns == {
        ("portfolio_id", "symbol"),
        ("portfolio_id", "position"),
    }


def test_holding_does_not_persist_deferred_financial_values() -> None:
    column_names = set(Holding.__table__.c.keys())

    assert "shares" not in column_names
    assert "invested_amount" not in column_names
    assert "amount_invested" not in column_names
    assert "current_market_value" not in column_names


def test_timestamp_columns_are_timezone_capable_and_consistent() -> None:
    for model in (User, Portfolio, Holding):
        created_at = model.__table__.c.created_at
        updated_at = model.__table__.c.updated_at

        assert isinstance(created_at.type, DateTime)
        assert created_at.type.timezone is True
        assert created_at.server_default is not None
        assert created_at.onupdate is None

        assert isinstance(updated_at.type, DateTime)
        assert updated_at.type.timezone is True
        assert updated_at.server_default is not None
        assert updated_at.onupdate is not None


def test_models_compile_as_postgresql_ddl_without_connecting() -> None:
    dialect = postgresql.dialect()

    ddl_by_table = {
        table.name: str(CreateTable(table).compile(dialect=dialect))
        for table in Base.metadata.sorted_tables
    }

    assert set(ddl_by_table) == EXPECTED_TABLES
    assert "UUID" in ddl_by_table["users"]
    assert "TIMESTAMP WITH TIME ZONE" in ddl_by_table["users"]
    assert "NUMERIC(20, 18)" in ddl_by_table["holdings"]
    assert "ON DELETE CASCADE" in ddl_by_table["portfolios"]
    assert "ON DELETE CASCADE" in ddl_by_table["holdings"]
