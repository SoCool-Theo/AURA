"""Read-only orchestration and mapping for allocation simulations."""

from collections.abc import Mapping
from datetime import UTC, date, datetime
from uuid import UUID

import pandas as pd
from sqlalchemy.orm import Session

from ..scenarios.simulator import (
    AllocationComparisonResult,
    HistoricalSimulationResult,
    simulate_allocation_change,
)
from ..schemas.simulation import (
    AllocationSimulationRequest,
    AllocationSimulationResponse,
)
from .analysis_service import _build_price_frame
from .market_data_service import MarketDataService
from .portfolio_baseline_resolver import PortfolioBaselineResolutionService
from .portfolio_service import PortfolioService
from .portfolio_valuation_service import PortfolioDisplayCurrency
from .simulation_execution import SimulationExecutionResult


class AllocationSymbolMismatchError(ValueError):
    """Raised when modified symbols differ from the saved portfolio."""


class EmptyPortfolioError(ValueError):
    """Raised when an owned portfolio has no saved holdings to simulate."""


def _optional_timestamp_date(value: pd.Timestamp | None) -> date | None:
    return None if value is None else value.date()


def _simulation_result_payload(
    result: HistoricalSimulationResult,
    allocation: Mapping[str, float],
) -> dict[str, object]:
    """Map one pure result and ordered allocation to schema-ready values."""
    return {
        "allocation": [
            {"symbol": symbol, "weight": weight}
            for symbol, weight in allocation.items()
        ],
        "metrics": {
            "normalized_starting_value": result.normalized_starting_value,
            "normalized_ending_value": result.normalized_ending_value,
            "cumulative_return": result.cumulative_return,
            "annualized_volatility": result.annualized_volatility,
            "sharpe_ratio": result.sharpe_ratio,
            "maximum_drawdown": {
                "max_drawdown": result.maximum_drawdown.max_drawdown,
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


def _map_allocation_simulation_response(
    *,
    portfolio_id: UUID,
    portfolio_name: str,
    request: AllocationSimulationRequest,
    original_weights: Mapping[str, float],
    modified_weights: Mapping[str, float],
    result: AllocationComparisonResult,
) -> AllocationSimulationResponse:
    """Map pure comparison values into Aura's validated response contract."""
    return AllocationSimulationResponse.model_validate(
        {
            "portfolio_id": portfolio_id,
            "portfolio_name": portfolio_name,
            "start_date": request.start_date,
            "end_date": request.end_date,
            "metadata": {
                "effective_start_date": result.original.effective_start_date.date(),
                "effective_end_date": result.original.effective_end_date.date(),
                "price_observation_count": (
                    result.original.price_observation_count
                ),
                "return_observation_count": (
                    result.original.return_observation_count
                ),
            },
            "original": _simulation_result_payload(
                result.original,
                original_weights,
            ),
            "modified": _simulation_result_payload(
                result.modified,
                modified_weights,
            ),
            "comparison": {
                "normalized_ending_value_delta": (
                    result.normalized_ending_value_delta
                ),
                "cumulative_return_delta": result.cumulative_return_delta,
                "annualized_volatility_delta": (
                    result.annualized_volatility_delta
                ),
                "sharpe_ratio_delta": result.sharpe_ratio_delta,
                "maximum_drawdown_delta": result.maximum_drawdown_delta,
            },
        }
    )


class AllocationSimulationService:
    """Coordinate owned allocation simulations without transactions."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._portfolio_service = PortfolioService(session)
        self._market_data_service = MarketDataService(session)
        self._baseline_resolver = PortfolioBaselineResolutionService(session)

    def run(
        self,
        *,
        user_id: UUID,
        portfolio_id: UUID,
        request: AllocationSimulationRequest,
        valuation_date: date | None = None,
    ) -> AllocationSimulationResponse | None:
        """Compare saved and modified allocations over one historical frame."""
        execution = self.run_with_context(
            user_id=user_id,
            portfolio_id=portfolio_id,
            request=request,
            valuation_date=valuation_date or datetime.now(UTC).date(),
        )
        return None if execution is None else execution.response

    def run_with_context(
        self,
        *,
        user_id: UUID,
        portfolio_id: UUID,
        request: AllocationSimulationRequest,
        valuation_date: date,
    ) -> SimulationExecutionResult[AllocationSimulationResponse] | None:
        """Compare allocations and retain the resolved original baseline."""
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

        symbols = [holding.symbol for holding in holdings]
        modified_by_symbol = {
            holding.symbol: float(holding.weight)
            for holding in request.modified_allocation
        }
        if set(modified_by_symbol) != set(symbols):
            raise AllocationSymbolMismatchError(
                "modified allocation symbols must exactly match "
                "saved portfolio symbols"
            )

        baseline = self._baseline_resolver.resolve(
            portfolio=portfolio,
            valuation_date=valuation_date,
            display_currency=PortfolioDisplayCurrency.USD,
        )
        original_weights = {
            holding.symbol: float(holding.weight)
            for holding in baseline.resolved_weights
        }
        modified_weights = {
            symbol: modified_by_symbol[symbol]
            for symbol in symbols
        }
        records = self._market_data_service.get_range(
            symbols,
            request.start_date,
            request.end_date,
        )
        prices = _build_price_frame(records, symbols)
        result = simulate_allocation_change(
            prices,
            original_weights,
            modified_weights,
        )
        return SimulationExecutionResult(
            response=_map_allocation_simulation_response(
                portfolio_id=portfolio.id,
                portfolio_name=portfolio.name,
                request=request,
                original_weights=original_weights,
                modified_weights=modified_weights,
                result=result,
            ),
            baseline=baseline,
        )


__all__ = [
    "AllocationSymbolMismatchError",
    "EmptyPortfolioError",
    "AllocationSimulationService",
]
