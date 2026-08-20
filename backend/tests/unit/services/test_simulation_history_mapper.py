import json
from copy import deepcopy
from datetime import date
from pathlib import Path
from uuid import UUID

import pytest
from pydantic import ValidationError

from backend.app.schemas.simulation import (
    AllocationSimulationResponse,
    CombinedSimulationResponse,
    HistoricalScenarioSimulationResponse,
)
from backend.app.services.simulation_history_mapper import (
    ALLOCATION_SIMULATION_RESPONSE_SCHEMA_VERSION,
    COMBINED_SIMULATION_RESPONSE_SCHEMA_VERSION,
    HISTORICAL_SCENARIO_SIMULATION_RESPONSE_SCHEMA_VERSION,
    SIMULATION_SCHEMA_VERSIONS,
    simulation_response_to_snapshot,
    simulation_snapshot_to_response,
    simulation_type_to_schema_version,
    validate_simulation_snapshot_consistency,
)
from backend.tests.unit.schemas.test_simulation import (
    _allocation_response_payload,
    _combined_response_payload,
    _response_payload,
)


_PORTFOLIO_ID = UUID("12345678-1234-5678-1234-567812345678")
_SCENARIO_ID = "covid-19-shock-2020"
_START_DATE = date(2020, 2, 1)
_END_DATE = date(2020, 4, 30)


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


_TYPE_VERSION_CASES = [
    (
        "historical-scenario",
        HISTORICAL_SCENARIO_SIMULATION_RESPONSE_SCHEMA_VERSION,
        HistoricalScenarioSimulationResponse,
    ),
    (
        "allocation",
        ALLOCATION_SIMULATION_RESPONSE_SCHEMA_VERSION,
        AllocationSimulationResponse,
    ),
    (
        "combined",
        COMBINED_SIMULATION_RESPONSE_SCHEMA_VERSION,
        CombinedSimulationResponse,
    ),
]


@pytest.mark.parametrize(
    ("simulation_type", "schema_version", "response_type"),
    _TYPE_VERSION_CASES,
)
def test_type_selects_exact_approved_schema_version(
    simulation_type: str,
    schema_version: str,
    response_type: type,
) -> None:
    assert simulation_type_to_schema_version(simulation_type) == schema_version
    assert SIMULATION_SCHEMA_VERSIONS[simulation_type] == schema_version
    assert isinstance(_response_for_type(simulation_type), response_type)


def test_unknown_simulation_type_is_rejected_deterministically() -> None:
    with pytest.raises(ValueError, match="unsupported simulation type"):
        simulation_type_to_schema_version("forecast")

    with pytest.raises(ValueError, match="unsupported simulation type"):
        simulation_snapshot_to_response(
            simulation_type="forecast",
            schema_version="forecast-v1",
            snapshot={},
        )


def test_unknown_schema_version_is_rejected_deterministically() -> None:
    with pytest.raises(
        ValueError,
        match="unsupported simulation snapshot schema version",
    ):
        simulation_snapshot_to_response(
            simulation_type="allocation",
            schema_version="allocation-simulation-response-v2",
            snapshot={},
        )


def test_mismatched_type_and_known_version_are_rejected_explicitly() -> None:
    with pytest.raises(ValueError, match="do not match"):
        simulation_snapshot_to_response(
            simulation_type="allocation",
            schema_version=(
                HISTORICAL_SCENARIO_SIMULATION_RESPONSE_SCHEMA_VERSION
            ),
            snapshot={},
        )


@pytest.mark.parametrize(
    ("simulation_type", "schema_version", "response_type"),
    _TYPE_VERSION_CASES,
)
def test_json_safe_snapshot_round_trip_uses_exact_response_model(
    simulation_type: str,
    schema_version: str,
    response_type: type,
) -> None:
    response = _response_for_type(simulation_type)

    snapshot = simulation_response_to_snapshot(
        simulation_type=simulation_type,
        response=response,
    )
    serialized = json.dumps(snapshot, allow_nan=False)
    round_tripped = simulation_snapshot_to_response(
        simulation_type=simulation_type,
        schema_version=schema_version,
        snapshot=snapshot,
    )

    assert isinstance(serialized, str)
    assert type(round_tripped) is response_type
    assert round_tripped == response
    assert snapshot == response.model_dump(mode="json")


