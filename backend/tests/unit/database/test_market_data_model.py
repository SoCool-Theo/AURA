from datetime import date
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    Numeric,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex, CreateTable

from backend.app.database import Base, Holding, MarketData, Portfolio, User


EXPECTED_TABLES = {
    "analyses",
    "users",
    "portfolios",
    "holdings",
    "market_data",
}


def test_market_data_uses_existing_base_and_expected_table_name() -> None:
    assert issubclass(MarketData, Base)
    assert MarketData.__tablename__ == "market_data"
    assert set(Base.metadata.tables) == EXPECTED_TABLES
    assert User.__table__ is Base.metadata.tables["users"]
    assert Portfolio.__table__ is Base.metadata.tables["portfolios"]
    assert Holding.__table__ is Base.metadata.tables["holdings"]


def test_market_data_has_only_canonical_columns() -> None:
    assert tuple(MarketData.__table__.c.keys()) == (
        "symbol",
        "date",
        "adjusted_close",
        "volume",
        "source",
    )
    assert "id" not in MarketData.__table__.c
    assert "created_at" not in MarketData.__table__.c
    assert "updated_at" not in MarketData.__table__.c


def test_market_data_uses_symbol_date_composite_primary_key() -> None:
    primary_key_columns = tuple(
        column.name for column in MarketData.__table__.primary_key.columns
    )

    assert primary_key_columns == ("symbol", "date")
    assert MarketData.__table__.c.symbol.primary_key is True
    assert MarketData.__table__.c.date.primary_key is True
    assert MarketData.__table__.c.source.primary_key is False
    assert not any(
        isinstance(constraint, UniqueConstraint)
        for constraint in MarketData.__table__.constraints
    )


def test_market_data_uses_required_exact_types_and_nullability() -> None:
    symbol = MarketData.__table__.c.symbol
    observation_date = MarketData.__table__.c.date
    adjusted_close = MarketData.__table__.c.adjusted_close
    volume = MarketData.__table__.c.volume
    source = MarketData.__table__.c.source

    assert isinstance(symbol.type, Text)
    assert symbol.nullable is False
    assert isinstance(observation_date.type, Date)
    assert observation_date.nullable is False
    assert isinstance(adjusted_close.type, Numeric)
    assert adjusted_close.type.precision == 28
    assert adjusted_close.type.scale == 12
    assert adjusted_close.nullable is False
    assert isinstance(volume.type, BigInteger)
    assert volume.nullable is True
    assert isinstance(source.type, Text)
    assert source.nullable is False


def test_market_data_constraints_cover_price_and_volume_bounds() -> None:
    checks = {
        constraint.name: str(constraint.sqltext)
        for constraint in MarketData.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert checks == {
        "ck_market_data_adjusted_close_positive": "adjusted_close > 0",
        "ck_market_data_volume_non_negative": (
            "volume IS NULL OR volume >= 0"
        ),
    }


def test_market_data_has_only_required_date_index() -> None:
    indexes = {
        index.name: tuple(column.name for column in index.columns)
        for index in MarketData.__table__.indexes
    }

    assert indexes == {"ix_market_data_date": ("date",)}


def test_market_data_represents_prepared_values_without_transforming() -> None:
    adjusted_close = Decimal("123.456789012345")
    observation_date = date(2026, 8, 13)
    record = MarketData(
        symbol="BRK.B",
        date=observation_date,
        adjusted_close=adjusted_close,
        volume=None,
        source="Synthetic",
    )

    assert record.symbol == "BRK.B"
    assert record.date is observation_date
    assert record.adjusted_close is adjusted_close
    assert record.volume is None
    assert record.source == "Synthetic"


def test_market_data_compiles_as_postgresql_ddl_without_connecting() -> None:
    dialect = postgresql.dialect()
    table_ddl = str(CreateTable(MarketData.__table__).compile(dialect=dialect))
    date_index = next(iter(MarketData.__table__.indexes))
    index_ddl = str(CreateIndex(date_index).compile(dialect=dialect))

    assert "PRIMARY KEY (symbol, date)" in table_ddl
    assert "NUMERIC(28, 12)" in table_ddl
    assert "volume BIGINT" in table_ddl
    assert "CONSTRAINT ck_market_data_adjusted_close_positive" in table_ddl
    assert "CONSTRAINT ck_market_data_volume_non_negative" in table_ddl
    assert index_ddl == "CREATE INDEX ix_market_data_date ON market_data (date)"
