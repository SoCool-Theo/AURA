"""Read-only current valuation for complete real portfolio holdings."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal, localcontext
from enum import StrEnum
from uuid import UUID

from sqlalchemy.orm import Session

from ..core.instruments import (
    InstrumentMetadata,
    InstrumentType,
    USD_THB_FX_SYMBOL,
    get_instrument_metadata,
)
from ..database.models import Holding, MarketData
from .market_data_service import (
    MarketDataService,
    validate_latest_market_observation,
)


# Two persisted Numeric(28,12) operands can produce a 56-digit exact product.
# The local 80-digit floor plus dynamic expansion prevents caller context loss.
_MINIMUM_DECIMAL_PRECISION = 80
_DECIMAL_GUARD_DIGITS = 8
_SUPPORTED_INVESTED_CURRENCIES = frozenset({"USD", "THB"})


class PortfolioDisplayCurrency(StrEnum):
    """Currencies supported for current valuation display values."""

    USD = "USD"
    THB = "THB"

    @classmethod
    def _missing_(cls, value: object) -> PortfolioDisplayCurrency | None:
        if isinstance(value, str):
            normalized = value.strip().upper()
            for member in cls:
                if member.value == normalized:
                    return member
        return None


class PortfolioValuationError(ValueError):
    """Base error for invalid portfolio valuation input or results."""


class InvalidHoldingModeError(PortfolioValuationError):
    """Raised when holdings are legacy, mixed, or incomplete real rows."""


class UnsupportedHoldingInstrumentError(PortfolioValuationError):
    """Raised when a holding is not an approved USD-quoted user asset."""


class InvalidPortfolioValueError(PortfolioValuationError):
    """Raised when a portfolio cannot produce a positive finite value."""


class UnsupportedDisplayCurrencyError(PortfolioValuationError):
    """Raised when the requested display currency is not USD or THB."""


@dataclass(frozen=True, slots=True)
class PortfolioFxContext:
    """One fresh FX observation shared by a complete THB valuation."""

    pair: str
    provider_symbol: str
    rate: Decimal
    as_of: date


@dataclass(frozen=True, slots=True)
class HoldingValuationResult:
    """Current valuation facts for one complete real holding."""

    holding_id: UUID | None
    symbol: str
    invested_amount: Decimal
    invested_currency: str
    shares: Decimal
    purchase_date: date
    position: int
    asset_price: Decimal
    asset_quote_currency: str
    price_as_of: date
    current_value_usd: Decimal
    current_value: Decimal
    current_allocation: Decimal


@dataclass(frozen=True, slots=True)
class PortfolioValuationResult:
    """Ordered on-demand valuation of one real-holding collection."""

    display_currency: PortfolioDisplayCurrency
    requested_date: date
    oldest_price_as_of: date
    newest_price_as_of: date
    total_current_value_usd: Decimal
    total_current_value: Decimal
    fx_context: PortfolioFxContext | None
    holdings: tuple[HoldingValuationResult, ...]


@dataclass(frozen=True, slots=True)
class _RealHoldingFacts:
    holding_id: UUID | None
    symbol: str
    invested_amount: Decimal
    invested_currency: str
    shares: Decimal
    purchase_date: date
    position: int
    instrument: InstrumentMetadata


def _is_positive_finite_decimal(value: object) -> bool:
    return (
        isinstance(value, Decimal)
        and value.is_finite()
        and value > 0
    )


def _resolve_display_currency(
    value: PortfolioDisplayCurrency | str,
) -> PortfolioDisplayCurrency:
    if not isinstance(value, str):
        raise UnsupportedDisplayCurrencyError(
            "display currency must be USD or THB"
        )
    try:
        return PortfolioDisplayCurrency(value.strip().upper())
    except ValueError as error:
        raise UnsupportedDisplayCurrencyError(
            f"unsupported display currency: {value}"
        ) from error


def _snapshot_real_holdings(
    holdings: Sequence[Holding],
) -> tuple[_RealHoldingFacts, ...]:
    selected_holdings = tuple(holdings)
    if not selected_holdings:
        raise InvalidPortfolioValueError(
            "portfolio valuation requires at least one real holding"
        )

    legacy_count = sum(
        holding.weight is not None for holding in selected_holdings
    )
    if legacy_count:
        if legacy_count == len(selected_holdings):
            raise InvalidHoldingModeError(
                "legacy weight-based holdings cannot be valued"
            )
        raise InvalidHoldingModeError(
            "mixed legacy and real holdings cannot be valued"
        )

    snapshots: list[_RealHoldingFacts] = []
    for holding in selected_holdings:
        required_values = {
            "invested_amount": holding.invested_amount,
            "invested_currency": holding.invested_currency,
            "shares": holding.shares,
            "purchase_date": holding.purchase_date,
            "position": holding.position,
        }
        missing_fields = [
            name for name, value in required_values.items() if value is None
        ]
        if missing_fields:
            raise InvalidHoldingModeError(
                "incomplete real holding "
                f"{holding.symbol}: missing {', '.join(missing_fields)}"
            )
        if not _is_positive_finite_decimal(holding.invested_amount):
            raise InvalidHoldingModeError(
                f"real holding invested_amount is invalid: {holding.symbol}"
            )
        if holding.invested_currency not in _SUPPORTED_INVESTED_CURRENCIES:
            raise InvalidHoldingModeError(
                f"real holding invested_currency is invalid: {holding.symbol}"
            )
        if not _is_positive_finite_decimal(holding.shares):
            raise InvalidHoldingModeError(
                f"real holding shares must be positive and finite: {holding.symbol}"
            )
        if type(holding.purchase_date) is not date:
            raise InvalidHoldingModeError(
                f"real holding purchase_date is invalid: {holding.symbol}"
            )
        if type(holding.position) is not int or holding.position < 0:
            raise InvalidHoldingModeError(
                f"real holding position is invalid: {holding.symbol}"
            )

        try:
            instrument = get_instrument_metadata(holding.symbol)
        except (TypeError, ValueError) as error:
            raise UnsupportedHoldingInstrumentError(
                f"unsupported holding symbol: {holding.symbol}"
            ) from error
        if instrument.instrument_type is not InstrumentType.ASSET:
            raise UnsupportedHoldingInstrumentError(
                f"internal market instrument cannot be a holding: {holding.symbol}"
            )
        if instrument.quote_currency != "USD":
            raise UnsupportedHoldingInstrumentError(
                "holding asset is not USD-quoted: "
                f"{instrument.provider_symbol}"
            )

        snapshots.append(
            _RealHoldingFacts(
                holding_id=holding.id,
                symbol=instrument.provider_symbol,
                invested_amount=holding.invested_amount,
                invested_currency=holding.invested_currency,
                shares=holding.shares,
                purchase_date=holding.purchase_date,
                position=holding.position,
                instrument=instrument,
            )
        )
    return tuple(snapshots)


def _multiplication_precision(
    operands: Sequence[tuple[Decimal, Decimal]],
) -> int:
    exact_product_digits = max(
        len(left.as_tuple().digits) + len(right.as_tuple().digits)
        for left, right in operands
    )
    return max(
        _MINIMUM_DECIMAL_PRECISION,
        exact_product_digits + _DECIMAL_GUARD_DIGITS,
    )


def _sum_precision(values: Sequence[Decimal]) -> int:
    lowest_exponent = min(value.as_tuple().exponent for value in values)
    highest_adjusted = max(value.adjusted() for value in values)
    aligned_digits = highest_adjusted - lowest_exponent + 1
    count_digits = len(str(len(values)))
    return max(
        _MINIMUM_DECIMAL_PRECISION,
        aligned_digits + count_digits + _DECIMAL_GUARD_DIGITS,
    )


class PortfolioValuationService:
    """Calculate current values without owning sessions or persisting data."""

    def __init__(self, session: Session) -> None:
        self._market_data = MarketDataService(session)

    def value(
        self,
        holdings: Sequence[Holding],
        *,
        requested_date: date | None = None,
        display_currency: PortfolioDisplayCurrency | str = (
            PortfolioDisplayCurrency.USD
        ),
    ) -> PortfolioValuationResult:
        """Value complete real holdings using fresh persisted market data."""
        valuation_date = requested_date or datetime.now(UTC).date()
        if type(valuation_date) is not date:
            raise TypeError("requested_date must be a date")
        selected_currency = _resolve_display_currency(display_currency)
        holding_facts = _snapshot_real_holdings(holdings)

        symbols = [holding.symbol for holding in holding_facts]
        observations = self._market_data.get_latest_usd_asset_observations(
            symbols,
            valuation_date,
        )
        observations_by_symbol = {
            observation.symbol: observation for observation in observations
        }
        priced_holdings: list[tuple[_RealHoldingFacts, MarketData]] = []
        for holding in holding_facts:
            observation = validate_latest_market_observation(
                observations_by_symbol.get(holding.symbol),
                symbol=holding.symbol,
                requested_date=valuation_date,
            )
            priced_holdings.append((holding, observation))

        fx_observation: MarketData | None = None
        if selected_currency is PortfolioDisplayCurrency.THB:
            fx_observation = self._market_data.get_latest_usd_thb_fx_observation(
                valuation_date
            )
            fx_observation = validate_latest_market_observation(
                fx_observation,
                symbol=USD_THB_FX_SYMBOL,
                requested_date=valuation_date,
            )

        usd_operands = [
            (holding.shares, observation.adjusted_close)
            for holding, observation in priced_holdings
        ]
        precision = _multiplication_precision(usd_operands)

        with localcontext() as context:
            context.prec = precision
            current_values_usd = [
                shares * price for shares, price in usd_operands
            ]
            context.prec = max(
                context.prec,
                _sum_precision(current_values_usd),
            )
            total_current_value_usd = sum(
                current_values_usd,
                start=Decimal(0),
            )
            if (
                not total_current_value_usd.is_finite()
                or total_current_value_usd <= 0
            ):
                raise InvalidPortfolioValueError(
                    "total current portfolio value must be positive and finite"
                )

            allocations = [
                current_value / total_current_value_usd
                for current_value in current_values_usd
            ]

            if fx_observation is None:
                display_values = current_values_usd
                total_current_value = total_current_value_usd
            else:
                fx_rate = fx_observation.adjusted_close
                fx_operands = [
                    (current_value, fx_rate)
                    for current_value in current_values_usd
                ]
                fx_operands.append((total_current_value_usd, fx_rate))
                context.prec = max(
                    context.prec,
                    _multiplication_precision(fx_operands),
                )
                display_values = [
                    current_value * fx_rate
                    for current_value in current_values_usd
                ]
                total_current_value = total_current_value_usd * fx_rate

        holding_results = tuple(
            HoldingValuationResult(
                holding_id=holding.holding_id,
                symbol=holding.symbol,
                invested_amount=holding.invested_amount,
                invested_currency=holding.invested_currency,
                shares=holding.shares,
                purchase_date=holding.purchase_date,
                position=holding.position,
                asset_price=observation.adjusted_close,
                asset_quote_currency=holding.instrument.quote_currency,
                price_as_of=observation.date,
                current_value_usd=current_value_usd,
                current_value=current_value,
                current_allocation=allocation,
            )
            for (
                (holding, observation),
                current_value_usd,
                current_value,
                allocation,
            ) in zip(
                priced_holdings,
                current_values_usd,
                display_values,
                allocations,
                strict=True,
            )
        )
        price_dates = [result.price_as_of for result in holding_results]
        fx_context = (
            None
            if fx_observation is None
            else PortfolioFxContext(
                pair="USD/THB",
                provider_symbol=USD_THB_FX_SYMBOL,
                rate=fx_observation.adjusted_close,
                as_of=fx_observation.date,
            )
        )
        return PortfolioValuationResult(
            display_currency=selected_currency,
            requested_date=valuation_date,
            oldest_price_as_of=min(price_dates),
            newest_price_as_of=max(price_dates),
            total_current_value_usd=total_current_value_usd,
            total_current_value=total_current_value,
            fx_context=fx_context,
            holdings=holding_results,
        )
