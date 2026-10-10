"""Aura legacy-weight and real-position portfolio holding model."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Date,
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
    """One ordered legacy allocation or aggregate real position."""

    __tablename__ = "holdings"
    __table_args__ = (
        CheckConstraint(
            "weight >= 0 AND weight <= 1",
            name="ck_holdings_weight_range",
        ),
        CheckConstraint(
            "invested_amount IS NULL OR invested_amount > 0",
            name="ck_holdings_invested_amount_positive",
        ),
        CheckConstraint(
            "proposed_amount IS NULL OR proposed_amount > 0",
            name="ck_holdings_proposed_amount_positive",
        ),
        CheckConstraint(
            "shares IS NULL OR shares > 0",
            name="ck_holdings_shares_positive",
        ),
        CheckConstraint(
            "invested_currency IS NULL OR "
            "invested_currency IN ('USD', 'THB')",
            name="ck_holdings_invested_currency",
        ),
        CheckConstraint(
            "(weight IS NOT NULL AND proposed_amount IS NULL AND "
            "invested_amount IS NULL AND invested_currency IS NULL AND "
            "shares IS NULL AND purchase_date IS NULL) OR "
            "(weight IS NULL AND proposed_amount IS NULL AND shares IS NOT NULL "
            "AND ((invested_amount IS NULL AND invested_currency IS NULL AND "
            "purchase_date IS NULL) OR (invested_amount IS NOT NULL AND "
            "invested_currency IS NOT NULL AND purchase_date IS NOT NULL))) OR "
            "(weight IS NULL AND proposed_amount IS NOT NULL AND "
            "invested_amount IS NULL AND invested_currency IS NULL AND "
            "shares IS NULL AND purchase_date IS NULL)",
            name="ck_holdings_complete_mode",
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
    invested_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=28, scale=12),
        nullable=True,
    )
    proposed_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=28, scale=12),
        nullable=True,
    )
    invested_currency: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    shares: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=28, scale=12),
        nullable=True,
    )
    purchase_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )
    weight: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=20, scale=18),
        nullable=True,
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
