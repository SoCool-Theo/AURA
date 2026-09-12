from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pandas as pd

import backend.app.services.allocation_simulation_service as allocation_module
import backend.app.services.historical_scenario_service as historical_module
from backend.app.scenarios.definitions import get_historical_scenario
from backend.app.services.portfolio_baseline_resolver import (
    PortfolioBaselineKind,
    PortfolioBaselineResolution,
    ResolvedPortfolioWeight,
)
from backend.app.services.portfolio_valuation_service import (
    PortfolioDisplayCurrency,
    PortfolioValuationResult,
)
from backend.app.services.simulation_execution import SimulationExecutionResult
from backend.tests.unit.services.test_allocation_simulation_service import (
    _comparison_result,
    _map_response as _allocation_map_response,
    _portfolio as _allocation_portfolio,
    _request as _allocation_request,
    _service_with_dependencies as _allocation_service,
)
from backend.tests.unit.services.test_combined_simulation_service import (
    _allocation_response,
    _request as _combined_request,
    _service_with_dependency as _combined_service,
)
from backend.tests.unit.services.test_historical_scenario_service import (
    _map_response as _historical_map_response,
    _portfolio as _historical_portfolio,
    _request as _historical_request,
    _service_with_dependencies as _historical_service,
    _simulation_result,
)


VALUATION_DATE = date(2026, 9, 12)


def _real_baseline(
    weights: tuple[tuple[str, str], ...],
) -> PortfolioBaselineResolution:
    return PortfolioBaselineResolution(
        baseline_kind=PortfolioBaselineKind.REAL,
        resolved_weights=tuple(
            ResolvedPortfolioWeight(symbol, Decimal(weight))
            for symbol, weight in weights
        ),
        valuation=MagicMock(spec=PortfolioValuationResult),
        valuation_as_of=VALUATION_DATE,
    )


def _mark_real(portfolio: object) -> None:
    for position, holding in enumerate(portfolio.holdings):
        holding.weight = None
        holding.invested_amount = Decimal("1")
        holding.invested_currency = "THB" if position == 0 else "USD"
        holding.shares = Decimal(position + 1)
        holding.purchase_date = date(2026, 1, position + 1)


def test_historical_real_run_uses_one_current_baseline_for_old_period() -> None:
    service, session, portfolio_service, market_data_service, _, _ = (
        _historical_service()
    )
    portfolio = _historical_portfolio()
    _mark_real(portfolio)
    portfolio_service.get.return_value = portfolio
    baseline = _real_baseline(
        (("BETA", "0.25"), ("ZERO", "0"), ("ALPHA", "0.75"))
    )
    resolver = MagicMock()
    resolver.resolve.return_value = baseline
    service._baseline_resolver = resolver
    records = [MagicMock(name="record")]
    market_data_service.get_range.return_value = records
    prices = pd.DataFrame({"sentinel": [1.0]})
    expected = _historical_map_response()
    scenario = get_historical_scenario("covid-19-shock-2020")
    assert scenario is not None

    with (
        patch.object(
            historical_module,
            "get_historical_scenario",
            return_value=scenario,
        ),
        patch.object(
            historical_module,
            "_build_price_frame",
            return_value=prices,
        ),
        patch.object(
            historical_module,
            "simulate_historical_scenario",
            return_value=_simulation_result(),
        ) as simulator,
        patch.object(
            historical_module,
            "_map_historical_scenario_response",
            return_value=expected,
        ),
    ):
        execution = service.run_with_context(
            user_id=portfolio.user_id,
            portfolio_id=portfolio.id,
            request=_historical_request(),
            valuation_date=VALUATION_DATE,
        )

    assert execution is not None
    assert execution.response is expected
    assert execution.baseline is baseline
    resolver.resolve.assert_called_once_with(
        portfolio=portfolio,
        valuation_date=VALUATION_DATE,
        display_currency=PortfolioDisplayCurrency.USD,
    )
    passed_weights = simulator.call_args.args[1]
    assert list(passed_weights.items()) == [
        ("BETA", 0.25),
        ("ZERO", 0.0),
        ("ALPHA", 0.75),
    ]
    assert portfolio.holdings[0].purchase_date > date(2020, 4, 30)
    assert baseline.valuation_as_of > date(2020, 4, 30)
    session.commit.assert_not_called()


def test_allocation_real_run_changes_only_original_weights() -> None:
    service, session, portfolio_service, market_data_service, _, _ = (
        _allocation_service()
    )
    portfolio = _allocation_portfolio()
    _mark_real(portfolio)
    portfolio_service.get.return_value = portfolio
    baseline = _real_baseline(
        (("BETA", "0.25"), ("ZERO", "0"), ("ALPHA", "0.75"))
    )
    resolver = MagicMock()
    resolver.resolve.return_value = baseline
    service._baseline_resolver = resolver
    request = _allocation_request()
    records = [MagicMock(name="record")]
    market_data_service.get_range.return_value = records
    prices = pd.DataFrame({"sentinel": [1.0]})
    expected = _allocation_map_response()

    with (
        patch.object(
            allocation_module,
            "_build_price_frame",
            return_value=prices,
        ) as build_frame,
        patch.object(
            allocation_module,
            "simulate_allocation_change",
            return_value=_comparison_result(),
        ) as simulator,
        patch.object(
            allocation_module,
            "_map_allocation_simulation_response",
            return_value=expected,
        ),
    ):
        execution = service.run_with_context(
            user_id=portfolio.user_id,
            portfolio_id=portfolio.id,
            request=request,
            valuation_date=VALUATION_DATE,
        )

    assert execution is not None
    assert execution.response is expected
    assert execution.baseline is baseline
    resolver.resolve.assert_called_once_with(
        portfolio=portfolio,
        valuation_date=VALUATION_DATE,
        display_currency=PortfolioDisplayCurrency.USD,
    )
    symbols = ["BETA", "ZERO", "ALPHA"]
    market_data_service.get_range.assert_called_once_with(
        symbols,
        request.start_date,
        request.end_date,
    )
    build_frame.assert_called_once_with(records, symbols)
    assert list(simulator.call_args.args[1].items()) == [
        ("BETA", 0.25),
        ("ZERO", 0.0),
        ("ALPHA", 0.75),
    ]
    assert list(simulator.call_args.args[2].items()) == [
        ("BETA", 0.5),
        ("ZERO", 0.0),
        ("ALPHA", 0.5),
    ]
    session.commit.assert_not_called()


def test_combined_real_run_delegates_one_baseline_with_same_date() -> None:
    service, session, allocation_service, _ = _combined_service()
    baseline = _real_baseline((("AAPL", "0.6"), ("MSFT", "0.4")))
    allocation_response = _allocation_response()
    allocation_service.run_with_context.return_value = SimulationExecutionResult(
        response=allocation_response,
        baseline=baseline,
    )

    execution = service.run_with_context(
        user_id=allocation_response.portfolio_id,
        portfolio_id=allocation_response.portfolio_id,
        request=_combined_request(),
        valuation_date=VALUATION_DATE,
    )

    assert execution is not None
    assert execution.baseline is baseline
    assert execution.response.scenario.id == "covid-19-shock-2020"
    allocation_service.run_with_context.assert_called_once()
    call = allocation_service.run_with_context.call_args.kwargs
    assert call["valuation_date"] == VALUATION_DATE
    assert call["request"].start_date == date(2020, 2, 1)
    assert call["request"].end_date == date(2020, 4, 30)
    assert call["request"].modified_allocation == (
        _combined_request().modified_allocation
    )
    allocation_service.run.assert_not_called()
    session.commit.assert_not_called()
