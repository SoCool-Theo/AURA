"""Display conversion using persisted FX, without revaluation or model inference."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal, localcontext
from typing import TYPE_CHECKING, Literal, TypeVar

from ..schemas.currency_display import (
    CurrencyDisplayContext, CurrencyDisplayHolding, CurrencyDisplayView,
)
from ..schemas.portfolio import PortfolioValuationFxResponse
from .market_data_service import MarketDataService, MarketDataUnavailableError

if TYPE_CHECKING:
    from ..schemas.forecasting import PortfolioOutlookResponse
    from ..schemas.weekly_forecasting import WeeklyPortfolioOutlookResponse
    from .portfolio_baseline_resolver import PortfolioBaselineResolution

ForecastResponseT = TypeVar("ForecastResponseT", bound="PortfolioOutlookResponse | WeeklyPortfolioOutlookResponse")


def optional_display_fx(market_data: MarketDataService, requested_date: date) -> PortfolioValuationFxResponse | None:
    """Unavailable FX disables the alternate view without blocking the result."""
    try:
        observation = market_data.get_latest_usd_thb_fx_observation(requested_date)
        if not 0 <= (requested_date - observation.date).days <= 4:
            return None
        return PortfolioValuationFxResponse(
            pair="USD/THB", provider_symbol=observation.symbol,
            rate=observation.adjusted_close, as_of=observation.date,
        )
    except (MarketDataUnavailableError, ValueError, IndexError):
        return None


def build_currency_display(
    *, baseline_kind: Literal["current", "planned"], source_currency: Literal["USD", "THB"],
    requested_date: date, baseline_amount: Decimal, holdings: list[CurrencyDisplayHolding],
    fx: PortfolioValuationFxResponse | None = None,
    expected_change_amount: Decimal | None = None, estimated_ending_value: Decimal | None = None,
) -> CurrencyDisplayContext:
    """Convert each exact amount; do not derive holdings from rounded weights."""
    source = CurrencyDisplayView(
        currency=source_currency, baseline_amount=baseline_amount, holdings=holdings,
        expected_change_amount=expected_change_amount, estimated_ending_value=estimated_ending_value,
    )
    views = [source]
    if fx is not None:
        def convert(amount: Decimal | None) -> Decimal | None:
            if amount is None:
                return None
            with localcontext() as context:
                context.prec = 80
                return amount * fx.rate if source_currency == "USD" else amount / fx.rate

        views.append(CurrencyDisplayView(
            currency="THB" if source_currency == "USD" else "USD",
            baseline_amount=convert(source.baseline_amount),
            expected_change_amount=convert(source.expected_change_amount),
            estimated_ending_value=convert(source.estimated_ending_value),
            holdings=[CurrencyDisplayHolding(
                symbol=holding.symbol, baseline_amount=convert(holding.baseline_amount),
                expected_change_amount=convert(holding.expected_change_amount),
                estimated_ending_value=convert(holding.estimated_ending_value),
            ) for holding in source.holdings],
        ))
    return CurrencyDisplayContext(
        baseline_kind=baseline_kind, source_currency=source_currency,
        requested_date=requested_date, fx=fx, views=views,
    )


def simulation_currency_display(baseline: PortfolioBaselineResolution, market_data: MarketDataService) -> CurrencyDisplayContext | None:
    """Capture conversion once at creation; history never reads current FX."""
    if baseline.baseline_kind.value == "legacy":
        return None
    valuation = baseline.valuation
    plan = baseline.planned_allocation
    requested_date = valuation.requested_date if valuation else datetime.now(UTC).date()
    if valuation:
        source_currency, total = "USD", valuation.total_current_value_usd
        holdings = [CurrencyDisplayHolding(symbol=h.symbol, baseline_amount=h.current_value_usd)
                    for h in valuation.holdings]
    else:
        source_currency, total = plan.plan_currency, plan.total_proposed_amount
        holdings = [CurrencyDisplayHolding(symbol=h.symbol, baseline_amount=h.proposed_amount)
                    for h in plan.holdings]
    return build_currency_display(
        baseline_kind="current" if valuation else "planned", source_currency=source_currency,
        requested_date=requested_date, baseline_amount=total, holdings=holdings,
        fx=optional_display_fx(market_data, requested_date),
    )


def with_forecast_currency_display(response: ForecastResponseT, market_data: MarketDataService) -> ForecastResponseT:
    """Add views to a completed forecast, preserving its canonical projection."""
    money = response.monetary_projection
    if money is None:
        return response
    requested_date = money.valuation_requested_date or datetime.now(UTC).date()
    display = build_currency_display(
        baseline_kind=response.baseline_kind, source_currency=money.currency,
        requested_date=requested_date, baseline_amount=money.baseline_amount,
        expected_change_amount=money.expected_change_amount,
        estimated_ending_value=money.estimated_ending_value,
        holdings=[CurrencyDisplayHolding(
            symbol=c.symbol, baseline_amount=c.monetary_projection.baseline_amount,
            expected_change_amount=c.monetary_projection.expected_change_amount,
            estimated_ending_value=c.monetary_projection.estimated_ending_value,
        ) for c in response.components],
        fx=optional_display_fx(market_data, requested_date),
    )
    return response.model_copy(update={"currency_display": display})
