from copy import deepcopy
from datetime import UTC, date, datetime, timedelta
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.database.models import Portfolio, Simulation
from backend.app.database.repositories import SimulationRepository
from backend.app.schemas.simulation import (
    AllocationSimulationResponse,
    CombinedSimulationResponse,
    HistoricalScenarioSimulationResponse,
)
from backend.app.schemas.simulation_history import (
    SimulationHistoryDetailResponse,
    SimulationHistoryListResponse,
)
from backend.app.services.portfolio_service import PortfolioService
from backend.app.services.simulation_history_mapper import (
    ALLOCATION_SIMULATION_RESPONSE_SCHEMA_VERSION,
    COMBINED_SIMULATION_RESPONSE_SCHEMA_VERSION,
    HISTORICAL_SCENARIO_SIMULATION_RESPONSE_SCHEMA_VERSION,
    simulation_response_to_snapshot,
)
from backend.app.services.simulation_history_service import (
    SimulationHistoryService,
    SimulationNotFoundError,
)
import backend.app.services.simulation_history_service as service_module
from backend.tests.unit.services.test_simulation_history_mapper import (
    _response_for_type,
)


_USER_ID = UUID("30000000-0000-0000-0000-000000000001")
_PORTFOLIO_ID = UUID("12345678-1234-5678-1234-567812345678")
_SIMULATION_ID = UUID("10000000-0000-0000-0000-000000000001")
_CREATED_AT = datetime(2026, 8, 20, 9, 30, tzinfo=UTC)
_SCHEMA_BY_TYPE = {
    "historical-scenario": (
        HISTORICAL_SCENARIO_SIMULATION_RESPONSE_SCHEMA_VERSION
    ),
    "allocation": ALLOCATION_SIMULATION_RESPONSE_SCHEMA_VERSION,
    "combined": COMBINED_SIMULATION_RESPONSE_SCHEMA_VERSION,
}


def _portfolio() -> Portfolio:
    return Portfolio(
        id=_PORTFOLIO_ID,
        user_id=_USER_ID,
        name="Balanced Learning Portfolio",
    )


def _metadata_for_type(
    simulation_type: str,
) -> tuple[str | None, date, date]:
    response = _response_for_type(simulation_type)
    if isinstance(response, AllocationSimulationResponse):
        return None, response.start_date, response.end_date
    return (
        response.scenario.id,
        response.scenario.requested_start_date,
        response.scenario.requested_end_date,
    )


def _record(
    simulation_type: str = "historical-scenario",
    *,
    simulation_id: UUID = _SIMULATION_ID,
    portfolio_id: UUID = _PORTFOLIO_ID,
    schema_version: str | None = None,
    snapshot: dict[str, object] | None = None,
    scenario_id: str | None | object = ...,
    requested_start_date: date | None = None,
    requested_end_date: date | None = None,
) -> Simulation:
    response = _response_for_type(
        simulation_type if simulation_type in _SCHEMA_BY_TYPE else "allocation"
    )
    default_scenario, default_start, default_end = _metadata_for_type(
        simulation_type if simulation_type in _SCHEMA_BY_TYPE else "allocation"
    )
    return Simulation(
        id=simulation_id,
        portfolio_id=portfolio_id,
        simulation_type=simulation_type,
        scenario_id=(default_scenario if scenario_id is ... else scenario_id),
        requested_start_date=requested_start_date or default_start,
        requested_end_date=requested_end_date or default_end,
        schema_version=(
            schema_version
            if schema_version is not None
            else _SCHEMA_BY_TYPE.get(simulation_type, "forecast-v1")
        ),
        result_snapshot=(
            snapshot
            if snapshot is not None
            else simulation_response_to_snapshot(
                simulation_type=(
                    simulation_type
                    if simulation_type in _SCHEMA_BY_TYPE
                    else "allocation"
                ),
                response=response,
            )
        ),
        created_at=_CREATED_AT,
    )


