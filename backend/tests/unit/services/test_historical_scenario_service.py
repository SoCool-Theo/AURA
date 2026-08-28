from copy import deepcopy
from datetime import date
from decimal import Decimal
import inspect
from unittest.mock import MagicMock, patch
from uuid import UUID

import pandas as pd
import pytest
from sqlalchemy.orm import Session

from backend.app.analytics.drawdown import MaxDrawdownResult
from backend.app.database.models import Holding, MarketData, Portfolio
from backend.app.scenarios.definitions import HISTORICAL_SCENARIOS
from backend.app.scenarios.simulator import (
    HistoricalSimulationResult,
    HistoricalTrajectoryPoint,
)
from backend.app.schemas.simulation import HistoricalScenarioSimulationResponse
import backend.app.services.analysis_service as analysis_service_module
import backend.app.services.historical_scenario_service as service_module
from backend.app.services.historical_scenario_service import (
    EmptyPortfolioError,
    HistoricalScenarioNotFoundError,
    HistoricalScenarioService,
    _map_historical_scenario_response,
)


_PORTFOLIO_ID = UUID("12345678-1234-5678-1234-567812345678")
_USER_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


def _simulation_result() -> HistoricalSimulationResult:
    return HistoricalSimulationResult(
        effective_start_date=pd.Timestamp("2020-02-03"),
        effective_end_date=pd.Timestamp("2020-04-30"),
        price_observation_count=4,
        return_observation_count=3,
        normalized_starting_value=1.0,
        normalized_ending_value=0.95,
        cumulative_return=-0.05,
        annualized_volatility=0.42,
        sharpe_ratio=None,
        maximum_drawdown=MaxDrawdownResult(
            max_drawdown=-0.25,
            peak_date=pd.Timestamp("2020-02-03"),
            trough_date=pd.Timestamp("2020-03-23"),
        ),
        trajectory=(
            HistoricalTrajectoryPoint(pd.Timestamp("2020-02-03"), 1.0),
            HistoricalTrajectoryPoint(pd.Timestamp("2020-03-02"), 0.8),
            HistoricalTrajectoryPoint(pd.Timestamp("2020-03-23"), 0.75),
            HistoricalTrajectoryPoint(pd.Timestamp("2020-04-30"), 0.95),
        ),
    )


def _map_response() -> HistoricalScenarioSimulationResponse:
    return _map_historical_scenario_response(
        portfolio_id=_PORTFOLIO_ID,
        portfolio_name="Balanced Learning Portfolio",
        scenario=HISTORICAL_SCENARIOS[0],
        result=_simulation_result(),
    )


def _request() -> service_module.HistoricalScenarioSimulationRequest:
    return service_module.HistoricalScenarioSimulationRequest(
        scenario_id="covid-19-shock-2020"
    )


def _portfolio(
    *,
    holdings: tuple[tuple[str, str], ...] = (
        ("BETA", "0.4"),
        ("ZERO", "0.0"),
        ("ALPHA", "0.6"),
    ),
) -> Portfolio:
    portfolio = Portfolio(
        id=_PORTFOLIO_ID,
        user_id=_USER_ID,
        name="Balanced Learning Portfolio",
    )
    portfolio.holdings.extend(
        Holding(
            symbol=symbol,
            weight=Decimal(weight),
            position=position,
        )
        for position, (symbol, weight) in enumerate(holdings)
    )
    return portfolio


def _record(
    symbol: str,
    observation_date: str,
    adjusted_close: str,
) -> MarketData:
    return MarketData(
        symbol=symbol,
        date=date.fromisoformat(observation_date),
        adjusted_close=Decimal(adjusted_close),
        volume=None,
        source="test-source",
    )


def _service_with_dependencies() -> tuple[
    HistoricalScenarioService,
    MagicMock,
    MagicMock,
    MagicMock,
    MagicMock,
    MagicMock,
]:
    session = MagicMock(spec=Session)
    portfolio_service = MagicMock(spec=service_module.PortfolioService)
    market_data_service = MagicMock(spec=service_module.MarketDataService)

    with (
        patch.object(
            service_module,
            "PortfolioService",
            return_value=portfolio_service,
        ) as portfolio_service_type,
        patch.object(
            service_module,
            "MarketDataService",
            return_value=market_data_service,
        ) as market_data_service_type,
    ):
        service = HistoricalScenarioService(session)

    return (
        service,
        session,
        portfolio_service,
        market_data_service,
        portfolio_service_type,
        market_data_service_type,
    )


