from copy import deepcopy
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
from sqlalchemy.orm import Session

import backend.app.services.portfolio_planned_preview_service as preview_module
from backend.app.database.models import (
    Holding,
    MarketData,
    Portfolio,
    PortfolioType,
)
from backend.app.services.market_data_service import (
    MarketDataService,
    MarketDataUnavailableError,
)
from backend.app.services.portfolio_planned_allocation_service import (
    InvalidPlannedPortfolioError,
)
from backend.app.services.portfolio_planned_preview_service import (
    PlannedEstimateStatus,
    PortfolioPlannedPreviewService,
)


PORTFOLIO_ID = UUID("81000000-0000-0000-0000-000000000001")
REQUESTED_DATE = date(2026, 9, 12)


def _portfolio(currency: str = "USD") -> Portfolio:
    portfolio = Portfolio(
        id=PORTFOLIO_ID,
        user_id=UUID("81000000-0000-0000-0000-000000000002"),
        name="Plan",
        portfolio_type=PortfolioType.PLANNED.value,
        plan_currency=currency,
    )
    portfolio.holdings.extend(
        [
            Holding(
                id=UUID("82000000-0000-0000-0000-000000000001"),
                symbol="AAPL",
                proposed_amount=Decimal("4000.000000000000"),
                position=0,
            ),
            Holding(
                id=UUID("82000000-0000-0000-0000-000000000002"),
                symbol="BND",
                proposed_amount=Decimal("1000.000000000000"),
                position=1,
            ),
        ]
    )
    return portfolio


def _observation(symbol: str, price: str) -> MarketData:
    return MarketData(
        symbol=symbol,
        date=date(2026, 9, 11),
        adjusted_close=Decimal(price),
        volume=None,
        source="test",
    )


def _service() -> tuple[PortfolioPlannedPreviewService, MagicMock, MagicMock]:
    session = MagicMock(spec=Session)
    market_data = MagicMock(spec=MarketDataService)
    with patch.object(
        preview_module,
        "MarketDataService",
        return_value=market_data,
    ):
        service = PortfolioPlannedPreviewService(session)
    return service, session, market_data


def test_usd_preview_calculates_estimates_without_fx_or_mutation() -> None:
    service, session, market_data = _service()
    portfolio = _portfolio()
    snapshot = deepcopy(
        [
            (holding.symbol, holding.proposed_amount, holding.position)
            for holding in portfolio.holdings
        ]
    )
    observations = {
        "AAPL": _observation("AAPL", "200"),
        "BND": _observation("BND", "100"),
    }
    market_data.get_latest_usd_asset_observations.side_effect = (
        lambda symbols, requested_date: [observations[symbols[0]]]
    )

    result = service.preview(
        portfolio=portfolio,
        requested_date=REQUESTED_DATE,
    )

    assert result.plan_currency == "USD"
    assert result.total_proposed_amount == Decimal("5000.000000000000")
    assert result.fx_context is None
    assert [holding.target_allocation for holding in result.holdings] == [
        Decimal("0.800000000000000000"),
        Decimal("0.200000000000000000"),
    ]
    assert [holding.estimated_shares for holding in result.holdings] == [
        Decimal("20.000000000000"),
        Decimal("10.000000000000"),
    ]
    assert all(
        holding.estimate_status is PlannedEstimateStatus.AVAILABLE
        for holding in result.holdings
    )
    market_data.get_latest_usd_thb_fx_observation.assert_not_called()
    assert [
        (holding.symbol, holding.proposed_amount, holding.position)
        for holding in portfolio.holdings
    ] == snapshot
    session.commit.assert_not_called()
    session.rollback.assert_not_called()


def test_thb_preview_uses_one_fx_observation_for_all_estimates() -> None:
    service, _, market_data = _service()
    portfolio = _portfolio("THB")
    portfolio.holdings[0].proposed_amount = Decimal("6500")
    portfolio.holdings[1].proposed_amount = Decimal("3250")
    market_data.get_latest_usd_thb_fx_observation.return_value = _observation(
        "THB=X",
        "32.5",
    )
    observations = {
        "AAPL": _observation("AAPL", "200"),
        "BND": _observation("BND", "100"),
    }
    market_data.get_latest_usd_asset_observations.side_effect = (
        lambda symbols, requested_date: [observations[symbols[0]]]
    )

    result = service.preview(
        portfolio=portfolio,
        requested_date=REQUESTED_DATE,
    )

    assert result.fx_context is not None
    assert result.fx_context.rate == Decimal("32.5")
    assert [holding.estimated_shares for holding in result.holdings] == [
        Decimal("1"),
        Decimal("1"),
    ]
    market_data.get_latest_usd_thb_fx_observation.assert_called_once_with(
        REQUESTED_DATE
    )


def test_missing_price_marks_only_affected_estimate_unavailable() -> None:
    service, _, market_data = _service()
    portfolio = _portfolio()

    def observations(
        symbols: list[str],
        requested_date: date,
    ) -> list[MarketData]:
        if symbols == ["BND"]:
            raise MarketDataUnavailableError("stale BND price")
        return [_observation("AAPL", "200")]

    market_data.get_latest_usd_asset_observations.side_effect = observations

    result = service.preview(
        portfolio=portfolio,
        requested_date=REQUESTED_DATE,
    )

    assert result.holdings[0].estimated_shares == Decimal("20")
    assert result.holdings[0].estimate_status is PlannedEstimateStatus.AVAILABLE
    unavailable = result.holdings[1]
    assert unavailable.estimate_status is PlannedEstimateStatus.PRICE_UNAVAILABLE
    assert unavailable.estimated_shares is None
    assert unavailable.asset_price is None
    assert unavailable.price_as_of is None
    assert [holding.target_allocation for holding in result.holdings] == [
        Decimal("0.800000000000000000"),
        Decimal("0.200000000000000000"),
    ]


def test_missing_thb_fx_preserves_prices_but_marks_estimates_unavailable() -> None:
    service, _, market_data = _service()
    portfolio = _portfolio("THB")
    market_data.get_latest_usd_thb_fx_observation.side_effect = (
        MarketDataUnavailableError("stale FX")
    )
    observations = {
        "AAPL": _observation("AAPL", "200"),
        "BND": _observation("BND", "100"),
    }
    market_data.get_latest_usd_asset_observations.side_effect = (
        lambda symbols, requested_date: [observations[symbols[0]]]
    )

    result = service.preview(
        portfolio=portfolio,
        requested_date=REQUESTED_DATE,
    )

    assert result.fx_context is None
    assert all(
        holding.estimate_status is PlannedEstimateStatus.FX_UNAVAILABLE
        for holding in result.holdings
    )
    assert all(holding.estimated_shares is None for holding in result.holdings)
    assert [holding.asset_price for holding in result.holdings] == [
        Decimal("200"),
        Decimal("100"),
    ]


def test_invalid_plan_and_non_date_boundary_fail_without_market_lookup() -> None:
    service, _, market_data = _service()
    current = Portfolio(
        id=PORTFOLIO_ID,
        user_id=UUID("81000000-0000-0000-0000-000000000002"),
        name="Current",
        portfolio_type=PortfolioType.CURRENT.value,
    )

    with pytest.raises(InvalidPlannedPortfolioError):
        service.preview(portfolio=current, requested_date=REQUESTED_DATE)
    with pytest.raises(TypeError, match="requested_date must be a date"):
        service.preview(
            portfolio=_portfolio(),
            requested_date="2026-09-12",  # type: ignore[arg-type]
        )

    market_data.get_latest_usd_asset_observations.assert_not_called()
    market_data.get_latest_usd_thb_fx_observation.assert_not_called()
