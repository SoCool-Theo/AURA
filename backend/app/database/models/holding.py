"""Aura weight-based portfolio holding model."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from ..base import Base

if TYPE_CHECKING:
    from .portfolio import Portfolio


class Holding(Base):
    """One normalized symbol and exact weight in an ordered portfolio."""

    __tablename__ = "holdings"
    __table_args__ = (
        CheckConstraint(
            "weight >= 0 AND weight <= 1",
            name="ck_holdings_weight_range",
        ),
        CheckConstraint(
            "position >= 0",
            name="ck_holdings_position_non_negative",
        ),
        UniqueConstraint(
            "portfolio_id",
            "symbol",
            name="uq_holdings_portfolio_symbol",
        ),
        UniqueConstraint(
            "portfolio_id",
            "position",
            name="uq_holdings_portfolio_position",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    portfolio_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        nullable=False,
    )
    symbol: Mapped[str] = mapped_column(Text, nullable=False)
    weight: Mapped[Decimal] = mapped_column(
        Numeric(precision=20, scale=18),
        nullable=False,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
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

    portfolio: Mapped[Portfolio] = relationship(back_populates="holdings")
