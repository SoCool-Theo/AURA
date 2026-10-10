from copy import deepcopy
from decimal import Decimal
import json
from unittest.mock import patch
from uuid import UUID

import pytest
from pydantic import ValidationError

from backend.app.database.models import Simulation
from backend.app.schemas.simulation_history import (
    SimulationHistoryV3DetailResponse,
)
from backend.app.services.market_data_service import MarketDataService
from backend.app.services.portfolio_baseline_resolver import (
    PortfolioBaselineKind,
    PortfolioBaselineResolution,
    ResolvedPortfolioWeight,
)
from backend.app.services.portfolio_valuation_service import (
    PortfolioValuationService,
)
from backend.app.services.portfolio_planned_allocation_service import (
    PlannedAllocationHolding,
    PlannedPortfolioAllocation,
)
from backend.app.services.simulation_history_mapper import (
    ALLOCATION_SIMULATION_RESPONSE_V3_SCHEMA_VERSION,
    COMBINED_SIMULATION_RESPONSE_V3_SCHEMA_VERSION,
    HISTORICAL_SCENARIO_SIMULATION_RESPONSE_V3_SCHEMA_VERSION,
    restore_simulation_snapshot,
    simulation_response_to_v3_snapshot,
    simulation_snapshot_to_response,
)
from backend.tests.unit.services.test_simulation_history_mapper import (
    _response_for_type,
)
from backend.tests.unit.services.test_simulation_history_service import (
    _CREATED_AT,
    _SIMULATION_ID,
    _metadata_for_type,
    _portfolio,
    _service_with_dependencies,
)


_V3_VERSION_BY_TYPE = {
    "historical-scenario": (
        HISTORICAL_SCENARIO_SIMULATION_RESPONSE_V3_SCHEMA_VERSION
    ),
    "allocation": ALLOCATION_SIMULATION_RESPONSE_V3_SCHEMA_VERSION,
    "combined": COMBINED_SIMULATION_RESPONSE_V3_SCHEMA_VERSION,
}


def _planned_baseline() -> PortfolioBaselineResolution:
    allocation = PlannedPortfolioAllocation(
        portfolio_id=UUID("62000000-0000-0000-0000-000000000001"),
        plan_currency="USD",
        total_proposed_amount=Decimal("1000"),
        holdings=(
            PlannedAllocationHolding(
                holding_id=UUID(
                    "63000000-0000-0000-0000-000000000001"
                ),
                symbol="MSFT",
                proposed_amount=Decimal("600"),
                target_allocation=Decimal("0.600000000000"),
                position=0,
            ),
            PlannedAllocationHolding(
                holding_id=UUID(
                    "63000000-0000-0000-0000-000000000002"
                ),
                symbol="AAPL",
                proposed_amount=Decimal("400"),
                target_allocation=Decimal("0.400000000000"),
                position=1,
            ),
        ),
    )
    return PortfolioBaselineResolution(
        baseline_kind=PortfolioBaselineKind.PLANNED,
        resolved_weights=(
            ResolvedPortfolioWeight(
                symbol="MSFT",
                weight=Decimal("0.600000000000"),
            ),
            ResolvedPortfolioWeight(
                symbol="AAPL",
                weight=Decimal("0.400000000000"),
            ),
        ),
        valuation=None,
        valuation_as_of=None,
        planned_allocation=allocation,
    )


@pytest.mark.parametrize(
    "simulation_type",
    ["historical-scenario", "allocation", "combined"],
)
def test_v3_mapper_freezes_complete_result_and_planned_baseline(
    simulation_type: str,
) -> None:
    response = _response_for_type(simulation_type)
    before = response.model_dump(mode="python")
    allocation = _planned_baseline().planned_allocation
    assert allocation is not None

    snapshot = simulation_response_to_v3_snapshot(
        simulation_type=simulation_type,
        response=response,
        planned_allocation=allocation,
    )

    assert snapshot["schema_version"] == _V3_VERSION_BY_TYPE[simulation_type]
    assert snapshot["result"] == response.model_dump(mode="json")
    assert snapshot["baseline"] == {
        "portfolio_type": "PLANNED",
        "baseline_source": "proposed-amount-target-allocation",
        "plan_currency": "USD",
        "total_proposed_amount": "1000",
        "hypothetical_notice": (
            "Hypothetical historical analysis only; not a forecast, "
            "recommendation, or executable order."
        ),
        "holdings": [
            {
                "id": str(holding.holding_id),
                "symbol": holding.symbol,
                "proposed_amount": str(holding.proposed_amount),
                "target_allocation": str(holding.target_allocation),
                "position": holding.position,
            }
            for holding in allocation.holdings
        ],
    }
    assert "estimated_shares" not in snapshot["baseline"]["holdings"][0]
    json.dumps(snapshot, allow_nan=False)
    assert response.model_dump(mode="python") == before

    restored = restore_simulation_snapshot(
        simulation_type=simulation_type,
        schema_version=_V3_VERSION_BY_TYPE[simulation_type],
        snapshot=snapshot,
    )
    assert restored.response == response
    assert restored.baseline is not None
    assert restored.baseline.portfolio_type == "PLANNED"
    assert restored.baseline.total_proposed_amount == Decimal("1000")
    assert simulation_snapshot_to_response(
        simulation_type=simulation_type,
        schema_version=_V3_VERSION_BY_TYPE[simulation_type],
        snapshot=snapshot,
    ) == response


