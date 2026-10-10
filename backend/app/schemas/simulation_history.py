"""Strict contracts for immutable Aura simulation-history retrieval."""

from datetime import date
from decimal import Decimal
import math
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import (
    AwareDatetime,
    Field,
    Strict,
    field_validator,
    model_validator,
)

from .common import AssetSymbol, AuraBaseModel
from .portfolio import PlannedPortfolioBaselineContext
from .simulation import (
    AllocationSimulationResponse,
    CombinedSimulationResponse,
    HistoricalScenarioSimulationResponse,
    _validate_scenario_id,
)


SimulationType = Literal[
    "historical-scenario",
    "allocation",
    "combined",
]
SimulationHistoryResult = (
    HistoricalScenarioSimulationResponse
    | AllocationSimulationResponse
    | CombinedSimulationResponse
)
SimulationV2SchemaVersion = Literal[
    "historical-scenario-simulation-response-v2",
    "allocation-simulation-response-v2",
    "combined-simulation-response-v2",
]
SimulationV3SchemaVersion = Literal[
    "historical-scenario-simulation-response-v3",
    "allocation-simulation-response-v3",
    "combined-simulation-response-v3",
]
StrictString = Annotated[str, Strict()]
PositiveDecimal = Annotated[
    Decimal,
    Field(gt=Decimal("0"), allow_inf_nan=False),
]
AllocationDecimal = Annotated[
    Decimal,
    Field(ge=Decimal("0"), le=Decimal("1"), allow_inf_nan=False),
]


class SimulationBaselineHolding(AuraBaseModel):
    """One immutable USD-valued current holding used for a simulation baseline."""

    id: UUID | None
    symbol: AssetSymbol
    invested_amount: PositiveDecimal | None = None
    invested_currency: Literal["USD", "THB"] | None = None
    shares: PositiveDecimal
    purchase_date: date | None = None
    position: Annotated[int, Field(strict=True, ge=0)]
    asset_price: PositiveDecimal
    asset_quote_currency: Literal["USD"]
    price_as_of: date
    current_value_usd: PositiveDecimal
    current_allocation: AllocationDecimal

    @model_validator(mode="after")
    def validate_optional_investment_provenance(self) -> Self:
        provenance = (
            self.invested_amount,
            self.invested_currency,
            self.purchase_date,
        )
        if all(value is None for value in provenance) or all(
            value is not None for value in provenance
        ):
            return self
        raise ValueError(
            "simulation investment provenance must be either complete or absent"
        )


class SimulationBaselineValuationContext(AuraBaseModel):
    """Immutable canonical-USD valuation that produced original weights."""

    valuation_currency: Literal["USD"]
    valuation_date: date
    oldest_price_as_of: date
    newest_price_as_of: date
    total_current_value_usd: PositiveDecimal
    holdings: Annotated[list[SimulationBaselineHolding], Field(min_length=1)]

    @model_validator(mode="after")
    def validate_dates(self) -> Self:
        if self.oldest_price_as_of > self.newest_price_as_of:
            raise ValueError(
                "oldest_price_as_of must not be after newest_price_as_of"
            )
        if self.newest_price_as_of > self.valuation_date:
            raise ValueError(
                "price observation dates must not be after valuation_date"
            )
        return self


class HistoricalScenarioSimulationV2Snapshot(AuraBaseModel):
    """V2 historical-scenario result with its immutable real baseline."""

    schema_version: Literal["historical-scenario-simulation-response-v2"]
    result: HistoricalScenarioSimulationResponse
    baseline: SimulationBaselineValuationContext


class AllocationSimulationV2Snapshot(AuraBaseModel):
    """V2 allocation result with its immutable real baseline."""

    schema_version: Literal["allocation-simulation-response-v2"]
    result: AllocationSimulationResponse
    baseline: SimulationBaselineValuationContext


class CombinedSimulationV2Snapshot(AuraBaseModel):
    """V2 combined result with its immutable real baseline."""

    schema_version: Literal["combined-simulation-response-v2"]
    result: CombinedSimulationResponse
    baseline: SimulationBaselineValuationContext


