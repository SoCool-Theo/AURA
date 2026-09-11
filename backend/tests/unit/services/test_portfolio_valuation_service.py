from dataclasses import FrozenInstanceError
from datetime import date
from decimal import Decimal, getcontext, localcontext
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
from sqlalchemy.orm import Session

from backend.app.core.instruments import InstrumentMetadata, InstrumentType
from backend.app.database.models import Holding, MarketData
from backend.app.services.market_data_service import (
    MarketDataService,
    MarketDataUnavailableError,
)
import backend.app.services.portfolio_valuation_service as valuation_module
from backend.app.services.portfolio_valuation_service import (
    InvalidHoldingModeError,
    InvalidPortfolioValueError,
    PortfolioDisplayCurrency,
    PortfolioValuationService,
    UnsupportedDisplayCurrencyError,
    UnsupportedHoldingInstrumentError,
)


REQUESTED_DATE = date(2026, 9, 11)
PORTFOLIO_ID = UUID("41000000-0000-0000-0000-000000000001")


def _holding(
    symbol: str = "AAPL",
    *,
    position: int = 0,
    shares: Decimal = Decimal("2.000000000000"),
    invested_amount: Decimal = Decimal("1000.000000000000"),
    invested_currency: str = "USD",
) -> Holding:
    return Holding(
        id=UUID(f"42000000-0000-0000-0000-{position + 1:012d}"),
        portfolio_id=PORTFOLIO_ID,
        symbol=symbol,
        weight=None,
        invested_amount=invested_amount,
        invested_currency=invested_currency,
        shares=shares,
        purchase_date=date(2026, 1, 10),
        position=position,
    )


def _legacy_holding(symbol: str = "AAPL", *, position: int = 0) -> Holding:
    return Holding(
        id=UUID(f"43000000-0000-0000-0000-{position + 1:012d}"),
        portfolio_id=PORTFOLIO_ID,
        symbol=symbol,
        weight=Decimal("1.000000000000000000"),
        invested_amount=None,
        invested_currency=None,
        shares=None,
        purchase_date=None,
        position=position,
    )


def _observation(
    symbol: str,
    price: Decimal,
    *,
    observation_date: date = REQUESTED_DATE,
) -> MarketData:
    return MarketData(
        symbol=symbol,
        date=observation_date,
        adjusted_close=price,
        volume=None,
        source="yfinance",
    )


def _service_with_market_data() -> tuple[
    PortfolioValuationService,
    MagicMock,
    MagicMock,
    MagicMock,
]:
    session = MagicMock(spec=Session)
    market_data = MagicMock(spec=MarketDataService)
    with patch.object(
        valuation_module,
        "MarketDataService",
        return_value=market_data,
    ) as market_data_type:
        service = PortfolioValuationService(session)
    return service, session, market_data, market_data_type


def test_one_holding_usd_valuation_uses_exact_decimal_math() -> None:
    service, _, market_data, _ = _service_with_market_data()
    holding = _holding(shares=Decimal("2.500000000000"))
    market_data.get_latest_usd_asset_observations.return_value = [
        _observation("AAPL", Decimal("10.250000000000"))
    ]

    result = service.value([holding], requested_date=REQUESTED_DATE)

    assert result.display_currency is PortfolioDisplayCurrency.USD
    assert result.requested_date == REQUESTED_DATE
    assert result.total_current_value_usd == Decimal("25.625000000000000000000000")
    assert result.total_current_value == result.total_current_value_usd
    assert result.fx_context is None
    assert result.oldest_price_as_of == REQUESTED_DATE
    assert result.newest_price_as_of == REQUESTED_DATE
    assert len(result.holdings) == 1
    valued = result.holdings[0]
    assert valued.holding_id == holding.id
    assert valued.symbol == "AAPL"
    assert valued.invested_amount == Decimal("1000.000000000000")
    assert valued.invested_currency == "USD"
    assert valued.shares == Decimal("2.500000000000")
    assert valued.purchase_date == date(2026, 1, 10)
    assert valued.position == 0
    assert valued.asset_price == Decimal("10.250000000000")
    assert valued.asset_quote_currency == "USD"
    assert valued.price_as_of == REQUESTED_DATE
    assert valued.current_value_usd == Decimal("25.625000000000000000000000")
    assert valued.current_value == valued.current_value_usd
    assert valued.current_allocation == Decimal(1)
    assert type(valued.current_value_usd) is Decimal
    assert type(valued.current_allocation) is Decimal


