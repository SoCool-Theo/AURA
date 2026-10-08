"""Shared mapping for immutable planned-portfolio baseline snapshots."""

from ..schemas.portfolio import (
    PLANNED_PORTFOLIO_HYPOTHETICAL_NOTICE,
    PlannedPortfolioBaselineContext,
    PlannedPortfolioSnapshotHolding,
)
from .portfolio_planned_allocation_service import PlannedPortfolioAllocation


def planned_allocation_to_snapshot_baseline(
    allocation: PlannedPortfolioAllocation,
) -> PlannedPortfolioBaselineContext:
    """Map one authoritative planned allocation without recalculation."""
    return PlannedPortfolioBaselineContext(
        portfolio_type="PLANNED",
        baseline_source="proposed-amount-target-allocation",
        plan_currency=allocation.plan_currency,
        total_proposed_amount=allocation.total_proposed_amount,
        hypothetical_notice=PLANNED_PORTFOLIO_HYPOTHETICAL_NOTICE,
        holdings=[
            PlannedPortfolioSnapshotHolding(
                id=holding.holding_id,
                symbol=holding.symbol,
                proposed_amount=holding.proposed_amount,
                target_allocation=holding.target_allocation,
                position=holding.position,
            )
            for holding in allocation.holdings
        ],
    )


__all__ = ["planned_allocation_to_snapshot_baseline"]
