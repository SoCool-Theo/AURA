from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Numeric,
    Text,
    UniqueConstraint,
    inspect,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable
from sqlalchemy.types import Uuid

from backend.app.database import Base, Holding, Portfolio, PortfolioType, User


EXPECTED_TABLES = {
    "analyses",
    "simulations",
    "users",
    "portfolios",
    "holdings",
    "market_data",
}


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
        "portfolio_type",
        "created_at",
        "updated_at",
    ):
        assert Portfolio.__table__.c[column_name].nullable is False

    for column_name in ("plan_currency", "source_plan_id"):
        assert Portfolio.__table__.c[column_name].nullable is True

    for column_name in (
        "id",
        "portfolio_id",
        "symbol",
        "position",
        "created_at",
        "updated_at",
    ):
        assert Holding.__table__.c[column_name].nullable is False

    for column_name in (
        "invested_amount",
        "proposed_amount",
        "invested_currency",
        "shares",
        "purchase_date",
        "weight",
    ):
        assert Holding.__table__.c[column_name].nullable is True


def test_user_credentials_are_nullable_text_and_support_legacy_construction(
) -> None:
    generated_user = User()
    explicit_id = uuid4()
    explicit_user = User(id=explicit_id)
    credential_user = User(
        email="canonical@example.com",
        password_hash="$argon2id$test-hash",
    )

    assert isinstance(User.__table__.c.email.type, Text)
    assert isinstance(User.__table__.c.password_hash.type, Text)
    assert User.__table__.c.email.nullable is True
    assert User.__table__.c.password_hash.nullable is True
    assert generated_user.email is None
    assert generated_user.password_hash is None
    assert explicit_user.id == explicit_id
    assert explicit_user.email is None
    assert explicit_user.password_hash is None
    assert credential_user.email == "canonical@example.com"
    assert credential_user.password_hash == "$argon2id$test-hash"


def test_user_credential_constraints_match_persistence_contract() -> None:
    check_constraints = {
        constraint.name: str(constraint.sqltext)
        for constraint in User.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }
    unique_constraints = {
        constraint.name: tuple(
            column.name for column in constraint.columns
        )
        for constraint in User.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    }

    assert check_constraints == {
        "ck_users_credentials_complete": (
            "(email IS NULL AND password_hash IS NULL) OR "
            "(email IS NOT NULL AND password_hash IS NOT NULL)"
        )
    }
    assert unique_constraints == {"uq_users_email": ("email",)}


def test_foreign_keys_target_owners_and_cascade_on_delete() -> None:
    portfolio_user_fk = next(iter(Portfolio.__table__.c.user_id.foreign_keys))
    portfolio_source_fk = next(
        iter(Portfolio.__table__.c.source_plan_id.foreign_keys)
    )
    holding_portfolio_fk = next(
        iter(Holding.__table__.c.portfolio_id.foreign_keys)
    )

    assert portfolio_user_fk.target_fullname == "users.id"
    assert portfolio_user_fk.ondelete == "CASCADE"
    assert portfolio_source_fk.target_fullname == "portfolios.id"
    assert portfolio_source_fk.ondelete == "SET NULL"
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