def _service_with_dependencies() -> tuple[
    SimulationHistoryService,
    MagicMock,
    MagicMock,
    MagicMock,
]:
    session = MagicMock(spec=Session)
    portfolio_service = MagicMock(spec=PortfolioService)
    repository = MagicMock(spec=SimulationRepository)
    with (
        patch.object(
            service_module,
            "PortfolioService",
            return_value=portfolio_service,
        ) as portfolio_service_type,
        patch.object(
            service_module,
            "SimulationRepository",
            return_value=repository,
        ) as repository_type,
    ):
        service = SimulationHistoryService(session)

    portfolio_service_type.assert_called_once_with(session)
    repository_type.assert_called_once_with(session)
    return service, session, portfolio_service, repository


def _assert_session_lifecycle_untouched(session: MagicMock) -> None:
    session.commit.assert_not_called()
    session.rollback.assert_not_called()
    session.close.assert_not_called()


@pytest.mark.parametrize(
    ("simulation_type", "response_type"),
    [
        ("historical-scenario", HistoricalScenarioSimulationResponse),
        ("allocation", AllocationSimulationResponse),
        ("combined", CombinedSimulationResponse),
    ],
)
def test_save_maps_validated_response_with_exact_metadata_and_version(
    simulation_type: str,
    response_type: type,
) -> None:
    service, session, portfolio_service, repository = (
        _service_with_dependencies()
    )
    portfolio_service.get.return_value = _portfolio()
    response = _response_for_type(simulation_type)
    response_before = response.model_dump(mode="python")
    scenario_id, start, end = _metadata_for_type(simulation_type)

    def persist(**kwargs: object) -> Simulation:
        return Simulation(
            id=_SIMULATION_ID,
            created_at=_CREATED_AT,
            **kwargs,
        )

    repository.create.side_effect = persist

    result = service.save(
        user_id=_USER_ID,
        portfolio_id=_PORTFOLIO_ID,
        simulation_type=simulation_type,  # type: ignore[arg-type]
        scenario_id=scenario_id,
        requested_start_date=start,
        requested_end_date=end,
        response=response,
    )

    assert isinstance(result, SimulationHistoryDetailResponse)
    assert type(result.result) is response_type
    assert result.result == response
    portfolio_service.get.assert_called_once_with(
        user_id=_USER_ID,
        portfolio_id=_PORTFOLIO_ID,
    )
    repository.create.assert_called_once()
    saved = repository.create.call_args.kwargs
    assert saved["portfolio_id"] == _PORTFOLIO_ID
    assert saved["simulation_type"] == simulation_type
    assert saved["scenario_id"] == scenario_id
    assert saved["requested_start_date"] == start
    assert saved["requested_end_date"] == end
    assert saved["schema_version"] == _SCHEMA_BY_TYPE[simulation_type]
    assert saved["result_snapshot"] == response.model_dump(mode="json")
    assert saved["result_snapshot"] is not response
    assert response.model_dump(mode="python") == response_before
    _assert_session_lifecycle_untouched(session)


def test_save_serializes_and_checks_consistency_before_repository_create() -> None:
    service, session, portfolio_service, repository = (
        _service_with_dependencies()
    )
    portfolio_service.get.return_value = _portfolio()
    response = _response_for_type("historical-scenario")
    snapshot = simulation_response_to_snapshot(
        simulation_type="historical-scenario",
        response=response,
    )
    events: list[str] = []
    repository.create.side_effect = lambda **kwargs: (
        events.append("create") or _record(snapshot=kwargs["result_snapshot"])
    )

    with (
        patch.object(
            service_module,
            "simulation_type_to_schema_version",
            side_effect=lambda value: events.append("version")
            or _SCHEMA_BY_TYPE[value],
        ),
        patch.object(
            service_module,
            "simulation_response_to_snapshot",
            side_effect=lambda **kwargs: events.append("snapshot") or snapshot,
        ),
        patch.object(
            service_module,
            "validate_simulation_snapshot_consistency",
            side_effect=lambda **kwargs: events.append("consistency"),
        ),
        patch.object(
            service_module,
            "_simulation_to_detail",
            side_effect=lambda record: events.append("detail")
            or MagicMock(spec=SimulationHistoryDetailResponse),
        ),
    ):
        service.save(
            user_id=_USER_ID,
            portfolio_id=_PORTFOLIO_ID,
            simulation_type="historical-scenario",
            scenario_id="covid-19-shock-2020",
            requested_start_date=date(2020, 2, 1),
            requested_end_date=date(2020, 4, 30),
            response=response,
        )

    assert events == ["version", "snapshot", "consistency", "create", "detail"]
    _assert_session_lifecycle_untouched(session)


