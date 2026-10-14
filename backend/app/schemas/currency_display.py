"""Backend-owned amount views; canonical allocations and metrics stay unchanged."""

from datetime import date
from decimal import Decimal, localcontext
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from .common import AssetSymbol, AuraBaseModel
from .portfolio import PortfolioValuationFxResponse

Currency = Literal["USD", "THB"]
Amount = Annotated[Decimal, Field(allow_inf_nan=False)]
PositiveAmount = Annotated[Decimal, Field(gt=0, allow_inf_nan=False)]


class CurrencyDisplayHolding(AuraBaseModel):
    symbol: AssetSymbol
    baseline_amount: PositiveAmount
    expected_change_amount: Amount | None = None
    estimated_ending_value: Amount | None = None


class CurrencyDisplayView(AuraBaseModel):
    currency: Currency
    baseline_amount: PositiveAmount
    expected_change_amount: Amount | None = None
    estimated_ending_value: Amount | None = None
    holdings: Annotated[list[CurrencyDisplayHolding], Field(min_length=1)]


class CurrencyDisplayContext(AuraBaseModel):
    baseline_kind: Literal["current", "planned"]
    source_currency: Currency
    requested_date: date
    fx: PortfolioValuationFxResponse | None = None
    views: Annotated[list[CurrencyDisplayView], Field(min_length=1, max_length=2)]

    @model_validator(mode="after")
    def validate_views(self) -> Self:
        currencies = [view.currency for view in self.views]
        if currencies[0] != self.source_currency or len(set(currencies)) != len(currencies):
            raise ValueError("currency views must start with the unique source currency")
        if len(currencies) > 1 and self.fx is None:
            raise ValueError("alternate currency requires an observed USD/THB rate")
        if self.fx is not None and not 0 <= (self.requested_date - self.fx.as_of).days <= 4:
            raise ValueError("currency display requires fresh, non-future FX")
        symbols = [holding.symbol for holding in self.views[0].holdings]
        if len(set(symbols)) != len(symbols):
            raise ValueError("currency holdings must have unique symbols")
        for view in self.views:
            if [holding.symbol for holding in view.holdings] != symbols:
                raise ValueError("currency views must preserve holding symbols and order")
            projected = view.expected_change_amount is not None
            if (view.estimated_ending_value is not None) != projected or any(
                (holding.expected_change_amount is not None) != projected
                or (holding.estimated_ending_value is not None) != projected
                for holding in view.holdings
            ):
                raise ValueError("currency projections must be complete")
        if len(self.views) == 2:
            source, alternate = self.views
            with localcontext() as context:
                context.prec = 80
                for left, right in [(source, alternate), *zip(source.holdings, alternate.holdings, strict=True)]:
                    for field in ("baseline_amount", "expected_change_amount", "estimated_ending_value"):
                        amount = getattr(left, field)
                        expected = None if amount is None else (amount * self.fx.rate if self.source_currency == "USD" else amount / self.fx.rate)
                        if getattr(right, field) != expected:
                            raise ValueError("alternate amounts must use the observed FX rate")
        return self


def validate_forecast_currency_display(display, kind, money, components):
    """A display view must reference the exact unchanged canonical projections."""
    if display is None:
        return
    if money is None or display.baseline_kind != kind or display.source_currency != money.currency:
        raise ValueError("currency display must match the canonical baseline")
    source = display.views[0]
    rows = {holding.symbol: holding for holding in source.holdings}
    if set(rows) != {component.symbol for component in components}:
        raise ValueError("currency display symbols must match forecast components")
    for amounts, projection in [(source, money), *[(rows[c.symbol], c.monetary_projection) for c in components]]:
        if projection is None or any(getattr(amounts, field) != getattr(projection, field)
            for field in ("baseline_amount", "expected_change_amount", "estimated_ending_value")):
            raise ValueError("source display amounts must match the canonical projection")
