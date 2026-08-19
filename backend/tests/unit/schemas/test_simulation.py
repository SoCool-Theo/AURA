from copy import deepcopy
from datetime import date
import json
from pathlib import Path
from uuid import UUID

import pytest
from pydantic import ValidationError

import backend.app.schemas as schemas_package
import backend.app.schemas.simulation as simulation_module
from backend.app.schemas.simulation import (
    HistoricalScenarioListResponse,
    HistoricalScenarioMetrics,
    HistoricalScenarioResponse,
    HistoricalScenarioSimulationMetadata,
    HistoricalScenarioSimulationRequest,
    HistoricalScenarioSimulationResponse,
    HistoricalScenarioTrajectoryPoint,
)


_EXAMPLE_PATH = (
    Path(__file__).resolve().parents[3]
    / "examples"
    / "simulation_response.json"
)
_PORTFOLIO_ID = "12345678-1234-5678-1234-567812345678"


def _scenario_payload(
    *,
    scenario_id: str = "covid-19-shock-2020",
) -> dict[str, object]:
    return {
        "id": scenario_id,
        "display_name": "COVID-19 Market Shock",
        "description": (
            "A sharp market shock and early recovery period during the "
            "COVID-19 disruption."
        ),
        "requested_start_date": "2020-02-01",
        "requested_end_date": "2020-04-30",
    }


def _metadata_payload() -> dict[str, object]:
    return {
        "effective_start_date": "2020-02-03",
        "effective_end_date": "2020-04-30",
        "price_observation_count": 4,
        "return_observation_count": 3,
    }


def _metrics_payload() -> dict[str, object]:
    return {
        "normalized_starting_value": 1.0,
        "normalized_ending_value": 0.95,
        "cumulative_return": -0.05,
        "annualized_volatility": 0.42,
        "sharpe_ratio": None,
        "maximum_drawdown": {
            "max_drawdown": -0.25,
            "peak_date": "2020-02-03",
            "trough_date": "2020-03-23",
        },
    }


def _trajectory_payload() -> list[dict[str, object]]:
    return [
        {"date": "2020-02-03", "normalized_value": 1.0},
        {"date": "2020-03-02", "normalized_value": 0.8},
        {"date": "2020-03-23", "normalized_value": 0.75},
        {"date": "2020-04-30", "normalized_value": 0.95},
    ]


def _response_payload() -> dict[str, object]:
    return {
        "portfolio_id": _PORTFOLIO_ID,
        "portfolio_name": "Balanced Learning Portfolio",
        "scenario": _scenario_payload(),
        "metadata": _metadata_payload(),
        "metrics": _metrics_payload(),
        "trajectory": _trajectory_payload(),
    }


def test_valid_scenario_response() -> None:
    response = HistoricalScenarioResponse.model_validate(_scenario_payload())

    assert response.id == "covid-19-shock-2020"
    assert response.display_name == "COVID-19 Market Shock"
    assert response.requested_start_date == date(2020, 2, 1)
    assert response.requested_end_date == date(2020, 4, 30)


def test_valid_list_response_preserves_caller_order() -> None:
    payload = [
        _scenario_payload(scenario_id="inflation-rate-shock-2022"),
        _scenario_payload(scenario_id="covid-19-shock-2020"),
    ]

    response = HistoricalScenarioListResponse(scenarios=payload)

    assert [scenario.id for scenario in response.scenarios] == [
        "inflation-rate-shock-2022",
        "covid-19-shock-2020",
    ]


def test_valid_simulation_request_preserves_unknown_id_exactly() -> None:
    request = HistoricalScenarioSimulationRequest(
        scenario_id="Unknown-Scenario-ID"
    )

    assert request.scenario_id == "Unknown-Scenario-ID"


@pytest.mark.parametrize(
    "scenario_id",
    ["", " ", "\t", " covid-19-shock-2020", "covid-19-shock-2020 "],
)
def test_simulation_request_rejects_empty_or_padded_id(
    scenario_id: str,
) -> None:
    with pytest.raises(ValidationError):
        HistoricalScenarioSimulationRequest(scenario_id=scenario_id)


@pytest.mark.parametrize(
    ("model_type", "payload"),
    [
        (HistoricalScenarioResponse, _scenario_payload()),
        (
            HistoricalScenarioListResponse,
            {"scenarios": [_scenario_payload()]},
        ),
        (
            HistoricalScenarioSimulationRequest,
            {"scenario_id": "covid-19-shock-2020"},
        ),
        (HistoricalScenarioSimulationMetadata, _metadata_payload()),
        (
            HistoricalScenarioTrajectoryPoint,
            _trajectory_payload()[0],
        ),
        (HistoricalScenarioMetrics, _metrics_payload()),
        (HistoricalScenarioSimulationResponse, _response_payload()),
    ],
)
def test_all_simulation_schemas_reject_unknown_fields(
    model_type: type[object],
    payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        model_type.model_validate(  # type: ignore[attr-defined]
            {**payload, "unexpected": "forbidden"}
        )


def test_valid_metadata_preserves_effective_period_and_counts() -> None:
    metadata = HistoricalScenarioSimulationMetadata.model_validate(
        _metadata_payload()
    )

    assert metadata.model_dump() == {
        "effective_start_date": date(2020, 2, 3),
        "effective_end_date": date(2020, 4, 30),
        "price_observation_count": 4,
        "return_observation_count": 3,
    }


def test_metadata_rejects_reversed_effective_dates() -> None:
    payload = _metadata_payload()
    payload["effective_start_date"] = "2020-05-01"

    with pytest.raises(ValidationError, match="effective_start_date"):
        HistoricalScenarioSimulationMetadata.model_validate(payload)


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("price_observation_count", 0),
        ("price_observation_count", -1),
        ("price_observation_count", True),
        ("return_observation_count", 0),
        ("return_observation_count", -1),
        ("return_observation_count", False),
    ],
)
def test_metadata_rejects_invalid_observation_counts(
    field_name: str,
    bad_value: object,
) -> None:
    payload = _metadata_payload()
    payload[field_name] = bad_value

    with pytest.raises(ValidationError):
        HistoricalScenarioSimulationMetadata.model_validate(payload)


