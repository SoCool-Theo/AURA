"""Shared SQLAlchemy declarative base for future Aura ORM models."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for Aura's future SQLAlchemy ORM models."""