def test_portfolio_type_and_plan_context_match_approved_contract() -> None:
    portfolio = Portfolio(name="Current portfolio")
    planned = Portfolio(
        name="Planned portfolio",
        portfolio_type=PortfolioType.PLANNED.value,
        plan_currency="THB",
    )
    checks = {
        constraint.name: str(constraint.sqltext)
        for constraint in Portfolio.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert set(PortfolioType) == {
        PortfolioType.CURRENT,
        PortfolioType.PLANNED,
        PortfolioType.LEGACY,
    }
    assert Portfolio.__table__.c.portfolio_type.default.arg == "CURRENT"
    assert str(Portfolio.__table__.c.portfolio_type.server_default.arg) == (
        "'CURRENT'"
    )
    assert isinstance(Portfolio.__table__.c.portfolio_type.type, Text)
    assert isinstance(Portfolio.__table__.c.plan_currency.type, Text)
    assert portfolio.plan_currency is None
    assert planned.portfolio_type == "PLANNED"
    assert planned.plan_currency == "THB"
    assert checks == {
        "ck_portfolios_type": (
            "portfolio_type IN ('CURRENT', 'PLANNED', 'LEGACY')"
        ),
        "ck_portfolios_plan_currency_by_type": (
            "(portfolio_type = 'PLANNED' AND "
            "plan_currency IN ('USD', 'THB')) OR "
            "(portfolio_type IN ('CURRENT', 'LEGACY') AND "
            "plan_currency IS NULL)"
        ),
        "ck_portfolios_source_plan": (
            "source_plan_id IS NULL OR "
            "(portfolio_type = 'CURRENT' AND source_plan_id <> id)"
        ),
    }


def test_holding_uses_approved_current_planned_and_legacy_types() -> None:
    weight_type = Holding.__table__.c.weight.type
    invested_amount_type = Holding.__table__.c.invested_amount.type
    proposed_amount_type = Holding.__table__.c.proposed_amount.type
    shares_type = Holding.__table__.c.shares.type

    assert isinstance(weight_type, Numeric)
    assert weight_type.precision == 20
    assert weight_type.scale == 18
    assert isinstance(invested_amount_type, Numeric)
    assert invested_amount_type.precision == 28
    assert invested_amount_type.scale == 12
    assert isinstance(proposed_amount_type, Numeric)
    assert proposed_amount_type.precision == 28
    assert proposed_amount_type.scale == 12
    assert isinstance(Holding.__table__.c.invested_currency.type, Text)
    assert isinstance(shares_type, Numeric)
    assert shares_type.precision == 28
    assert shares_type.scale == 12
    assert isinstance(Holding.__table__.c.purchase_date.type, Date)
    assert Holding.__table__.c.position.type.python_type is int


def test_holding_supports_complete_legacy_current_and_planned_construction(
) -> None:
    legacy = Holding(
        symbol="AAPL",
        weight=Decimal("1.000000000000000000"),
        position=0,
    )
    real = Holding(
        symbol="BTC-USD",
        invested_amount=Decimal("1000.000000000000"),
        invested_currency="USD",
        shares=Decimal("0.010000000000"),
        purchase_date=date(2026, 1, 2),
        position=1,
    )
    planned = Holding(
        symbol="MSFT",
        proposed_amount=Decimal("2500.000000000000"),
        position=2,
    )

    assert legacy.invested_amount is None
    assert legacy.invested_currency is None
    assert legacy.shares is None
    assert legacy.purchase_date is None
    assert legacy.proposed_amount is None
    assert real.weight is None
    assert real.proposed_amount is None
    assert planned.weight is None
    assert planned.invested_amount is None
    assert planned.proposed_amount == Decimal("2500.000000000000")


def test_holding_check_constraints_cover_approved_row_contract() -> None:
    checks = {
        constraint.name: str(constraint.sqltext)
        for constraint in Holding.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert checks == {
        "ck_holdings_weight_range": "weight >= 0 AND weight <= 1",
        "ck_holdings_invested_amount_positive": (
            "invested_amount IS NULL OR invested_amount > 0"
        ),
        "ck_holdings_proposed_amount_positive": (
            "proposed_amount IS NULL OR proposed_amount > 0"
        ),
        "ck_holdings_shares_positive": "shares IS NULL OR shares > 0",
        "ck_holdings_invested_currency": (
            "invested_currency IS NULL OR "
            "invested_currency IN ('USD', 'THB')"
        ),
        "ck_holdings_complete_mode": (
            "(weight IS NOT NULL AND proposed_amount IS NULL AND "
            "invested_amount IS NULL AND invested_currency IS NULL AND "
            "shares IS NULL AND purchase_date IS NULL) OR "
            "(weight IS NULL AND proposed_amount IS NULL AND shares IS NOT "
            "NULL AND ((invested_amount IS NULL AND invested_currency IS "
            "NULL AND purchase_date IS NULL) OR (invested_amount IS NOT "
            "NULL AND invested_currency IS NOT NULL AND purchase_date IS "
            "NOT NULL))) OR (weight IS NULL AND proposed_amount IS NOT "
            "NULL AND invested_amount IS NULL AND invested_currency IS NULL "
            "AND shares IS NULL AND purchase_date IS NULL)"
        ),
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


def test_holding_persists_inputs_but_not_derived_financial_values() -> None:
    column_names = set(Holding.__table__.c.keys())

    assert "shares" in column_names
    assert "invested_amount" in column_names
    assert "proposed_amount" in column_names
    assert "invested_currency" in column_names
    assert "purchase_date" in column_names
    assert "amount_invested" not in column_names
    assert "current_value" not in column_names
    assert "current_value_usd" not in column_names
    assert "current_value_thb" not in column_names
    assert "current_allocation" not in column_names
    assert "allocation" not in column_names
    assert "latest_price" not in column_names
    assert "current_market_value" not in column_names
    assert "estimated_shares" not in column_names


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
    assert "email TEXT" in ddl_by_table["users"]
    assert "password_hash TEXT" in ddl_by_table["users"]
    assert "CONSTRAINT uq_users_email UNIQUE (email)" in (
        ddl_by_table["users"]
    )
    assert "CONSTRAINT ck_users_credentials_complete CHECK" in (
        ddl_by_table["users"]
    )
    assert "TIMESTAMP WITH TIME ZONE" in ddl_by_table["users"]
    assert "NUMERIC(20, 18)" in ddl_by_table["holdings"]
    assert ddl_by_table["holdings"].count("NUMERIC(28, 12)") == 3
    assert "portfolio_type TEXT" in ddl_by_table["portfolios"]
    assert "plan_currency TEXT" in ddl_by_table["portfolios"]
    assert "source_plan_id UUID" in ddl_by_table["portfolios"]
    assert "CONSTRAINT ck_portfolios_type CHECK" in (
        ddl_by_table["portfolios"]
    )
    assert "ON DELETE SET NULL" in ddl_by_table["portfolios"]
    assert "proposed_amount NUMERIC(28, 12)" in ddl_by_table["holdings"]
    assert "invested_currency TEXT" in ddl_by_table["holdings"]
    assert "purchase_date DATE" in ddl_by_table["holdings"]
    assert "CONSTRAINT ck_holdings_complete_mode CHECK" in (
        ddl_by_table["holdings"]
    )
    assert "ON DELETE CASCADE" in ddl_by_table["portfolios"]
    assert "ON DELETE CASCADE" in ddl_by_table["holdings"]
