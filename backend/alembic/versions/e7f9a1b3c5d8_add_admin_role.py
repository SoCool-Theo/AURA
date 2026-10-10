"""Add persisted administrator authorization; existing accounts remain customers."""

from alembic import op
import sqlalchemy as sa

revision = "e7f9a1b3c5d8"
down_revision = "d6e8f0a2b4c6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users", sa.Column("role", sa.Text(), server_default="CUSTOMER", nullable=False)
    )
    op.create_check_constraint(
        "ck_users_role", "users", "role IN ('CUSTOMER', 'ADMIN')"
    )
    op.create_check_constraint(
        "ck_users_admin_credentials",
        "users",
        "role != 'ADMIN' OR (email IS NOT NULL AND password_hash IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_users_admin_credentials", "users", type_="check")
    op.drop_constraint("ck_users_role", "users", type_="check")
    op.drop_column("users", "role")
