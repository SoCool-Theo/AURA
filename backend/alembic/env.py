"""Alembic environment for Aura's synchronous PostgreSQL migrations."""

from logging.config import fileConfig

from alembic import context

from backend.app.core.config import settings
from backend.app.database.base import Base
from backend.app.database.connection import create_database_engine


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _database_url() -> str:
    if settings.database_url is None:
        raise RuntimeError(
            "DATABASE_URL must be configured to run Alembic migrations"
        )
    return str(settings.database_url)


def run_migrations_offline() -> None:
    """Generate migration SQL without creating a database connection."""
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations through an explicitly created database connection."""
    engine = create_database_engine(_database_url())
    try:
        with engine.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                compare_type=True,
            )

            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
