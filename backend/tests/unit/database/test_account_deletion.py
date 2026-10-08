"""Synthetic in-memory deletion tests; never connect to a user's database."""

from datetime import date
from uuid import uuid4
from unittest.mock import MagicMock

import pytest
from sqlalchemy import JSON, MetaData, create_engine, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session

from backend.app.database.models import (
    Analysis, Holding, MarketData, Portfolio, Simulation, User, WatchlistItem,
)
from backend.app.database.repositories import UserRepository


def test_delete_flushes_without_owning_transaction():
    session = MagicMock(spec=Session)
    user = User()
    UserRepository(session).delete(user)
    session.delete.assert_called_once_with(user)
    session.flush.assert_called_once_with()
    session.commit.assert_not_called()
    session.rollback.assert_not_called()
    session.close.assert_not_called()


@pytest.mark.parametrize("commit", [True, False])
def test_account_cascades_are_scoped_atomic_and_preserve_market_data(commit):
    engine = create_engine("sqlite+pysqlite:///:memory:")
    models = [User, Portfolio, Holding, Analysis, Simulation, WatchlistItem, MarketData]
    metadata = MetaData()
    tables = {model: model.__table__.to_metadata(metadata) for model in models}
    # Use copies of the actual FK/constraint definitions with SQLite JSON only.
    # Production models and their PostgreSQL JSONB columns remain unchanged.
    for table in tables.values():
        for column in table.columns:
            if isinstance(column.type, JSONB):
                column.type = JSON()
    with engine.connect() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")
    metadata.create_all(engine)
    user_ids = [uuid4(), uuid4()]
    portfolios = []
    day = date(2026, 9, 17)
    try:
        with engine.begin() as connection:
            for index, user_id in enumerate(user_ids):
                connection.execute(tables[User].insert(), {
                    "id": user_id, "email": f"synthetic-{index}@example.com", "password_hash": "encoded-hash",
                })
                # Both CURRENT and PLANNED, including a converted-plan reference.
                plan_id, current_id = uuid4(), uuid4()
                portfolios.extend([plan_id, current_id])
                for portfolio_id, kind in [(plan_id, "PLANNED"), (current_id, "CURRENT")]:
                    connection.execute(tables[Portfolio].insert(), {
                        "id": portfolio_id, "user_id": user_id, "name": kind,
                        "portfolio_type": kind, "plan_currency": "USD" if kind == "PLANNED" else None,
                        "source_plan_id": plan_id if kind == "CURRENT" else None,
                    })
                    connection.execute(tables[Holding].insert(), {
                        "id": uuid4(), "portfolio_id": portfolio_id, "symbol": "AAPL", "position": 0,
                        "proposed_amount": 100 if kind == "PLANNED" else None,
                        "shares": 1 if kind == "CURRENT" else None,
                        "invested_amount": 100 if kind == "CURRENT" else None,
                        "invested_currency": "USD" if kind == "CURRENT" else None,
                        "purchase_date": day if kind == "CURRENT" else None,
                    })
                    connection.execute(tables[Analysis].insert(), {
                        "id": uuid4(), "portfolio_id": portfolio_id, "start_date": day, "end_date": day,
                        "schema_version": "test", "result_snapshot": {},
                    })
                    for simulation_type in ["allocation", "historical-scenario", "combined"]:
                        connection.execute(tables[Simulation].insert(), {
                            "id": uuid4(), "portfolio_id": portfolio_id, "simulation_type": simulation_type,
                            "scenario_id": None if simulation_type == "allocation" else "synthetic",
                            "requested_start_date": day, "requested_end_date": day,
                            "schema_version": "test", "result_snapshot": {},
                        })
                connection.execute(tables[WatchlistItem].insert(), {
                    "id": uuid4(), "user_id": user_id, "symbol": "AAPL",
                })
            connection.execute(tables[MarketData].insert(), {
                "symbol": "AAPL", "date": day, "adjusted_close": 100, "source": "synthetic",
            })
        with Session(engine) as session:
            user = session.get(User, user_ids[0])
            UserRepository(session).delete(user)
            if commit:
                session.commit()
            else:
                session.rollback()
        with engine.connect() as connection:
            for model, owner_column, expected in [
                (User, "id", user_ids[1:] if commit else user_ids),
                (Portfolio, "user_id", user_ids[1:] if commit else user_ids),
                (WatchlistItem, "user_id", user_ids[1:] if commit else user_ids),
                *[(model, "portfolio_id", portfolios[2:] if commit else portfolios)
                  for model in [Holding, Analysis, Simulation]],
            ]:
                actual = set(connection.execute(select(tables[model].c[owner_column])).scalars())
                assert actual == set(expected)
            assert connection.execute(select(tables[MarketData].c.symbol)).scalars().all() == ["AAPL"]
    finally:
        engine.dispose()