def _assert_session_lifecycle_untouched(session: MagicMock) -> None:
    session.commit.assert_not_called()
    session.rollback.assert_not_called()
    session.close.assert_not_called()
    session.flush.assert_not_called()


def test_mapper_returns_valid_response_with_portfolio_identity() -> None:
    response = _map_response()

    assert isinstance(response, HistoricalScenarioSimulationResponse)
    assert response.portfolio_id == _PORTFOLIO_ID
    assert response.portfolio_name == "Balanced Learning Portfolio"


def test_mapper_preserves_complete_scenario_definition() -> None:
    response = _map_response()

    assert response.scenario.model_dump() == {
        "id": "covid-19-shock-2020",
        "display_name": "COVID-19 Market Shock",
        "description": (
            "A sharp market shock and early recovery period during the "
            "COVID-19 disruption."
        ),
        "requested_start_date": date(2020, 2, 1),
        "requested_end_date": date(2020, 4, 30),
    }


def test_mapper_keeps_requested_and_effective_dates_separate() -> None:
    response = _map_response()

    assert response.scenario.requested_start_date == date(2020, 2, 1)
    assert response.scenario.requested_end_date == date(2020, 4, 30)
    assert response.metadata.effective_start_date == date(2020, 2, 3)
    assert response.metadata.effective_end_date == date(2020, 4, 30)
    assert response.metadata.price_observation_count == 4
    assert response.metadata.return_observation_count == 3


def test_mapper_preserves_metrics_nullable_sharpe_and_signed_drawdown() -> None:
    response = _map_response()

    assert response.metrics.normalized_starting_value == 1.0
    assert response.metrics.normalized_ending_value == 0.95
    assert response.metrics.cumulative_return == -0.05
    assert response.metrics.annualized_volatility == 0.42
    assert response.metrics.sharpe_ratio is None
    assert response.metrics.maximum_drawdown.model_dump() == {
        "max_drawdown": -0.25,
        "peak_date": date(2020, 2, 3),
        "trough_date": date(2020, 3, 23),
    }


def test_mapper_preserves_trajectory_order_and_values() -> None:
    response = _map_response()

    assert [point.model_dump() for point in response.trajectory] == [
        {"date": date(2020, 2, 3), "normalized_value": 1.0},
        {"date": date(2020, 3, 2), "normalized_value": 0.8},
        {"date": date(2020, 3, 23), "normalized_value": 0.75},
        {"date": date(2020, 4, 30), "normalized_value": 0.95},
    ]


def test_mapper_does_not_mutate_caller_inputs() -> None:
    scenario = HISTORICAL_SCENARIOS[0]
    result = _simulation_result()
    scenario_snapshot = deepcopy(scenario)
    result_snapshot = deepcopy(result)
    trajectory_identity = id(result.trajectory)

    _map_historical_scenario_response(
        portfolio_id=_PORTFOLIO_ID,
        portfolio_name="Balanced Learning Portfolio",
        scenario=scenario,
        result=result,
    )

    assert scenario == scenario_snapshot
    assert result == result_snapshot
    assert id(result.trajectory) == trajectory_identity


def test_constructor_reuses_only_the_caller_owned_session() -> None:
    (
        service,
        session,
        _,
        _,
        portfolio_service_type,
        market_data_service_type,
    ) = _service_with_dependencies()

    assert service._session is session
    portfolio_service_type.assert_called_once_with(session)
    market_data_service_type.assert_called_once_with(session)
    _assert_session_lifecycle_untouched(session)


