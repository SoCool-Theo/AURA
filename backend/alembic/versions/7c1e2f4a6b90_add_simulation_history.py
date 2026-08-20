"""add simulation history

Revision ID: 7c1e2f4a6b90
Revises: 2b6e5d4a9c81
Create Date: 2026-08-20 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "7c1e2f4a6b90"
down_revision: str | Sequence[str] | None = "2b6e5d4a9c81"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create immutable simulation-history persistence."""
    op.create_table(
        "simulations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("portfolio_id", sa.Uuid(), nullable=False),
        sa.Column("simulation_type", sa.Text(), nullable=False),
        sa.Column("scenario_id", sa.Text(), nullable=True),
        sa.Column("requested_start_date", sa.Date(), nullable=False),
        sa.Column("requested_end_date", sa.Date(), nullable=False),
        sa.Column("schema_version", sa.Text(), nullable=False),
        sa.Column(
            "result_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "simulation_type IN "
            "('historical-scenario', 'allocation', 'combined')",
            name="ck_simulations_type",
        ),
        sa.CheckConstraint(
            "(simulation_type = 'allocation' AND scenario_id IS NULL) OR "
            "(simulation_type <> 'allocation' AND scenario_id IS NOT NULL)",
            name="ck_simulations_scenario_by_type",
        ),
        sa.CheckConstraint(
            "requested_start_date <= requested_end_date",
            name="ck_simulations_date_order",
        ),
        sa.ForeignKeyConstraint(
            ["portfolio_id"],
            ["portfolios.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_simulations_portfolio_created_at",
        "simulations",
        ["portfolio_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Remove only simulation-history persistence."""
    op.drop_index(
        "ix_simulations_portfolio_created_at",
        table_name="simulations",
    )
    op.drop_table("simulations")
