from sqlalchemy import DateTime, Text, UniqueConstraint, inspect
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable
from sqlalchemy.types import Uuid

from backend.app.database import Base, User, WatchlistItem


def test_watchlist_model_has_only_observation_identity_fields() -> None:
    assert issubclass(WatchlistItem, Base)
    assert WatchlistItem.__tablename__ == "watchlist_items"
    assert tuple(WatchlistItem.__table__.c.keys()) == (
        "id",
        "user_id",
        "symbol",
        "created_at",
    )
    assert isinstance(WatchlistItem.__table__.c.id.type, Uuid)
    assert isinstance(WatchlistItem.__table__.c.user_id.type, Uuid)
    assert isinstance(WatchlistItem.__table__.c.symbol.type, Text)
    assert isinstance(WatchlistItem.__table__.c.created_at.type, DateTime)
    assert WatchlistItem.__table__.c.created_at.type.timezone is True


def test_watchlist_model_enforces_owner_symbol_uniqueness_and_cascade() -> None:
    constraints = {
        constraint.name: tuple(column.name for column in constraint.columns)
        for constraint in WatchlistItem.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    user_fk = next(iter(WatchlistItem.__table__.c.user_id.foreign_keys))
    user_items = inspect(User).relationships.watchlist_items

    assert constraints == {
        "uq_watchlist_items_user_symbol": ("user_id", "symbol")
    }
    assert user_fk.target_fullname == "users.id"
    assert user_fk.ondelete == "CASCADE"
    assert "delete-orphan" in user_items.cascade
    assert user_items.passive_deletes is True


def test_watchlist_model_compiles_to_postgresql_without_derived_values() -> None:
    ddl = str(
        CreateTable(WatchlistItem.__table__).compile(
            dialect=postgresql.dialect()
        )
    )

    assert "CONSTRAINT uq_watchlist_items_user_symbol UNIQUE" in ddl
    assert "FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE" in ddl
    for disallowed in (
        "latest_price",
        "daily_change",
        "ytd_change",
        "shares",
        "invested_amount",
        "purchase_date",
        "allocation",
    ):
        assert disallowed not in ddl