def test_portfolio_lookup_occurs_before_scenario_lookup() -> None:
    service, session, portfolio_service, market_data_service, _, _ = (
        _service_with_dependencies()
    )
    events: list[str] = []
    portfolio = _portfolio()
    portfolio_service.get.side_effect = lambda **_: (
        events.append("portfolio") or portfolio
    )
    market_data_service.get_range.return_value = []

    def lookup(_: str) -> object:
        events.append("scenario")
        return HISTORICAL_SCENARIOS[0]

    with (
        patch.object(
            service_module,
            "get_historical_scenario",
            side_effect=lookup,
        ),
        patch.object(
            service_module,
            "_build_price_frame",
            return_value=pd.DataFrame({"sentinel": [1.0]}),
        ),
        patch.object(
            service_module,
            "simulate_historical_scenario",
            return_value=_simulation_result(),
        ),
        patch.object(
            service_module,
            "_map_historical_scenario_response",
            return_value=_map_response(),
        ),
    ):
        service.run(
            user_id=_USER_ID,
            portfolio_id=_PORTFOLIO_ID,
            request=_request(),
        )

    assert events == ["portfolio", "scenario"]
    _assert_session_lifecycle_untouched(session)


@pytest.mark.parametrize("portfolio_state", ["missing", "wrong-owner"])
def test_missing_and_wrong_owner_portfolio_behavior_remains_indistinguishable(
    portfolio_state: str,
) -> None:
    service, session, portfolio_service, market_data_service, _, _ = (
        _service_with_dependencies()
    )
    portfolio_service.get.return_value = None

    with (
        patch.object(
            service_module,
            "get_historical_scenario",
        ) as scenario_lookup,
        patch.object(
            service_module,
            "simulate_historical_scenario",
        ) as simulator,
    ):
        result = service.run(
            user_id=_USER_ID,
            portfolio_id=_PORTFOLIO_ID,
            request=_request(),
        )

    assert portfolio_state in {"missing", "wrong-owner"}
    assert result is None
    portfolio_service.get.assert_called_once_with(
        user_id=_USER_ID,
        portfolio_id=_PORTFOLIO_ID,
    )
    scenario_lookup.assert_not_called()
    market_data_service.get_range.assert_not_called()
    simulator.assert_not_called()
    _assert_session_lifecycle_untouched(session)


def test_unknown_scenario_raises_stable_service_error() -> None:
    service, session, portfolio_service, market_data_service, _, _ = (
        _service_with_dependencies()
    )
    portfolio_service.get.return_value = _portfolio()
    request = service_module.HistoricalScenarioSimulationRequest(
        scenario_id="unknown-scenario"
    )

    with patch.object(
        service_module,
        "get_historical_scenario",
        return_value=None,
    ) as scenario_lookup:
        with pytest.raises(HistoricalScenarioNotFoundError) as raised:
            service.run(
                user_id=_USER_ID,
                portfolio_id=_PORTFOLIO_ID,
                request=request,
            )

    assert str(raised.value) == "Historical scenario not found"
    scenario_lookup.assert_called_once_with("unknown-scenario")
    market_data_service.get_range.assert_not_called()
    _assert_session_lifecycle_untouched(session)


def test_empty_owned_portfolio_fails_before_scenario_or_market_data() -> None:
    service, session, portfolio_service, market_data_service, _, _ = (
        _service_with_dependencies()
    )
    portfolio_service.get.return_value = _portfolio(holdings=())

    with patch.object(
        service_module,
        "get_historical_scenario",
    ) as scenario_lookup:
        with pytest.raises(EmptyPortfolioError) as raised:
            service.run(
                user_id=_USER_ID,
                portfolio_id=_PORTFOLIO_ID,
                request=_request(),
            )

    assert str(raised.value) == "portfolio must contain at least one holding"
    scenario_lookup.assert_not_called()
    market_data_service.get_range.assert_not_called()
    _assert_session_lifecycle_untouched(session)


