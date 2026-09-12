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
    """Production write contract for one aggregate real asset position."""

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


def _validate_unique_holding_symbols(
    holdings: list[PortfolioRealHoldingInput],
) -> None:
    symbols = [holding.symbol for holding in holdings]
    if len(symbols) != len(set(symbols)):
        raise ValueError(
            "holding symbols must be unique after normalization"
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
    """Replace a portfolio's complete ordered real holdings."""

    holdings: Annotated[
        list[PortfolioRealHoldingInput],
        Field(min_length=1),
    ]

    @model_validator(mode="after")
    def validate_holdings(self) -> Self:
        _validate_unique_holding_symbols(self.holdings)
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


_PositiveValuationDecimal = Annotated[
    Decimal,
    Field(gt=Decimal("0"), allow_inf_nan=False),
]
_AllocationDecimal = Annotated[
    Decimal,
    Field(ge=Decimal("0"), le=Decimal("1"), allow_inf_nan=False),
]


class PortfolioValuationFxResponse(AuraBaseModel):
    """Fresh USD/THB context used by one THB portfolio valuation."""

    pair: Literal["USD/THB"]
    provider_symbol: Literal["THB=X"]
    rate: _PositiveValuationDecimal
    as_of: date


class PortfolioHoldingValuationResponse(AuraBaseModel):
    """Public current valuation of one saved real holding."""

    id: UUID
    symbol: AssetSymbol
    invested_amount: _PositiveNumeric28Scale12
    invested_currency: _InvestedCurrency
    shares: _PositiveNumeric28Scale12
    purchase_date: date
    position: Annotated[int, Field(strict=True, ge=0)]
    asset_price: _PositiveValuationDecimal
    asset_quote_currency: Literal["USD"]
    price_as_of: date
    current_value_usd: _PositiveValuationDecimal
    current_value: _PositiveValuationDecimal
    current_allocation: _AllocationDecimal


class PortfolioValuationResponse(AuraBaseModel):
    """Public ordered on-demand valuation of one saved portfolio."""

    portfolio_id: UUID
    valuation_currency: _InvestedCurrency
    requested_date: date
    oldest_price_as_of: date
    newest_price_as_of: date
    total_current_value_usd: _PositiveValuationDecimal
    total_current_value: _PositiveValuationDecimal
    fx: PortfolioValuationFxResponse | None
    holdings: Annotated[
        list[PortfolioHoldingValuationResponse],
        Field(min_length=1),
    ]

    @model_validator(mode="after")
    def validate_context(self) -> Self:
        if self.oldest_price_as_of > self.newest_price_as_of:
            raise ValueError(
                "oldest_price_as_of must not be after newest_price_as_of"
            )
        if self.newest_price_as_of > self.requested_date:
            raise ValueError(
                "price observation dates must not be after requested_date"
            )
        if self.valuation_currency == "USD" and self.fx is not None:
            raise ValueError("USD valuation must not contain FX context")
        if self.valuation_currency == "THB" and self.fx is None:
            raise ValueError("THB valuation requires FX context")
        if self.fx is not None and self.fx.as_of > self.requested_date:
            raise ValueError("FX observation date must not be after requested_date")
        return self
