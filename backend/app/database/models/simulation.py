"""Persistence model for immutable Aura simulation-history snapshots."""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from ..base import Base

if TYPE_CHECKING:
    from .portfolio import Portfolio


class Simulation(Base):
    """Relational metadata and one immutable simulation result snapshot."""

    __tablename__ = "simulations"
    __table_args__ = (
        CheckConstraint(
            "simulation_type IN "
            "('historical-scenario', 'allocation', 'combined')",
            name="ck_simulations_type",
        ),
        CheckConstraint(
            "(simulation_type = 'allocation' AND scenario_id IS NULL) OR "
            "(simulation_type <> 'allocation' AND scenario_id IS NOT NULL)",
            name="ck_simulations_scenario_by_type",
        ),
        CheckConstraint(
            "requested_start_date <= requested_end_date",
            name="ck_simulations_date_order",
        ),
        Index(
            "ix_simulations_portfolio_created_at",
            "portfolio_id",
            "created_at",
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
    simulation_type: Mapped[str] = mapped_column(Text, nullable=False)
    scenario_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    requested_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    requested_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    schema_version: Mapped[str] = mapped_column(Text, nullable=False)
    result_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    portfolio: Mapped[Portfolio] = relationship(back_populates="simulations")