@pytest.mark.parametrize("ownership_state", ["missing", "wrong-owner"])
def test_save_unowned_portfolio_returns_none_before_mapping_or_persistence(
    ownership_state: str,
) -> None:
    service, session, portfolio_service, repository = (
        _service_with_dependencies()
    )
    portfolio_service.get.return_value = None

    with (
        patch.object(service_module, "simulation_response_to_snapshot") as mapper,
        patch.object(
            service_module,
            "validate_simulation_snapshot_consistency",
        ) as consistency,
    ):
        result = service.save(
            user_id=_USER_ID,
            portfolio_id=_PORTFOLIO_ID,
            simulation_type="allocation",
            scenario_id=None,
            requested_start_date=date(2020, 2, 1),
            requested_end_date=date(2020, 4, 30),
            response=_response_for_type("allocation"),
        )

    assert result is None
    mapper.assert_not_called()
    consistency.assert_not_called()
    repository.create.assert_not_called()
    _assert_session_lifecycle_untouched(session)


def test_save_repository_failure_propagates_without_transaction_management() -> None:
    service, session, portfolio_service, repository = (
        _service_with_dependencies()
    )
    portfolio_service.get.return_value = _portfolio()
    failure = SQLAlchemyError("simulation write failed")
    repository.create.side_effect = failure

    with pytest.raises(SQLAlchemyError) as raised:
        service.save(
            user_id=_USER_ID,
            portfolio_id=_PORTFOLIO_ID,
            simulation_type="allocation",
            scenario_id=None,
            requested_start_date=date(2020, 2, 1),
            requested_end_date=date(2020, 4, 30),
            response=_response_for_type("allocation"),
        )

    assert raised.value is failure
    _assert_session_lifecycle_untouched(session)


def test_list_owned_empty_history_returns_valid_empty_response() -> None:
    service, session, portfolio_service, repository = (
        _service_with_dependencies()
    )
    portfolio_service.get.return_value = _portfolio()
    repository.list_for_portfolio.return_value = []

    result = service.list_for_portfolio(
        user_id=_USER_ID,
        portfolio_id=_PORTFOLIO_ID,
    )

    assert isinstance(result, SimulationHistoryListResponse)
    assert result.simulations == []
    repository.list_for_portfolio.assert_called_once_with(_PORTFOLIO_ID)
    _assert_session_lifecycle_untouched(session)


def test_list_preserves_repository_order_for_all_types_without_snapshots() -> None:
    service, session, portfolio_service, repository = (
        _service_with_dependencies()
    )
    portfolio_service.get.return_value = _portfolio()
    records = [
        _record("combined", simulation_id=UUID(int=3)),
        _record("allocation", simulation_id=UUID(int=2)),
        _record("historical-scenario", simulation_id=UUID(int=1)),
    ]
    repository.list_for_portfolio.return_value = records

    with (
        patch.object(service_module, "restore_simulation_snapshot") as restore,
        patch.object(
            service_module,
            "validate_simulation_snapshot_consistency",
        ) as consistency,
    ):
        result = service.list_for_portfolio(
            user_id=_USER_ID,
            portfolio_id=_PORTFOLIO_ID,
        )

    assert result is not None
    assert [summary.id for summary in result.simulations] == [
        record.id for record in records
    ]
    assert [summary.simulation_type for summary in result.simulations] == [
        "combined",
        "allocation",
        "historical-scenario",
    ]
    restore.assert_not_called()
    consistency.assert_not_called()
    _assert_session_lifecycle_untouched(session)


