"""allow quantity-only current holdings

Revision ID: f2c8e9a1b3d4
Revises: e5b7c9d2a4f1
Create Date: 2026-09-18 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import context, op
import sqlalchemy as sa


revision: str = "f2c8e9a1b3d4"
down_revision: str | Sequence[str] | None = "e5b7c9d2a4f1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_NEW_MODE_CHECK = (
    "(weight IS NOT NULL AND proposed_amount IS NULL AND "
    "invested_amount IS NULL AND invested_currency IS NULL AND "
    "shares IS NULL AND purchase_date IS NULL) OR "
    "(weight IS NULL AND proposed_amount IS NULL AND shares IS NOT NULL "
    "AND ((invested_amount IS NULL AND invested_currency IS NULL AND "
    "purchase_date IS NULL) OR (invested_amount IS NOT NULL AND "
    "invested_currency IS NOT NULL AND purchase_date IS NOT NULL))) OR "
    "(weight IS NULL AND proposed_amount IS NOT NULL AND "
    "invested_amount IS NULL AND invested_currency IS NULL AND "
    "shares IS NULL AND purchase_date IS NULL)"
)

_OLD_MODE_CHECK = (
    "(weight IS NOT NULL AND proposed_amount IS NULL AND "
    "invested_amount IS NULL AND invested_currency IS NULL AND "
    "shares IS NULL AND purchase_date IS NULL) OR "
    "(weight IS NULL AND proposed_amount IS NULL AND "
    "invested_amount IS NOT NULL AND invested_currency IS NOT NULL AND "
    "shares IS NOT NULL AND purchase_date IS NOT NULL) OR "
    "(weight IS NULL AND proposed_amount IS NOT NULL AND "
    "invested_amount IS NULL AND invested_currency IS NULL AND "
    "shares IS NULL AND purchase_date IS NULL)"
)

_QUANTITY_ONLY_EXISTS_SQL = sa.text(
    "SELECT EXISTS ("
    "SELECT 1 FROM holdings WHERE "
    "weight IS NULL AND proposed_amount IS NULL AND shares IS NOT NULL AND "
    "invested_amount IS NULL AND invested_currency IS NULL AND "
    "purchase_date IS NULL"
    ")"
)


def upgrade() -> None:
    """Permit CURRENT holdings with quantity and no purchase provenance."""
    op.drop_constraint(
        "ck_holdings_complete_mode",
        "holdings",
        type_="check",
    )
    op.create_check_constraint(
        "ck_holdings_complete_mode",
        "holdings",
        _NEW_MODE_CHECK,
    )


def downgrade() -> None:
    """Restore the prior full-provenance rule only when data permits it."""
    if context.is_offline_mode():
        op.execute(
            sa.text(
                "DO $aura$ BEGIN "
                "IF EXISTS (SELECT 1 FROM holdings WHERE "
                "weight IS NULL AND proposed_amount IS NULL AND "
                "shares IS NOT NULL AND invested_amount IS NULL AND "
                "invested_currency IS NULL AND purchase_date IS NULL) THEN "
                "RAISE EXCEPTION 'Cannot downgrade quantity-only current "
                "holdings while quantity-only rows exist'; "
                "END IF; END $aura$"
            )
        )
    else:
        if op.get_bind().scalar(_QUANTITY_ONLY_EXISTS_SQL):
            raise RuntimeError(
                "Cannot downgrade quantity-only current holdings while "
                "quantity-only rows exist; no investment provenance will be "
                "fabricated."
            )

    op.drop_constraint(
        "ck_holdings_complete_mode",
        "holdings",
        type_="check",
    )
    op.create_check_constraint(
        "ck_holdings_complete_mode",
        "holdings",
        _OLD_MODE_CHECK,
    )
