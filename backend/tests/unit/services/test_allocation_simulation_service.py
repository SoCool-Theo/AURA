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
from backend.app.scenarios.simulator import (
    AllocationComparisonResult,
    HistoricalSimulationResult,
    HistoricalTrajectoryPoint,
)
from backend.app.schemas.simulation import (
    AllocationSimulationRequest,
    AllocationSimulationResponse,
)
import backend.app.services.allocation_simulation_service as service_module
import backend.app.services.analysis_service as analysis_service_module
from backend.app.services.allocation_simulation_service import (
    AllocationSimulationService,
    AllocationSymbolMismatchError,
    EmptyPortfolioError,
    _map_allocation_simulation_response,
)
from backend.app.services.portfolio_baseline_resolver import (
    PortfolioBaselineKind,
    PortfolioBaselineResolution,
    PortfolioBaselineResolutionService,
    ResolvedPortfolioWeight,
)
from backend.app.services.portfolio_valuation_service import InvalidHoldingModeError


_PORTFOLIO_ID = UUID("12345678-1234-5678-1234-567812345678")
_USER_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


def _historical_result(*, modified: bool = False) -> HistoricalSimulationResult:
    if not modified:
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

    return HistoricalSimulationResult(
        effective_start_date=pd.Timestamp("2020-02-03"),
        effective_end_date=pd.Timestamp("2020-04-30"),
        price_observation_count=4,
        return_observation_count=3,
        normalized_starting_value=1.0,
        normalized_ending_value=1.05,
        cumulative_return=0.05,
        annualized_volatility=0.3,
        sharpe_ratio=1.2,
        maximum_drawdown=MaxDrawdownResult(
            max_drawdown=-0.1,
            peak_date=pd.Timestamp("2020-02-03"),
            trough_date=pd.Timestamp("2020-03-02"),
        ),
        trajectory=(
            HistoricalTrajectoryPoint(pd.Timestamp("2020-02-03"), 1.0),
            HistoricalTrajectoryPoint(pd.Timestamp("2020-03-02"), 0.9),
            HistoricalTrajectoryPoint(pd.Timestamp("2020-03-23"), 0.97),
            HistoricalTrajectoryPoint(pd.Timestamp("2020-04-30"), 1.05),
        ),
    )


def _comparison_result(
    *,
    sharpe_ratio_delta: float | None = None,
) -> AllocationComparisonResult:
    return AllocationComparisonResult(
        original=_historical_result(),
        modified=_historical_result(modified=True),
        normalized_ending_value_delta=0.1,
        cumulative_return_delta=0.1,
        annualized_volatility_delta=-0.12,
        sharpe_ratio_delta=sharpe_ratio_delta,
        maximum_drawdown_delta=0.15,
    )