def test_multiple_holdings_preserve_order_total_dates_and_allocations() -> None:
    service, _, market_data, _ = _service_with_market_data()
    holdings = [
        _holding("MSFT", position=0, shares=Decimal("3")),
        _holding("AAPL", position=1, shares=Decimal("2")),
    ]
    market_data.get_latest_usd_asset_observations.return_value = [
        _observation(
            "MSFT",
            Decimal("20"),
            observation_date=date(2026, 9, 10),
        ),
        _observation("AAPL", Decimal("10")),
    ]

    result = service.value(holdings, requested_date=REQUESTED_DATE)

    assert [holding.symbol for holding in result.holdings] == ["MSFT", "AAPL"]
    assert [holding.current_value_usd for holding in result.holdings] == [
        Decimal("60"),
        Decimal("20"),
    ]
    assert result.total_current_value_usd == Decimal("80")
    assert [holding.current_allocation for holding in result.holdings] == [
        Decimal("0.75"),
        Decimal("0.25"),
    ]
    assert sum(
        holding.current_allocation for holding in result.holdings
    ) == Decimal(1)
    assert result.oldest_price_as_of == date(2026, 9, 10)
    assert result.newest_price_as_of == date(2026, 9, 11)
    market_data.get_latest_usd_asset_observations.assert_called_once_with(
        ["MSFT", "AAPL"],
        REQUESTED_DATE,
    )


@pytest.mark.parametrize(
    ("symbol", "shares", "price", "expected"),
    [
        (
            "AAPL",
            Decimal("0.125000000000"),
            Decimal("123.456789012000"),
            Decimal("15.432098626500000000000000"),
        ),
        (
            "BTC-USD",
            Decimal("0.000000000001"),
            Decimal("99999.999999999999"),
            Decimal("0.000000099999999999999999"),
        ),
    ],
)
def test_fractional_share_quantities_are_not_converted_to_float(
    symbol: str,
    shares: Decimal,
    price: Decimal,
    expected: Decimal,
) -> None:
    service, _, market_data, _ = _service_with_market_data()
    market_data.get_latest_usd_asset_observations.return_value = [
        _observation(symbol, price)
    ]

    result = service.value(
        [_holding(symbol, shares=shares)],
        requested_date=REQUESTED_DATE,
    )

    assert result.holdings[0].current_value_usd == expected
    assert type(result.holdings[0].current_value_usd) is Decimal


def test_invested_amount_and_currency_do_not_drive_current_value() -> None:
    service, _, market_data, _ = _service_with_market_data()
    holdings = [
        _holding(
            "AAPL",
            position=0,
            shares=Decimal("2"),
            invested_amount=Decimal("10"),
            invested_currency="USD",
        ),
        _holding(
            "MSFT",
            position=1,
            shares=Decimal("2"),
            invested_amount=Decimal("999999"),
            invested_currency="THB",
        ),
    ]
    market_data.get_latest_usd_asset_observations.return_value = [
        _observation("AAPL", Decimal("25")),
        _observation("MSFT", Decimal("25")),
    ]

    result = service.value(holdings, requested_date=REQUESTED_DATE)

    assert [holding.current_value_usd for holding in result.holdings] == [
        Decimal("50"),
        Decimal("50"),
    ]
    assert [holding.current_allocation for holding in result.holdings] == [
        Decimal("0.5"),
        Decimal("0.5"),
    ]
    assert result.holdings[0].invested_amount == Decimal("10")
    assert result.holdings[1].invested_currency == "THB"
    market_data.get_latest_usd_thb_fx_observation.assert_not_called()


