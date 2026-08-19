"""Read-only orchestration and mapping for historical scenario simulation."""

from datetime import date
from uuid import UUID

import pandas as pd
from sqlalchemy.orm import Session

from ..scenarios.definitions import (
    HistoricalScenarioDefinition,
    get_historical_scenario,
)
from ..scenarios.simulator import (
    HistoricalSimulationResult,
    simulate_historical_scenario,
)
from ..schemas.simulation import (
    HistoricalScenarioSimulationRequest,
    HistoricalScenarioSimulationResponse,
)
from .analysis_service import _build_price_frame
from .market_data_service import MarketDataService
from .portfolio_service import PortfolioService


class HistoricalScenarioNotFoundError(Exception):
    """Raised when a requested predefined historical scenario is unknown."""


class EmptyPortfolioError(ValueError):
    """Raised when an owned portfolio has no saved holdings to simulate."""


def _optional_timestamp_date(value: pd.Timestamp | None) -> date | None:
    return None if value is None else value.date()


def _map_historical_scenario_response(
    *,
    portfolio_id: UUID,
    portfolio_name: str,
    scenario: HistoricalScenarioDefinition,
    result: HistoricalSimulationResult,
) -> HistoricalScenarioSimulationResponse:
    """Map pure domain values into Aura's validated simulation contract."""
    return HistoricalScenarioSimulationResponse.model_validate(
        {
            "portfolio_id": portfolio_id,
            "portfolio_name": portfolio_name,
            "scenario": {
                "id": scenario.id,
                "display_name": scenario.display_name,
                "description": scenario.description,
                "requested_start_date": scenario.requested_start_date,
                "requested_end_date": scenario.requested_end_date,
            },
            "metadata": {
                "effective_start_date": result.effective_start_date.date(),
                "effective_end_date": result.effective_end_date.date(),
                "price_observation_count": result.price_observation_count,
                "return_observation_count": result.return_observation_count,
            },
            "metrics": {
                "normalized_starting_value": (
                    result.normalized_starting_value
                ),
                "normalized_ending_value": result.normalized_ending_value,
                "cumulative_return": result.cumulative_return,
                "annualized_volatility": result.annualized_volatility,
                "sharpe_ratio": result.sharpe_ratio,
                "maximum_drawdown": {
                    "max_drawdown": (
                        result.maximum_drawdown.max_drawdown
                    ),
                    "peak_date": _optional_timestamp_date(
                        result.maximum_drawdown.peak_date
                    ),
                    "trough_date": _optional_timestamp_date(
                        result.maximum_drawdown.trough_date
                    ),
                },
            },
            "trajectory": [
                {
                    "date": point.date.date(),
                    "normalized_value": point.normalized_value,
                }
                for point in result.trajectory
            ],
        }
    )


class HistoricalScenarioService:
    """Coordinate owned historical simulations without managing transactions."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._portfolio_service = PortfolioService(session)
        self._market_data_service = MarketDataService(session)

    def run(
        self,
        *,
        user_id: UUID,
        portfolio_id: UUID,
        request: HistoricalScenarioSimulationRequest,
    ) -> HistoricalScenarioSimulationResponse | None:
        """Run one predefined scenario for an owned saved portfolio."""
        portfolio = self._portfolio_service.get(
            user_id=user_id,
            portfolio_id=portfolio_id,
        )
        if portfolio is None:
            return None

        holdings = tuple(portfolio.holdings)
        if not holdings:
            raise EmptyPortfolioError(
                "portfolio must contain at least one holding"
            )

        scenario = get_historical_scenario(request.scenario_id)
        if scenario is None:
            raise HistoricalScenarioNotFoundError(
                "Historical scenario not found"
            )

        symbols = [holding.symbol for holding in holdings]
        weights = {
            holding.symbol: float(holding.weight)
            for holding in holdings
        }
        records = self._market_data_service.get_range(
            symbols,
            scenario.requested_start_date,
            scenario.requested_end_date,
        )
        prices = _build_price_frame(records, symbols)
        result = simulate_historical_scenario(prices, weights)
        return _map_historical_scenario_response(
            portfolio_id=portfolio.id,
            portfolio_name=portfolio.name,
            scenario=scenario,
            result=result,
        )


__all__ = [
    "HistoricalScenarioNotFoundError",
    "EmptyPortfolioError",
    "HistoricalScenarioService",
]
