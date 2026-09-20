from copy import deepcopy
from decimal import Decimal
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from backend.app.database.models import Simulation
from backend.app.schemas.simulation_history import SimulationHistoryV2DetailResponse
from backend.app.services.market_data_service import MarketDataService
from backend.app.services.portfolio_baseline_resolver import (
    PortfolioBaselineKind,
    PortfolioBaselineResolution,
    ResolvedPortfolioWeight,
)
from backend.app.services.portfolio_valuation_service import (
    PortfolioValuationService,
)
from backend.app.services.simulation_history_mapper import (
    ALLOCATION_SIMULATION_RESPONSE_V2_SCHEMA_VERSION,
    COMBINED_SIMULATION_RESPONSE_V2_SCHEMA_VERSION,
    HISTORICAL_SCENARIO_SIMULATION_RESPONSE_V2_SCHEMA_VERSION,
    restore_simulation_snapshot,
    simulation_response_to_v2_snapshot,
    simulation_snapshot_to_response,
)
from backend.tests.unit.services.test_portfolio_analysis_preparation_service import (
    VALUATION_DATE,
    _valuation_result,
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


_V2_VERSION_BY_TYPE = {
    "historical-scenario": (
        HISTORICAL_SCENARIO_SIMULATION_RESPONSE_V2_SCHEMA_VERSION
    ),
    "allocation": ALLOCATION_SIMULATION_RESPONSE_V2_SCHEMA_VERSION,
    "combined": COMBINED_SIMULATION_RESPONSE_V2_SCHEMA_VERSION,
}


def _real_baseline() -> PortfolioBaselineResolution:
    valuation = _valuation_result()
    return PortfolioBaselineResolution(
        baseline_kind=PortfolioBaselineKind.REAL,
        resolved_weights=tuple(
            ResolvedPortfolioWeight(
                symbol=holding.symbol,
                weight=holding.current_allocation,
            )
            for holding in valuation.holdings
        ),
        valuation=valuation,
        valuation_as_of=VALUATION_DATE,
    )


@pytest.mark.parametrize(
    "simulation_type",
    ["historical-scenario", "allocation", "combined"],
)
def test_v2_mapper_preserves_complete_result_and_exact_usd_baseline(
    simulation_type: str,
) -> None:
    response = _response_for_type(simulation_type)
    before = response.model_dump(mode="python")
    valuation = _real_baseline().valuation
    assert valuation is not None

    snapshot = simulation_response_to_v2_snapshot(
        simulation_type=simulation_type,
        response=response,
        valuation=valuation,
    )

    assert snapshot["schema_version"] == _V2_VERSION_BY_TYPE[simulation_type]
    assert snapshot["result"] == response.model_dump(mode="json")
    assert snapshot["baseline"] == {
        "valuation_currency": "USD",
        "valuation_date": "2026-09-12",
        "oldest_price_as_of": "2026-09-12",
        "newest_price_as_of": "2026-09-12",
        "total_current_value_usd": "100",
        "holdings": [
            {
                "id": str(holding.holding_id),
                "symbol": holding.symbol,
                "invested_amount": str(holding.invested_amount),
                "invested_currency": holding.invested_currency,
                "shares": str(holding.shares),
                "purchase_date": holding.purchase_date.isoformat(),
                "position": holding.position,
                "asset_price": str(holding.asset_price),
                "asset_quote_currency": "USD",
                "price_as_of": holding.price_as_of.isoformat(),
                "current_value_usd": str(holding.current_value_usd),
                "current_allocation": str(holding.current_allocation),
            }
            for holding in valuation.holdings
        ],
    }
    assert "fx_context" not in snapshot["baseline"]
    assert "current_value" not in snapshot["baseline"]["holdings"][0]
    assert response.model_dump(mode="python") == before

    restored = restore_simulation_snapshot(
        simulation_type=simulation_type,
        schema_version=_V2_VERSION_BY_TYPE[simulation_type],
        snapshot=snapshot,
    )
    assert restored.response == response
    assert restored.baseline is not None
    assert restored.baseline.valuation_date == VALUATION_DATE
    assert [holding.current_allocation for holding in restored.baseline.holdings] == [
        Decimal("0.6000000000000000000000000000"),
        Decimal("0.4000000000000000000000000000"),
    ]
    assert simulation_snapshot_to_response(
        simulation_type=simulation_type,
        schema_version=_V2_VERSION_BY_TYPE[simulation_type],
        snapshot=snapshot,
    ) == response


def test_v2_mapper_rejects_malformed_and_cross_type_snapshots() -> None:
    response = _response_for_type("allocation")
    valuation = _real_baseline().valuation
    assert valuation is not None
    snapshot = simulation_response_to_v2_snapshot(
        simulation_type="allocation",
        response=response,
        valuation=valuation,
    )
    malformed = deepcopy(snapshot)
    malformed["baseline"]["holdings"] = []

    with pytest.raises(ValidationError):
        restore_simulation_snapshot(
            simulation_type="allocation",
            schema_version=ALLOCATION_SIMULATION_RESPONSE_V2_SCHEMA_VERSION,
            snapshot=malformed,
        )

    with pytest.raises(ValueError, match="do not match"):
        restore_simulation_snapshot(
            simulation_type="combined",
            schema_version=ALLOCATION_SIMULATION_RESPONSE_V2_SCHEMA_VERSION,
            snapshot=snapshot,
        )

    with pytest.raises(
        ValueError,
        match="unsupported simulation snapshot schema version",
    ):
        restore_simulation_snapshot(
            simulation_type="allocation",
            schema_version="allocation-simulation-response-v4",
            snapshot=snapshot,
        )


@pytest.mark.parametrize(
    "simulation_type",
    ["historical-scenario", "allocation", "combined"],
)
def test_real_save_creates_v2_and_returns_validated_immutable_detail(
    simulation_type: str,
) -> None:
    service, session, portfolio_service, repository = _service_with_dependencies()
    portfolio = _portfolio()
    portfolio_service.get.return_value = portfolio
    response = _response_for_type(simulation_type)
    scenario_id, start_date, end_date = _metadata_for_type(simulation_type)
    baseline = _real_baseline()

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

    assert isinstance(detail, SimulationHistoryV2DetailResponse)
    assert detail.schema_version == _V2_VERSION_BY_TYPE[simulation_type]
    assert detail.result == response
    assert detail.baseline.valuation_date == VALUATION_DATE
    assert detail.baseline.total_current_value_usd == Decimal("100")
    saved = repository.create.call_args.kwargs
    assert saved["schema_version"] == _V2_VERSION_BY_TYPE[simulation_type]
    assert saved["result_snapshot"]["result"] == response.model_dump(mode="json")
    assert saved["result_snapshot"]["baseline"] == detail.baseline.model_dump(
        mode="json"
    )
    session.commit.assert_not_called()
    session.rollback.assert_not_called()
    session.close.assert_not_called()


def test_v2_get_uses_only_saved_snapshot_after_external_prices_change() -> None:
    service, session, portfolio_service, repository = _service_with_dependencies()
    portfolio = _portfolio()
    portfolio_service.get.return_value = portfolio
    response = _response_for_type("allocation")
    valuation = _real_baseline().valuation
    assert valuation is not None
    snapshot = simulation_response_to_v2_snapshot(
        simulation_type="allocation",
        response=response,
        valuation=valuation,
    )
    repository.get_for_portfolio.return_value = Simulation(
        id=_SIMULATION_ID,
        portfolio_id=portfolio.id,
        simulation_type="allocation",
        scenario_id=None,
        requested_start_date=response.start_date,
        requested_end_date=response.end_date,
        schema_version=ALLOCATION_SIMULATION_RESPONSE_V2_SCHEMA_VERSION,
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

    assert isinstance(detail, SimulationHistoryV2DetailResponse)
    assert detail.result == response
    assert detail.baseline.model_dump(mode="json") == snapshot["baseline"]
    revalue.assert_not_called()
    current_prices.assert_not_called()
    session.commit.assert_not_called()
    session.rollback.assert_not_called()
    session.close.assert_not_called()
