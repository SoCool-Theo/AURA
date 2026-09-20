"""Guarded PostgreSQL verification for the planned-portfolio foundation."""

from __future__ import annotations

from collections.abc import Iterator
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from alembic import command
from alembic.config import Config
import pytest
import sqlalchemy as sa
from sqlalchemy import Engine, inspect, text
from sqlalchemy.exc import IntegrityError

from backend.app.core.config import settings
from backend.tests.integration.database.postgres_test_guard import (
    create_guarded_engine,
    read_only_preflight,
    read_test_database_url,
)


BACKEND_ROOT = Path(__file__).resolve().parents[3]
ALEMBIC_CONFIG_PATH = BACKEND_ROOT / "alembic.ini"
REVISION = "e5b7c9d2a4f1"
PREVIOUS_REVISION = "d4a6f8c2e1b7"
USER_ID = UUID("31000000-0000-0000-0000-000000000001")
PLANNED_PORTFOLIO_ID = UUID("32000000-0000-0000-0000-000000000001")
PLANNED_HOLDING_ID = UUID("33000000-0000-0000-0000-000000000001")


def _current_revision(engine: Engine) -> str | None:
    with engine.connect() as connection:
        return connection.scalar(text("SELECT version_num FROM alembic_version"))


def _application_snapshot(engine: Engine) -> tuple[tuple[object, ...], ...]:
    with engine.connect() as connection:
        portfolios = tuple(
            connection.execute(
                text(
                    "SELECT id, user_id, name, created_at, updated_at "
                    "FROM portfolios ORDER BY id"
                )
            ).tuples()
        )
        holdings = tuple(
            connection.execute(
                text(
                    "SELECT id, portfolio_id, symbol, invested_amount, "
                    "invested_currency, shares, purchase_date, weight, "
                    "position, created_at, updated_at FROM holdings ORDER BY id"
                )
            ).tuples()
        )
    return portfolios + holdings


