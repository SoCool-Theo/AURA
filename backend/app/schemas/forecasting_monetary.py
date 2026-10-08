"""Additive portfolio-only monetary estimate contract shared by all horizons."""

from datetime import date
from decimal import Decimal
from typing import Annotated, Literal, Self

from pydantic import Field, field_validator, model_validator

from ..forecasting.monetary_projection import MONETARY_PROJECTION_LIMITATIONS, projection_amounts
from .common import AuraBaseModel


FiniteAmount = Annotated[Decimal, Field(allow_inf_nan=False)]


class PortfolioMonetaryProjectionResponse(AuraBaseModel):
    currency: Literal["USD", "THB"]
    baseline_source: Literal["current_market_value", "planned_investment"]
    baseline_amount: Annotated[Decimal, Field(gt=0, allow_inf_nan=False)]
    expected_change_amount: FiniteAmount
    estimated_ending_value: FiniteAmount
    hypothetical: Annotated[bool, Field(strict=True)]
    assumes_unchanged_fx: Annotated[bool, Field(strict=True)]
    valuation_requested_date: date | None
    oldest_price_as_of: date | None
    newest_price_as_of: date | None
    limitations: list[str]

    @field_validator("limitations")
    @classmethod
    def approved_wording(cls, value: list[str]) -> list[str]:
        if tuple(value) != MONETARY_PROJECTION_LIMITATIONS:
            raise ValueError("monetary limitations must use approved wording")
        return value

    @model_validator(mode="after")
    def baseline_context(self) -> Self:
        dates = (self.valuation_requested_date, self.oldest_price_as_of, self.newest_price_as_of)
        if self.baseline_source == "current_market_value":
            if self.currency != "USD" or self.hypothetical or any(value is None for value in dates):
                raise ValueError("current monetary projection requires USD valuation provenance")
            if not self.oldest_price_as_of <= self.newest_price_as_of <= self.valuation_requested_date:
                raise ValueError("invalid monetary valuation dates")
        elif not self.hypothetical or any(value is not None for value in dates):
            raise ValueError("planned monetary projection must be hypothetical without valuation dates")
        if self.assumes_unchanged_fx != (self.currency == "THB"):
            raise ValueError("THB monetary estimates must disclose the unchanged FX assumption")
        return self


def validate_monetary_projection(
    projection: PortfolioMonetaryProjectionResponse | None, baseline_kind: str, expected_return: float,
) -> None:
    if baseline_kind == "legacy":
        if projection is not None:
            raise ValueError("legacy weights cannot supply a monetary projection")
        return
    source = "current_market_value" if baseline_kind == "current" else "planned_investment"
    if projection is None or projection.baseline_source != source:
        raise ValueError("monetary projection must match the portfolio baseline")
    change, ending = projection_amounts(projection.baseline_amount, expected_return)
    if projection.expected_change_amount != change or projection.estimated_ending_value != ending:
        raise ValueError("monetary amounts must match the unchanged portfolio expected return")
