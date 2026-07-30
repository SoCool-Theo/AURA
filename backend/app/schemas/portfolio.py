"""Pydantic request contracts for weight-based portfolio analysis."""

import math
from typing import Annotated, Self

from pydantic import Field, Strict, field_validator, model_validator

from .common import AnalysisPeriod, AssetSymbol, AuraBaseModel


class PortfolioHoldingInput(AuraBaseModel):
    """A normalized asset symbol and its decimal portfolio weight."""

    symbol: AssetSymbol
    weight: Annotated[
        float,
        Field(
            strict=True,
            ge=0.0,
            le=1.0,
            allow_inf_nan=False,
        ),
    ]


class PortfolioAnalysisRequest(AnalysisPeriod):
    """A named, weight-based portfolio request over an inclusive period."""

    portfolio_name: Annotated[str, Strict()]
    holdings: Annotated[
        list[PortfolioHoldingInput],
        Field(min_length=1),
    ]

    @field_validator("portfolio_name", mode="before")
    @classmethod
    def normalize_portfolio_name(cls, value: object) -> object:
        if not isinstance(value, str):
            return value

        normalized = value.strip()
        if not normalized:
            raise ValueError(
                "portfolio_name cannot be empty after normalization"
            )
        return normalized

    @model_validator(mode="after")
    def validate_portfolio(self) -> Self:
        symbols = [holding.symbol for holding in self.holdings]
        if len(symbols) != len(set(symbols)):
            raise ValueError(
                "holding symbols must be unique after normalization"
            )

        total_weight = math.fsum(
            holding.weight for holding in self.holdings
        )
        if not math.isclose(
            total_weight,
            1.0,
            rel_tol=0.0,
            abs_tol=1e-9,
        ):
            raise ValueError(
                "holding weights must sum to 1.0 within an absolute "
                "tolerance of 1e-9"
            )
        return self
