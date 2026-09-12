"""add real holding fields

Revision ID: d4a6f8c2e1b7
Revises: 7c1e2f4a6b90
Create Date: 2026-09-11 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import context, op
import sqlalchemy as sa



revision: str = "d4a6f8c2e1b7"
down_revision: str | Sequence[str] | None = "7c1e2f4a6b90"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add nullable real-position fields without rewriting legacy rows."""
    op.add_column(
        "holdings",
        sa.Column(
            "invested_amount",
            sa.Numeric(precision=28, scale=12),
            nullable=True,
        ),
    )
    op.add_column(
        "holdings",
        sa.Column("invested_currency", sa.Text(), nullable=True),
    )
    op.add_column(
        "holdings",
        sa.Column(
            "shares",
            sa.Numeric(precision=28, scale=12),
            nullable=True,
        ),
    )
    op.add_column(
        "holdings",
        sa.Column("purchase_date", sa.Date(), nullable=True),
    )
    op.alter_column(
        "holdings",
        "weight",
        existing_type=sa.Numeric(precision=20, scale=18),
        nullable=True,
    )
    op.create_check_constraint(
        "ck_holdings_invested_amount_positive",
        "holdings",
        "invested_amount IS NULL OR invested_amount > 0",
    )
    op.create_check_constraint(
        "ck_holdings_shares_positive",
        "holdings",
        "shares IS NULL OR shares > 0",
    )
    op.create_check_constraint(
        "ck_holdings_invested_currency",
        "holdings",
        "invested_currency IS NULL OR "
        "invested_currency IN ('USD', 'THB')",
    )
    op.create_check_constraint(
        "ck_holdings_complete_mode",
        "holdings",
        "(weight IS NOT NULL AND invested_amount IS NULL AND "
        "invested_currency IS NULL AND shares IS NULL AND "
        "purchase_date IS NULL) OR "
        "(weight IS NULL AND invested_amount IS NOT NULL AND "
        "invested_currency IS NOT NULL AND shares IS NOT NULL AND "
        "purchase_date IS NOT NULL)",
    )


def downgrade() -> None:
    """Restore weight-only holdings only when every row remains legacy."""
    if context.is_offline_mode():
        op.execute(
            sa.text(
                "DO $aura$ BEGIN "
                "IF EXISTS (SELECT 1 FROM holdings WHERE "
                "weight IS NULL OR invested_amount IS NOT NULL OR "
                "invested_currency IS NOT NULL OR shares IS NOT NULL OR "
                "purchase_date IS NOT NULL) THEN "
                "RAISE EXCEPTION 'Cannot downgrade real-holding migration "
                "while non-legacy holdings exist'; "
                "END IF; END $aura$"
            )
        )
    else:
        connection = op.get_bind()
        unsafe_row_exists = connection.scalar(
            sa.text(
                "SELECT EXISTS ("
                "SELECT 1 FROM holdings WHERE "
                "weight IS NULL OR invested_amount IS NOT NULL OR "
                "invested_currency IS NOT NULL OR shares IS NOT NULL OR "
                "purchase_date IS NOT NULL"
                ")"
            )
        )
        if unsafe_row_exists:
            raise RuntimeError(
                "Cannot downgrade real-holding migration while non-legacy "
                "holdings exist; no weights will be fabricated and no "
                "holdings will be deleted."
            )

    op.drop_constraint(
        "ck_holdings_complete_mode",
        "holdings",
        type_="check",
    )
    op.drop_constraint(
        "ck_holdings_invested_currency",
        "holdings",
        type_="check",
    )
    op.drop_constraint(
        "ck_holdings_shares_positive",
        "holdings",
        type_="check",
    )
    op.drop_constraint(
        "ck_holdings_invested_amount_positive",
        "holdings",
        type_="check",
    )
    op.alter_column(
        "holdings",
        "weight",
        existing_type=sa.Numeric(precision=20, scale=18),
        nullable=False,
    )
    op.drop_column("holdings", "purchase_date")
    op.drop_column("holdings", "shares")
    op.drop_column("holdings", "invested_currency")
    op.drop_column("holdings", "invested_amount")
