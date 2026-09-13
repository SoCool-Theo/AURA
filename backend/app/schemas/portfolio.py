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
_PortfolioType = Annotated[
    Literal["CURRENT", "PLANNED", "LEGACY"],
    BeforeValidator(_normalize_invested_currency),
]
_CreatablePortfolioType = Annotated[
    Literal["CURRENT", "PLANNED"],
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


class PortfolioPlannedHoldingInput(AuraBaseModel):
    """One proposed investment amount in the portfolio's plan currency."""

    symbol: AssetSymbol
    proposed_amount: _PositiveNumeric28Scale12


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
    holdings: list[PortfolioRealHoldingInput | PortfolioPlannedHoldingInput],
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
    """Create an explicitly current or planned empty portfolio draft."""

    portfolio_type: _CreatablePortfolioType = "CURRENT"
    plan_currency: _InvestedCurrency | None = None

    @model_validator(mode="after")
    def validate_type_context(self) -> Self:
        if self.portfolio_type == "PLANNED" and self.plan_currency is None:
            raise ValueError("planned portfolios require plan_currency")
        if self.portfolio_type == "CURRENT" and self.plan_currency is not None:
            raise ValueError("current portfolios must not define plan_currency")
        return self


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


class PortfolioPlannedHoldingsReplaceRequest(AuraBaseModel):
    """Replace a planned portfolio's complete ordered proposed amounts."""

    holdings: Annotated[
        list[PortfolioPlannedHoldingInput],
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
    proposed_amount: _PositiveNumeric28Scale12 | None = None
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
        if self.proposed_amount is not None:
            if self.weight is not None or any(
                value is not None for value in real_values
            ):
                raise ValueError(
                    "holding response must use exactly one legacy, current, "
                    "or planned mode"
                )
            return self
        if self.weight is not None:
            if any(value is not None for value in real_values):
                raise ValueError(
                    "holding response must use exactly one legacy, current, "
                    "or planned mode"
                )
            return self
        if all(value is not None for value in real_values):
            return self
        raise ValueError(
            "holding response must use exactly one legacy, current, or "
            "planned mode"
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
            and not (
                (real_field_names | {"proposed_amount"})
                & self.model_fields_set
            )
        ):
            for field_name in real_field_names:
                serialized.pop(field_name, None)
            serialized.pop("proposed_amount", None)
        elif self.proposed_amount is not None:
            for field_name in real_field_names:
                serialized.pop(field_name, None)
        else:
            serialized.pop("proposed_amount", None)
        return serialized


class PortfolioResponse(AuraBaseModel):
    """A complete end-user portfolio response."""

    id: UUID
    name: Annotated[str, Strict()]
    portfolio_type: _PortfolioType = "CURRENT"
    plan_currency: _InvestedCurrency | None = None
    source_plan_id: UUID | None = None
    created_at: AwareDatetime
    updated_at: AwareDatetime
    holdings: list[PortfolioHoldingResponse]

    @model_validator(mode="after")
    def validate_portfolio_type_context(self) -> Self:
        if self.portfolio_type == "PLANNED":
            if self.plan_currency is None or self.source_plan_id is not None:
                raise ValueError("planned portfolio context is incomplete")
            valid_holdings = all(
                holding.proposed_amount is not None
                for holding in self.holdings
            )
        elif self.portfolio_type == "CURRENT":
            if self.plan_currency is not None:
                raise ValueError("current portfolio must not define plan currency")
            valid_holdings = all(
                holding.proposed_amount is None
                and holding.weight is None
                and holding.invested_amount is not None
                for holding in self.holdings
            )
        else:
            if self.plan_currency is not None or self.source_plan_id is not None:
                raise ValueError("legacy portfolio context is invalid")
            valid_holdings = all(
                holding.weight is not None for holding in self.holdings
            )
        if not valid_holdings:
            raise ValueError("holdings do not match portfolio_type")
        return self


class PortfolioSummaryResponse(AuraBaseModel):
    """A lightweight portfolio representation for ordered listings."""

    id: UUID
    name: Annotated[str, Strict()]
    portfolio_type: _PortfolioType = "CURRENT"
    plan_currency: _InvestedCurrency | None = None
    created_at: AwareDatetime
    updated_at: AwareDatetime

    @model_validator(mode="after")
    def validate_portfolio_type_context(self) -> Self:
        if (self.portfolio_type == "PLANNED") != (
            self.plan_currency is not None
        ):
            raise ValueError("plan_currency must match portfolio_type")
        return self


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


class PortfolioPlannedAllocationHoldingResponse(AuraBaseModel):
    """One backend-derived target allocation in saved holding order."""

    id: UUID
    symbol: AssetSymbol
    proposed_amount: _PositiveNumeric28Scale12
    target_allocation: _AllocationDecimal
    position: Annotated[int, Field(strict=True, ge=0)]


class PortfolioPlannedAllocationResponse(AuraBaseModel):
    """Canonical target allocation derived without market prices or FX."""

    portfolio_id: UUID
    portfolio_type: Literal["PLANNED"]
    plan_currency: _InvestedCurrency
    total_proposed_amount: _PositiveValuationDecimal
    holdings: Annotated[
        list[PortfolioPlannedAllocationHoldingResponse],
        Field(min_length=1),
    ]


class PortfolioValuationFxResponse(AuraBaseModel):
    """Fresh USD/THB context used by one THB portfolio valuation."""

    pair: Literal["USD/THB"]
    provider_symbol: Literal["THB=X"]
    rate: _PositiveValuationDecimal
    as_of: date


class PortfolioPlannedPreviewHoldingResponse(AuraBaseModel):
    """One planned holding with optional non-authoritative share estimate."""

    id: UUID
    symbol: AssetSymbol
    proposed_amount: _PositiveNumeric28Scale12
    target_allocation: _AllocationDecimal
    position: Annotated[int, Field(strict=True, ge=0)]
    estimate_status: Literal[
        "AVAILABLE",
        "PRICE_UNAVAILABLE",
        "FX_UNAVAILABLE",
    ]
    estimated_shares: _PositiveValuationDecimal | None
    asset_price: _PositiveValuationDecimal | None
    asset_quote_currency: Literal["USD"] | None
    price_as_of: date | None

    @model_validator(mode="after")
    def validate_estimate_context(self) -> Self:
        price_context = (
            self.asset_price,
            self.asset_quote_currency,
            self.price_as_of,
        )
        if self.estimate_status == "AVAILABLE":
            if self.estimated_shares is None or not all(
                value is not None for value in price_context
            ):
                raise ValueError("available estimate requires price context")
        elif self.estimate_status == "PRICE_UNAVAILABLE":
            if self.estimated_shares is not None or any(
                value is not None for value in price_context
            ):
                raise ValueError("unavailable price must not expose price context")
        elif self.estimated_shares is not None or not all(
            value is not None for value in price_context
        ):
            raise ValueError("unavailable FX requires asset price context")
        return self


class PortfolioPlannedPreviewResponse(AuraBaseModel):
    """Planned allocation with best-effort current estimate context."""

    portfolio_id: UUID
    portfolio_type: Literal["PLANNED"]
    plan_currency: _InvestedCurrency
    requested_date: date
    total_proposed_amount: _PositiveValuationDecimal
    fx: PortfolioValuationFxResponse | None
    holdings: Annotated[
        list[PortfolioPlannedPreviewHoldingResponse],
        Field(min_length=1),
    ]

    @model_validator(mode="after")
    def validate_currency_context(self) -> Self:
        if self.plan_currency == "USD" and self.fx is not None:
            raise ValueError("USD planned preview must not include FX")
        if self.fx is not None and self.fx.as_of > self.requested_date:
            raise ValueError("FX observation date must not be after requested_date")
        if any(
            holding.price_as_of is not None
            and holding.price_as_of > self.requested_date
            for holding in self.holdings
        ):
            raise ValueError(
                "price observation dates must not be after requested_date"
            )

        statuses = {holding.estimate_status for holding in self.holdings}
        if self.plan_currency == "USD" and "FX_UNAVAILABLE" in statuses:
            raise ValueError("USD planned preview cannot require FX")
        if self.plan_currency == "THB":
            if self.fx is None and "AVAILABLE" in statuses:
                raise ValueError("available THB estimates require FX context")
            if self.fx is not None and "FX_UNAVAILABLE" in statuses:
                raise ValueError(
                    "THB estimates cannot report unavailable FX with FX context"
                )
        return self


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
