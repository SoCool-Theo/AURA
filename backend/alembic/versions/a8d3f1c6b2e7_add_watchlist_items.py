"""add watchlist items

Revision ID: a8d3f1c6b2e7
Revises: f2c8e9a1b3d4
Create Date: 2026-09-24 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "a8d3f1c6b2e7"
down_revision: str | Sequence[str] | None = "f2c8e9a1b3d4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create observation-only user-owned Watchlist persistence."""
    op.create_table(
        "watchlist_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("symbol", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_watchlist_items_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_watchlist_items"),
        sa.UniqueConstraint(
            "user_id",
            "symbol",
            name="uq_watchlist_items_user_symbol",
        ),
    )


def downgrade() -> None:
    """Remove Watchlist persistence without touching market data."""
    op.drop_table("watchlist_items")
