"""Add durable manual requests and refresh run history."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "c1d3e5f7a9b2"
down_revision = "b0c2d4e6f8a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "market_data_refresh_runs",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("trigger", sa.Text(), nullable=False),
        sa.Column("requested_by", sa.Uuid(as_uuid=True)),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("stored_count", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("updated_symbols", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("failed_symbols", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("error_code", sa.Text()),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("trigger IN ('ADMIN', 'SCHEDULED', 'CATCH_UP', 'OPERATOR')", name="ck_market_runs_trigger"),
        sa.CheckConstraint("status IN ('queued', 'running', 'success', 'partial', 'failed')", name="ck_market_runs_status"),
        sa.CheckConstraint("attempt_count >= 0 AND stored_count >= 0", name="ck_market_runs_counts"),
        sa.CheckConstraint("(trigger = 'ADMIN' AND requested_by IS NOT NULL) OR (trigger != 'ADMIN' AND requested_by IS NULL)", name="ck_market_runs_actor"),
    )
    op.create_index("ix_market_runs_requested_at", "market_data_refresh_runs", ["requested_at", "id"])


def downgrade() -> None:
    op.drop_index("ix_market_runs_requested_at", table_name="market_data_refresh_runs")
    op.drop_table("market_data_refresh_runs")