def test_orchestration_preserves_holdings_dates_alignment_and_simulator_inputs() -> None:
    service, session, portfolio_service, market_data_service, _, _ = (
        _service_with_dependencies()
    )
    portfolio = _portfolio()
    records = [MagicMock(name="record-one"), MagicMock(name="record-two")]
    prices = pd.DataFrame(
        {
            "BETA": [100.0, 101.0, 102.0],
            "ZERO": [50.0, 50.0, 50.0],
            "ALPHA": [200.0, 202.0, 204.0],
        },
        index=pd.DatetimeIndex(
            ["2020-02-03", "2020-02-04", "2020-02-05"]
        ),
    )
    response = _map_response()
    portfolio_service.get.return_value = portfolio
    market_data_service.get_range.return_value = records

    with (
        patch.object(
            service_module,
            "get_historical_scenario",
            return_value=HISTORICAL_SCENARIOS[0],
        ) as scenario_lookup,
        patch.object(
            service_module,
            "_build_price_frame",
            return_value=prices,
        ) as build_price_frame,
        patch.object(
            service_module,
            "simulate_historical_scenario",
            return_value=_simulation_result(),
        ) as simulator,
        patch.object(
            service_module,
            "_map_historical_scenario_response",
            return_value=response,
        ) as mapper,
    ):
        result = service.run(
            user_id=_USER_ID,
            portfolio_id=_PORTFOLIO_ID,
            request=_request(),
        )

    assert result is response
    portfolio_service.get.assert_called_once_with(
        user_id=_USER_ID,
        portfolio_id=_PORTFOLIO_ID,
    )
    scenario_lookup.assert_called_once_with("covid-19-shock-2020")
    symbols = market_data_service.get_range.call_args.args[0]
    assert symbols == ["BETA", "ZERO", "ALPHA"]
    market_data_service.get_range.assert_called_once_with(
        symbols,
        date(2020, 2, 1),
        date(2020, 4, 30),
    )
    build_price_frame.assert_called_once_with(records, symbols)
    passed_weights = simulator.call_args.args[1]
    simulator.assert_called_once_with(prices, passed_weights)
    assert list(passed_weights.items()) == [
        ("BETA", 0.4),
        ("ZERO", 0.0),
        ("ALPHA", 0.6),
    ]
    mapper.assert_called_once_with(
        portfolio_id=portfolio.id,
        portfolio_name=portfolio.name,
        scenario=HISTORICAL_SCENARIOS[0],
        result=_simulation_result(),
    )
    market_data_service.store.assert_not_called()
    _assert_session_lifecycle_untouched(session)


def test_new_q4_scenario_runs_through_existing_service_path() -> None:
    service, session, portfolio_service, market_data_service, _, _ = (
        _service_with_dependencies()
    )
    portfolio_service.get.return_value = _portfolio(
        holdings=(("ALPHA", "1.0"),)
    )
    market_data_service.get_range.return_value = [
        _record("ALPHA", "2018-10-01", "100.000000000000"),
        _record("ALPHA", "2018-10-02", "80.000000000000"),
        _record("ALPHA", "2018-10-03", "90.000000000000"),
        _record("ALPHA", "2018-12-31", "95.000000000000"),
    ]
    request = service_module.HistoricalScenarioSimulationRequest(
        scenario_id="q4-market-selloff-2018"
    )

    response = service.run(
        user_id=_USER_ID,
        portfolio_id=_PORTFOLIO_ID,
        request=request,
    )

    assert isinstance(response, HistoricalScenarioSimulationResponse)
    assert response.scenario.model_dump() == {
        "id": "q4-market-selloff-2018",
        "display_name": "Q4 2018 Market Selloff",
        "description": (
            "A sharp late-2018 market selloff marked by elevated volatility."
        ),
        "requested_start_date": date(2018, 10, 1),
        "requested_end_date": date(2018, 12, 31),
    }
    assert response.metadata.effective_start_date == date(2018, 10, 1)
    assert response.metadata.effective_end_date == date(2018, 12, 31)
    assert response.metrics.normalized_starting_value == 1.0
    market_data_service.get_range.assert_called_once_with(
        ["ALPHA"],
        date(2018, 10, 1),
        date(2018, 12, 31),
    )
    _assert_session_lifecycle_untouched(session)


def test_service_reuses_analysis_exact_alignment_helper_by_identity() -> None:
    assert (
        service_module._build_price_frame
        is analysis_service_module._build_price_frame
    )