def test_no_premature_rounding_changes_tiny_values_or_allocations() -> None:
    service, _, market_data, _ = _service_with_market_data()
    holdings = [
        _holding("AAPL", position=0, shares=Decimal("0.000000000001")),
        _holding("MSFT", position=1, shares=Decimal("0.000000000002")),
    ]
    price = Decimal("123.456789012000")
    market_data.get_latest_usd_asset_observations.return_value = [
        _observation("AAPL", price),
        _observation("MSFT", price),
    ]

    result = service.value(holdings, requested_date=REQUESTED_DATE)

    assert [holding.current_value_usd for holding in result.holdings] == [
        Decimal("0.000000000123456789012000"),
        Decimal("0.000000000246913578024000"),
    ]
    assert result.total_current_value_usd == Decimal(
        "0.000000000370370367036000"
    )
    with localcontext() as context:
        context.prec = 80
        one_third = Decimal(1) / Decimal(3)
        two_thirds = Decimal(2) / Decimal(3)
    assert result.holdings[0].current_allocation == one_third
    assert result.holdings[1].current_allocation == two_thirds


def test_service_math_isolated_from_low_global_decimal_precision() -> None:
    service, _, market_data, _ = _service_with_market_data()
    market_data.get_latest_usd_asset_observations.return_value = [
        _observation("AAPL", Decimal("123.456789012000"))
    ]

    original_precision = getcontext().prec
    try:
        getcontext().prec = 6
        result = service.value(
            [_holding(shares=Decimal("0.123456789012"))],
            requested_date=REQUESTED_DATE,
        )
    finally:
        getcontext().prec = original_precision

    with localcontext() as context:
        context.prec = 80
        expected = Decimal("0.123456789012") * Decimal("123.456789012000")
    assert result.total_current_value_usd == expected


def test_equal_three_way_allocations_are_not_patched_on_final_holding() -> None:
    service, _, market_data, _ = _service_with_market_data()
    holdings = [
        _holding("AAPL", position=0, shares=Decimal(1)),
        _holding("MSFT", position=1, shares=Decimal(1)),
        _holding("NVDA", position=2, shares=Decimal(1)),
    ]
    market_data.get_latest_usd_asset_observations.return_value = [
        _observation(symbol, Decimal(1))
        for symbol in ("AAPL", "MSFT", "NVDA")
    ]

    result = service.value(holdings, requested_date=REQUESTED_DATE)

    allocations = [holding.current_allocation for holding in result.holdings]
    assert allocations[0] == allocations[1] == allocations[2]


def test_legacy_holdings_are_rejected_before_market_data_lookup() -> None:
    service, _, market_data, _ = _service_with_market_data()

    with pytest.raises(InvalidHoldingModeError, match="legacy"):
        service.value([_legacy_holding()], requested_date=REQUESTED_DATE)

    market_data.get_latest_usd_asset_observations.assert_not_called()


def test_mixed_legacy_and_real_holdings_are_rejected() -> None:
    service, _, market_data, _ = _service_with_market_data()

    with pytest.raises(InvalidHoldingModeError, match="mixed"):
        service.value(
            [_holding(), _legacy_holding("MSFT", position=1)],
            requested_date=REQUESTED_DATE,
        )

    market_data.get_latest_usd_asset_observations.assert_not_called()


@pytest.mark.parametrize(
    "missing_field",
    ["invested_amount", "invested_currency", "shares", "purchase_date"],
)
def test_incomplete_real_holding_is_rejected(missing_field: str) -> None:
    service, _, market_data, _ = _service_with_market_data()
    holding = _holding()
    setattr(holding, missing_field, None)

    with pytest.raises(InvalidHoldingModeError, match=missing_field):
        service.value([holding], requested_date=REQUESTED_DATE)

    market_data.get_latest_usd_asset_observations.assert_not_called()


@pytest.mark.parametrize(
    "shares",
    [Decimal("0"), Decimal("-1"), Decimal("NaN"), Decimal("Infinity")],
)
def test_non_positive_or_non_finite_shares_are_rejected(
    shares: Decimal,
) -> None:
    service, _, market_data, _ = _service_with_market_data()

    with pytest.raises(InvalidHoldingModeError, match="shares"):
        service.value(
            [_holding(shares=shares)],
            requested_date=REQUESTED_DATE,
        )

    market_data.get_latest_usd_asset_observations.assert_not_called()


@pytest.mark.parametrize("symbol", ["THB=X", "UNKNOWN"])
def test_internal_or_unsupported_holding_symbol_is_rejected(symbol: str) -> None:
    service, _, market_data, _ = _service_with_market_data()

    with pytest.raises(UnsupportedHoldingInstrumentError):
        service.value(
            [_holding(symbol)],
            requested_date=REQUESTED_DATE,
        )

    market_data.get_latest_usd_asset_observations.assert_not_called()