def test_serialization_rejects_response_type_mismatch() -> None:
    with pytest.raises(ValueError, match="does not match"):
        simulation_response_to_snapshot(
            simulation_type="allocation",
            response=_response_for_type("combined"),
        )


def test_snapshot_is_detached_and_source_response_is_not_mutated() -> None:
    response = _response_for_type("historical-scenario")
    original = response.model_dump(mode="python")

    snapshot = simulation_response_to_snapshot(
        simulation_type="historical-scenario",
        response=response,
    )
    snapshot["portfolio_name"] = "Changed"
    snapshot["scenario"]["display_name"] = "Changed"  # type: ignore[index]
    snapshot["trajectory"][0]["normalized_value"] = 99.0  # type: ignore[index]

    assert response.model_dump(mode="python") == original
    assert response.portfolio_name == "Balanced Learning Portfolio"
    assert response.trajectory[0].normalized_value == 1.0


@pytest.mark.parametrize(
    ("simulation_type", "schema_version"),
    [(case[0], case[1]) for case in _TYPE_VERSION_CASES],
)
def test_revalidation_does_not_mutate_snapshot_input(
    simulation_type: str,
    schema_version: str,
) -> None:
    response = _response_for_type(simulation_type)
    snapshot = simulation_response_to_snapshot(
        simulation_type=simulation_type,
        response=response,
    )
    original = deepcopy(snapshot)

    simulation_snapshot_to_response(
        simulation_type=simulation_type,
        schema_version=schema_version,
        snapshot=snapshot,
    )

    assert snapshot == original


def test_all_mode_snapshots_preserve_ordering_and_financial_values() -> None:
    historical = simulation_response_to_snapshot(
        simulation_type="historical-scenario",
        response=_response_for_type("historical-scenario"),
    )
    allocation = simulation_response_to_snapshot(
        simulation_type="allocation",
        response=_response_for_type("allocation"),
    )
    combined = simulation_response_to_snapshot(
        simulation_type="combined",
        response=_response_for_type("combined"),
    )

    assert [point["date"] for point in historical["trajectory"]] == [
        "2020-02-03",
        "2020-03-02",
        "2020-03-23",
        "2020-04-30",
    ]
    assert historical["metrics"]["sharpe_ratio"] is None
    assert historical["metrics"]["maximum_drawdown"]["max_drawdown"] == -0.25
    assert [
        holding["symbol"]
        for holding in allocation["original"]["allocation"]
    ] == ["MSFT", "AAPL"]
    assert allocation["comparison"] == {
        "normalized_ending_value_delta": 0.09,
        "cumulative_return_delta": 0.09,
        "annualized_volatility_delta": -0.1,
        "sharpe_ratio_delta": None,
        "maximum_drawdown_delta": 0.15,
    }
    assert combined["original"]["metrics"]["sharpe_ratio"] is None
    assert combined["original"]["metrics"]["maximum_drawdown"][
        "max_drawdown"
    ] == -0.25


@pytest.mark.parametrize(
    "simulation_type",
    ["historical-scenario", "allocation", "combined"],
)
def test_requested_and_effective_dates_are_preserved(
    simulation_type: str,
) -> None:
    response = _response_for_type(simulation_type)
    snapshot = simulation_response_to_snapshot(
        simulation_type=simulation_type,
        response=response,
    )

    if simulation_type == "allocation":
        assert snapshot["start_date"] == "2020-02-01"
        assert snapshot["end_date"] == "2020-04-30"
    else:
        assert snapshot["scenario"]["requested_start_date"] == "2020-02-01"
        assert snapshot["scenario"]["requested_end_date"] == "2020-04-30"
    assert snapshot["metadata"]["effective_start_date"] == "2020-02-03"
    assert snapshot["metadata"]["effective_end_date"] == "2020-04-30"


