"""add user profile fields

Revision ID: b9e4d2f7c1a6
Revises: a8d3f1c6b2e7
Create Date: 2026-09-25 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "b9e4d2f7c1a6"
down_revision: str | Sequence[str] | None = "a8d3f1c6b2e7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add optional identity fields and bounded regional preferences."""
    op.add_column("users", sa.Column("display_name", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("phone_number", sa.Text(), nullable=True))
    op.add_column(
        "users",
        sa.Column(
            "preferred_language",
            sa.Text(),
            server_default="en",
            nullable=False,
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "timezone",
            sa.Text(),
            server_default="Asia/Bangkok",
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_users_display_name_length",
        "users",
        "display_name IS NULL OR length(display_name) BETWEEN 1 AND 100",
    )
    op.create_check_constraint(
        "ck_users_phone_number_length",
        "users",
        "phone_number IS NULL OR length(phone_number) BETWEEN 4 AND 32",
    )
    op.create_check_constraint(
        "ck_users_preferred_language",
        "users",
        "preferred_language IN ('en', 'th')",
    )
    op.create_check_constraint(
        "ck_users_timezone",
        "users",
        "timezone IN ('Asia/Bangkok', 'Asia/Yangon')",
    )


def downgrade() -> None:
    """Remove profile fields without affecting credentials or owned data."""
    op.drop_constraint("ck_users_timezone", "users", type_="check")
    op.drop_constraint("ck_users_preferred_language", "users", type_="check")
    op.drop_constraint("ck_users_phone_number_length", "users", type_="check")
    op.drop_constraint("ck_users_display_name_length", "users", type_="check")
    op.drop_column("users", "timezone")
    op.drop_column("users", "preferred_language")
    op.drop_column("users", "phone_number")
    op.drop_column("users", "display_name")