def test_non_usd_asset_quote_currency_is_rejected() -> None:
    service, _, market_data, _ = _service_with_market_data()
    unsupported = InstrumentMetadata(
        provider_symbol="AAPL",
        instrument_type=InstrumentType.ASSET,
        quote_currency="EUR",
    )

    with (
        patch.object(
            valuation_module,
            "get_instrument_metadata",
            return_value=unsupported,
        ),
        pytest.raises(UnsupportedHoldingInstrumentError, match="USD-quoted"),
    ):
        service.value([_holding()], requested_date=REQUESTED_DATE)

    market_data.get_latest_usd_asset_observations.assert_not_called()


def test_empty_collection_rejects_invalid_zero_total() -> None:
    service, _, market_data, _ = _service_with_market_data()

    with pytest.raises(InvalidPortfolioValueError, match="at least one"):
        service.value([], requested_date=REQUESTED_DATE)

    market_data.get_latest_usd_asset_observations.assert_not_called()


@pytest.mark.parametrize("reason", ["unavailable", "stale"])
def test_missing_or_stale_asset_data_propagates_unavailable_error(
    reason: str,
) -> None:
    service, _, market_data, _ = _service_with_market_data()
    failure = MarketDataUnavailableError(
        f"latest market data is {reason} for AAPL"
    )
    market_data.get_latest_usd_asset_observations.side_effect = failure

    with pytest.raises(MarketDataUnavailableError) as raised:
        service.value([_holding()], requested_date=REQUESTED_DATE)

    assert raised.value is failure


def test_defensive_validation_rejects_stale_asset_observation() -> None:
    service, _, market_data, _ = _service_with_market_data()
    market_data.get_latest_usd_asset_observations.return_value = [
        _observation(
            "AAPL",
            Decimal("10"),
            observation_date=date(2026, 9, 6),
        )
    ]

    with pytest.raises(MarketDataUnavailableError, match="stale"):
        service.value([_holding()], requested_date=REQUESTED_DATE)


def test_missing_asset_result_does_not_silently_drop_holding() -> None:
    service, _, market_data, _ = _service_with_market_data()
    market_data.get_latest_usd_asset_observations.return_value = [
        _observation("AAPL", Decimal("10"))
    ]

    with pytest.raises(MarketDataUnavailableError, match="MSFT"):
        service.value(
            [_holding("AAPL"), _holding("MSFT", position=1)],
            requested_date=REQUESTED_DATE,
        )


def test_thb_display_uses_one_fx_rate_for_all_values_and_total() -> None:
    service, _, market_data, _ = _service_with_market_data()
    holdings = [
        _holding("AAPL", position=0, shares=Decimal("2")),
        _holding("MSFT", position=1, shares=Decimal("3")),
    ]
    market_data.get_latest_usd_asset_observations.return_value = [
        _observation("AAPL", Decimal("10")),
        _observation("MSFT", Decimal("20")),
    ]
    market_data.get_latest_usd_thb_fx_observation.return_value = _observation(
        "THB=X",
        Decimal("32.96"),
        observation_date=date(2026, 9, 10),
    )

    result = service.value(
        holdings,
        requested_date=REQUESTED_DATE,
        display_currency="thb",
    )

    assert result.display_currency is PortfolioDisplayCurrency.THB
    assert result.total_current_value_usd == Decimal("80")
    assert result.total_current_value == Decimal("2636.80")
    assert [holding.current_value for holding in result.holdings] == [
        Decimal("659.20"),
        Decimal("1977.60"),
    ]
    assert result.fx_context is not None
    assert result.fx_context.pair == "USD/THB"
    assert result.fx_context.provider_symbol == "THB=X"
    assert result.fx_context.rate == Decimal("32.96")
    assert result.fx_context.as_of == date(2026, 9, 10)
    market_data.get_latest_usd_thb_fx_observation.assert_called_once_with(
        REQUESTED_DATE
    )


