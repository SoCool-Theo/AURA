"""Public catalogue and authenticated portfolio simulation endpoints."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import CurrentUser, DatabaseSession
from app.scenarios.definitions import HISTORICAL_SCENARIOS
from app.schemas.simulation import (
    AllocationSimulationRequest,
    AllocationSimulationResponse,
    CombinedSimulationRequest,
    CombinedSimulationResponse,
    HistoricalScenarioListResponse,
    HistoricalScenarioResponse,
    HistoricalScenarioSimulationRequest,
    HistoricalScenarioSimulationResponse,
)
from app.schemas.simulation_history import (
    SimulationHistoryDetailResponse,
    SimulationHistoryListResponse,
)
from app.services.allocation_simulation_service import (
    AllocationSimulationService,
    AllocationSymbolMismatchError,
    EmptyPortfolioError as AllocationEmptyPortfolioError,
)
from app.services.combined_simulation_service import CombinedSimulationService
from app.services.historical_scenario_service import (
    EmptyPortfolioError,
    HistoricalScenarioNotFoundError,
    HistoricalScenarioService,
)
from app.services.simulation_history_service import (
    SimulationHistoryService,
    SimulationNotFoundError,
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


def _combined_internal_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Unable to run combined simulation",
    )


def _history_internal_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Unable to retrieve simulation history",
    )


def _history_detail_internal_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Unable to retrieve simulation",
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


def _simulation_not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Simulation not found",
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


@router.get(
    "/portfolios/{portfolio_id}/simulations",
    response_model=SimulationHistoryListResponse,
    status_code=status.HTTP_200_OK,
)
def list_simulation_history(
    portfolio_id: UUID,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> SimulationHistoryListResponse:
    """Return immutable simulation metadata for one owned portfolio."""
    try:
        history = SimulationHistoryService(session).list_for_portfolio(
            user_id=current_user.id,
            portfolio_id=portfolio_id,
        )
    except Exception as error:
        raise _history_internal_error() from error

    if history is None:
        raise _portfolio_not_found()
    return history


@router.get(
    "/portfolios/{portfolio_id}/simulations/{simulation_id}",
    response_model=SimulationHistoryDetailResponse,
    status_code=status.HTTP_200_OK,
)
def get_simulation_history(
    portfolio_id: UUID,
    simulation_id: UUID,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> SimulationHistoryDetailResponse:
    """Return one validated immutable simulation for an owned portfolio."""
    try:
        simulation = SimulationHistoryService(session).get(
            user_id=current_user.id,
            portfolio_id=portfolio_id,
            simulation_id=simulation_id,
        )
    except SimulationNotFoundError as error:
        raise _simulation_not_found() from error
    except Exception as error:
        raise _history_detail_internal_error() from error

    if simulation is None:
        raise _portfolio_not_found()
    return simulation


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
    """Run one scenario for the authenticated user's portfolio."""
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

    try:
        history = SimulationHistoryService(session).save(
            user_id=current_user.id,
            portfolio_id=portfolio_id,
            simulation_type="historical-scenario",
            scenario_id=response.scenario.id,
            requested_start_date=response.scenario.requested_start_date,
            requested_end_date=response.scenario.requested_end_date,
            response=response,
        )
        if history is None:
            raise _portfolio_not_found()
        session.commit()
    except HTTPException:
        raise
    except Exception as error:
        raise _internal_error() from error
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

    try:
        history = SimulationHistoryService(session).save(
            user_id=current_user.id,
            portfolio_id=portfolio_id,
            simulation_type="allocation",
            scenario_id=None,
            requested_start_date=response.start_date,
            requested_end_date=response.end_date,
            response=response,
        )
        if history is None:
            raise _portfolio_not_found()
        session.commit()
    except HTTPException:
        raise
    except Exception as error:
        raise _allocation_internal_error() from error
    return response


@router.post(
    "/portfolios/{portfolio_id}/simulations/combined",
    response_model=CombinedSimulationResponse,
    status_code=status.HTTP_200_OK,
)
def run_combined_simulation(
    portfolio_id: UUID,
    request: CombinedSimulationRequest,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> CombinedSimulationResponse:
    """Compare allocations during one scenario for an owned portfolio."""
    try:
        response = CombinedSimulationService(session).run(
            user_id=current_user.id,
            portfolio_id=portfolio_id,
            request=request,
        )
    except HistoricalScenarioNotFoundError as error:
        raise _scenario_not_found() from error
    except (
        AllocationSymbolMismatchError,
        AllocationEmptyPortfolioError,
    ) as error:
        raise _unprocessable_historical_input(str(error)) from error
    except ValueError as error:
        if _is_expected_historical_data_error(error):
            raise _unprocessable_historical_input(str(error)) from error
        raise _combined_internal_error() from error
    except Exception as error:
        raise _combined_internal_error() from error

    if response is None:
        raise _portfolio_not_found()

    try:
        history = SimulationHistoryService(session).save(
            user_id=current_user.id,
            portfolio_id=portfolio_id,
            simulation_type="combined",
            scenario_id=response.scenario.id,
            requested_start_date=response.scenario.requested_start_date,
            requested_end_date=response.scenario.requested_end_date,
            response=response,
        )
        if history is None:
            raise _portfolio_not_found()
        session.commit()
    except HTTPException:
        raise
    except Exception as error:
        raise _combined_internal_error() from error
    return response
