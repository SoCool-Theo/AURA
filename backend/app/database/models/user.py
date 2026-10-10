"""Minimal Aura user ownership model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from ..base import Base

if TYPE_CHECKING:
    from .portfolio import Portfolio
    from .watchlist import WatchlistItem


class User(Base):
    """Minimal owner for Aura portfolios pending an account contract."""

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "(email IS NULL AND password_hash IS NULL) OR "
            "(email IS NOT NULL AND password_hash IS NOT NULL)",
            name="ck_users_credentials_complete",
        ),
        CheckConstraint(
            "display_name IS NULL OR "
            "length(display_name) BETWEEN 1 AND 100",
            name="ck_users_display_name_length",
        ),
        CheckConstraint(
            "phone_number IS NULL OR "
            "length(phone_number) BETWEEN 4 AND 32",
            name="ck_users_phone_number_length",
        ),
        CheckConstraint(
            "preferred_language IN ('en', 'th')",
            name="ck_users_preferred_language",
        ),
        CheckConstraint(
            "timezone IN ('Asia/Bangkok', 'Asia/Yangon')",
            name="ck_users_timezone",
        ),
        UniqueConstraint("email", name="uq_users_email"),
        CheckConstraint("role IN ('CUSTOMER', 'ADMIN')", name="ck_users_role"),
        CheckConstraint(
            "role != 'ADMIN' OR (email IS NOT NULL AND password_hash IS NOT NULL)",
            name="ck_users_admin_credentials",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    email: Mapped[str | None] = mapped_column(Text, nullable=True)
    password_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    display_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    phone_number: Mapped[str | None] = mapped_column(Text, nullable=True)
    preferred_language: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="en",
        server_default="en",
    )
    timezone: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="Asia/Bangkok",
        server_default="Asia/Bangkok",
    )
    role: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="CUSTOMER",
        server_default="CUSTOMER",
    )

    portfolios: Mapped[list[Portfolio]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    watchlist_items: Mapped[list[WatchlistItem]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