def test_allocations_are_identical_for_usd_and_thb_display() -> None:
    service, _, market_data, _ = _service_with_market_data()
    holdings = [_holding("AAPL"), _holding("MSFT", position=1)]
    market_data.get_latest_usd_asset_observations.return_value = [
        _observation("AAPL", Decimal("10")),
        _observation("MSFT", Decimal("30")),
    ]
    market_data.get_latest_usd_thb_fx_observation.return_value = _observation(
        "THB=X",
        Decimal("32.96"),
    )

    usd = service.value(holdings, requested_date=REQUESTED_DATE)
    thb = service.value(
        holdings,
        requested_date=REQUESTED_DATE,
        display_currency="THB",
    )

    assert [holding.current_allocation for holding in usd.holdings] == [
        holding.current_allocation for holding in thb.holdings
    ]


def test_usd_succeeds_without_requesting_unavailable_fx() -> None:
    service, _, market_data, _ = _service_with_market_data()
    market_data.get_latest_usd_asset_observations.return_value = [
        _observation("AAPL", Decimal("10"))
    ]
    market_data.get_latest_usd_thb_fx_observation.side_effect = (
        MarketDataUnavailableError("FX unavailable")
    )

    result = service.value([_holding()], requested_date=REQUESTED_DATE)

    assert result.total_current_value_usd == Decimal("20.000000000000")
    market_data.get_latest_usd_thb_fx_observation.assert_not_called()


@pytest.mark.parametrize(
    "fx_behavior",
    [
        MarketDataUnavailableError("FX missing"),
        _observation(
            "THB=X",
            Decimal("32.96"),
            observation_date=date(2026, 9, 6),
        ),
    ],
)
def test_missing_or_stale_fx_fails_thb_only(fx_behavior: object) -> None:
    service, _, market_data, _ = _service_with_market_data()
    market_data.get_latest_usd_asset_observations.return_value = [
        _observation("AAPL", Decimal("10"))
    ]
    if isinstance(fx_behavior, Exception):
        market_data.get_latest_usd_thb_fx_observation.side_effect = fx_behavior
    else:
        market_data.get_latest_usd_thb_fx_observation.return_value = fx_behavior

    usd_result = service.value([_holding()], requested_date=REQUESTED_DATE)
    with pytest.raises(MarketDataUnavailableError):
        service.value(
            [_holding()],
            requested_date=REQUESTED_DATE,
            display_currency="THB",
        )

    assert usd_result.display_currency is PortfolioDisplayCurrency.USD


def test_input_collection_objects_and_session_remain_caller_owned() -> None:
    service, session, market_data, market_data_type = _service_with_market_data()
    holdings = [_holding("AAPL"), _holding("MSFT", position=1)]
    original_collection = list(holdings)
    original_fields = [
        (
            holding.id,
            holding.symbol,
            holding.invested_amount,
            holding.invested_currency,
            holding.shares,
            holding.purchase_date,
            holding.weight,
            holding.position,
        )
        for holding in holdings
    ]
    market_data.get_latest_usd_asset_observations.return_value = [
        _observation("AAPL", Decimal("10")),
        _observation("MSFT", Decimal("20")),
    ]

    service.value(holdings, requested_date=REQUESTED_DATE)

    assert holdings == original_collection
    assert all(
        actual is original
        for actual, original in zip(holdings, original_collection, strict=True)
    )
    assert [
        (
            holding.id,
            holding.symbol,
            holding.invested_amount,
            holding.invested_currency,
            holding.shares,
            holding.purchase_date,
            holding.weight,
            holding.position,
        )
        for holding in holdings
    ] == original_fields
    market_data_type.assert_called_once_with(session)
    session.commit.assert_not_called()
    session.rollback.assert_not_called()
    session.close.assert_not_called()


def test_result_contracts_are_immutable() -> None:
    service, _, market_data, _ = _service_with_market_data()
    market_data.get_latest_usd_asset_observations.return_value = [
        _observation("AAPL", Decimal("10"))
    ]
    result = service.value([_holding()], requested_date=REQUESTED_DATE)

    with pytest.raises(FrozenInstanceError):
        result.total_current_value = Decimal("0")
    with pytest.raises(FrozenInstanceError):
        result.holdings[0].current_allocation = Decimal("0")


def test_unsupported_display_currency_fails_before_market_lookup() -> None:
    service, _, market_data, _ = _service_with_market_data()

    with pytest.raises(UnsupportedDisplayCurrencyError, match="EUR"):
        service.value(
            [_holding()],
            requested_date=REQUESTED_DATE,
            display_currency="EUR",
        )

    market_data.get_latest_usd_asset_observations.assert_not_called()