@pytest.mark.parametrize("ownership_state", ["missing", "wrong-owner"])
def test_list_unowned_portfolio_exposes_no_history(
    ownership_state: str,
) -> None:
    service, session, portfolio_service, repository = (
        _service_with_dependencies()
    )
    portfolio_service.get.return_value = None

    result = service.list_for_portfolio(
        user_id=_USER_ID,
        portfolio_id=_PORTFOLIO_ID,
    )

    assert result is None
    repository.list_for_portfolio.assert_not_called()
    _assert_session_lifecycle_untouched(session)


@pytest.mark.parametrize(
    ("simulation_type", "response_type"),
    [
        ("historical-scenario", HistoricalScenarioSimulationResponse),
        ("allocation", AllocationSimulationResponse),
        ("combined", CombinedSimulationResponse),
    ],
)
def test_get_restores_exact_response_type_without_mutating_snapshot(
    simulation_type: str,
    response_type: type,
) -> None:
    service, session, portfolio_service, repository = (
        _service_with_dependencies()
    )
    portfolio_service.get.return_value = _portfolio()
    record = _record(simulation_type)
    snapshot_before = deepcopy(record.result_snapshot)
    repository.get_for_portfolio.return_value = record

    result = service.get(
        user_id=_USER_ID,
        portfolio_id=_PORTFOLIO_ID,
        simulation_id=record.id,
    )

    assert isinstance(result, SimulationHistoryDetailResponse)
    assert type(result.result) is response_type
    assert result.result == _response_for_type(simulation_type)
    assert record.result_snapshot == snapshot_before
    repository.get_for_portfolio.assert_called_once_with(
        portfolio_id=_PORTFOLIO_ID,
        simulation_id=record.id,
    )
    _assert_session_lifecycle_untouched(session)


def test_get_preserves_nullable_sharpe_and_signed_drawdown() -> None:
    service, session, portfolio_service, repository = (
        _service_with_dependencies()
    )
    portfolio_service.get.return_value = _portfolio()
    repository.get_for_portfolio.return_value = _record()

    result = service.get(
        user_id=_USER_ID,
        portfolio_id=_PORTFOLIO_ID,
        simulation_id=_SIMULATION_ID,
    )

    assert result is not None
    assert isinstance(result.result, HistoricalScenarioSimulationResponse)
    assert result.result.metrics.sharpe_ratio is None
    assert result.result.metrics.maximum_drawdown.max_drawdown == -0.25
    _assert_session_lifecycle_untouched(session)


@pytest.mark.parametrize("simulation_state", ["missing", "other-portfolio"])
def test_get_missing_and_other_portfolio_are_identical_not_found(
    simulation_state: str,
) -> None:
    service, session, portfolio_service, repository = (
        _service_with_dependencies()
    )
    portfolio_service.get.return_value = _portfolio()
    repository.get_for_portfolio.return_value = (
        None
        if simulation_state == "missing"
        else _record(portfolio_id=uuid4())
    )

    with pytest.raises(
        SimulationNotFoundError,
        match="^Simulation not found$",
    ):
        service.get(
            user_id=_USER_ID,
            portfolio_id=_PORTFOLIO_ID,
            simulation_id=_SIMULATION_ID,
        )

    _assert_session_lifecycle_untouched(session)


