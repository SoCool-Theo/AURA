"""Add persistent administrative audit history."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "f8a0b2c4d6e9"
down_revision = "e7f9a1b3c5d8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("actor_kind", sa.Text(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("target_type", sa.Text(), nullable=False),
        sa.Column("target_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("details", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "(actor_kind = 'OPERATOR' AND actor_user_id IS NULL) OR "
            "(actor_kind = 'ADMIN' AND actor_user_id IS NOT NULL)",
            name="ck_audit_logs_actor",
        ),
        sa.CheckConstraint("length(action) BETWEEN 1 AND 64", name="ck_audit_logs_action"),
        sa.CheckConstraint("length(target_type) BETWEEN 1 AND 64", name="ck_audit_logs_target_type"),
    )
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at", "id"])
    op.create_index("ix_audit_logs_actor_created_at", "audit_logs", ["actor_user_id", "created_at", "id"])
    op.create_index("ix_audit_logs_target_created_at", "audit_logs", ["target_type", "target_id", "created_at", "id"])


def downgrade() -> None:
    op.drop_index("ix_audit_logs_target_created_at", table_name="audit_logs")
    op.drop_index("ix_audit_logs_actor_created_at", table_name="audit_logs")
    op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")
    op.drop_table("audit_logs")
