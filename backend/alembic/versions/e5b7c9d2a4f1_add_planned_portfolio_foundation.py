"""add planned portfolio foundation

Revision ID: e5b7c9d2a4f1
Revises: d4a6f8c2e1b7
Create Date: 2026-09-13 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import context, op
import sqlalchemy as sa


revision: str = "e5b7c9d2a4f1"
down_revision: str | Sequence[str] | None = "d4a6f8c2e1b7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_INVALID_EXISTING_PORTFOLIO_STATE = (
    "SELECT 1 FROM holdings GROUP BY portfolio_id HAVING NOT ("
    "bool_and(weight IS NOT NULL AND invested_amount IS NULL AND "
    "invested_currency IS NULL AND shares IS NULL AND "
    "purchase_date IS NULL) OR "
    "bool_and(weight IS NULL AND invested_amount IS NOT NULL AND "
    "invested_currency IS NOT NULL AND shares IS NOT NULL AND "
    "purchase_date IS NOT NULL))"
)


def _guard_upgrade_state() -> None:
    """Reject mixed/incomplete portfolios before changing their schema."""
    if context.is_offline_mode():
        op.execute(
            sa.text(
                "DO $aura$ BEGIN IF EXISTS ("
                f"{_INVALID_EXISTING_PORTFOLIO_STATE}"
                ") THEN RAISE EXCEPTION 'Cannot classify mixed or "
                "incomplete portfolio holdings'; END IF; END $aura$"
            )
        )
        return

    connection = op.get_bind()
    invalid_state_exists = connection.scalar(
        sa.text(
            "SELECT EXISTS ("
            f"{_INVALID_EXISTING_PORTFOLIO_STATE}"
            ")"
        )
    )
    if invalid_state_exists:
        raise RuntimeError(
            "Cannot classify mixed or incomplete portfolio holdings; "
            "the planned-portfolio migration made no changes."
        )


def upgrade() -> None:
    """Add explicit portfolio types and planned holding amounts."""
    _guard_upgrade_state()

    op.add_column(
        "portfolios",
        sa.Column(
            "portfolio_type",
            sa.Text(),
            server_default=sa.text("'CURRENT'"),
            nullable=False,
        ),
    )
    op.add_column(
        "portfolios",
        sa.Column("plan_currency", sa.Text(), nullable=True),
    )
    op.add_column(
        "portfolios",
        sa.Column("source_plan_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_portfolios_source_plan_id_portfolios",
        "portfolios",
        "portfolios",
        ["source_plan_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.execute(
        sa.text(
            "UPDATE portfolios SET portfolio_type = 'LEGACY' "
            "WHERE EXISTS (SELECT 1 FROM holdings "
            "WHERE holdings.portfolio_id = portfolios.id "
            "AND holdings.weight IS NOT NULL)"
        )
    )
    op.create_check_constraint(
        "ck_portfolios_type",
        "portfolios",
        "portfolio_type IN ('CURRENT', 'PLANNED', 'LEGACY')",
    )
    op.create_check_constraint(
        "ck_portfolios_plan_currency_by_type",
        "portfolios",
        "(portfolio_type = 'PLANNED' AND "
        "plan_currency IN ('USD', 'THB')) OR "
        "(portfolio_type IN ('CURRENT', 'LEGACY') AND "
        "plan_currency IS NULL)",
    )
    op.create_check_constraint(
        "ck_portfolios_source_plan",
        "portfolios",
        "source_plan_id IS NULL OR "
        "(portfolio_type = 'CURRENT' AND source_plan_id <> id)",
    )

    op.add_column(
        "holdings",
        sa.Column(
            "proposed_amount",
            sa.Numeric(precision=28, scale=12),
            nullable=True,
        ),
    )
    op.drop_constraint(
        "ck_holdings_complete_mode",
        "holdings",
        type_="check",
    )
    op.create_check_constraint(
        "ck_holdings_proposed_amount_positive",
        "holdings",
        "proposed_amount IS NULL OR proposed_amount > 0",
    )
    op.create_check_constraint(
        "ck_holdings_complete_mode",
        "holdings",
        "(weight IS NOT NULL AND proposed_amount IS NULL AND "
        "invested_amount IS NULL AND invested_currency IS NULL AND "
        "shares IS NULL AND purchase_date IS NULL) OR "
        "(weight IS NULL AND proposed_amount IS NULL AND "
        "invested_amount IS NOT NULL AND invested_currency IS NOT NULL AND "
        "shares IS NOT NULL AND purchase_date IS NOT NULL) OR "
        "(weight IS NULL AND proposed_amount IS NOT NULL AND "
        "invested_amount IS NULL AND invested_currency IS NULL AND "
        "shares IS NULL AND purchase_date IS NULL)",
    )


def _guard_downgrade_state() -> None:
    """Refuse to discard planned data or plan provenance."""
    unsafe_state = (
        "SELECT 1 FROM portfolios WHERE portfolio_type = 'PLANNED' "
        "OR plan_currency IS NOT NULL OR source_plan_id IS NOT NULL "
        "UNION ALL SELECT 1 FROM holdings "
        "WHERE proposed_amount IS NOT NULL"
    )
    if context.is_offline_mode():
        op.execute(
            sa.text(
                "DO $aura$ BEGIN IF EXISTS ("
                f"{unsafe_state}"
                ") THEN RAISE EXCEPTION 'Cannot downgrade while planned "
                "portfolio data or source-plan provenance exists'; "
                "END IF; END $aura$"
            )
        )
        return

    connection = op.get_bind()
    if connection.scalar(sa.text(f"SELECT EXISTS ({unsafe_state})")):
        raise RuntimeError(
            "Cannot downgrade while planned portfolio data or source-plan "
            "provenance exists; no planned data will be discarded."
        )


def downgrade() -> None:
    """Remove the planned foundation only when doing so loses no data."""
    _guard_downgrade_state()

    op.drop_constraint(
        "ck_holdings_complete_mode",
        "holdings",
        type_="check",
    )
    op.drop_constraint(
        "ck_holdings_proposed_amount_positive",
        "holdings",
        type_="check",
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
    op.drop_column("holdings", "proposed_amount")

    op.drop_constraint(
        "ck_portfolios_source_plan",
        "portfolios",
        type_="check",
    )
    op.drop_constraint(
        "ck_portfolios_plan_currency_by_type",
        "portfolios",
        type_="check",
    )
    op.drop_constraint(
        "ck_portfolios_type",
        "portfolios",
        type_="check",
    )
    op.drop_constraint(
        "fk_portfolios_source_plan_id_portfolios",
        "portfolios",
        type_="foreignkey",
    )
    op.drop_column("portfolios", "source_plan_id")
    op.drop_column("portfolios", "plan_currency")
    op.drop_column("portfolios", "portfolio_type")
