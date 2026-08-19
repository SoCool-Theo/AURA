"""Public catalogue and authenticated portfolio simulation endpoints."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import CurrentUser, DatabaseSession
from app.scenarios.definitions import HISTORICAL_SCENARIOS
from app.schemas.simulation import (
    AllocationSimulationRequest,
    AllocationSimulationResponse,
    HistoricalScenarioListResponse,
    HistoricalScenarioResponse,
    HistoricalScenarioSimulationRequest,
    HistoricalScenarioSimulationResponse,
)
from app.services.allocation_simulation_service import (
    AllocationSimulationService,
    AllocationSymbolMismatchError,
    EmptyPortfolioError as AllocationEmptyPortfolioError,
)
from app.services.historical_scenario_service import (
    EmptyPortfolioError,
    HistoricalScenarioNotFoundError,
    HistoricalScenarioService,
)


router = APIRouter(tags=["Simulations"])

_MISSING_MARKET_DATA_PREFIX = (
    "market data is unavailable for requested symbols: "
)
_INSUFFICIENT_HISTORY_ERROR = (
    "prices must contain at least three rows for historical simulation"
)


def _internal_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Unable to run historical scenario",
    )


def _allocation_internal_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Unable to run allocation simulation",
    )


def _portfolio_not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Portfolio not found",
    )


def _scenario_not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Historical scenario not found",
    )


def _unprocessable_historical_input(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=detail,
    )


def _is_expected_historical_data_error(error: ValueError) -> bool:
    detail = str(error)
    return (
        detail.startswith(_MISSING_MARKET_DATA_PREFIX)
        or detail == _INSUFFICIENT_HISTORY_ERROR
    )


@router.get(
    "/simulations/historical-scenarios",
    response_model=HistoricalScenarioListResponse,
    status_code=status.HTTP_200_OK,
)
def list_historical_scenarios() -> HistoricalScenarioListResponse:
    """Return the public deterministic predefined scenario catalogue."""
    return HistoricalScenarioListResponse(
        scenarios=[
            HistoricalScenarioResponse(
                id=scenario.id,
                display_name=scenario.display_name,
                description=scenario.description,
                requested_start_date=scenario.requested_start_date,
                requested_end_date=scenario.requested_end_date,
            )
            for scenario in HISTORICAL_SCENARIOS
        ]
    )


@router.post(
    "/portfolios/{portfolio_id}/simulations/historical-scenarios",
    response_model=HistoricalScenarioSimulationResponse,
    status_code=status.HTTP_200_OK,
)
def run_historical_scenario(
    portfolio_id: UUID,
    request: HistoricalScenarioSimulationRequest,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> HistoricalScenarioSimulationResponse:
    """Run one read-only scenario for the authenticated user's portfolio."""
    try:
        response = HistoricalScenarioService(session).run(
            user_id=current_user.id,
            portfolio_id=portfolio_id,
            request=request,
        )
    except HistoricalScenarioNotFoundError as error:
        raise _scenario_not_found() from error
    except EmptyPortfolioError as error:
        raise _unprocessable_historical_input(str(error)) from error
    except ValueError as error:
        if _is_expected_historical_data_error(error):
            raise _unprocessable_historical_input(str(error)) from error
        raise _internal_error() from error
    except Exception as error:
        raise _internal_error() from error

    if response is None:
        raise _portfolio_not_found()
    return response


@router.post(
    "/portfolios/{portfolio_id}/simulations/allocations",
    response_model=AllocationSimulationResponse,
    status_code=status.HTTP_200_OK,
)
def run_allocation_simulation(
    portfolio_id: UUID,
    request: AllocationSimulationRequest,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> AllocationSimulationResponse:
    """Compare one allocation for the authenticated user's portfolio."""
    try:
        response = AllocationSimulationService(session).run(
            user_id=current_user.id,
            portfolio_id=portfolio_id,
            request=request,
        )
    except (
        AllocationSymbolMismatchError,
        AllocationEmptyPortfolioError,
    ) as error:
        raise _unprocessable_historical_input(str(error)) from error
    except ValueError as error:
        if _is_expected_historical_data_error(error):
            raise _unprocessable_historical_input(str(error)) from error
        raise _allocation_internal_error() from error
    except Exception as error:
        raise _allocation_internal_error() from error

    if response is None:
        raise _portfolio_not_found()
    return response
