"""Explicit synchronous SQLAlchemy engine and session infrastructure."""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import TypeAlias

from pydantic import PostgresDsn
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import Session, sessionmaker

from ..core.config import settings


DatabaseUrl: TypeAlias = str | URL | PostgresDsn
SessionFactory: TypeAlias = sessionmaker[Session]


def _resolve_database_url(database_url: DatabaseUrl | None) -> URL:
    configured_url = (
        database_url if database_url is not None else settings.database_url
    )
    if configured_url is None:
        raise RuntimeError("DATABASE_URL is not configured")

    resolved_url = make_url(
        configured_url
        if isinstance(configured_url, (str, URL))
        else str(configured_url)
    )
    if resolved_url.drivername != "postgresql+psycopg":
        raise ValueError(
            "database URL must use the postgresql+psycopg driver"
        )
    return resolved_url


def create_database_engine(
    database_url: DatabaseUrl | None = None,
) -> Engine:
    """Create a PostgreSQL engine without opening a network connection."""
    return create_engine(
        _resolve_database_url(database_url),
        pool_pre_ping=True,
    )


def create_session_factory(engine: Engine) -> SessionFactory:
    """Create independent synchronous sessions bound to ``engine``."""
    return sessionmaker(
        bind=engine,
        class_=Session,
        autoflush=False,
        expire_on_commit=False,
    )


@contextmanager
def session_scope(factory: SessionFactory) -> Iterator[Session]:
    """Yield a session, rolling back failures and always closing it."""
    session = factory()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def check_database_connection(engine: Engine) -> bool:
    """Execute a trivial query and propagate any connectivity failure."""
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return True
