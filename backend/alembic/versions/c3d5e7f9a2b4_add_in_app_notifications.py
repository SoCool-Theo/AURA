"""Add account-scoped in-app notifications and preferences.

Revision ID: c3d5e7f9a2b4
Revises: b9e4d2f7c1a6
"""

from alembic import op
import sqlalchemy as sa

revision = "c3d5e7f9a2b4"
down_revision = "b9e4d2f7c1a6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notification_preferences",
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("analysis_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("simulation_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_table(
        "notifications",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("portfolio_id", sa.Uuid(), sa.ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("report_id", sa.Uuid(), sa.ForeignKey("analyses.id", ondelete="CASCADE")),
        sa.Column("simulation_id", sa.Uuid(), sa.ForeignKey("simulations.id", ondelete="CASCADE")),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("read_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("(kind = 'analysis' AND report_id IS NOT NULL AND simulation_id IS NULL) OR (kind = 'simulation' AND simulation_id IS NOT NULL AND report_id IS NULL)", name="ck_notifications_target"),
        sa.UniqueConstraint("report_id", name="uq_notifications_report"),
        sa.UniqueConstraint("simulation_id", name="uq_notifications_simulation"),
    )
    op.create_index("ix_notifications_user_created_at", "notifications", ["user_id", "created_at", "id"])


def downgrade() -> None:
    op.drop_table("notifications")
    op.drop_table("notification_preferences")