@pytest.mark.parametrize("ownership_state", ["missing", "wrong-owner"])
def test_get_unowned_parent_returns_none_before_simulation_lookup(
    ownership_state: str,
) -> None:
    service, session, portfolio_service, repository = (
        _service_with_dependencies()
    )
    portfolio_service.get.return_value = None

    result = service.get(
        user_id=_USER_ID,
        portfolio_id=_PORTFOLIO_ID,
        simulation_id=_SIMULATION_ID,
    )

    assert result is None
    repository.get_for_portfolio.assert_not_called()
    _assert_session_lifecycle_untouched(session)


@pytest.mark.parametrize(
    ("record", "message"),
    [
        (_record("forecast"), "unsupported simulation type"),
        (
            _record(
                "allocation",
                schema_version="allocation-simulation-response-v4",
            ),
            "unsupported simulation snapshot schema version",
        ),
        (
            _record(
                "allocation",
                schema_version=(
                    HISTORICAL_SCENARIO_SIMULATION_RESPONSE_SCHEMA_VERSION
                ),
            ),
            "do not match",
        ),
    ],
)
def test_get_rejects_unknown_type_version_and_mismatched_pair(
    record: Simulation,
    message: str,
) -> None:
    service, session, portfolio_service, repository = (
        _service_with_dependencies()
    )
    portfolio_service.get.return_value = _portfolio()
    repository.get_for_portfolio.return_value = record

    with pytest.raises(ValueError, match=message):
        service.get(
            user_id=_USER_ID,
            portfolio_id=_PORTFOLIO_ID,
            simulation_id=record.id,
        )

    _assert_session_lifecycle_untouched(session)


def test_get_rejects_malformed_snapshot_without_mutating_it() -> None:
    service, session, portfolio_service, repository = (
        _service_with_dependencies()
    )
    portfolio_service.get.return_value = _portfolio()
    snapshot: dict[str, object] = {"malformed": [True]}
    record = _record("allocation", snapshot=snapshot)
    repository.get_for_portfolio.return_value = record
    before = deepcopy(snapshot)

    with pytest.raises(ValidationError):
        service.get(
            user_id=_USER_ID,
            portfolio_id=_PORTFOLIO_ID,
            simulation_id=record.id,
        )

    assert snapshot == before
    _assert_session_lifecycle_untouched(session)


@pytest.mark.parametrize(
    ("record", "message"),
    [
        (
            _record(
                "allocation",
                portfolio_id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
            ),
            "portfolio_id does not match",
        ),
        (
            _record("combined", scenario_id="different-scenario"),
            "scenario_id does not match",
        ),
        (
            _record(
                "historical-scenario",
                requested_start_date=date(2020, 2, 1) - timedelta(days=1),
            ),
            "requested_start_date does not match",
        ),
        (
            _record(
                "allocation",
                requested_end_date=date(2020, 4, 30) + timedelta(days=1),
            ),
            "requested_end_date does not match",
        ),
    ],
)
def test_detail_mapping_rejects_relational_snapshot_metadata_mismatch(
    record: Simulation,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        service_module._simulation_to_detail(record)


def test_get_repository_failure_propagates_without_transaction_management() -> None:
    service, session, portfolio_service, repository = (
        _service_with_dependencies()
    )
    portfolio_service.get.return_value = _portfolio()
    failure = SQLAlchemyError("simulation read failed")
    repository.get_for_portfolio.side_effect = failure

    with pytest.raises(SQLAlchemyError) as raised:
        service.get(
            user_id=_USER_ID,
            portfolio_id=_PORTFOLIO_ID,
            simulation_id=_SIMULATION_ID,
        )

    assert raised.value is failure
    _assert_session_lifecycle_untouched(session)


def test_service_exports_only_history_service_and_not_found_error() -> None:
    assert service_module.__all__ == [
        "SimulationNotFoundError",
        "SimulationHistoryService",
    ]
    assert not hasattr(SimulationHistoryService, "delete")
    assert not hasattr(SimulationHistoryService, "update")
    assert not hasattr(SimulationHistoryService, "search")