def test_metadata_rejects_inconsistent_observation_counts() -> None:
    payload = _metadata_payload()
    payload["return_observation_count"] = 2

    with pytest.raises(ValidationError, match="price_observation_count minus one"):
        HistoricalScenarioSimulationMetadata.model_validate(payload)


@pytest.mark.parametrize("bad_value", [float("nan"), float("inf"), -float("inf")])
def test_trajectory_rejects_nonfinite_normalized_values(
    bad_value: float,
) -> None:
    with pytest.raises(ValidationError):
        HistoricalScenarioTrajectoryPoint(
            date="2020-02-03",  # type: ignore[arg-type]
            normalized_value=bad_value,
        )


@pytest.mark.parametrize(
    "field_name",
    [
        "normalized_starting_value",
        "normalized_ending_value",
        "cumulative_return",
        "annualized_volatility",
        "sharpe_ratio",
    ],
)
@pytest.mark.parametrize("bad_value", [float("nan"), float("inf"), -float("inf")])
def test_metrics_reject_nonfinite_available_values(
    field_name: str,
    bad_value: float,
) -> None:
    payload = _metrics_payload()
    payload[field_name] = bad_value

    with pytest.raises(ValidationError):
        HistoricalScenarioMetrics.model_validate(payload)


def test_metrics_accept_nullable_sharpe_and_serialize_it_as_null() -> None:
    metrics = HistoricalScenarioMetrics.model_validate(_metrics_payload())

    assert metrics.sharpe_ratio is None
    assert json.loads(metrics.model_dump_json())["sharpe_ratio"] is None


def test_metrics_preserve_signed_negative_maximum_drawdown() -> None:
    metrics = HistoricalScenarioMetrics.model_validate(_metrics_payload())

    assert metrics.maximum_drawdown.max_drawdown == -0.25


@pytest.mark.parametrize("starting_value", [0.0, 0.999, 1.001, -1.0])
def test_metrics_require_normalized_starting_value_of_one(
    starting_value: float,
) -> None:
    payload = _metrics_payload()
    payload["normalized_starting_value"] = starting_value

    with pytest.raises(ValidationError, match="must equal 1.0"):
        HistoricalScenarioMetrics.model_validate(payload)


def test_complete_simulation_response_preserves_trajectory_order() -> None:
    response = HistoricalScenarioSimulationResponse.model_validate(
        _response_payload()
    )

    assert response.portfolio_id == UUID(_PORTFOLIO_ID)
    assert [point.date for point in response.trajectory] == [
        date(2020, 2, 3),
        date(2020, 3, 2),
        date(2020, 3, 23),
        date(2020, 4, 30),
    ]
    assert [point.normalized_value for point in response.trajectory] == [
        1.0,
        0.8,
        0.75,
        0.95,
    ]


def test_complete_response_rejects_unsorted_trajectory() -> None:
    payload = _response_payload()
    trajectory = payload["trajectory"]
    assert isinstance(trajectory, list)
    trajectory[1], trajectory[2] = trajectory[2], trajectory[1]

    with pytest.raises(ValidationError, match="strictly increasing"):
        HistoricalScenarioSimulationResponse.model_validate(payload)


def test_validation_does_not_mutate_caller_owned_structures() -> None:
    payload = _response_payload()
    snapshot = deepcopy(payload)
    trajectory = payload["trajectory"]
    assert isinstance(trajectory, list)
    trajectory_identity = id(trajectory)

    HistoricalScenarioSimulationResponse.model_validate(payload)

    assert payload == snapshot
    assert id(payload["trajectory"]) == trajectory_identity


def test_canonical_simulation_example_validates_and_is_strict_json() -> None:
    raw_text = _EXAMPLE_PATH.read_text(encoding="utf-8")
    payload = json.loads(
        raw_text,
        parse_constant=lambda value: pytest.fail(
            f"non-standard JSON constant: {value}"
        ),
    )

    response = HistoricalScenarioSimulationResponse.model_validate(payload)

    assert response.scenario.id == "covid-19-shock-2020"
    assert response.metrics.normalized_starting_value == 1.0
    assert response.metrics.sharpe_ratio is None


def test_direct_simulation_module_exports_are_importable() -> None:
    expected_names = [
        "HistoricalScenarioResponse",
        "HistoricalScenarioListResponse",
        "HistoricalScenarioSimulationRequest",
        "HistoricalScenarioSimulationMetadata",
        "HistoricalScenarioTrajectoryPoint",
        "HistoricalScenarioMetrics",
        "HistoricalScenarioSimulationResponse",
    ]

    assert simulation_module.__all__ == expected_names
    assert all(hasattr(simulation_module, name) for name in expected_names)


def test_package_level_schema_export_contract_remains_unchanged() -> None:
    assert len(schemas_package.__all__) == 21
    assert not any(
        "Simulation" in name for name in schemas_package.__all__
    )
    assert all(
        name not in schemas_package.__all__
        for name in simulation_module.__all__
    )
