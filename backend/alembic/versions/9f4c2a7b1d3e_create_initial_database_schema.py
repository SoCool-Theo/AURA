"""create initial database schema

Revision ID: 9f4c2a7b1d3e
Revises:
Create Date: 2026-08-13 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "9f4c2a7b1d3e"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create Aura's complete initial database schema."""
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "portfolios",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "holdings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("portfolio_id", sa.Uuid(), nullable=False),
        sa.Column("symbol", sa.Text(), nullable=False),
        sa.Column("weight", sa.Numeric(precision=20, scale=18), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "position >= 0",
            name="ck_holdings_position_non_negative",
        ),
        sa.CheckConstraint(
            "weight >= 0 AND weight <= 1",
            name="ck_holdings_weight_range",
        ),
        sa.ForeignKeyConstraint(
            ["portfolio_id"],
            ["portfolios.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "portfolio_id",
            "position",
            name="uq_holdings_portfolio_position",
        ),
        sa.UniqueConstraint(
            "portfolio_id",
            "symbol",
            name="uq_holdings_portfolio_symbol",
        ),
    )
    op.create_table(
        "market_data",
        sa.Column("symbol", sa.Text(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column(
            "adjusted_close",
            sa.Numeric(precision=28, scale=12),
            nullable=False,
        ),
        sa.Column("volume", sa.BigInteger(), nullable=True),
        sa.Column("source", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "adjusted_close > 0",
            name="ck_market_data_adjusted_close_positive",
        ),
        sa.CheckConstraint(
            "volume IS NULL OR volume >= 0",
            name="ck_market_data_volume_non_negative",
        ),
        sa.PrimaryKeyConstraint("symbol", "date"),
    )
    op.create_index(
        "ix_market_data_date",
        "market_data",
        ["date"],
        unique=False,
    )
    op.create_table(
        "analyses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("portfolio_id", sa.Uuid(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
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
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "start_date <= end_date",
            name="ck_analyses_date_order",
        ),
        sa.ForeignKeyConstraint(
            ["portfolio_id"],
            ["portfolios.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_analyses_portfolio_created_at",
        "analyses",
        ["portfolio_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Remove Aura's complete initial database schema."""
    op.drop_index(
        "ix_analyses_portfolio_created_at",
        table_name="analyses",
    )
    op.drop_table("analyses")
    op.drop_index("ix_market_data_date", table_name="market_data")
    op.drop_table("market_data")
    op.drop_table("holdings")
    op.drop_table("portfolios")
    op.drop_table("users")