def test_v3_mapper_rejects_malformed_and_cross_type_snapshots() -> None:
    response = _response_for_type("allocation")
    allocation = _planned_baseline().planned_allocation
    assert allocation is not None
    snapshot = simulation_response_to_v3_snapshot(
        simulation_type="allocation",
        response=response,
        planned_allocation=allocation,
    )
    malformed = deepcopy(snapshot)
    malformed["baseline"]["holdings"][0]["proposed_amount"] = "0"

    with pytest.raises(ValidationError):
        restore_simulation_snapshot(
            simulation_type="allocation",
            schema_version=ALLOCATION_SIMULATION_RESPONSE_V3_SCHEMA_VERSION,
            snapshot=malformed,
        )

    with pytest.raises(ValueError, match="do not match"):
        restore_simulation_snapshot(
            simulation_type="combined",
            schema_version=ALLOCATION_SIMULATION_RESPONSE_V3_SCHEMA_VERSION,
            snapshot=snapshot,
        )


def test_v3_restore_rejects_original_allocation_that_differs_from_plan() -> None:
    response = _response_for_type("allocation")
    allocation = _planned_baseline().planned_allocation
    assert allocation is not None
    snapshot = simulation_response_to_v3_snapshot(
        simulation_type="allocation",
        response=response,
        planned_allocation=allocation,
    )
    snapshot["baseline"]["holdings"][0]["proposed_amount"] = "500"
    snapshot["baseline"]["holdings"][0]["target_allocation"] = "0.5"
    snapshot["baseline"]["holdings"][1]["proposed_amount"] = "500"
    snapshot["baseline"]["holdings"][1]["target_allocation"] = "0.5"

    with pytest.raises(
        ValidationError,
        match="baseline weight does not match original allocation",
    ):
        restore_simulation_snapshot(
            simulation_type="allocation",
            schema_version=ALLOCATION_SIMULATION_RESPONSE_V3_SCHEMA_VERSION,
            snapshot=snapshot,
        )


@pytest.mark.parametrize(
    "simulation_type",
    ["historical-scenario", "allocation", "combined"],
)
def test_planned_save_creates_v3_and_returns_immutable_detail(
    simulation_type: str,
) -> None:
    service, session, portfolio_service, repository = _service_with_dependencies()
    portfolio = _portfolio()
    portfolio_service.get.return_value = portfolio
    response = _response_for_type(simulation_type)
    scenario_id, start_date, end_date = _metadata_for_type(simulation_type)
    baseline = _planned_baseline()

    def persist(**kwargs: object) -> Simulation:
        return Simulation(
            id=_SIMULATION_ID,
            created_at=_CREATED_AT,
            **kwargs,
        )

    repository.create.side_effect = persist

    detail = service.save(
        user_id=portfolio.user_id,
        portfolio_id=portfolio.id,
        simulation_type=simulation_type,  # type: ignore[arg-type]
        scenario_id=scenario_id,
        requested_start_date=start_date,
        requested_end_date=end_date,
        response=response,
        baseline=baseline,
    )

    assert isinstance(detail, SimulationHistoryV3DetailResponse)
    assert detail.schema_version == _V3_VERSION_BY_TYPE[simulation_type]
    assert detail.result == response
    assert detail.baseline.plan_currency == "USD"
    assert detail.baseline.total_proposed_amount == Decimal("1000")
    saved = repository.create.call_args.kwargs
    assert saved["schema_version"] == _V3_VERSION_BY_TYPE[simulation_type]
    assert saved["result_snapshot"]["baseline"] == detail.baseline.model_dump(
        mode="json"
    )
    session.commit.assert_not_called()
    session.rollback.assert_not_called()
    session.close.assert_not_called()


def test_v3_get_uses_only_frozen_snapshot_after_plan_and_prices_change() -> None:
    service, session, portfolio_service, repository = _service_with_dependencies()
    portfolio = _portfolio()
    portfolio_service.get.return_value = portfolio
    response = _response_for_type("allocation")
    allocation = _planned_baseline().planned_allocation
    assert allocation is not None
    snapshot = simulation_response_to_v3_snapshot(
        simulation_type="allocation",
        response=response,
        planned_allocation=allocation,
    )
    repository.get_for_portfolio.return_value = Simulation(
        id=_SIMULATION_ID,
        portfolio_id=portfolio.id,
        simulation_type="allocation",
        scenario_id=None,
        requested_start_date=response.start_date,
        requested_end_date=response.end_date,
        schema_version=ALLOCATION_SIMULATION_RESPONSE_V3_SCHEMA_VERSION,
        result_snapshot=snapshot,
        created_at=_CREATED_AT,
    )

    with (
        patch.object(
            PortfolioValuationService,
            "value",
            side_effect=AssertionError("history GET attempted revaluation"),
        ) as revalue,
        patch.object(
            MarketDataService,
            "get_latest_usd_asset_observations",
            side_effect=AssertionError("history GET queried current prices"),
        ) as current_prices,
    ):
        detail = service.get(
            user_id=portfolio.user_id,
            portfolio_id=portfolio.id,
            simulation_id=_SIMULATION_ID,
        )

    assert isinstance(detail, SimulationHistoryV3DetailResponse)
    assert detail.result == response
    assert detail.baseline.model_dump(mode="json") == snapshot["baseline"]
    revalue.assert_not_called()
    current_prices.assert_not_called()
    session.commit.assert_not_called()
    session.rollback.assert_not_called()
    session.close.assert_not_called()
