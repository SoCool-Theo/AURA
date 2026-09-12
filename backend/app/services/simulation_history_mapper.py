"""Pure serialization and validation for simulation-history snapshots."""

from copy import deepcopy
from dataclasses import dataclass
from datetime import date
from types import MappingProxyType
from typing import Any, Mapping
from uuid import UUID

from ..schemas.simulation import (
    AllocationSimulationResponse,
    CombinedSimulationResponse,
    HistoricalScenarioSimulationResponse,
)
from ..schemas.simulation_history import (
    AllocationSimulationV2Snapshot,
    CombinedSimulationV2Snapshot,
    HistoricalScenarioSimulationV2Snapshot,
    SimulationBaselineHolding,
    SimulationBaselineValuationContext,
    SimulationHistoryResult,
)
from .portfolio_valuation_service import (
    PortfolioDisplayCurrency,
    PortfolioValuationResult,
)


HISTORICAL_SCENARIO_SIMULATION_RESPONSE_SCHEMA_VERSION = (
    "historical-scenario-simulation-response-v1"
)
ALLOCATION_SIMULATION_RESPONSE_SCHEMA_VERSION = (
    "allocation-simulation-response-v1"
)
COMBINED_SIMULATION_RESPONSE_SCHEMA_VERSION = (
    "combined-simulation-response-v1"
)
HISTORICAL_SCENARIO_SIMULATION_RESPONSE_V2_SCHEMA_VERSION = (
    "historical-scenario-simulation-response-v2"
)
ALLOCATION_SIMULATION_RESPONSE_V2_SCHEMA_VERSION = (
    "allocation-simulation-response-v2"
)
COMBINED_SIMULATION_RESPONSE_V2_SCHEMA_VERSION = (
    "combined-simulation-response-v2"
)

SIMULATION_SCHEMA_VERSIONS: Mapping[str, str] = MappingProxyType(
    {
        "historical-scenario": (
            HISTORICAL_SCENARIO_SIMULATION_RESPONSE_SCHEMA_VERSION
        ),
        "allocation": ALLOCATION_SIMULATION_RESPONSE_SCHEMA_VERSION,
        "combined": COMBINED_SIMULATION_RESPONSE_SCHEMA_VERSION,
    }
)
SIMULATION_V2_SCHEMA_VERSIONS: Mapping[str, str] = MappingProxyType(
    {
        "historical-scenario": (
            HISTORICAL_SCENARIO_SIMULATION_RESPONSE_V2_SCHEMA_VERSION
        ),
        "allocation": ALLOCATION_SIMULATION_RESPONSE_V2_SCHEMA_VERSION,
        "combined": COMBINED_SIMULATION_RESPONSE_V2_SCHEMA_VERSION,
    }
)

_RESPONSE_SCHEMAS: Mapping[
    str,
    type[SimulationHistoryResult],
] = MappingProxyType(
    {
        "historical-scenario": HistoricalScenarioSimulationResponse,
        "allocation": AllocationSimulationResponse,
        "combined": CombinedSimulationResponse,
    }
)
_SUPPORTED_SCHEMA_VERSIONS = frozenset(SIMULATION_SCHEMA_VERSIONS.values())
_SUPPORTED_V2_SCHEMA_VERSIONS = frozenset(
    SIMULATION_V2_SCHEMA_VERSIONS.values()
)
_V2_SNAPSHOT_SCHEMAS = MappingProxyType(
    {
        "historical-scenario": HistoricalScenarioSimulationV2Snapshot,
        "allocation": AllocationSimulationV2Snapshot,
        "combined": CombinedSimulationV2Snapshot,
    }
)


@dataclass(frozen=True, slots=True)
class RestoredSimulationSnapshot:
    """Validated result plus optional immutable real-baseline context."""

    response: SimulationHistoryResult
    baseline: SimulationBaselineValuationContext | None
    schema_version: str