def test_real_alignment_uses_exact_intersection_without_filling() -> None:
    service, session, portfolio_service, market_data_service, _, _ = (
        _service_with_dependencies()
    )
    portfolio = _portfolio(
        holdings=(("BTC-USD", "0.4"), ("AAPL", "0.6"))
    )
    records = [
        _record("AAPL", "2020-02-03", "100.000000000000"),
        _record("AAPL", "2020-02-05", "102.000000000000"),
        _record("BTC-USD", "2020-02-03", "9000.000000000000"),
        _record("BTC-USD", "2020-02-04", "9100.000000000000"),
        _record("BTC-USD", "2020-02-05", "9200.000000000000"),
    ]
    portfolio_service.get.return_value = portfolio
    market_data_service.get_range.return_value = records
    captured_prices: list[pd.DataFrame] = []

    def simulate(
        prices: pd.DataFrame,
        weights: dict[str, float],
    ) -> HistoricalSimulationResult:
        captured_prices.append(prices.copy(deep=True))
        assert list(weights) == ["BTC-USD", "AAPL"]
        return _simulation_result()

    with (
        patch.object(
            service_module,
            "get_historical_scenario",
            return_value=HISTORICAL_SCENARIOS[0],
        ),
        patch.object(
            service_module,
            "simulate_historical_scenario",
            side_effect=simulate,
        ),
    ):
        service.run(
            user_id=_USER_ID,
            portfolio_id=_PORTFOLIO_ID,
            request=_request(),
        )

    prices = captured_prices[0]
    assert list(prices.index) == [
        pd.Timestamp("2020-02-03"),
        pd.Timestamp("2020-02-05"),
    ]
    assert list(prices.columns) == ["BTC-USD", "AAPL"]
    assert prices.to_dict(orient="list") == {
        "BTC-USD": [9000.0, 9200.0],
        "AAPL": [100.0, 102.0],
    }
    assert not prices.isna().any().any()
    _assert_session_lifecycle_untouched(session)


def test_missing_symbol_error_and_portfolio_order_are_preserved() -> None:
    service, session, portfolio_service, market_data_service, _, _ = (
        _service_with_dependencies()
    )
    portfolio_service.get.return_value = _portfolio(
        holdings=(("MSFT", "0.4"), ("AAPL", "0.3"), ("BND", "0.3"))
    )
    market_data_service.get_range.return_value = [
        _record("AAPL", "2020-02-03", "100.000000000000")
    ]

    with (
        patch.object(
            service_module,
            "get_historical_scenario",
            return_value=HISTORICAL_SCENARIOS[0],
        ),
        patch.object(
            service_module,
            "simulate_historical_scenario",
        ) as simulator,
    ):
        with pytest.raises(ValueError) as raised:
            service.run(
                user_id=_USER_ID,
                portfolio_id=_PORTFOLIO_ID,
                request=_request(),
            )

    assert str(raised.value) == (
        "market data is unavailable for requested symbols: MSFT, BND"
    )
    simulator.assert_not_called()
    _assert_session_lifecycle_untouched(session)


def test_simulator_insufficient_data_error_propagates_unchanged() -> None:
    service, session, portfolio_service, market_data_service, _, _ = (
        _service_with_dependencies()
    )
    portfolio_service.get.return_value = _portfolio()
    market_data_service.get_range.return_value = []
    prices = pd.DataFrame(
        {
            "BETA": [100.0, 101.0],
            "ZERO": [50.0, 50.0],
            "ALPHA": [200.0, 201.0],
        },
        index=pd.DatetimeIndex(["2020-02-03", "2020-02-04"]),
    )

    with (
        patch.object(
            service_module,
            "get_historical_scenario",
            return_value=HISTORICAL_SCENARIOS[0],
        ),
        patch.object(
            service_module,
            "_build_price_frame",
            return_value=prices,
        ),
    ):
        with pytest.raises(ValueError) as raised:
            service.run(
                user_id=_USER_ID,
                portfolio_id=_PORTFOLIO_ID,
                request=_request(),
            )

    assert str(raised.value) == (
        "prices must contain at least three rows for historical simulation"
    )
    _assert_session_lifecycle_untouched(session)