def _remove_reserved_rows(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(
            text("DELETE FROM portfolios WHERE id = :portfolio_id"),
            {"portfolio_id": PLANNED_PORTFOLIO_ID},
        )
        connection.execute(
            text("DELETE FROM users WHERE id = :user_id"),
            {"user_id": USER_ID},
        )


@pytest.fixture(scope="module")
def migrated_database() -> Iterator[Engine]:
    preflight = read_only_preflight()
    if preflight.alembic_revision != PREVIOUS_REVISION:
        pytest.fail(
            "planned migration test database must start at the approved "
            f"revision {PREVIOUS_REVISION}"
        )

    raw_url = read_test_database_url()
    engine = create_guarded_engine(raw_url)
    baseline = _application_snapshot(engine)
    with engine.connect() as connection:
        reserved_count = connection.scalar(
            text(
                "SELECT "
                "(SELECT count(*) FROM users WHERE id = :user_id) + "
                "(SELECT count(*) FROM portfolios WHERE id = :portfolio_id)"
            ),
            {
                "user_id": USER_ID,
                "portfolio_id": PLANNED_PORTFOLIO_ID,
            },
        )
    if reserved_count:
        engine.dispose()
        pytest.fail(
            "reserved planned-migration test identities already exist; "
            "refusing to overwrite them"
        )

    settings.database_url = raw_url
    configuration = Config(str(ALEMBIC_CONFIG_PATH))
    command.upgrade(configuration, REVISION)

    try:
        yield engine
    finally:
        try:
            current_revision = _current_revision(engine)
            if current_revision == REVISION:
                _remove_reserved_rows(engine)
                settings.database_url = raw_url
                command.downgrade(configuration, PREVIOUS_REVISION)
            elif current_revision != PREVIOUS_REVISION:
                raise RuntimeError(
                    "unexpected Alembic revision during guarded cleanup; "
                    "no cleanup migration was attempted"
                )
            _remove_reserved_rows(engine)
            assert _current_revision(engine) == PREVIOUS_REVISION
            assert _application_snapshot(engine) == baseline
        finally:
            engine.dispose()


def test_live_upgrade_backfills_types_and_enforces_planned_shapes(
    migrated_database: Engine,
) -> None:
    engine = migrated_database
    assert _current_revision(engine) == REVISION

    portfolio_columns = {
        column["name"] for column in inspect(engine).get_columns("portfolios")
    }
    holding_columns = {
        column["name"] for column in inspect(engine).get_columns("holdings")
    }
    assert {"portfolio_type", "plan_currency", "source_plan_id"}.issubset(
        portfolio_columns
    )
    assert "proposed_amount" in holding_columns

    with engine.connect() as connection:
        invalid_classification_count = connection.scalar(
            text(
                "SELECT count(*) FROM portfolios p WHERE "
                "(EXISTS (SELECT 1 FROM holdings h "
                "WHERE h.portfolio_id = p.id AND h.weight IS NOT NULL) "
                "AND p.portfolio_type <> 'LEGACY') OR "
                "(NOT EXISTS (SELECT 1 FROM holdings h "
                "WHERE h.portfolio_id = p.id AND h.weight IS NOT NULL) "
                "AND p.portfolio_type <> 'CURRENT')"
            )
        )
    assert invalid_classification_count == 0

    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO users (id) VALUES (:id)"),
            {"id": USER_ID},
        )
        connection.execute(
            text(
                "INSERT INTO portfolios "
                "(id, user_id, name, portfolio_type, plan_currency) "
                "VALUES (:id, :user_id, :name, 'PLANNED', 'USD')"
            ),
            {
                "id": PLANNED_PORTFOLIO_ID,
                "user_id": USER_ID,
                "name": "Guarded planned migration test",
            },
        )
        connection.execute(
            text(
                "INSERT INTO holdings "
                "(id, portfolio_id, symbol, proposed_amount, position) "
                "VALUES (:id, :portfolio_id, 'AAPL', :amount, 0)"
            ),
            {
                "id": PLANNED_HOLDING_ID,
                "portfolio_id": PLANNED_PORTFOLIO_ID,
                "amount": Decimal("1000.000000000000"),
            },
        )

    with engine.connect() as connection:
        planned_row = connection.execute(
            text(
                "SELECT p.portfolio_type, p.plan_currency, h.proposed_amount, "
                "h.weight, h.shares FROM portfolios p JOIN holdings h "
                "ON h.portfolio_id = p.id WHERE p.id = :id"
            ),
            {"id": PLANNED_PORTFOLIO_ID},
        ).one()
    assert planned_row == (
        "PLANNED",
        "USD",
        Decimal("1000.000000000000"),
        None,
        None,
    )

    with pytest.raises(IntegrityError) as raised:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO holdings "
                    "(id, portfolio_id, symbol, proposed_amount, position) "
                    "VALUES (:id, :portfolio_id, 'MSFT', 0, 1)"
                ),
                {
                    "id": UUID("33000000-0000-0000-0000-000000000002"),
                    "portfolio_id": PLANNED_PORTFOLIO_ID,
                },
            )
    assert raised.value.orig.diag.constraint_name == (
        "ck_holdings_proposed_amount_positive"
    )


def test_live_downgrade_refuses_to_discard_planned_data(
    migrated_database: Engine,
) -> None:
    engine = migrated_database
    raw_url = read_test_database_url()
    settings.database_url = raw_url

    with pytest.raises(RuntimeError, match="no planned data will be discarded"):
        command.downgrade(
            Config(str(ALEMBIC_CONFIG_PATH)),
            PREVIOUS_REVISION,
        )

    assert _current_revision(engine) == REVISION
    with engine.connect() as connection:
        assert connection.scalar(
            text("SELECT count(*) FROM portfolios WHERE id = :id"),
            {"id": PLANNED_PORTFOLIO_ID},
        ) == 1
