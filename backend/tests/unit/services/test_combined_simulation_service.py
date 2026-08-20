from copy import deepcopy
from datetime import date
import inspect
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
from sqlalchemy.orm import Session

from backend.app.scenarios.definitions import get_historical_scenario
from backend.app.schemas.simulation import (
    AllocationSimulationRequest,
    AllocationSimulationResponse,
    CombinedSimulationRequest,
    CombinedSimulationResponse,
)
import backend.app.services.combined_simulation_service as service_module
from backend.app.services.allocation_simulation_service import (
    AllocationSimulationService,
    AllocationSymbolMismatchError,
    EmptyPortfolioError,
)
from backend.app.services.combined_simulation_service import (
    CombinedSimulationService,
    _map_combined_simulation_response,
)
from backend.app.services.historical_scenario_service import (
    HistoricalScenarioNotFoundError,
)


_PORTFOLIO_ID = UUID("12345678-1234-5678-1234-567812345678")
_USER_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


def _request(
    *,
    scenario_id: str = "covid-19-shock-2020",
) -> CombinedSimulationRequest:
    return CombinedSimulationRequest.model_validate(
        {
            "scenario_id": scenario_id,
            "modified_allocation": [
                {"symbol": "MSFT", "weight": 0.7},
                {"symbol": "AAPL", "weight": 0.3},
            ],
        }
    )


def _allocation_response() -> AllocationSimulationResponse:
    return AllocationSimulationResponse.model_validate(
        {
            "portfolio_id": _PORTFOLIO_ID,
            "portfolio_name": "Balanced Learning Portfolio",
            "start_date": "2020-02-01",
            "end_date": "2020-04-30",
            "metadata": {
                "effective_start_date": "2020-02-03",
                "effective_end_date": "2020-04-30",
                "price_observation_count": 3,
                "return_observation_count": 2,
            },
            "original": {
                "allocation": [
                    {"symbol": "AAPL", "weight": 0.6},
                    {"symbol": "MSFT", "weight": 0.4},
                ],
                "metrics": {
                    "normalized_starting_value": 1.0,
                    "normalized_ending_value": 0.8,
                    "cumulative_return": -0.2,
                    "annualized_volatility": 0.42,
                    "sharpe_ratio": None,
                    "maximum_drawdown": {
                        "max_drawdown": -0.3,
                        "peak_date": "2020-02-03",
                        "trough_date": "2020-03-23",
                    },
                },
                "trajectory": [
                    {"date": "2020-02-03", "normalized_value": 1.0},
                    {"date": "2020-03-23", "normalized_value": 0.7},
                    {"date": "2020-04-30", "normalized_value": 0.8},
                ],
            },
            "modified": {
                "allocation": [
                    {"symbol": "AAPL", "weight": 0.3},
                    {"symbol": "MSFT", "weight": 0.7},
                ],
                "metrics": {
                    "normalized_starting_value": 1.0,
                    "normalized_ending_value": 1.1,
                    "cumulative_return": 0.1,
                    "annualized_volatility": 0.3,
                    "sharpe_ratio": 1.2,
                    "maximum_drawdown": {
                        "max_drawdown": -0.1,
                        "peak_date": "2020-02-03",
                        "trough_date": "2020-03-23",
                    },
                },
                "trajectory": [
                    {"date": "2020-02-03", "normalized_value": 1.0},
                    {"date": "2020-03-23", "normalized_value": 0.9},
                    {"date": "2020-04-30", "normalized_value": 1.1},
                ],
            },
            "comparison": {
                "normalized_ending_value_delta": 0.3,
                "cumulative_return_delta": 0.3,
                "annualized_volatility_delta": -0.12,
                "sharpe_ratio_delta": None,
                "maximum_drawdown_delta": 0.2,
            },
        }
    )


def _service_with_dependency() -> tuple[
    CombinedSimulationService,
    MagicMock,
    MagicMock,
    MagicMock,
]:
    session = MagicMock(spec=Session)
    allocation_service = MagicMock(spec=AllocationSimulationService)
    with patch.object(
        service_module,
        "AllocationSimulationService",
        return_value=allocation_service,
    ) as allocation_service_type:
        service = CombinedSimulationService(session)
    return service, session, allocation_service, allocation_service_type


def _assert_session_lifecycle_untouched(session: MagicMock) -> None:
    session.commit.assert_not_called()
    session.rollback.assert_not_called()
    session.close.assert_not_called()
    session.flush.assert_not_called()


def test_mapper_preserves_complete_scenario_and_allocation_response() -> None:
    scenario = get_historical_scenario("covid-19-shock-2020")
    assert scenario is not None
    allocation_response = _allocation_response()

    response = _map_combined_simulation_response(
        scenario=scenario,
        allocation_response=allocation_response,
    )

    assert isinstance(response, CombinedSimulationResponse)
    assert response.portfolio_id == allocation_response.portfolio_id
    assert response.portfolio_name == allocation_response.portfolio_name
    assert response.scenario.model_dump() == {
        "id": scenario.id,
        "display_name": scenario.display_name,
        "description": scenario.description,
        "requested_start_date": scenario.requested_start_date,
        "requested_end_date": scenario.requested_end_date,
    }
    assert response.metadata.effective_start_date == date(2020, 2, 3)
    assert response.metadata.effective_end_date == date(2020, 4, 30)
    assert response.metadata is allocation_response.metadata
    assert response.original is allocation_response.original
    assert response.modified is allocation_response.modified
    assert response.comparison is allocation_response.comparison
    assert response.original.metrics.maximum_drawdown.max_drawdown == -0.3
    assert response.original.metrics.sharpe_ratio is None
    assert response.comparison.sharpe_ratio_delta is None
    assert response.comparison.maximum_drawdown_delta == 0.2