def test_service_returns_valid_frozen_schema_response() -> None:
    service, session, portfolio_service, market_data_service, _, _ = (
        _service_with_dependencies()
    )
    portfolio_service.get.return_value = _portfolio()
    market_data_service.get_range.return_value = []
    prices = pd.DataFrame(
        {
            "BETA": [100.0, 101.0, 102.0],
            "ZERO": [50.0, 50.0, 50.0],
            "ALPHA": [200.0, 202.0, 204.0],
        },
        index=pd.DatetimeIndex(
            ["2020-02-03", "2020-02-04", "2020-02-05"]
        ),
    )

    with (
        patch.object(
            service_module,
            "get_historical_scenario",
            return_value=HISTORICAL_SCENARIOS[0],
        ),
        patch.object(
            service_module,
            "_build_price_frame",
            return_value=prices,
        ),
        patch.object(
            service_module,
            "simulate_historical_scenario",
            return_value=_simulation_result(),
        ),
    ):
        response = service.run(
            user_id=_USER_ID,
            portfolio_id=_PORTFOLIO_ID,
            request=_request(),
        )

    assert isinstance(response, HistoricalScenarioSimulationResponse)
    assert response.portfolio_id == _PORTFOLIO_ID
    assert response.scenario.id == "covid-19-shock-2020"
    assert response.metrics.sharpe_ratio is None
    assert response.metrics.maximum_drawdown.max_drawdown == -0.25
    _assert_session_lifecycle_untouched(session)


def test_service_does_not_mutate_request_portfolio_holdings_or_records() -> None:
    service, session, portfolio_service, market_data_service, _, _ = (
        _service_with_dependencies()
    )
    request = _request()
    portfolio = _portfolio()
    records = [
        _record("BETA", "2020-02-03", "100.000000000000"),
        _record("ZERO", "2020-02-03", "50.000000000000"),
        _record("ALPHA", "2020-02-03", "200.000000000000"),
    ]
    request_snapshot = request.model_dump()
    holding_snapshot = [
        (holding.symbol, holding.weight, holding.position)
        for holding in portfolio.holdings
    ]
    holding_identities = [id(holding) for holding in portfolio.holdings]
    record_snapshot = [
        (record.symbol, record.date, record.adjusted_close)
        for record in records
    ]
    portfolio_service.get.return_value = portfolio
    market_data_service.get_range.return_value = records

    with (
        patch.object(
            service_module,
            "get_historical_scenario",
            return_value=HISTORICAL_SCENARIOS[0],
        ),
        patch.object(
            service_module,
            "_build_price_frame",
            return_value=pd.DataFrame(
                {
                    "BETA": [100.0, 101.0, 102.0],
                    "ZERO": [50.0, 50.0, 50.0],
                    "ALPHA": [200.0, 202.0, 204.0],
                },
                index=pd.date_range("2020-02-03", periods=3),
            ),
        ),
        patch.object(
            service_module,
            "simulate_historical_scenario",
            return_value=_simulation_result(),
        ),
    ):
        service.run(
            user_id=_USER_ID,
            portfolio_id=_PORTFOLIO_ID,
            request=request,
        )

    assert request.model_dump() == request_snapshot
    assert [id(holding) for holding in portfolio.holdings] == holding_identities
    assert [
        (holding.symbol, holding.weight, holding.position)
        for holding in portfolio.holdings
    ] == holding_snapshot
    assert [
        (record.symbol, record.date, record.adjusted_close)
        for record in records
    ] == record_snapshot
    _assert_session_lifecycle_untouched(session)


def test_service_module_has_no_http_persistence_network_or_csv_behavior() -> None:
    source = inspect.getsource(service_module)

    for forbidden_reference in (
        "fastapi",
        "HTTPException",
        "AnalysisRepository",
        "save_snapshot",
        "session.commit",
        "session.rollback",
        "session.close",
        "yfinance",
        "read_csv",
        "requests",
    ):
        assert forbidden_reference not in source


def test_direct_service_exports_are_importable_without_package_export_change() -> None:
    assert service_module.__all__ == [
        "HistoricalScenarioNotFoundError",
        "EmptyPortfolioError",
        "HistoricalScenarioService",
    ]
