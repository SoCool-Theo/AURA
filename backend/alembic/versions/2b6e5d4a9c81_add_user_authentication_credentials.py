"""add user authentication credentials

Revision ID: 2b6e5d4a9c81
Revises: 9f4c2a7b1d3e
Create Date: 2026-08-18 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "2b6e5d4a9c81"
down_revision: str | Sequence[str] | None = "9f4c2a7b1d3e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add nullable, pair-constrained User credential storage."""
    op.add_column(
        "users",
        sa.Column("email", sa.Text(), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("password_hash", sa.Text(), nullable=True),
    )
    op.create_unique_constraint(
        "uq_users_email",
        "users",
        ["email"],
    )
    op.create_check_constraint(
        "ck_users_credentials_complete",
        "users",
        "(email IS NULL AND password_hash IS NULL) OR "
        "(email IS NOT NULL AND password_hash IS NOT NULL)",
    )


def downgrade() -> None:
    """Remove only User credential persistence fields and constraints."""
    op.drop_constraint(
        "ck_users_credentials_complete",
        "users",
        type_="check",
    )
    op.drop_constraint(
        "uq_users_email",
        "users",
        type_="unique",
    )
    op.drop_column("users", "password_hash")
    op.drop_column("users", "email")