def test_known_scenario_builds_allocation_request_and_delegates_once() -> None:
    service, session, allocation_service, allocation_service_type = (
        _service_with_dependency()
    )
    request = _request()
    allocation_response = _allocation_response()
    allocation_service.run.return_value = allocation_response

    with patch.object(
        service_module,
        "get_historical_scenario",
        wraps=get_historical_scenario,
    ) as scenario_lookup:
        response = service.run(
            user_id=_USER_ID,
            portfolio_id=_PORTFOLIO_ID,
            request=request,
        )

    assert isinstance(response, CombinedSimulationResponse)
    scenario_lookup.assert_called_once_with("covid-19-shock-2020")
    allocation_service_type.assert_called_once_with(session)
    allocation_service.run.assert_called_once()
    call = allocation_service.run.call_args.kwargs
    assert call["user_id"] == _USER_ID
    assert call["portfolio_id"] == _PORTFOLIO_ID
    forwarded_request = call["request"]
    assert isinstance(forwarded_request, AllocationSimulationRequest)
    assert forwarded_request.start_date == date(2020, 2, 1)
    assert forwarded_request.end_date == date(2020, 4, 30)
    assert forwarded_request.modified_allocation == request.modified_allocation
    assert [
        holding.model_dump()
        for holding in forwarded_request.modified_allocation
    ] == [holding.model_dump() for holding in request.modified_allocation]
    _assert_session_lifecycle_untouched(session)


def test_allocation_none_is_returned_without_mapping() -> None:
    service, session, allocation_service, _ = _service_with_dependency()
    allocation_service.run.return_value = None

    with patch.object(
        service_module,
        "_map_combined_simulation_response",
    ) as mapper:
        response = service.run(
            user_id=_USER_ID,
            portfolio_id=_PORTFOLIO_ID,
            request=_request(),
        )

    assert response is None
    allocation_service.run.assert_called_once()
    mapper.assert_not_called()
    _assert_session_lifecycle_untouched(session)


def test_unknown_scenario_uses_existing_error_before_allocation() -> None:
    service, session, allocation_service, _ = _service_with_dependency()

    with pytest.raises(HistoricalScenarioNotFoundError) as raised:
        service.run(
            user_id=_USER_ID,
            portfolio_id=_PORTFOLIO_ID,
            request=_request(scenario_id="unknown-scenario"),
        )

    assert str(raised.value) == "Historical scenario not found"
    allocation_service.run.assert_not_called()
    _assert_session_lifecycle_untouched(session)


@pytest.mark.parametrize(
    "error",
    [
        AllocationSymbolMismatchError(
            "modified allocation symbols must exactly match saved portfolio symbols"
        ),
        EmptyPortfolioError("portfolio must contain at least one holding"),
        ValueError("market data is unavailable for requested symbols: MSFT"),
    ],
    ids=["symbol-mismatch", "empty-portfolio", "historical-data"],
)
def test_allocation_domain_errors_propagate_unchanged(error: Exception) -> None:
    service, session, allocation_service, _ = _service_with_dependency()
    allocation_service.run.side_effect = error

    with pytest.raises(type(error)) as raised:
        service.run(
            user_id=_USER_ID,
            portfolio_id=_PORTFOLIO_ID,
            request=_request(),
        )

    assert raised.value is error
    allocation_service.run.assert_called_once()
    _assert_session_lifecycle_untouched(session)


def test_unexpected_allocation_error_propagates_unchanged() -> None:
    service, session, allocation_service, _ = _service_with_dependency()
    error = RuntimeError("unexpected allocation failure")
    allocation_service.run.side_effect = error

    with pytest.raises(RuntimeError) as raised:
        service.run(
            user_id=_USER_ID,
            portfolio_id=_PORTFOLIO_ID,
            request=_request(),
        )

    assert raised.value is error
    allocation_service.run.assert_called_once()
    _assert_session_lifecycle_untouched(session)


def test_service_does_not_mutate_caller_owned_request() -> None:
    service, session, allocation_service, _ = _service_with_dependency()
    request = _request()
    request_snapshot = deepcopy(request.model_dump())
    holding_identities = [id(holding) for holding in request.modified_allocation]
    allocation_service.run.return_value = _allocation_response()

    service.run(
        user_id=_USER_ID,
        portfolio_id=_PORTFOLIO_ID,
        request=request,
    )

    assert request.model_dump() == request_snapshot
    assert [id(holding) for holding in request.modified_allocation] == (
        holding_identities
    )
    _assert_session_lifecycle_untouched(session)


def test_service_module_only_composes_existing_read_only_behavior() -> None:
    source = inspect.getsource(service_module)

    for forbidden_reference in (
        "PortfolioService",
        "MarketDataService",
        "_build_price_frame",
        "simulate_allocation_change",
        "simulate_historical_scenario",
        "fastapi",
        "HTTPException",
        "AnalysisRepository",
        "session.commit",
        "session.rollback",
        "session.close",
        "session.flush",
    ):
        assert forbidden_reference not in source


def test_direct_service_export_is_importable_without_package_change() -> None:
    assert service_module.__all__ == ["CombinedSimulationService"]
