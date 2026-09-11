"""Pydantic contracts for portfolio analysis, CRUD, and holding facts."""

from datetime import UTC, date, datetime
from decimal import Decimal
import math
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import (
    AwareDatetime,
    BeforeValidator,
    ConfigDict,
    Field,
    SerializerFunctionWrapHandler,
    Strict,
    field_validator,
    model_serializer,
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


def _normalize_invested_currency(value: object) -> object:
    if not isinstance(value, str):
        return value
    return value.strip().upper()


_InvestedCurrency = Annotated[
    Literal["USD", "THB"],
    BeforeValidator(_normalize_invested_currency),
]
_PositiveNumeric28Scale12 = Annotated[
    Decimal,
    Field(
        gt=Decimal("0"),
        max_digits=28,
        decimal_places=12,
        allow_inf_nan=False,
    ),
]


class PortfolioRealHoldingInput(AuraBaseModel):
    """Future write contract for one aggregate real asset position."""

    symbol: AssetSymbol
    invested_amount: _PositiveNumeric28Scale12
    invested_currency: _InvestedCurrency = "USD"
    shares: _PositiveNumeric28Scale12
    purchase_date: date

    @field_validator("purchase_date")
    @classmethod
    def reject_future_purchase_date(cls, value: date) -> date:
        if value > datetime.now(UTC).date():
            raise ValueError("purchase_date must not be in the future")
        return value


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
    """One complete legacy allocation or real position in portfolio order."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: UUID | None = None
    symbol: AssetSymbol
    weight: Annotated[
        float | None,
        Field(
            strict=True,
            ge=0.0,
            le=1.0,
            allow_inf_nan=False,
        ),
    ] = None
    invested_amount: _PositiveNumeric28Scale12 | None = None
    invested_currency: _InvestedCurrency | None = None
    shares: _PositiveNumeric28Scale12 | None = None
    purchase_date: date | None = None
    position: Annotated[int, Field(strict=True, ge=0)]

    @model_validator(mode="after")
    def validate_complete_holding_mode(self) -> Self:
        if "id" in self.model_fields_set and self.id is None:
            raise ValueError("holding id cannot be null when supplied")

        real_values = (
            self.invested_amount,
            self.invested_currency,
            self.shares,
            self.purchase_date,
        )
        if self.weight is not None:
            if any(value is not None for value in real_values):
                raise ValueError(
                    "holding response must use exactly one legacy or real mode"
                )
            return self
        if all(value is not None for value in real_values):
            return self
        raise ValueError(
            "holding response must use exactly one legacy or real mode"
        )

    @model_serializer(mode="wrap")
    def preserve_legacy_response_shape(
        self,
        handler: SerializerFunctionWrapHandler,
    ) -> dict[str, object]:
        serialized = handler(self)
        if "id" not in self.model_fields_set and self.id is None:
            serialized.pop("id", None)

        real_field_names = {
            "invested_amount",
            "invested_currency",
            "shares",
            "purchase_date",
        }
        if (
            self.weight is not None
            and not (real_field_names & self.model_fields_set)
        ):
            for field_name in real_field_names:
                serialized.pop(field_name, None)
        return serialized


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
