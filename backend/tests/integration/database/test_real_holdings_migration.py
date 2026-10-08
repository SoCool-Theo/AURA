"""Guarded PostgreSQL coverage for the additive real-holdings migration."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from alembic import command
from alembic.config import Config
import pytest
import sqlalchemy as sa
from sqlalchemy import Engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError

from backend.app.core.config import settings
from backend.app.database.connection import create_database_engine


BACKEND_ROOT = Path(__file__).resolve().parents[3]
PROJECT_ROOT = BACKEND_ROOT.parent
ALEMBIC_CONFIG_PATH = BACKEND_ROOT / "alembic.ini"
TEST_ENV_PATH = PROJECT_ROOT / ".env.test-database"
REVISION = "d4a6f8c2e1b7"
PREVIOUS_REVISION = "7c1e2f4a6b90"
APPLICATION_TABLES = {
    "analyses",
    "holdings",
    "market_data",
    "portfolios",
    "simulations",
    "users",
}
USER_ID = UUID("21000000-0000-0000-0000-000000000001")
PORTFOLIO_ID = UUID("22000000-0000-0000-0000-000000000001")
LEGACY_HOLDING_ID = UUID("23000000-0000-0000-0000-000000000001")
SECOND_LEGACY_HOLDING_ID = UUID("23000000-0000-0000-0000-000000000004")
REAL_HOLDING_ID = UUID("23000000-0000-0000-0000-000000000002")
REAL_THB_HOLDING_ID = UUID("23000000-0000-0000-0000-000000000003")


class _RedactedDatabaseUrl(str):
    def __repr__(self) -> str:
        return "<validated TEST_DATABASE_URL for localhost:5433/aura_test>"


def _read_test_database_url(test_env_path: Path = TEST_ENV_PATH) -> str:
    if not test_env_path.is_file():
        raise RuntimeError(
            ".env.test-database is required for migration tests"
        )

    matches: list[str] = []
    for line in test_env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        key, separator, value = stripped.partition("=")
        if separator and key.strip() == "TEST_DATABASE_URL":
            cleaned_value = value.strip()
            if (
                len(cleaned_value) >= 2
                and cleaned_value[0] == cleaned_value[-1]
                and cleaned_value[0] in {"'", '"'}
            ):
                cleaned_value = cleaned_value[1:-1]
            matches.append(cleaned_value)

    if len(matches) != 1 or not matches[0]:
        raise RuntimeError(
            ".env.test-database must contain exactly one non-empty "
            "TEST_DATABASE_URL; DATABASE_URL fallback is forbidden"
        )
    return matches[0]


def _validate_test_database_url(raw_url: str) -> None:
    if "supabase" in raw_url.casefold():
        raise RuntimeError("Supabase targets are forbidden for migration tests")

    try:
        url = make_url(raw_url)
    except (TypeError, ValueError, sa.exc.ArgumentError) as exc:
        raise RuntimeError("TEST_DATABASE_URL is not a valid URL") from exc
    if url.drivername != "postgresql+psycopg":
        raise RuntimeError(
            "TEST_DATABASE_URL must use postgresql+psycopg"
        )
    if (url.host or "").casefold() not in {"127.0.0.1", "localhost"}:
        raise RuntimeError(
            "real-holdings migration tests require an isolated loopback host"
        )
    if url.port != 5433:
        raise RuntimeError(
            "real-holdings migration tests require isolated port 5433"
        )
    if url.database != "aura_test":
        raise RuntimeError(
            "real-holdings migration tests require database aura_test"
        )


def _activate_test_database_url(raw_url: str) -> None:
    _validate_test_database_url(raw_url)
    settings.database_url = raw_url


def _alembic_config(raw_url: str) -> Config:
    _validate_test_database_url(raw_url)
    configured_url = settings.database_url
    if configured_url is None or str(configured_url) != raw_url:
        raise RuntimeError(
            "Alembic test URL is not the validated TEST_DATABASE_URL"
        )
    return Config(str(ALEMBIC_CONFIG_PATH))


def _upgrade(raw_url: str, revision: str) -> None:
    _activate_test_database_url(raw_url)
    command.upgrade(_alembic_config(raw_url), revision)


def _downgrade(raw_url: str, revision: str) -> None:
    _activate_test_database_url(raw_url)
    command.downgrade(_alembic_config(raw_url), revision)


def _table_names(engine: Engine) -> set[str]:
    return set(inspect(engine).get_table_names(schema="public"))


def _current_revision(engine: Engine) -> str | None:
    with engine.connect() as connection:
        return connection.scalar(text("SELECT version_num FROM alembic_version"))


def _assert_engine_target(engine: Engine, raw_url: str) -> None:
    _validate_test_database_url(raw_url)
    if engine.url != make_url(raw_url):
        raise RuntimeError(
            "database engine does not use the validated TEST_DATABASE_URL"
        )


def _delete_test_holdings(engine: Engine, raw_url: str) -> None:
    _assert_engine_target(engine, raw_url)
    with engine.begin() as connection:
        connection.execute(
            text("DELETE FROM holdings WHERE portfolio_id = :portfolio_id"),
            {"portfolio_id": PORTFOLIO_ID},
        )


def _delete_all_test_rows(engine: Engine, raw_url: str) -> None:
    _delete_test_holdings(engine, raw_url)
    with engine.begin() as connection:
        connection.execute(
            text("DELETE FROM portfolios WHERE id = :portfolio_id"),
            {"portfolio_id": PORTFOLIO_ID},
        )
        connection.execute(
            text("DELETE FROM users WHERE id = :user_id"),
            {"user_id": USER_ID},
        )


def _holding_snapshot(engine: Engine) -> list[tuple[object, ...]]:
    with engine.connect() as connection:
        return list(
            connection.execute(
                text(
                    "SELECT id, portfolio_id, symbol, weight, position, "
                    "created_at, updated_at FROM holdings ORDER BY id"
                )
            ).tuples()
        )


def _application_row_counts(engine: Engine) -> dict[str, int]:
    counts: dict[str, int] = {}
    with engine.connect() as connection:
        for table_name in sorted(APPLICATION_TABLES):
            counts[table_name] = connection.scalar(
                text(f'SELECT count(*) FROM "{table_name}"')
            )
    return counts


def test_test_database_url_loader_never_falls_back_to_database_url(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    test_env_path = tmp_path / ".env.test-database"
    test_env_path.write_text(
        "DATABASE_URL=postgresql+psycopg://ignored@remote.example/postgres\n",
        encoding="utf-8",
    )
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://ignored@remote.example/postgres",
    )

    with pytest.raises(RuntimeError, match="fallback is forbidden"):
        _read_test_database_url(test_env_path)


@pytest.mark.parametrize(
    "raw_url",
    [
        "postgresql+psycopg://aura:ignored@db.example/aura_test",
        "postgresql+psycopg://aura:ignored@localhost:5432/aura_test",
        "postgresql+psycopg://aura:ignored@localhost:5433/postgres",
        "postgresql+psycopg://aura:ignored@supabase.example:5433/aura_test",
    ],
)
def test_test_database_url_validation_rejects_unapproved_targets(
    raw_url: str,
) -> None:
    with pytest.raises(RuntimeError):
        _validate_test_database_url(raw_url)


@pytest.fixture(scope="module")
def test_database_url() -> str:
    raw_url = _RedactedDatabaseUrl(_read_test_database_url())
    _activate_test_database_url(raw_url)
    return raw_url


@pytest.fixture(scope="module")
def postgres_engine(test_database_url: str) -> Iterator[Engine]:
    raw_url = test_database_url
    engine = create_database_engine(raw_url)
    fixture_ready = False
    baseline_counts: dict[str, int] = {}
    baseline_holdings: list[tuple[object, ...]] = []

    try:
        _assert_engine_target(engine, raw_url)
        with engine.connect() as connection:
            database_name, database_user, server_version = connection.execute(
                text(
                    "SELECT current_database(), current_user, "
                    "current_setting('server_version')"
                )
            ).one()
        if database_name != "aura_test":
            pytest.fail("connected database is not an isolated Aura test DB")
        if database_user != "aura":
            pytest.fail("migration test database must use the Aura test role")
        if not server_version.startswith("18."):
            pytest.fail("migration test database must use PostgreSQL 18")

        existing_tables = _table_names(engine)
        expected_tables = APPLICATION_TABLES | {"alembic_version"}
        if existing_tables != expected_tables:
            pytest.fail(
                "migration test database must contain exactly the expected "
                f"pre-Phase-2 tables; found: {sorted(existing_tables)}"
            )
        if _current_revision(engine) != PREVIOUS_REVISION:
            pytest.fail(
                "migration test database must start at revision "
                f"{PREVIOUS_REVISION}"
            )
        with engine.connect() as connection:
            test_identity_count = connection.scalar(
                text(
                    "SELECT "
                    "(SELECT count(*) FROM users WHERE id = :user_id) + "
                    "(SELECT count(*) FROM portfolios "
                    "WHERE id = :portfolio_id) + "
                    "(SELECT count(*) FROM holdings "
                    "WHERE portfolio_id = :portfolio_id)"
                ),
                {"user_id": USER_ID, "portfolio_id": PORTFOLIO_ID},
            )
        if test_identity_count:
            pytest.fail(
                "reserved migration-test identities already exist; refusing "
                "to overwrite or delete them"
            )

        baseline_counts = _application_row_counts(engine)
        baseline_holdings = _holding_snapshot(engine)
        fixture_ready = True
        yield engine
    finally:
        try:
            if fixture_ready:
                current_revision = _current_revision(engine)
                if current_revision == REVISION:
                    _delete_test_holdings(engine, raw_url)
                    _downgrade(raw_url, PREVIOUS_REVISION)
                elif current_revision != PREVIOUS_REVISION:
                    raise RuntimeError(
                        "unexpected Alembic revision during guarded cleanup; "
                        "no migration cleanup was attempted"
                    )
                _delete_all_test_rows(engine, raw_url)
                assert _current_revision(engine) == PREVIOUS_REVISION
                assert _application_row_counts(engine) == baseline_counts
                assert _holding_snapshot(engine) == baseline_holdings
        finally:
            engine.dispose()


@pytest.fixture()
def previous_revision_database(
    postgres_engine: Engine,
    test_database_url: str,
) -> Iterator[Engine]:
    if _current_revision(postgres_engine) != PREVIOUS_REVISION:
        pytest.fail(
            f"migration test must begin at revision {PREVIOUS_REVISION}"
        )
    try:
        yield postgres_engine
    finally:
        current_revision = _current_revision(postgres_engine)
        if current_revision == REVISION:
            _delete_test_holdings(postgres_engine, test_database_url)
            _downgrade(test_database_url, PREVIOUS_REVISION)
        elif current_revision != PREVIOUS_REVISION:
            raise RuntimeError(
                "unexpected Alembic revision during guarded test cleanup; "
                "no migration cleanup was attempted"
            )
        _delete_all_test_rows(postgres_engine, test_database_url)


def _insert_parent_rows(connection: sa.Connection) -> None:
    connection.execute(
        text("INSERT INTO users (id) VALUES (:user_id)"),
        {"user_id": USER_ID},
    )
    connection.execute(
        text(
            "INSERT INTO portfolios (id, user_id, name) "
            "VALUES (:id, :user_id, :name)"
        ),
        {
            "id": PORTFOLIO_ID,
            "user_id": USER_ID,
            "name": "Migration test portfolio",
        },
    )


def _insert_holding(
    connection: sa.Connection,
    **values: object,
) -> None:
    connection.execute(
        text(
            "INSERT INTO holdings ("
            "id, portfolio_id, symbol, invested_amount, "
            "invested_currency, shares, purchase_date, weight, position"
            ") VALUES ("
            ":id, :portfolio_id, :symbol, :invested_amount, "
            ":invested_currency, :shares, :purchase_date, :weight, :position"
            ")"
        ),
        values,
    )


def test_upgrade_preserves_representative_legacy_holding_unchanged(
    previous_revision_database: Engine,
    test_database_url: str,
) -> None:
    engine = previous_revision_database
    with engine.begin() as connection:
        _insert_parent_rows(connection)
        connection.execute(
            text(
                "INSERT INTO holdings ("
                "id, portfolio_id, symbol, weight, position"
                ") VALUES (:id, :portfolio_id, :symbol, :weight, :position)"
            ),
            [
                {
                    "id": LEGACY_HOLDING_ID,
                    "portfolio_id": PORTFOLIO_ID,
                    "symbol": "AAPL",
                    "weight": Decimal("0.600000000000000000"),
                    "position": 0,
                },
                {
                    "id": SECOND_LEGACY_HOLDING_ID,
                    "portfolio_id": PORTFOLIO_ID,
                    "symbol": "MSFT",
                    "weight": Decimal("0.400000000000000000"),
                    "position": 1,
                },
            ],
        )

    _upgrade(test_database_url, REVISION)

    columns = {column["name"]: column for column in inspect(engine).get_columns(
        "holdings"
    )}
    assert columns["weight"]["nullable"] is True
    for column_name in (
        "invested_amount",
        "invested_currency",
        "shares",
        "purchase_date",
    ):
        assert columns[column_name]["nullable"] is True

    with engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT id, portfolio_id, symbol, weight, position, "
                "invested_amount, invested_currency, shares, purchase_date "
                "FROM holdings WHERE portfolio_id = :portfolio_id "
                "ORDER BY position"
            ),
            {"portfolio_id": PORTFOLIO_ID},
        ).all()
    assert rows == [
        (
            LEGACY_HOLDING_ID,
            PORTFOLIO_ID,
            "AAPL",
            Decimal("0.600000000000000000"),
            0,
            None,
            None,
            None,
            None,
        ),
        (
            SECOND_LEGACY_HOLDING_ID,
            PORTFOLIO_ID,
            "MSFT",
            Decimal("0.400000000000000000"),
            1,
            None,
            None,
            None,
            None,
        ),
    ]


def test_database_accepts_complete_modes_and_rejects_invalid_rows(
    previous_revision_database: Engine,
    test_database_url: str,
) -> None:
    engine = previous_revision_database
    _upgrade(test_database_url, REVISION)
    with engine.begin() as connection:
        _insert_parent_rows(connection)

    valid_base = {
        "id": REAL_HOLDING_ID,
        "portfolio_id": PORTFOLIO_ID,
        "symbol": "MSFT",
        "invested_amount": Decimal("1000.000000000000"),
        "invested_currency": "USD",
        "shares": Decimal("5.000000000000"),
        "purchase_date": date(2026, 1, 2),
        "weight": None,
        "position": 1,
    }
    invalid_cases = [
        (
            {**valid_base, "invested_currency": "EUR"},
            "ck_holdings_invested_currency",
        ),
        (
            {**valid_base, "invested_amount": Decimal("0")},
            "ck_holdings_invested_amount_positive",
        ),
        (
            {**valid_base, "invested_amount": Decimal("-1")},
            "ck_holdings_invested_amount_positive",
        ),
        (
            {**valid_base, "shares": Decimal("0")},
            "ck_holdings_shares_positive",
        ),
        (
            {**valid_base, "shares": Decimal("-1")},
            "ck_holdings_shares_positive",
        ),
        (
            {
                **valid_base,
                "invested_amount": None,
                "invested_currency": None,
                "purchase_date": None,
            },
            "ck_holdings_complete_mode",
        ),
        (
            {
                **valid_base,
                "purchase_date": None,
            },
            "ck_holdings_complete_mode",
        ),
        (
            {
                **valid_base,
                "invested_currency": None,
                "shares": None,
                "purchase_date": None,
                "weight": Decimal("1.000000000000000000"),
            },
            "ck_holdings_complete_mode",
        ),
        (
            {
                **valid_base,
                "weight": Decimal("1.000000000000000000"),
            },
            "ck_holdings_complete_mode",
        ),
    ]
    for values, expected_constraint in invalid_cases:
        with pytest.raises(IntegrityError) as raised:
            with engine.begin() as connection:
                _insert_holding(connection, **values)
        assert raised.value.orig.diag.constraint_name == expected_constraint

    with engine.begin() as connection:
        _insert_holding(
            connection,
            id=LEGACY_HOLDING_ID,
            portfolio_id=PORTFOLIO_ID,
            symbol="AAPL",
            invested_amount=None,
            invested_currency=None,
            shares=None,
            purchase_date=None,
            weight=Decimal("1.000000000000000000"),
            position=0,
        )
        _insert_holding(connection, **valid_base)
        _insert_holding(
            connection,
            id=REAL_THB_HOLDING_ID,
            portfolio_id=PORTFOLIO_ID,
            symbol="BTC-USD",
            invested_amount=Decimal("50000.000000000000"),
            invested_currency="THB",
            shares=Decimal("0.010000000000"),
            purchase_date=date(2026, 2, 3),
            weight=None,
            position=2,
        )

    with engine.connect() as connection:
        assert connection.scalar(
            text(
                "SELECT count(*) FROM holdings "
                "WHERE portfolio_id = :portfolio_id"
            ),
            {"portfolio_id": PORTFOLIO_ID},
        ) == 3


def test_legacy_only_downgrade_restores_old_schema_and_data(
    previous_revision_database: Engine,
    test_database_url: str,
) -> None:
    engine = previous_revision_database
    with engine.begin() as connection:
        _insert_parent_rows(connection)
        connection.execute(
            text(
                "INSERT INTO holdings ("
                "id, portfolio_id, symbol, weight, position"
                ") VALUES (:id, :portfolio_id, :symbol, :weight, :position)"
            ),
            {
                "id": LEGACY_HOLDING_ID,
                "portfolio_id": PORTFOLIO_ID,
                "symbol": "AAPL",
                "weight": Decimal("1.000000000000000000"),
                "position": 0,
            },
        )
    _upgrade(test_database_url, REVISION)
    _downgrade(test_database_url, PREVIOUS_REVISION)

    columns = {column["name"]: column for column in inspect(engine).get_columns(
        "holdings"
    )}
    assert columns["weight"]["nullable"] is False
    assert not {
        "invested_amount",
        "invested_currency",
        "shares",
        "purchase_date",
    } & columns.keys()
    with engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT id, portfolio_id, symbol, weight, position "
                "FROM holdings WHERE id = :id"
            ),
            {"id": LEGACY_HOLDING_ID},
        ).one()
    assert row == (
        LEGACY_HOLDING_ID,
        PORTFOLIO_ID,
        "AAPL",
        Decimal("1.000000000000000000"),
        0,
    )


def test_downgrade_refuses_real_holding_without_data_loss(
    previous_revision_database: Engine,
    test_database_url: str,
) -> None:
    engine = previous_revision_database
    _upgrade(test_database_url, REVISION)
    with engine.begin() as connection:
        _insert_parent_rows(connection)
        _insert_holding(
            connection,
            id=REAL_HOLDING_ID,
            portfolio_id=PORTFOLIO_ID,
            symbol="BTC-USD",
            invested_amount=Decimal("1000.000000000000"),
            invested_currency="USD",
            shares=Decimal("0.010000000000"),
            purchase_date=date(2026, 1, 2),
            weight=None,
            position=0,
        )

    with pytest.raises(RuntimeError, match="no weights will be fabricated"):
        _downgrade(test_database_url, PREVIOUS_REVISION)

    with engine.connect() as connection:
        assert connection.scalar(
            text("SELECT version_num FROM alembic_version")
        ) == REVISION
        row = connection.execute(
            text(
                "SELECT id, invested_amount, invested_currency, shares, "
                "purchase_date, weight FROM holdings WHERE id = :id"
            ),
            {"id": REAL_HOLDING_ID},
        ).one()
    assert row == (
        REAL_HOLDING_ID,
        Decimal("1000.000000000000"),
        "USD",
        Decimal("0.010000000000"),
        date(2026, 1, 2),
        None,
    )