def simulation_type_to_schema_version(simulation_type: str) -> str:
    """Return the approved schema version for one simulation type."""
    try:
        return SIMULATION_SCHEMA_VERSIONS[simulation_type]
    except KeyError as error:
        raise ValueError(
            f"unsupported simulation type: {simulation_type!r}"
        ) from error


def simulation_type_to_v2_schema_version(simulation_type: str) -> str:
    """Return the approved V2 schema version for one simulation type."""
    try:
        return SIMULATION_V2_SCHEMA_VERSIONS[simulation_type]
    except KeyError as error:
        raise ValueError(
            f"unsupported simulation type: {simulation_type!r}"
        ) from error


def _response_schema_for_type(
    simulation_type: str,
) -> type[SimulationHistoryResult]:
    try:
        return _RESPONSE_SCHEMAS[simulation_type]
    except KeyError as error:
        raise ValueError(
            f"unsupported simulation type: {simulation_type!r}"
        ) from error


def _response_schema_for_snapshot(
    *,
    simulation_type: str,
    schema_version: str,
) -> type[SimulationHistoryResult]:
    expected_v1 = simulation_type_to_schema_version(simulation_type)
    expected_v2 = simulation_type_to_v2_schema_version(simulation_type)
    if schema_version not in (
        _SUPPORTED_SCHEMA_VERSIONS | _SUPPORTED_V2_SCHEMA_VERSIONS
    ):
        raise ValueError(
            "unsupported simulation snapshot schema version: "
            f"{schema_version!r}"
        )
    if schema_version not in {expected_v1, expected_v2}:
        raise ValueError(
            "simulation type and schema version do not match: "
            f"{simulation_type!r}, {schema_version!r}"
        )
    return _response_schema_for_type(simulation_type)


def simulation_response_to_snapshot(
    *,
    simulation_type: str,
    response: SimulationHistoryResult,
) -> dict[str, Any]:
    """Serialize one exact validated response to a detached JSON snapshot."""
    expected_type = _response_schema_for_type(simulation_type)
    if not isinstance(response, expected_type):
        raise ValueError(
            "simulation response type does not match simulation_type"
        )
    return deepcopy(response.model_dump(mode="json"))


def simulation_response_to_v2_snapshot(
    *,
    simulation_type: str,
    response: SimulationHistoryResult,
    valuation: PortfolioValuationResult,
) -> dict[str, Any]:
    """Serialize authoritative result and real USD baseline without formulas."""
    expected_type = _response_schema_for_type(simulation_type)
    if not isinstance(response, expected_type):
        raise ValueError(
            "simulation response type does not match simulation_type"
        )
    if (
        valuation.display_currency is not PortfolioDisplayCurrency.USD
        or valuation.fx_context is not None
    ):
        raise ValueError("simulation V2 baseline requires USD without FX")

    baseline = SimulationBaselineValuationContext(
        valuation_currency="USD",
        valuation_date=valuation.requested_date,
        oldest_price_as_of=valuation.oldest_price_as_of,
        newest_price_as_of=valuation.newest_price_as_of,
        total_current_value_usd=valuation.total_current_value_usd,
        holdings=[
            SimulationBaselineHolding(
                id=holding.holding_id,
                symbol=holding.symbol,
                invested_amount=holding.invested_amount,
                invested_currency=holding.invested_currency,
                shares=holding.shares,
                purchase_date=holding.purchase_date,
                position=holding.position,
                asset_price=holding.asset_price,
                asset_quote_currency=holding.asset_quote_currency,
                price_as_of=holding.price_as_of,
                current_value_usd=holding.current_value_usd,
                current_allocation=holding.current_allocation,
            )
            for holding in valuation.holdings
        ],
    )
    snapshot_schema = _V2_SNAPSHOT_SCHEMAS[simulation_type]
    snapshot = snapshot_schema(
        schema_version=simulation_type_to_v2_schema_version(simulation_type),
        result=response,
        baseline=baseline,
    )
    return deepcopy(snapshot.model_dump(mode="json"))


