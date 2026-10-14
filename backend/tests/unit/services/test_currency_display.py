"""Deterministic currency amounts and immutable simulation replay."""

from copy import deepcopy
from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal, localcontext
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from pydantic import ValidationError

from backend.app.database.models import Simulation
from backend.app.schemas.currency_display import CurrencyDisplayContext, CurrencyDisplayHolding
from backend.app.schemas.portfolio import PortfolioValuationFxResponse
from backend.app.services.currency_display import build_currency_display, optional_display_fx
from backend.app.services.market_data_service import MarketDataUnavailableError
from backend.tests.unit.services.test_simulation_history_mapper import _response_for_type
from backend.tests.unit.services.test_simulation_history_service import (
    _CREATED_AT, _SIMULATION_ID, _metadata_for_type, _portfolio, _service_with_dependencies,
)
from backend.tests.unit.services.test_simulation_history_v2 import _real_baseline
from backend.tests.unit.services.test_simulation_history_v3 import _planned_baseline


DAY = date(2026, 10, 14)
FX = PortfolioValuationFxResponse(pair="USD/THB", provider_symbol="THB=X", rate=Decimal("34.125"), as_of=DAY)


@pytest.mark.parametrize("currency", ["USD", "THB"])
@pytest.mark.parametrize("change", ["-123.4567890123456789", "0", "100.125", "-2500"])
def test_exact_bidirectional_amounts_signed_returns_and_no_input_mutation(currency, change):
    amount, change = Decimal("1000.1234567890123456789"), Decimal(change)
    with localcontext() as context:
        context.prec = 80
        ending = amount + change
        expected = [value * FX.rate if currency == "USD" else value / FX.rate for value in (amount, change, ending)]
    holding = CurrencyDisplayHolding(symbol="AAPL", baseline_amount=amount,
        expected_change_amount=change, estimated_ending_value=ending)
    before = holding.model_dump()
    result = build_currency_display(baseline_kind="planned", source_currency=currency, requested_date=DAY,
        baseline_amount=amount, expected_change_amount=change, estimated_ending_value=ending, holdings=[holding], fx=FX)
    source, alternate = result.views
    assert [source.baseline_amount, source.expected_change_amount, source.estimated_ending_value] == [amount, change, ending]
    assert [alternate.baseline_amount, alternate.expected_change_amount, alternate.estimated_ending_value] == expected
    assert alternate.holdings[0].model_dump(exclude={"symbol"}) == alternate.model_dump(exclude={"currency", "holdings"})
    assert holding.model_dump() == before
    CurrencyDisplayContext.model_validate_json(result.model_dump_json())


@pytest.mark.parametrize("offset", [-1, 5])
def test_future_or_stale_fx_cannot_convert_or_block_default_amounts(offset):
    market = Mock()
    market.get_latest_usd_thb_fx_observation.return_value = SimpleNamespace(
        symbol="THB=X", adjusted_close=FX.rate, date=DAY - timedelta(days=offset))
    assert optional_display_fx(market, DAY) is None


def test_missing_fx_keeps_source_currency_and_missing_data_is_optional():
    market = Mock()
    market.get_latest_usd_thb_fx_observation.side_effect = MarketDataUnavailableError("missing")
    assert optional_display_fx(market, DAY) is None
    display = build_currency_display(baseline_kind="planned", source_currency="THB", requested_date=DAY,
        baseline_amount=Decimal("50"), holdings=[CurrencyDisplayHolding(symbol="AAPL", baseline_amount="50")])
    assert [view.currency for view in display.views] == ["THB"]
    assert display.fx is None


@pytest.mark.parametrize("kind", ["current", "planned-usd", "planned-thb"])
@pytest.mark.parametrize("mode", ["historical-scenario", "allocation", "combined"])
def test_simulation_saves_and_replays_the_same_fx_without_market_reads(kind, mode):
    baseline = _real_baseline() if kind == "current" else _planned_baseline()
    if kind == "planned-thb":
        baseline = replace(baseline, planned_allocation=replace(baseline.planned_allocation, plan_currency="THB"))
    service, session, portfolios, repository = _service_with_dependencies()
    portfolio = _portfolio()
    portfolios.get.return_value = portfolio
    market = Mock()
    market.get_latest_usd_thb_fx_observation.side_effect = lambda requested_date: SimpleNamespace(
        symbol="THB=X", adjusted_close=FX.rate, date=requested_date)
    repository.create.side_effect = lambda **kwargs: Simulation(id=_SIMULATION_ID, created_at=_CREATED_AT, **kwargs)
    response = _response_for_type(mode)
    before = response.model_dump()
    scenario_id, start, end = _metadata_for_type(mode)
    with patch("backend.app.services.simulation_history_service.MarketDataService", return_value=market):
        detail = service.save(user_id=portfolio.user_id, portfolio_id=portfolio.id, simulation_type=mode,
            scenario_id=scenario_id, requested_start_date=start, requested_end_date=end, response=response, baseline=baseline)
    assert response.model_dump() == before
    assert detail.result.model_dump(exclude={"currency_display"}) == response.model_dump(exclude={"currency_display"})
    assert len(detail.result.currency_display.views) == 2
    assert detail.result.currency_display.fx.rate == FX.rate
    captured = deepcopy(repository.create.call_args.kwargs)
    repository.get_for_portfolio.return_value = Simulation(id=_SIMULATION_ID, created_at=_CREATED_AT, **captured)
    market.get_latest_usd_thb_fx_observation.side_effect = AssertionError("history must not query FX")
    with patch("backend.app.services.simulation_history_service.MarketDataService", side_effect=AssertionError("no market service during replay")):
        reopened = service.get(user_id=portfolio.user_id, portfolio_id=portfolio.id, simulation_id=_SIMULATION_ID)
    assert reopened == detail
    assert repository.get_for_portfolio.return_value.result_snapshot == captured["result_snapshot"]
    session.commit.assert_not_called()
    corrupted = deepcopy(captured)
    saved_display = detail.result.currency_display
    source = saved_display.views[0]
    corrupted["result_snapshot"]["result"]["currency_display"] = build_currency_display(
        baseline_kind=saved_display.baseline_kind, source_currency=saved_display.source_currency,
        requested_date=saved_display.requested_date, fx=saved_display.fx,
        baseline_amount=source.baseline_amount * 2,
        holdings=[CurrencyDisplayHolding(symbol=h.symbol, baseline_amount=h.baseline_amount * 2) for h in source.holdings],
    ).model_dump(mode="json")
    repository.get_for_portfolio.return_value = Simulation(id=_SIMULATION_ID, created_at=_CREATED_AT, **corrupted)
    with pytest.raises(ValueError, match="saved baseline"):
        service.get(user_id=portfolio.user_id, portfolio_id=portfolio.id, simulation_id=_SIMULATION_ID)


def test_currency_contract_rejects_missing_fx_reordered_holdings_and_fabricated_conversion():
    display = build_currency_display(baseline_kind="current", source_currency="USD", requested_date=DAY,
        baseline_amount=Decimal("10"), holdings=[CurrencyDisplayHolding(symbol="AAPL", baseline_amount="10")], fx=FX)
    for mutate in [lambda d: d.update(fx=None),
                   lambda d: d["views"][1]["holdings"][0].update(symbol="MSFT"),
                   lambda d: d["views"][1].update(baseline_amount="999")]:
        payload = display.model_dump(mode="json")
        mutate(payload)
        with pytest.raises(ValidationError):
            CurrencyDisplayContext.model_validate(payload)