def _request(
    *,
    modified_allocation: list[dict[str, object]] | None = None,
) -> AllocationSimulationRequest:
    allocation = modified_allocation or [
        {"symbol": "ALPHA", "weight": 0.5},
        {"symbol": "BETA", "weight": 0.5},
        {"symbol": "ZERO", "weight": 0.0},
    ]
    return AllocationSimulationRequest.model_validate(
        {
            "start_date": "2020-02-01",
            "end_date": "2020-04-30",
            "modified_allocation": allocation,
        }
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


def _original_weights() -> dict[str, float]:
    return {"BETA": 0.4, "ZERO": 0.0, "ALPHA": 0.6}


def _modified_weights() -> dict[str, float]:
    return {"BETA": 0.5, "ZERO": 0.0, "ALPHA": 0.5}


def test_planned_simulation_stays_guarded_until_snapshot_contract_exists(
) -> None:
    service, session, portfolio_service, market_data, _, _ = (
        _service_with_dependencies()
    )
    portfolio_service.get.return_value = _portfolio()
    baseline_resolver = MagicMock(spec=PortfolioBaselineResolutionService)
    baseline_resolver.resolve.return_value = PortfolioBaselineResolution(
        baseline_kind=PortfolioBaselineKind.PLANNED,
        resolved_weights=(ResolvedPortfolioWeight("BETA", Decimal("1")),),
        valuation=None,
        valuation_as_of=None,
    )
    service._baseline_resolver = baseline_resolver

    with pytest.raises(
        InvalidHoldingModeError,
        match="planned simulation snapshots are not implemented",
    ):
        service.run_with_context(
            user_id=_USER_ID,
            portfolio_id=_PORTFOLIO_ID,
            request=_request(),
            valuation_date=date(2026, 9, 12),
        )

    market_data.get_range.assert_not_called()
    _assert_session_lifecycle_untouched(session)


def _map_response(
    *,
    result: AllocationComparisonResult | None = None,
) -> AllocationSimulationResponse:
    return _map_allocation_simulation_response(
        portfolio_id=_PORTFOLIO_ID,
        portfolio_name="Balanced Learning Portfolio",
        request=_request(),
        original_weights=_original_weights(),
        modified_weights=_modified_weights(),
        result=_comparison_result() if result is None else result,
    )


def _service_with_dependencies() -> tuple[
    AllocationSimulationService,
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
        service = AllocationSimulationService(session)

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


def test_mapper_returns_valid_response_with_identity_and_requested_period() -> None:
    response = _map_response()

    assert isinstance(response, AllocationSimulationResponse)
    assert response.portfolio_id == _PORTFOLIO_ID
    assert response.portfolio_name == "Balanced Learning Portfolio"
    assert response.start_date == date(2020, 2, 1)
    assert response.end_date == date(2020, 4, 30)


def test_mapper_preserves_shared_effective_metadata() -> None:
    response = _map_response()

    assert response.metadata.model_dump() == {
        "effective_start_date": date(2020, 2, 3),
        "effective_end_date": date(2020, 4, 30),
        "price_observation_count": 4,
        "return_observation_count": 3,
    }


def test_mapper_preserves_original_and_modified_canonical_allocations() -> None:
    response = _map_response()

    assert [holding.model_dump() for holding in response.original.allocation] == [
        {"symbol": "BETA", "weight": 0.4},
        {"symbol": "ZERO", "weight": 0.0},
        {"symbol": "ALPHA", "weight": 0.6},
    ]
    assert [holding.model_dump() for holding in response.modified.allocation] == [
        {"symbol": "BETA", "weight": 0.5},
        {"symbol": "ZERO", "weight": 0.0},
        {"symbol": "ALPHA", "weight": 0.5},
    ]


def test_mapper_preserves_metrics_trajectories_and_signed_drawdowns() -> None:
    response = _map_response()

    assert response.original.metrics.sharpe_ratio is None
    assert response.original.metrics.maximum_drawdown.max_drawdown == -0.25
    assert response.modified.metrics.sharpe_ratio == 1.2
    assert response.modified.metrics.maximum_drawdown.max_drawdown == -0.1
    assert [point.normalized_value for point in response.original.trajectory] == [
        1.0,
        0.8,
        0.75,
        0.95,
    ]
    assert [point.normalized_value for point in response.modified.trajectory] == [
        1.0,
        0.9,
        0.97,
        1.05,
    ]


def test_mapper_preserves_all_comparison_deltas_and_nullable_sharpe() -> None:
    response = _map_response()

    assert response.comparison.model_dump() == {
        "normalized_ending_value_delta": 0.1,
        "cumulative_return_delta": 0.1,
        "annualized_volatility_delta": -0.12,
        "sharpe_ratio_delta": None,
        "maximum_drawdown_delta": 0.15,
    }


def test_mapper_preserves_defined_sharpe_delta() -> None:
    response = _map_response(
        result=_comparison_result(sharpe_ratio_delta=0.75)
    )

    assert response.comparison.sharpe_ratio_delta == 0.75


def test_mapper_does_not_mutate_request_weights_or_result() -> None:
    request = _request()
    original_weights = _original_weights()
    modified_weights = _modified_weights()
    result = _comparison_result()
    request_snapshot = request.model_dump()
    original_snapshot = list(original_weights.items())
    modified_snapshot = list(modified_weights.items())
    result_snapshot = deepcopy(result)

    _map_allocation_simulation_response(
        portfolio_id=_PORTFOLIO_ID,
        portfolio_name="Balanced Learning Portfolio",
        request=request,
        original_weights=original_weights,
        modified_weights=modified_weights,
        result=result,
    )

    assert request.model_dump() == request_snapshot
    assert list(original_weights.items()) == original_snapshot
    assert list(modified_weights.items()) == modified_snapshot
    assert result == result_snapshot


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


def test_missing_or_wrong_owner_portfolio_returns_none_without_disclosure() -> None:
    service, session, portfolio_service, market_data_service, _, _ = (
        _service_with_dependencies()
    )
    portfolio_service.get.return_value = None

    with (
        patch.object(service_module, "_build_price_frame") as build_price_frame,
        patch.object(
            service_module,
            "simulate_allocation_change",
        ) as simulate_allocation_change,
    ):
        response = service.run(
            user_id=_USER_ID,
            portfolio_id=_PORTFOLIO_ID,
            request=_request(),
        )

    assert response is None
    portfolio_service.get.assert_called_once_with(
        user_id=_USER_ID,
        portfolio_id=_PORTFOLIO_ID,
    )
    market_data_service.get_range.assert_not_called()
    build_price_frame.assert_not_called()
    simulate_allocation_change.assert_not_called()
    _assert_session_lifecycle_untouched(session)


def test_empty_owned_portfolio_fails_before_market_data() -> None:
    service, session, portfolio_service, market_data_service, _, _ = (
        _service_with_dependencies()
    )
    portfolio_service.get.return_value = _portfolio(holdings=())

    with pytest.raises(EmptyPortfolioError) as raised:
        service.run(
            user_id=_USER_ID,
            portfolio_id=_PORTFOLIO_ID,
            request=_request(),
        )

    assert str(raised.value) == "portfolio must contain at least one holding"
    market_data_service.get_range.assert_not_called()
    _assert_session_lifecycle_untouched(session)


@pytest.mark.parametrize(
    "modified_allocation",
    [
        [
            {"symbol": "BETA", "weight": 0.4},
            {"symbol": "ALPHA", "weight": 0.6},
        ],
        [
            {"symbol": "BETA", "weight": 0.5},
            {"symbol": "ZERO", "weight": 0.0},
            {"symbol": "ALPHA", "weight": 0.5},
            {"symbol": "GLD", "weight": 0.0},
        ],
    ],
    ids=["missing-symbol", "additional-symbol"],
)
def test_symbol_mismatch_fails_before_market_data(
    modified_allocation: list[dict[str, object]],
) -> None:
    service, session, portfolio_service, market_data_service, _, _ = (
        _service_with_dependencies()
    )
    portfolio_service.get.return_value = _portfolio()

    with pytest.raises(AllocationSymbolMismatchError) as raised:
        service.run(
            user_id=_USER_ID,
            portfolio_id=_PORTFOLIO_ID,
            request=_request(modified_allocation=modified_allocation),
        )

    assert str(raised.value) == (
        "modified allocation symbols must exactly match saved portfolio symbols"
    )
    market_data_service.get_range.assert_not_called()
    _assert_session_lifecycle_untouched(session)


def test_successful_orchestration_uses_saved_order_and_one_shared_frame() -> None:
    service, session, portfolio_service, market_data_service, _, _ = (
        _service_with_dependencies()
    )
    portfolio = _portfolio()
    request = _request()
    records = [MagicMock(name="record-one"), MagicMock(name="record-two")]
    prices = pd.DataFrame(
        {
            "BETA": [100.0, 101.0, 102.0],
            "ZERO": [50.0, 50.0, 50.0],
            "ALPHA": [200.0, 202.0, 204.0],
        },
        index=pd.date_range("2020-02-03", periods=3),
    )
    comparison = _comparison_result()
    response = _map_response()
    portfolio_service.get.return_value = portfolio
    market_data_service.get_range.return_value = records

    with (
        patch.object(
            service_module,
            "_build_price_frame",
            return_value=prices,
        ) as build_price_frame,
        patch.object(
            service_module,
            "simulate_allocation_change",
            return_value=comparison,
        ) as simulate_allocation_change,
        patch.object(
            service_module,
            "_map_allocation_simulation_response",
            return_value=response,
        ) as mapper,
    ):
        result = service.run(
            user_id=_USER_ID,
            portfolio_id=_PORTFOLIO_ID,
            request=request,
        )

    assert result is response
    portfolio_service.get.assert_called_once_with(
        user_id=_USER_ID,
        portfolio_id=_PORTFOLIO_ID,
    )
    symbols = market_data_service.get_range.call_args.args[0]
    assert symbols == ["BETA", "ZERO", "ALPHA"]
    market_data_service.get_range.assert_called_once_with(
        symbols,
        date(2020, 2, 1),
        date(2020, 4, 30),
    )
    build_price_frame.assert_called_once_with(records, symbols)
    original_weights = simulate_allocation_change.call_args.args[1]
    modified_weights = simulate_allocation_change.call_args.args[2]
    simulate_allocation_change.assert_called_once_with(
        prices,
        original_weights,
        modified_weights,
    )
    assert list(original_weights.items()) == [
        ("BETA", 0.4),
        ("ZERO", 0.0),
        ("ALPHA", 0.6),
    ]
    assert list(modified_weights.items()) == [
        ("BETA", 0.5),
        ("ZERO", 0.0),
        ("ALPHA", 0.5),
    ]
    mapper.assert_called_once_with(
        portfolio_id=portfolio.id,
        portfolio_name=portfolio.name,
        request=request,
        original_weights=original_weights,
        modified_weights=modified_weights,
        result=comparison,
    )
    market_data_service.store.assert_not_called()
    _assert_session_lifecycle_untouched(session)


def test_real_alignment_uses_exact_intersection_once_in_saved_order() -> None:
    service, session, portfolio_service, market_data_service, _, _ = (
        _service_with_dependencies()
    )
    portfolio_service.get.return_value = _portfolio(
        holdings=(("BTC-USD", "0.4"), ("AAPL", "0.6"))
    )
    request = _request(
        modified_allocation=[
            {"symbol": "AAPL", "weight": 0.7},
            {"symbol": "BTC-USD", "weight": 0.3},
        ]
    )
    market_data_service.get_range.return_value = [
        _record("AAPL", "2020-02-03", "100.000000000000"),
        _record("AAPL", "2020-02-05", "102.000000000000"),
        _record("BTC-USD", "2020-02-03", "9000.000000000000"),
        _record("BTC-USD", "2020-02-04", "9100.000000000000"),
        _record("BTC-USD", "2020-02-05", "9200.000000000000"),
    ]
    captured_prices: list[pd.DataFrame] = []

    def compare(
        prices: pd.DataFrame,
        original_weights: dict[str, float],
        modified_weights: dict[str, float],
    ) -> AllocationComparisonResult:
        captured_prices.append(prices.copy(deep=True))
        assert list(original_weights) == ["BTC-USD", "AAPL"]
        assert list(modified_weights) == ["BTC-USD", "AAPL"]
        return _comparison_result()

    with (
        patch.object(
            service_module,
            "simulate_allocation_change",
            side_effect=compare,
        ),
        patch.object(
            service_module,
            "_map_allocation_simulation_response",
            return_value=_map_response(),
        ),
    ):
        service.run(
            user_id=_USER_ID,
            portfolio_id=_PORTFOLIO_ID,
            request=request,
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


def test_missing_historical_data_failure_propagates_unchanged() -> None:
    service, session, portfolio_service, market_data_service, _, _ = (
        _service_with_dependencies()
    )
    portfolio_service.get.return_value = _portfolio()
    market_data_service.get_range.return_value = [
        _record("BETA", "2020-02-03", "100.000000000000")
    ]

    with patch.object(
        service_module,
        "simulate_allocation_change",
    ) as simulate_allocation_change:
        with pytest.raises(ValueError) as raised:
            service.run(
                user_id=_USER_ID,
                portfolio_id=_PORTFOLIO_ID,
                request=_request(),
            )

    assert str(raised.value) == (
        "market data is unavailable for requested symbols: ZERO, ALPHA"
    )
    simulate_allocation_change.assert_not_called()
    _assert_session_lifecycle_untouched(session)


def test_insufficient_aligned_data_failure_propagates_unchanged() -> None:
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
        index=pd.date_range("2020-02-03", periods=2),
    )

    with patch.object(
        service_module,
        "_build_price_frame",
        return_value=prices,
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


def test_service_does_not_mutate_request_or_saved_holdings() -> None:
    service, session, portfolio_service, market_data_service, _, _ = (
        _service_with_dependencies()
    )
    request = _request()
    portfolio = _portfolio()
    request_snapshot = request.model_dump()
    holding_snapshot = [
        (holding.symbol, holding.weight, holding.position)
        for holding in portfolio.holdings
    ]
    holding_identities = [id(holding) for holding in portfolio.holdings]
    portfolio_service.get.return_value = portfolio
    market_data_service.get_range.return_value = []

    with (
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
            "simulate_allocation_change",
            return_value=_comparison_result(),
        ),
        patch.object(
            service_module,
            "_map_allocation_simulation_response",
            return_value=_map_response(),
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
    _assert_session_lifecycle_untouched(session)


def test_service_reuses_analysis_exact_alignment_helper_by_identity() -> None:
    assert (
        service_module._build_price_frame
        is analysis_service_module._build_price_frame
    )


def test_service_module_has_no_http_persistence_network_or_csv_behavior() -> None:
    source = inspect.getsource(service_module)

    for forbidden_reference in (
        "fastapi",
        "HTTPException",
        "AnalysisRepository",
        "session.commit",
        "session.rollback",
        "session.close",
        "session.flush",
        "yfinance",
        "read_csv",
        "requests",
    ):
        assert forbidden_reference not in source


def test_direct_service_exports_are_importable_without_package_change() -> None:
    assert service_module.__all__ == [
        "AllocationSymbolMismatchError",
        "EmptyPortfolioError",
        "AllocationSimulationService",
    ]
