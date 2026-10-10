"""Add account suspension and revocable session versions."""

from alembic import op
import sqlalchemy as sa

revision = "b0c2d4e6f8a1"
down_revision = "a9b1c3d5e7f0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("is_suspended", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("users", sa.Column("auth_version", sa.Integer(), nullable=False, server_default="0"))
    op.create_check_constraint("ck_users_auth_version", "users", "auth_version >= 0")


def downgrade() -> None:
    op.drop_constraint("ck_users_auth_version", "users", type_="check")
    op.drop_column("users", "auth_version")
    op.drop_column("users", "is_suspended")
