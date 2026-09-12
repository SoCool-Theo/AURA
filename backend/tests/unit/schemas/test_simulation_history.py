from copy import deepcopy
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

import pytest
from pydantic import ValidationError

import backend.app.schemas as schemas_package
import backend.app.schemas.simulation_history as history_module
from backend.app.schemas.simulation import (
    AllocationSimulationResponse,
    CombinedSimulationResponse,
    HistoricalScenarioSimulationResponse,
)
from backend.app.schemas.simulation_history import (
    SimulationHistoryDetailResponse,
    SimulationHistoryListResponse,
    SimulationHistorySummary,
)
from backend.tests.unit.schemas.test_simulation import (
    _allocation_response_payload,
    _combined_response_payload,
    _response_payload,
)


_PORTFOLIO_ID = UUID("12345678-1234-5678-1234-567812345678")
_CREATED_AT = datetime(2026, 8, 20, 9, 30, tzinfo=UTC)


def _response_for_type(
    simulation_type: str,
) -> (
    HistoricalScenarioSimulationResponse
    | AllocationSimulationResponse
    | CombinedSimulationResponse
):
    if simulation_type == "historical-scenario":
        return HistoricalScenarioSimulationResponse.model_validate(
            _response_payload()
        )
    if simulation_type == "allocation":
        return AllocationSimulationResponse.model_validate(
            _allocation_response_payload()
        )
    return CombinedSimulationResponse.model_validate(
        _combined_response_payload()
    )


def _summary_payload(
    simulation_type: str = "historical-scenario",
    *,
    simulation_id: str = "10000000-0000-0000-0000-000000000001",
) -> dict[str, object]:
    return {
        "id": simulation_id,
        "portfolio_id": str(_PORTFOLIO_ID),
        "simulation_type": simulation_type,
        "scenario_id": (
            None
            if simulation_type == "allocation"
            else "covid-19-shock-2020"
        ),
        "requested_start_date": "2020-02-01",
        "requested_end_date": "2020-04-30",
        "created_at": _CREATED_AT.isoformat(),
    }


@pytest.mark.parametrize(
    "simulation_type",
    ["historical-scenario", "allocation", "combined"],
)
def test_summary_accepts_each_approved_simulation_type(
    simulation_type: str,
) -> None:
    summary = SimulationHistorySummary.model_validate(
        _summary_payload(simulation_type)
    )

    assert summary.simulation_type == simulation_type
    assert summary.portfolio_id == _PORTFOLIO_ID
    assert summary.created_at == _CREATED_AT


def test_summary_rejects_unknown_simulation_type() -> None:
    payload = _summary_payload()
    payload["simulation_type"] = "forecast"

    with pytest.raises(ValidationError, match="Input should be"):
        SimulationHistorySummary.model_validate(payload)


@pytest.mark.parametrize(
    ("simulation_type", "scenario_id"),
    [
        ("historical-scenario", None),
        ("combined", None),
        ("allocation", "covid-19-shock-2020"),
    ],
)
def test_summary_enforces_scenario_nullability(
    simulation_type: str,
    scenario_id: str | None,
) -> None:
    payload = _summary_payload(simulation_type)
    payload["scenario_id"] = scenario_id

    with pytest.raises(ValidationError, match="scenario_id"):
        SimulationHistorySummary.model_validate(payload)


@pytest.mark.parametrize(
    "scenario_id",
    ["", " ", " covid-19-shock-2020", "covid-19-shock-2020 "],
)
def test_summary_reuses_existing_scenario_id_behavior(
    scenario_id: str,
) -> None:
    payload = _summary_payload()
    payload["scenario_id"] = scenario_id

    with pytest.raises(ValidationError, match="scenario_id"):
        SimulationHistorySummary.model_validate(payload)


def test_summary_rejects_reversed_requested_dates() -> None:
    payload = _summary_payload()
    payload["requested_start_date"] = "2020-05-01"

    with pytest.raises(ValidationError, match="requested_start_date"):
        SimulationHistorySummary.model_validate(payload)