def test_malformed_snapshot_is_rejected_by_selected_existing_schema() -> None:
    snapshot = simulation_response_to_snapshot(
        simulation_type="allocation",
        response=_response_for_type("allocation"),
    )
    snapshot["unexpected"] = True

    with pytest.raises(
        ValidationError,
        match="Extra inputs are not permitted",
    ):
        simulation_snapshot_to_response(
            simulation_type="allocation",
            schema_version=ALLOCATION_SIMULATION_RESPONSE_SCHEMA_VERSION,
            snapshot=snapshot,
        )


@pytest.mark.parametrize(
    "simulation_type",
    ["historical-scenario", "allocation", "combined"],
)
def test_relational_consistency_accepts_matching_metadata(
    simulation_type: str,
) -> None:
    validate_simulation_snapshot_consistency(
        simulation_type=simulation_type,
        response=_response_for_type(simulation_type),
        portfolio_id=_PORTFOLIO_ID,
        scenario_id=None if simulation_type == "allocation" else _SCENARIO_ID,
        requested_start_date=_START_DATE,
        requested_end_date=_END_DATE,
    )


@pytest.mark.parametrize(
    "simulation_type",
    ["historical-scenario", "allocation", "combined"],
)
def test_relational_portfolio_mismatch_is_rejected(
    simulation_type: str,
) -> None:
    with pytest.raises(ValueError, match="portfolio_id"):
        validate_simulation_snapshot_consistency(
            simulation_type=simulation_type,
            response=_response_for_type(simulation_type),
            portfolio_id=UUID("99999999-9999-9999-9999-999999999999"),
            scenario_id=(
                None if simulation_type == "allocation" else _SCENARIO_ID
            ),
            requested_start_date=_START_DATE,
            requested_end_date=_END_DATE,
        )


@pytest.mark.parametrize(
    "simulation_type",
    ["historical-scenario", "combined"],
)
def test_relational_scenario_mismatch_is_rejected(
    simulation_type: str,
) -> None:
    with pytest.raises(ValueError, match="scenario_id"):
        validate_simulation_snapshot_consistency(
            simulation_type=simulation_type,
            response=_response_for_type(simulation_type),
            portfolio_id=_PORTFOLIO_ID,
            scenario_id="inflation-rate-shock-2022",
            requested_start_date=_START_DATE,
            requested_end_date=_END_DATE,
        )


def test_allocation_relational_scenario_must_be_null() -> None:
    with pytest.raises(ValueError, match="must be null"):
        validate_simulation_snapshot_consistency(
            simulation_type="allocation",
            response=_response_for_type("allocation"),
            portfolio_id=_PORTFOLIO_ID,
            scenario_id=_SCENARIO_ID,
            requested_start_date=_START_DATE,
            requested_end_date=_END_DATE,
        )


@pytest.mark.parametrize(
    ("simulation_type", "start_date", "end_date", "message"),
    [
        ("historical-scenario", date(2020, 1, 31), _END_DATE, "start_date"),
        ("allocation", _START_DATE, date(2020, 5, 1), "end_date"),
        ("combined", date(2020, 1, 31), _END_DATE, "start_date"),
    ],
)
def test_relational_requested_date_mismatch_is_rejected(
    simulation_type: str,
    start_date: date,
    end_date: date,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        validate_simulation_snapshot_consistency(
            simulation_type=simulation_type,
            response=_response_for_type(simulation_type),
            portfolio_id=_PORTFOLIO_ID,
            scenario_id=(
                None if simulation_type == "allocation" else _SCENARIO_ID
            ),
            requested_start_date=start_date,
            requested_end_date=end_date,
        )


def test_mapper_module_remains_database_and_framework_independent() -> None:
    source_path = (
        Path(__file__).resolve().parents[3]
        / "app"
        / "services"
        / "simulation_history_mapper.py"
    )
    source = source_path.read_text(encoding="utf-8")

    forbidden_imports = [
        "sqlalchemy",
        "database.models",
        "database.repositories",
        "fastapi",
        "api.dependencies",
    ]
    assert all(value not in source for value in forbidden_imports)
