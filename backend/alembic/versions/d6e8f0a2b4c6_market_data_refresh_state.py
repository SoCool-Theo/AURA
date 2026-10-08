"""Persist market-data refresh health without changing financial records."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "d6e8f0a2b4c6"
down_revision = "c3d5e7f9a2b4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "market_data_refresh_state",
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("status", sa.Text(), server_default="never", nullable=False),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_complete_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_complete_slot", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("stored_count", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("updated_symbols", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("failed_symbols", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("error_code", sa.Text(), nullable=True),
        sa.Column("worker_running", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("worker_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("id = 1", name="ck_market_refresh_singleton"),
        sa.CheckConstraint("status IN ('never', 'running', 'success', 'partial', 'failed')", name="ck_market_refresh_status"),
        sa.CheckConstraint("attempt_count >= 0 AND stored_count >= 0", name="ck_market_refresh_counts"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("market_data_refresh_state")