def restore_simulation_snapshot(
    *,
    simulation_type: str,
    schema_version: str,
    snapshot: Mapping[str, Any],
) -> RestoredSimulationSnapshot:
    """Revalidate one V1 or V2 snapshot through its exact contract."""
    response_schema = _response_schema_for_snapshot(
        simulation_type=simulation_type,
        schema_version=schema_version,
    )
    payload = deepcopy(dict(snapshot))
    if schema_version in _SUPPORTED_SCHEMA_VERSIONS:
        return RestoredSimulationSnapshot(
            response=response_schema.model_validate(payload),
            baseline=None,
            schema_version=schema_version,
        )

    snapshot_schema = _V2_SNAPSHOT_SCHEMAS[simulation_type]
    validated = snapshot_schema.model_validate(payload)
    return RestoredSimulationSnapshot(
        response=validated.result,
        baseline=validated.baseline,
        schema_version=schema_version,
    )


def simulation_snapshot_to_response(
    *,
    simulation_type: str,
    schema_version: str,
    snapshot: Mapping[str, Any],
) -> SimulationHistoryResult:
    """Revalidate a detached snapshot through exactly one response schema."""
    restored = restore_simulation_snapshot(
        simulation_type=simulation_type,
        schema_version=schema_version,
        snapshot=snapshot,
    )
    return restored.response


def validate_simulation_snapshot_consistency(
    *,
    simulation_type: str,
    response: SimulationHistoryResult,
    portfolio_id: UUID,
    scenario_id: str | None,
    requested_start_date: date,
    requested_end_date: date,
) -> None:
    """Check future relational metadata against a validated snapshot."""
    expected_type = _response_schema_for_type(simulation_type)
    if not isinstance(response, expected_type):
        raise ValueError(
            "simulation response type does not match simulation_type"
        )
    if response.portfolio_id != portfolio_id:
        raise ValueError(
            "simulation snapshot portfolio_id does not match relational "
            "portfolio_id"
        )

    if isinstance(response, AllocationSimulationResponse):
        if scenario_id is not None:
            raise ValueError(
                "relational scenario_id must be null for allocation "
                "simulations"
            )
        snapshot_scenario_id = None
        snapshot_start_date = response.start_date
        snapshot_end_date = response.end_date
    else:
        snapshot_scenario_id = response.scenario.id
        snapshot_start_date = response.scenario.requested_start_date
        snapshot_end_date = response.scenario.requested_end_date

    if snapshot_scenario_id != scenario_id:
        raise ValueError(
            "simulation snapshot scenario_id does not match relational "
            "scenario_id"
        )
    if snapshot_start_date != requested_start_date:
        raise ValueError(
            "simulation snapshot requested_start_date does not match "
            "relational requested_start_date"
        )
    if snapshot_end_date != requested_end_date:
        raise ValueError(
            "simulation snapshot requested_end_date does not match "
            "relational requested_end_date"
        )


__all__ = [
    "HISTORICAL_SCENARIO_SIMULATION_RESPONSE_SCHEMA_VERSION",
    "ALLOCATION_SIMULATION_RESPONSE_SCHEMA_VERSION",
    "COMBINED_SIMULATION_RESPONSE_SCHEMA_VERSION",
    "HISTORICAL_SCENARIO_SIMULATION_RESPONSE_V2_SCHEMA_VERSION",
    "ALLOCATION_SIMULATION_RESPONSE_V2_SCHEMA_VERSION",
    "COMBINED_SIMULATION_RESPONSE_V2_SCHEMA_VERSION",
    "SIMULATION_SCHEMA_VERSIONS",
    "SIMULATION_V2_SCHEMA_VERSIONS",
    "simulation_type_to_schema_version",
    "simulation_type_to_v2_schema_version",
    "simulation_response_to_snapshot",
    "simulation_response_to_v2_snapshot",
    "simulation_snapshot_to_response",
    "restore_simulation_snapshot",
    "RestoredSimulationSnapshot",
    "validate_simulation_snapshot_consistency",
]
