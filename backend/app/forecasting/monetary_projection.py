"""Read-only money illustrations from the already resolved portfolio baseline."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, DecimalException, localcontext
import math
from numbers import Real
from typing import TYPE_CHECKING

from .inference_errors import ForecastPredictionError

if TYPE_CHECKING:
    from ..services.portfolio_baseline_resolver import PortfolioBaselineResolution


MONETARY_PROJECTION_LIMITATIONS = (
    "Monetary estimates illustrate the expected return applied to the baseline; they are not guaranteed balances.",
    "Amounts assume unchanged holdings or planned allocation and exclude fees, taxes, deposits and withdrawals.",
    "Planned portfolio amounts are hypothetical; THB projections assume unchanged exchange rates, not an FX forecast.",
    "Volatility is not a monetary loss estimate; no calibrated portfolio monetary prediction interval is provided.",
    "Model returns are not bounded at -100%; a negative ending estimate is a mathematical output, not a realizable long-only balance.",
)


@dataclass(frozen=True, slots=True)
class PortfolioMonetaryProjection:
    currency: str
    baseline_source: str
    baseline_amount: Decimal
    expected_change_amount: Decimal
    estimated_ending_value: Decimal
    hypothetical: bool
    assumes_unchanged_fx: bool
    valuation_requested_date: date | None
    oldest_price_as_of: date | None
    newest_price_as_of: date | None
    limitations: tuple[str, ...] = MONETARY_PROJECTION_LIMITATIONS


def projection_amounts(baseline_amount: Decimal, expected_return: float) -> tuple[Decimal, Decimal]:
    """Preserve the model ratio and money precision; never round or clamp here."""
    if (not isinstance(baseline_amount, Decimal) or not baseline_amount.is_finite()
            or baseline_amount <= 0 or not isinstance(expected_return, Real)
            or isinstance(expected_return, bool) or not math.isfinite(expected_return)):
        raise ForecastPredictionError("invalid monetary projection inputs")
    rate = Decimal(str(expected_return))
    try:
        with localcontext() as context:
            # Enough digits for multiplication and alignment when adding the baseline,
            # including very small/large finite model returns and low caller precision.
            context.prec = max(80, len(baseline_amount.as_tuple().digits)
                               + len(rate.as_tuple().digits) + abs(rate.as_tuple().exponent) + 8)
            change = baseline_amount * rate
            ending = baseline_amount + change
        if not change.is_finite() or not ending.is_finite():
            raise ForecastPredictionError("invalid monetary projection amounts")
        return change, ending
    except DecimalException:
        raise ForecastPredictionError("invalid monetary projection amounts") from None


def build_monetary_projection(
    baseline: PortfolioBaselineResolution, expected_return: float,
) -> PortfolioMonetaryProjection | None:
    """Reuse valuation/allocation facts; no queries, FX conversion or model calls."""
    kind = baseline.baseline_kind.value
    if kind == "legacy":
        return None  # Saved weights alone cannot establish a real money baseline.
    if kind == "current":
        valuation = baseline.valuation
        if valuation is None or baseline.planned_allocation is not None:
            raise ForecastPredictionError("missing current monetary baseline")
        requested, oldest, newest = (
            valuation.requested_date, valuation.oldest_price_as_of, valuation.newest_price_as_of,
        )
        if (any(type(value) is not date for value in (requested, oldest, newest))
                or not oldest <= newest <= requested or baseline.valuation_as_of != requested):
            raise ForecastPredictionError("invalid current monetary baseline dates")
        amount, currency, source = valuation.total_current_value_usd, "USD", "current_market_value"
    elif kind == "planned":
        allocation = baseline.planned_allocation
        if allocation is None or baseline.valuation is not None or baseline.valuation_as_of is not None:
            raise ForecastPredictionError("missing planned monetary baseline")
        amount, currency, source = allocation.total_proposed_amount, allocation.plan_currency, "planned_investment"
        if currency not in ("USD", "THB"):
            raise ForecastPredictionError("unsupported monetary projection currency")
        requested = oldest = newest = None
    else:
        raise ForecastPredictionError("invalid monetary baseline kind")
    change, ending = projection_amounts(amount, expected_return)
    return PortfolioMonetaryProjection(
        currency, source, amount, change, ending, kind == "planned", currency == "THB",
        requested, oldest, newest,
    )
