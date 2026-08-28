"""Persistence model for cleaned and validated Aura market data."""

from datetime import date
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    Index,
    Numeric,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base


class MarketData(Base):
    """One canonical daily market observation for a normalized symbol."""

    __tablename__ = "market_data"
    __table_args__ = (
        CheckConstraint(
            "adjusted_close > 0",
            name="ck_market_data_adjusted_close_positive",
        ),
        CheckConstraint(
            "volume IS NULL OR volume >= 0",
            name="ck_market_data_volume_non_negative",
        ),
        Index("ix_market_data_date", "date"),
    )

    symbol: Mapped[str] = mapped_column(Text, primary_key=True)
    date: Mapped[date] = mapped_column(Date, primary_key=True)
    adjusted_close: Mapped[Decimal] = mapped_column(
        Numeric(precision=28, scale=12),
        nullable=False,
    )
    volume: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    source: Mapped[str] = mapped_column(Text, nullable=False)
