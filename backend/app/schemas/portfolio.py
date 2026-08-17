"""Pydantic contracts for weight-based portfolio analysis and CRUD."""

import math
from typing import Annotated, Self
from uuid import UUID

from pydantic import (
    AwareDatetime,
    Field,
    Strict,
    field_validator,
    model_validator,
)

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


def _normalize_portfolio_name(value: object, *, field_name: str) -> object:
    if not isinstance(value, str):
        return value

    normalized = value.strip()
    if not normalized:
        raise ValueError(
            f"{field_name} cannot be empty after normalization"
        )
    return normalized


def _validate_portfolio_holdings(
    holdings: list[PortfolioHoldingInput],
) -> None:
    symbols = [holding.symbol for holding in holdings]
    if len(symbols) != len(set(symbols)):
        raise ValueError(
            "holding symbols must be unique after normalization"
        )

    total_weight = math.fsum(holding.weight for holding in holdings)
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
        return _normalize_portfolio_name(
            value,
            field_name="portfolio_name",
        )

    @model_validator(mode="after")
    def validate_portfolio(self) -> Self:
        _validate_portfolio_holdings(self.holdings)
        return self


class _PortfolioNameRequest(AuraBaseModel):
    """Private shared validation for CRUD requests containing only a name."""

    name: Annotated[str, Strict()]

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: object) -> object:
        return _normalize_portfolio_name(value, field_name="name")


class PortfolioCreateRequest(_PortfolioNameRequest):
    """Create an empty named portfolio draft."""


class PortfolioUpdateRequest(_PortfolioNameRequest):
    """Rename an existing portfolio."""


class PortfolioDuplicateRequest(_PortfolioNameRequest):
    """Supply the name for a duplicated portfolio."""


class PortfolioHoldingsReplaceRequest(AuraBaseModel):
    """Replace a portfolio's complete ordered allocation."""

    holdings: Annotated[
        list[PortfolioHoldingInput],
        Field(min_length=1),
    ]

    @model_validator(mode="after")
    def validate_holdings(self) -> Self:
        _validate_portfolio_holdings(self.holdings)
        return self


class PortfolioHoldingResponse(AuraBaseModel):
    """One persisted holding in its portfolio order."""

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
    position: Annotated[int, Field(strict=True, ge=0)]


class PortfolioResponse(AuraBaseModel):
    """A complete end-user portfolio response."""

    id: UUID
    name: Annotated[str, Strict()]
    created_at: AwareDatetime
    updated_at: AwareDatetime
    holdings: list[PortfolioHoldingResponse]


class PortfolioSummaryResponse(AuraBaseModel):
    """A lightweight portfolio representation for ordered listings."""

    id: UUID
    name: Annotated[str, Strict()]
    created_at: AwareDatetime
    updated_at: AwareDatetime


class PortfolioListResponse(AuraBaseModel):
    """An ordered collection of portfolio summaries."""

    portfolios: list[PortfolioSummaryResponse]