@pytest.mark.parametrize(
    "model_type",
    [
        SimulationHistorySummary,
        SimulationHistoryListResponse,
        SimulationHistoryDetailResponse,
    ],
)
def test_history_contracts_reject_unknown_fields(model_type: type) -> None:
    if model_type is SimulationHistoryListResponse:
        payload: dict[str, object] = {
            "simulations": [],
            "unexpected": True,
        }
    else:
        payload = _summary_payload()
        if model_type is SimulationHistoryDetailResponse:
            payload["result"] = _response_payload()
        payload["unexpected"] = True

    with pytest.raises(
        ValidationError,
        match="Extra inputs are not permitted",
    ):
        model_type.model_validate(payload)


def test_list_preserves_caller_supplied_order() -> None:
    first = _summary_payload(
        "allocation",
        simulation_id="20000000-0000-0000-0000-000000000002",
    )
    second = _summary_payload(
        "combined",
        simulation_id="10000000-0000-0000-0000-000000000001",
    )

    history = SimulationHistoryListResponse.model_validate(
        {"simulations": [first, second]}
    )

    assert [str(item.id) for item in history.simulations] == [
        first["id"],
        second["id"],
    ]


@pytest.mark.parametrize(
    "simulation_type",
    ["historical-scenario", "allocation", "combined"],
)
def test_detail_accepts_each_exact_existing_response_type(
    simulation_type: str,
) -> None:
    response = _response_for_type(simulation_type)
    payload = _summary_payload(simulation_type)
    payload["result"] = response

    detail = SimulationHistoryDetailResponse.model_validate(payload)

    assert detail.result is response
    assert type(detail.result) is type(response)
    assert detail.model_dump(mode="json")["result"] == response.model_dump(
        mode="json"
    )


def test_detail_rejects_result_type_mismatched_to_discriminator() -> None:
    payload = _summary_payload("allocation")
    payload["result"] = _response_for_type("combined")

    with pytest.raises(ValidationError, match="does not match"):
        SimulationHistoryDetailResponse.model_validate(payload)


def test_detail_rejects_malformed_result_content() -> None:
    payload = _summary_payload()
    payload["result"] = {"malformed": True}

    with pytest.raises(ValidationError):
        SimulationHistoryDetailResponse.model_validate(payload)


def test_contract_validation_does_not_mutate_caller_data() -> None:
    payload = _summary_payload("combined")
    payload["result"] = _combined_response_payload()
    original = deepcopy(payload)

    SimulationHistoryDetailResponse.model_validate(payload)

    assert payload == original


def test_history_contracts_are_direct_imports_without_package_expansion(
) -> None:
    expected_names = [
        "SimulationType",
        "SimulationHistoryResult",
        "SimulationHistorySummary",
        "SimulationHistoryListResponse",
        "SimulationHistoryDetailResponse",
        "SimulationHistoryV2DetailResponse",
        "SimulationHistoryDetail",
        "SimulationBaselineHolding",
        "SimulationBaselineValuationContext",
        "HistoricalScenarioSimulationV2Snapshot",
        "AllocationSimulationV2Snapshot",
        "CombinedSimulationV2Snapshot",
        "SimulationV2SchemaVersion",
    ]

    assert history_module.__all__ == expected_names
    assert all(hasattr(history_module, name) for name in expected_names)
    assert len(schemas_package.__all__) == 21
    assert all(name not in schemas_package.__all__ for name in expected_names)


def test_summary_uses_uuid_date_and_aware_datetime_conventions() -> None:
    summary = SimulationHistorySummary.model_validate(_summary_payload())

    assert isinstance(summary.id, UUID)
    assert summary.requested_start_date == date(2020, 2, 1)
    assert summary.requested_end_date == date(2020, 4, 30)
    assert summary.created_at.tzinfo is not None
    assert summary.created_at.utcoffset() == timedelta(0)
