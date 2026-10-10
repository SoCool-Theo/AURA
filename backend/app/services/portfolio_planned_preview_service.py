"""Optional current-price estimates for planned portfolio holdings."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, localcontext
from enum import StrEnum
from uuid import UUID

from sqlalchemy.orm import Session

from ..database.models import MarketData, Portfolio
from .market_data_service import MarketDataService, MarketDataUnavailableError
from .portfolio_planned_allocation_service import (
    PlannedAllocationHolding,
    PlannedPortfolioAllocation,
    PortfolioPlannedAllocationService,
)
from .portfolio_valuation_service import PortfolioFxContext


_MINIMUM_DECIMAL_PRECISION = 80


class PlannedEstimateStatus(StrEnum):
    """Availability of one non-authoritative estimated share value."""

    AVAILABLE = "AVAILABLE"
    PRICE_UNAVAILABLE = "PRICE_UNAVAILABLE"
    FX_UNAVAILABLE = "FX_UNAVAILABLE"


@dataclass(frozen=True, slots=True)
class PlannedHoldingPreview:
    """One target allocation with optional current-price estimate context."""

    holding_id: UUID
    symbol: str
    proposed_amount: Decimal
    target_allocation: Decimal
    position: int
    estimate_status: PlannedEstimateStatus
    estimated_shares: Decimal | None
    asset_price: Decimal | None
    asset_quote_currency: str | None
    price_as_of: date | None


@dataclass(frozen=True, slots=True)
class PlannedPortfolioPreview:
    """Price-independent allocation plus best-effort display estimates."""

    portfolio_id: UUID
    plan_currency: str
    requested_date: date
    total_proposed_amount: Decimal
    fx_context: PortfolioFxContext | None
    holdings: tuple[PlannedHoldingPreview, ...]


class PortfolioPlannedPreviewService:
    """Build a non-authoritative preview without mutating saved facts."""

    def __init__(self, session: Session) -> None:
        self._market_data = MarketDataService(session)
        self._allocation_service = PortfolioPlannedAllocationService()

    def preview(
        self,
        *,
        portfolio: Portfolio,
        requested_date: date,
    ) -> PlannedPortfolioPreview:
        """Return allocations even when current price or FX data is absent."""
        if type(requested_date) is not date:
            raise TypeError("requested_date must be a date")

        allocation = self._allocation_service.resolve(portfolio)
        fx_observation = self._optional_fx_observation(
            allocation,
            requested_date,
        )
        fx_context = (
            None
            if fx_observation is None
            else PortfolioFxContext(
                pair="USD/THB",
                provider_symbol=fx_observation.symbol,
                rate=fx_observation.adjusted_close,
                as_of=fx_observation.date,
            )
        )
        return PlannedPortfolioPreview(
            portfolio_id=allocation.portfolio_id,
            plan_currency=allocation.plan_currency,
            requested_date=requested_date,
            total_proposed_amount=allocation.total_proposed_amount,
            fx_context=fx_context,
            holdings=tuple(
                self._preview_holding(
                    holding=holding,
                    plan_currency=allocation.plan_currency,
                    requested_date=requested_date,
                    fx_observation=fx_observation,
                )
                for holding in allocation.holdings
            ),
        )

    def _optional_fx_observation(
        self,
        allocation: PlannedPortfolioAllocation,
        requested_date: date,
    ) -> MarketData | None:
        if allocation.plan_currency != "THB":
            return None
        try:
            return self._market_data.get_latest_usd_thb_fx_observation(
                requested_date
            )
        except (MarketDataUnavailableError, ValueError):
            return None

    def _preview_holding(
        self,
        *,
        holding: PlannedAllocationHolding,
        plan_currency: str,
        requested_date: date,
        fx_observation: MarketData | None,
    ) -> PlannedHoldingPreview:
        try:
            observation = self._market_data.get_latest_usd_asset_observations(
                [holding.symbol],
                requested_date,
            )[0]
        except (MarketDataUnavailableError, ValueError, IndexError):
            return PlannedHoldingPreview(
                holding_id=holding.holding_id,
                symbol=holding.symbol,
                proposed_amount=holding.proposed_amount,
                target_allocation=holding.target_allocation,
                position=holding.position,
                estimate_status=PlannedEstimateStatus.PRICE_UNAVAILABLE,
                estimated_shares=None,
                asset_price=None,
                asset_quote_currency=None,
                price_as_of=None,
            )

        if plan_currency == "THB" and fx_observation is None:
            return PlannedHoldingPreview(
                holding_id=holding.holding_id,
                symbol=holding.symbol,
                proposed_amount=holding.proposed_amount,
                target_allocation=holding.target_allocation,
                position=holding.position,
                estimate_status=PlannedEstimateStatus.FX_UNAVAILABLE,
                estimated_shares=None,
                asset_price=observation.adjusted_close,
                asset_quote_currency="USD",
                price_as_of=observation.date,
            )

        with localcontext() as context:
            context.prec = _MINIMUM_DECIMAL_PRECISION
            amount_usd = holding.proposed_amount
            if fx_observation is not None:
                amount_usd = amount_usd / fx_observation.adjusted_close
            estimated_shares = amount_usd / observation.adjusted_close

        return PlannedHoldingPreview(
            holding_id=holding.holding_id,
            symbol=holding.symbol,
            proposed_amount=holding.proposed_amount,
            target_allocation=holding.target_allocation,
            position=holding.position,
            estimate_status=PlannedEstimateStatus.AVAILABLE,
            estimated_shares=estimated_shares,
            asset_price=observation.adjusted_close,
            asset_quote_currency="USD",
            price_as_of=observation.date,
        )


__all__ = [
    "PlannedEstimateStatus",
    "PlannedHoldingPreview",
    "PlannedPortfolioPreview",
    "PortfolioPlannedPreviewService",
]