def _validate_planned_original_allocation(
    result: AllocationSimulationResponse | CombinedSimulationResponse,
    baseline: PlannedPortfolioBaselineContext,
) -> None:
    original_by_symbol = {
        holding.symbol: holding for holding in result.original.allocation
    }
    baseline_symbols = [holding.symbol for holding in baseline.holdings]
    if set(original_by_symbol) != set(baseline_symbols):
        raise ValueError(
            "planned simulation baseline symbols do not match original allocation"
        )
    for holding in baseline.holdings:
        if not math.isclose(
            original_by_symbol[holding.symbol].weight,
            float(holding.target_allocation),
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            raise ValueError(
                "planned simulation baseline weight does not match original "
                f"allocation: {holding.symbol}"
            )


class HistoricalScenarioSimulationV3Snapshot(AuraBaseModel):
    """V3 historical-scenario result with its immutable planned baseline."""

    schema_version: Literal["historical-scenario-simulation-response-v3"]
    result: HistoricalScenarioSimulationResponse
    baseline: PlannedPortfolioBaselineContext


class AllocationSimulationV3Snapshot(AuraBaseModel):
    """V3 allocation result with its immutable planned baseline."""

    schema_version: Literal["allocation-simulation-response-v3"]
    result: AllocationSimulationResponse
    baseline: PlannedPortfolioBaselineContext

    @model_validator(mode="after")
    def validate_result_baseline(self) -> Self:
        _validate_planned_original_allocation(self.result, self.baseline)
        return self


class CombinedSimulationV3Snapshot(AuraBaseModel):
    """V3 combined result with its immutable planned baseline."""

    schema_version: Literal["combined-simulation-response-v3"]
    result: CombinedSimulationResponse
    baseline: PlannedPortfolioBaselineContext

    @model_validator(mode="after")
    def validate_result_baseline(self) -> Self:
        _validate_planned_original_allocation(self.result, self.baseline)
        return self


class SimulationHistorySummary(AuraBaseModel):
    """Relational metadata for one immutable simulation snapshot."""

    id: UUID
    portfolio_id: UUID
    simulation_type: SimulationType
    scenario_id: StrictString | None
    requested_start_date: date
    requested_end_date: date
    created_at: AwareDatetime

    @field_validator("scenario_id")
    @classmethod
    def validate_scenario_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _validate_scenario_id(value)

    @model_validator(mode="after")
    def validate_metadata(self) -> Self:
        if self.requested_start_date > self.requested_end_date:
            raise ValueError(
                "requested_start_date must be on or before "
                "requested_end_date"
            )

        if self.simulation_type == "allocation":
            if self.scenario_id is not None:
                raise ValueError(
                    "scenario_id must be null for allocation simulations"
                )
        elif self.scenario_id is None:
            raise ValueError(
                "scenario_id is required for historical-scenario and "
                "combined simulations"
            )
        return self


class SimulationHistoryListResponse(AuraBaseModel):
    """An ordered collection of simulation-history summaries."""

    simulations: list[SimulationHistorySummary]


class SimulationHistoryDetailResponse(SimulationHistorySummary):
    """Simulation-history metadata and its canonical validated result."""

    result: SimulationHistoryResult

    @model_validator(mode="after")
    def validate_result_type(self) -> Self:
        expected_type = {
            "historical-scenario": HistoricalScenarioSimulationResponse,
            "allocation": AllocationSimulationResponse,
            "combined": CombinedSimulationResponse,
        }[self.simulation_type]
        if not isinstance(self.result, expected_type):
            raise ValueError(
                "result response type does not match simulation_type"
            )
        return self


class SimulationHistoryV2DetailResponse(SimulationHistorySummary):
    """Real-holding history detail with its immutable USD baseline."""

    schema_version: SimulationV2SchemaVersion
    baseline: SimulationBaselineValuationContext
    result: SimulationHistoryResult

    @model_validator(mode="after")
    def validate_version_and_result_type(self) -> Self:
        expected = {
            "historical-scenario": (
                "historical-scenario-simulation-response-v2",
                HistoricalScenarioSimulationResponse,
            ),
            "allocation": (
                "allocation-simulation-response-v2",
                AllocationSimulationResponse,
            ),
            "combined": (
                "combined-simulation-response-v2",
                CombinedSimulationResponse,
            ),
        }[self.simulation_type]
        expected_version, expected_type = expected
        if self.schema_version != expected_version:
            raise ValueError(
                "simulation type and V2 schema version do not match"
            )
        if not isinstance(self.result, expected_type):
            raise ValueError(
                "result response type does not match simulation_type"
            )
        return self


class SimulationHistoryV3DetailResponse(SimulationHistorySummary):
    """Planned-portfolio history detail with its immutable target baseline."""

    schema_version: SimulationV3SchemaVersion
    baseline: PlannedPortfolioBaselineContext
    result: SimulationHistoryResult

    @model_validator(mode="after")
    def validate_version_and_result_type(self) -> Self:
        expected = {
            "historical-scenario": (
                "historical-scenario-simulation-response-v3",
                HistoricalScenarioSimulationResponse,
            ),
            "allocation": (
                "allocation-simulation-response-v3",
                AllocationSimulationResponse,
            ),
            "combined": (
                "combined-simulation-response-v3",
                CombinedSimulationResponse,
            ),
        }[self.simulation_type]
        expected_version, expected_type = expected
        if self.schema_version != expected_version:
            raise ValueError(
                "simulation type and V3 schema version do not match"
            )
        if not isinstance(self.result, expected_type):
            raise ValueError(
                "result response type does not match simulation_type"
            )
        if isinstance(
            self.result,
            (AllocationSimulationResponse, CombinedSimulationResponse),
        ):
            _validate_planned_original_allocation(
                self.result,
                self.baseline,
            )
        return self


SimulationHistoryDetail = (
    SimulationHistoryDetailResponse
    | SimulationHistoryV2DetailResponse
    | SimulationHistoryV3DetailResponse
)

__all__ = [
    "SimulationType",
    "SimulationHistoryResult",
    "SimulationHistorySummary",
    "SimulationHistoryListResponse",
    "SimulationHistoryDetailResponse",
    "SimulationHistoryV2DetailResponse",
    "SimulationHistoryV3DetailResponse",
    "SimulationHistoryDetail",
    "SimulationBaselineHolding",
    "SimulationBaselineValuationContext",
    "HistoricalScenarioSimulationV2Snapshot",
    "AllocationSimulationV2Snapshot",
    "CombinedSimulationV2Snapshot",
    "HistoricalScenarioSimulationV3Snapshot",
    "AllocationSimulationV3Snapshot",
    "CombinedSimulationV3Snapshot",
    "SimulationV2SchemaVersion",
    "SimulationV3SchemaVersion",
]
