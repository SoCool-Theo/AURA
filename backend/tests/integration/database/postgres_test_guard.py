"""Credential-safe guards for the Phase 12 local PostgreSQL verification."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from alembic import command
from alembic.config import Config
import sqlalchemy as sa
from sqlalchemy import Engine, text
from sqlalchemy.engine import URL, make_url

from backend.app.core.config import settings


BACKEND_ROOT = Path(__file__).resolve().parents[3]
PROJECT_ROOT = BACKEND_ROOT.parent
TEST_ENV_PATH = PROJECT_ROOT / ".env.test-database"
EXPECTED_HOSTS = frozenset({"127.0.0.1", "localhost"})
EXPECTED_PORT = 5433
EXPECTED_DATABASE = "aura_test"
EXPECTED_ROLE = "aura"
EXPECTED_POSTGRESQL_MAJOR = 18
APPLICATION_TABLES = (
    "users",
    "portfolios",
    "holdings",
    "market_data",
    "analyses",
    "simulations",
)
PHASE12_SYMBOLS = ("AAPL", "MSFT", "THB=X")
PHASE12_CURRENT_DATE = date(2026, 9, 12)
PREVIOUS_REVISION = "7c1e2f4a6b90"
REAL_HOLDING_REVISION = "d4a6f8c2e1b7"
ALEMBIC_CONFIG_PATH = BACKEND_ROOT / "alembic.ini"


class RedactedDatabaseUrl(str):
    """Keep accidental repr output free of database credentials."""

    def __repr__(self) -> str:
        return "<validated local Phase 12 test database URL>"


@dataclass(frozen=True, slots=True)
class SanitizedPreflight:
    host: str
    port: int
    database: str
    role: str
    postgresql_version: str
    alembic_revision: str


@dataclass(frozen=True, slots=True)
class BaselineInventory:
    table_names: tuple[str, ...]
    row_counts: dict[str, int]
    legacy_holding_count: int
    real_holding_count: int
    overlapping_market_rows: tuple[tuple[object, ...], ...]
    coverage: dict[str, tuple[date | None, date | None, int]]


@dataclass(frozen=True, slots=True)
class MigrationVerification:
    starting_revision: str
    ending_revision: str
    migration_applied: bool
    legacy_rows_preserved: bool
    real_columns_null_for_legacy: bool
    mode_constraints_present: bool


def read_test_database_url(path: Path = TEST_ENV_PATH) -> RedactedDatabaseUrl:
    """Read exactly TEST_DATABASE_URL without consulting process environment."""
    if not path.is_file():
        raise RuntimeError("required test database configuration is missing")

    matches: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        key, separator, value = stripped.partition("=")
        if separator and key.strip() == "TEST_DATABASE_URL":
            cleaned = value.strip()
            if (
                len(cleaned) >= 2
                and cleaned[0] == cleaned[-1]
                and cleaned[0] in {"'", '"'}
            ):
                cleaned = cleaned[1:-1]
            matches.append(cleaned)

    if len(matches) != 1 or not matches[0]:
        raise RuntimeError("exactly one test database URL is required")
    return RedactedDatabaseUrl(matches[0])


def validate_test_database_url(raw_url: str) -> URL:
    """Reject every database target except the approved local test database."""
    if "supabase" in raw_url.casefold():
        raise RuntimeError("remote database targets are forbidden")
    try:
        url = make_url(raw_url)
    except (TypeError, ValueError, sa.exc.ArgumentError) as error:
        raise RuntimeError("invalid test database configuration") from error

    if url.drivername != "postgresql+psycopg":
        raise RuntimeError("unexpected database driver")
    if (url.host or "").casefold() not in EXPECTED_HOSTS:
        raise RuntimeError("unexpected database host")
    if url.port != EXPECTED_PORT:
        raise RuntimeError("unexpected database port")
    if url.database != EXPECTED_DATABASE:
        raise RuntimeError("unexpected database name")
    if url.username != EXPECTED_ROLE:
        raise RuntimeError("unexpected database role")
    return url


def create_guarded_engine(raw_url: str) -> Engine:
    """Create an engine only after validating the explicit test URL."""
    validate_test_database_url(raw_url)
    return sa.create_engine(raw_url, future=True)


def read_only_preflight() -> SanitizedPreflight:
    """Verify connection identity, PostgreSQL 18, and Alembic revision."""
    raw_url = read_test_database_url()
    url = validate_test_database_url(raw_url)
    engine = create_guarded_engine(raw_url)
    try:
        with engine.connect() as connection:
            with connection.begin():
                connection.execute(text("SET TRANSACTION READ ONLY"))
                database, role, version, version_number = connection.execute(
                    text(
                        "SELECT current_database(), current_user, "
                        "current_setting('server_version'), "
                        "current_setting('server_version_num')"
                    )
                ).one()
                revision = connection.scalar(
                    text("SELECT version_num FROM alembic_version")
                )
    finally:
        engine.dispose()

    if database != EXPECTED_DATABASE:
        raise RuntimeError("connected database identity mismatch")
    if role != EXPECTED_ROLE:
        raise RuntimeError("connected database role mismatch")
    if int(version_number) // 10000 != EXPECTED_POSTGRESQL_MAJOR:
        raise RuntimeError("unexpected PostgreSQL major version")
    if revision is None:
        raise RuntimeError("Alembic revision is unavailable")

    return SanitizedPreflight(
        host=str(url.host),
        port=int(url.port or 0),
        database=str(database),
        role=str(role),
        postgresql_version=str(version),
        alembic_revision=str(revision),
    )


def read_only_baseline_inventory() -> BaselineInventory:
    """Capture aggregate baseline state without exposing private row data."""
    read_only_preflight()
    raw_url = read_test_database_url()
    engine = create_guarded_engine(raw_url)
    try:
        with engine.connect() as connection:
            with connection.begin():
                connection.execute(text("SET TRANSACTION READ ONLY"))
                table_names = tuple(
                    connection.execute(
                        text(
                            "SELECT tablename FROM pg_catalog.pg_tables "
                            "WHERE schemaname = 'public' ORDER BY tablename"
                        )
                    ).scalars()
                )
                row_counts = {
                    table: int(
                        connection.scalar(
                            text(f'SELECT count(*) FROM "{table}"')
                        )
                        or 0
                    )
                    for table in APPLICATION_TABLES
                }
                holding_columns = set(
                    connection.execute(
                        text(
                            "SELECT column_name FROM information_schema.columns "
                            "WHERE table_schema = 'public' "
                            "AND table_name = 'holdings'"
                        )
                    ).scalars()
                )
                legacy_count = int(
                    connection.scalar(
                        text("SELECT count(*) FROM holdings WHERE weight IS NOT NULL")
                    )
                    or 0
                )
                if {
                    "invested_amount",
                    "invested_currency",
                    "shares",
                    "purchase_date",
                }.issubset(holding_columns):
                    real_count = int(
                        connection.scalar(
                            text(
                                "SELECT count(*) FROM holdings "
                                "WHERE weight IS NULL "
                                "AND invested_amount IS NOT NULL "
                                "AND invested_currency IS NOT NULL "
                                "AND shares IS NOT NULL "
                                "AND purchase_date IS NOT NULL"
                            )
                        )
                        or 0
                    )
                else:
                    real_count = 0
                overlap_rows = tuple(
                    connection.execute(
                        text(
                            "SELECT symbol, date, adjusted_close, volume, source "
                            "FROM market_data "
                            "WHERE symbol = ANY(:symbols) AND date = :date "
                            "ORDER BY symbol"
                        ),
                        {
                            "symbols": list(PHASE12_SYMBOLS),
                            "date": PHASE12_CURRENT_DATE,
                        },
                    ).tuples()
                )
                coverage = {
                    str(row.symbol): (
                        row.minimum_date,
                        row.maximum_date,
                        int(row.row_count),
                    )
                    for row in connection.execute(
                        text(
                            "SELECT symbol, min(date) AS minimum_date, "
                            "max(date) AS maximum_date, count(*) AS row_count "
                            "FROM market_data WHERE symbol = ANY(:symbols) "
                            "GROUP BY symbol ORDER BY symbol"
                        ),
                        {"symbols": list(PHASE12_SYMBOLS)},
                    )
                }
    finally:
        engine.dispose()

    return BaselineInventory(
        table_names=table_names,
        row_counts=row_counts,
        legacy_holding_count=legacy_count,
        real_holding_count=real_count,
        overlapping_market_rows=overlap_rows,
        coverage=coverage,
    )


def guarded_upgrade_and_verify() -> MigrationVerification:
    """Apply only the real-holdings revision and verify legacy preservation."""
    preflight = read_only_preflight()
    if preflight.alembic_revision not in {
        PREVIOUS_REVISION,
        REAL_HOLDING_REVISION,
    }:
        raise RuntimeError("unexpected starting Alembic revision")

    raw_url = read_test_database_url()
    engine = create_guarded_engine(raw_url)
    try:
        with engine.connect() as connection:
            with connection.begin():
                connection.execute(text("SET TRANSACTION READ ONLY"))
                legacy_before = tuple(
                    connection.execute(
                        text(
                            "SELECT id, portfolio_id, symbol, weight, position "
                            "FROM holdings ORDER BY id"
                        )
                    ).tuples()
                )
                portfolio_ids_before = tuple(
                    connection.execute(
                        text("SELECT id FROM portfolios ORDER BY id")
                    ).scalars()
                )
    finally:
        engine.dispose()

    applied = preflight.alembic_revision == PREVIOUS_REVISION
    if applied:
        settings.database_url = raw_url
        configuration = Config(str(ALEMBIC_CONFIG_PATH))
        command.upgrade(configuration, REAL_HOLDING_REVISION)

    engine = create_guarded_engine(raw_url)
    try:
        with engine.connect() as connection:
            with connection.begin():
                connection.execute(text("SET TRANSACTION READ ONLY"))
                ending_revision = str(
                    connection.scalar(
                        text("SELECT version_num FROM alembic_version")
                    )
                )
                legacy_after = tuple(
                    connection.execute(
                        text(
                            "SELECT id, portfolio_id, symbol, weight, position, "
                            "invested_amount, invested_currency, shares, "
                            "purchase_date FROM holdings ORDER BY id"
                        )
                    ).tuples()
                )
                portfolio_ids_after = tuple(
                    connection.execute(
                        text("SELECT id FROM portfolios ORDER BY id")
                    ).scalars()
                )
                constraints = set(
                    connection.execute(
                        text(
                            "SELECT conname FROM pg_constraint "
                            "WHERE conrelid = 'holdings'::regclass"
                        )
                    ).scalars()
                )
    finally:
        engine.dispose()

    expected_legacy_after = tuple(
        (*row, None, None, None, None) for row in legacy_before
    )
    required_constraints = {
        "ck_holdings_invested_amount_positive",
        "ck_holdings_shares_positive",
        "ck_holdings_invested_currency",
        "ck_holdings_complete_mode",
    }
    rows_preserved = (
        portfolio_ids_after == portfolio_ids_before
        and tuple(row[:5] for row in legacy_after) == legacy_before
    )
    real_fields_null = legacy_after == expected_legacy_after
    constraints_present = required_constraints.issubset(constraints)
    if ending_revision != REAL_HOLDING_REVISION:
        raise RuntimeError("real-holdings migration did not reach target")
    if not rows_preserved or not real_fields_null or not constraints_present:
        raise RuntimeError("real-holdings migration verification failed")

    return MigrationVerification(
        starting_revision=preflight.alembic_revision,
        ending_revision=ending_revision,
        migration_applied=applied,
        legacy_rows_preserved=rows_preserved,
        real_columns_null_for_legacy=real_fields_null,
        mode_constraints_present=constraints_present,
    )


def print_sanitized_migration_verification() -> int:
    """Run the guarded upgrade and emit no connection exception details."""
    try:
        result = guarded_upgrade_and_verify()
    except Exception:
        print("alembic_revision=unverified")
        return 1

    print(f"alembic_revision={result.ending_revision}")
    print(f"migration_applied={result.migration_applied}")
    print(f"legacy_rows_preserved={result.legacy_rows_preserved}")
    print(
        "real_columns_null_for_legacy="
        f"{result.real_columns_null_for_legacy}"
    )
    print(f"mode_constraints_present={result.mode_constraints_present}")
    return 0


def print_sanitized_preflight() -> int:
    """Print only approved diagnostics and never emit exception details."""
    try:
        result = read_only_preflight()
    except Exception:
        print("host=unverified")
        print("port=unverified")
        print("database=unverified")
        print("role=unverified")
        print("postgresql_version=unverified")
        print("alembic_revision=unverified")
        return 1

    print(f"host={result.host}")
    print(f"port={result.port}")
    print(f"database={result.database}")
    print(f"role={result.role}")
    print(f"postgresql_version={result.postgresql_version}")
    print(f"alembic_revision={result.alembic_revision}")
    return 0


def print_sanitized_inventory() -> int:
    """Print only aggregate inventory and non-secret market coverage."""
    try:
        inventory = read_only_baseline_inventory()
    except Exception:
        print("inventory_status=unavailable")
        return 1

    print(f"table_names={','.join(inventory.table_names)}")
    for table in APPLICATION_TABLES:
        print(f"row_count_{table}={inventory.row_counts[table]}")
    print(f"legacy_holding_count={inventory.legacy_holding_count}")
    print(f"real_holding_count={inventory.real_holding_count}")
    print(
        "candidate_market_overlap_count="
        f"{len(inventory.overlapping_market_rows)}"
    )
    for symbol in PHASE12_SYMBOLS:
        minimum, maximum, count = inventory.coverage.get(
            symbol,
            (None, None, 0),
        )
        print(f"coverage_{symbol}={minimum},{maximum},{count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(print_sanitized_preflight())
