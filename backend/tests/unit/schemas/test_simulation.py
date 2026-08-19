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
    AllocationSimulationComparison,
    AllocationSimulationRequest,
    AllocationSimulationResponse,
    AllocationSimulationResult,
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


def _allocation_payload(
    *,
    first_weight: float = 0.6,
    second_weight: float = 0.4,
) -> list[dict[str, object]]:
    return [
        {"symbol": "MSFT", "weight": first_weight},
        {"symbol": "AAPL", "weight": second_weight},
    ]


def _allocation_request_payload() -> dict[str, object]:
    return {
        "start_date": "2020-02-01",
        "end_date": "2020-04-30",
        "modified_allocation": _allocation_payload(
            first_weight=0.3,
            second_weight=0.7,
        ),
    }


def _allocation_result_payload(
    *,
    modified: bool = False,
) -> dict[str, object]:
    if not modified:
        return {
            "allocation": _allocation_payload(),
            "metrics": _metrics_payload(),
            "trajectory": _trajectory_payload(),
        }

    return {
        "allocation": _allocation_payload(
            first_weight=0.3,
            second_weight=0.7,
        ),
        "metrics": {
            "normalized_starting_value": 1.0,
            "normalized_ending_value": 1.04,
            "cumulative_return": 0.04,
            "annualized_volatility": 0.32,
            "sharpe_ratio": 1.2,
            "maximum_drawdown": {
                "max_drawdown": -0.1,
                "peak_date": "2020-02-03",
                "trough_date": "2020-03-02",
            },
        },
        "trajectory": [
            {"date": "2020-02-03", "normalized_value": 1.0},
            {"date": "2020-03-02", "normalized_value": 0.9},
            {"date": "2020-03-23", "normalized_value": 0.98},
            {"date": "2020-04-30", "normalized_value": 1.04},
        ],
    }


def _comparison_payload() -> dict[str, object]:
    return {
        "normalized_ending_value_delta": 0.09,
        "cumulative_return_delta": 0.09,
        "annualized_volatility_delta": -0.1,
        "sharpe_ratio_delta": None,
        "maximum_drawdown_delta": 0.15,
    }


def _allocation_response_payload() -> dict[str, object]:
    return {
        "portfolio_id": _PORTFOLIO_ID,
        "portfolio_name": "Balanced Learning Portfolio",
        "start_date": "2020-02-01",
        "end_date": "2020-04-30",
        "metadata": _metadata_payload(),
        "original": _allocation_result_payload(),
        "modified": _allocation_result_payload(modified=True),
        "comparison": _comparison_payload(),
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
        (AllocationSimulationRequest, _allocation_request_payload()),
        (AllocationSimulationResult, _allocation_result_payload()),
        (AllocationSimulationComparison, _comparison_payload()),
        (AllocationSimulationResponse, _allocation_response_payload()),
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


def test_valid_allocation_request_preserves_period_and_order() -> None:
    request = AllocationSimulationRequest.model_validate(
        _allocation_request_payload()
    )

    assert request.start_date == date(2020, 2, 1)
    assert request.end_date == date(2020, 4, 30)
    assert [holding.symbol for holding in request.modified_allocation] == [
        "MSFT",
        "AAPL",
    ]
    assert [holding.weight for holding in request.modified_allocation] == [
        0.3,
        0.7,
    ]


def test_allocation_request_inherits_symbol_normalization() -> None:
    payload = _allocation_request_payload()
    payload["modified_allocation"] = [
        {"symbol": " msft ", "weight": 0.3},
        {"symbol": "aapl", "weight": 0.7},
    ]

    request = AllocationSimulationRequest.model_validate(payload)

    assert [holding.symbol for holding in request.modified_allocation] == [
        "MSFT",
        "AAPL",
    ]


def test_allocation_request_accepts_zero_and_one_weight_boundaries() -> None:
    payload = _allocation_request_payload()
    payload["modified_allocation"] = _allocation_payload(
        first_weight=0.0,
        second_weight=1.0,
    )

    request = AllocationSimulationRequest.model_validate(payload)

    assert [holding.weight for holding in request.modified_allocation] == [
        0.0,
        1.0,
    ]


@pytest.mark.parametrize("invalid_weight", [-0.01, 1.01])
def test_allocation_request_rejects_out_of_range_weights(
    invalid_weight: float,
) -> None:
    payload = _allocation_request_payload()
    payload["modified_allocation"] = _allocation_payload(
        first_weight=invalid_weight,
        second_weight=1.0 - invalid_weight,
    )

    with pytest.raises(ValidationError):
        AllocationSimulationRequest.model_validate(payload)


@pytest.mark.parametrize(
    ("first_weight", "second_weight"),
    [(0.5, 0.499999998), (0.5, 0.500000002)],
)
def test_allocation_request_rejects_total_outside_existing_tolerance(
    first_weight: float,
    second_weight: float,
) -> None:
    payload = _allocation_request_payload()
    payload["modified_allocation"] = _allocation_payload(
        first_weight=first_weight,
        second_weight=second_weight,
    )

    with pytest.raises(ValidationError, match="absolute tolerance of 1e-9"):
        AllocationSimulationRequest.model_validate(payload)


@pytest.mark.parametrize(
    ("first_weight", "second_weight"),
    [(0.5, 0.4999999995), (0.5, 0.5000000005)],
)
def test_allocation_request_accepts_total_within_existing_tolerance(
    first_weight: float,
    second_weight: float,
) -> None:
    payload = _allocation_request_payload()
    payload["modified_allocation"] = _allocation_payload(
        first_weight=first_weight,
        second_weight=second_weight,
    )

    request = AllocationSimulationRequest.model_validate(payload)

    assert len(request.modified_allocation) == 2


def test_allocation_request_rejects_duplicate_normalized_symbols() -> None:
    payload = _allocation_request_payload()
    payload["modified_allocation"] = [
        {"symbol": " aapl ", "weight": 0.5},
        {"symbol": "AAPL", "weight": 0.5},
    ]

    with pytest.raises(ValidationError, match="unique after normalization"):
        AllocationSimulationRequest.model_validate(payload)


def test_allocation_request_rejects_reversed_period() -> None:
    payload = _allocation_request_payload()
    payload["start_date"] = "2020-05-01"

    with pytest.raises(ValidationError, match="start_date"):
        AllocationSimulationRequest.model_validate(payload)


def test_allocation_request_does_not_support_scenario_id() -> None:
    payload = _allocation_request_payload()
    payload["scenario_id"] = "covid-19-shock-2020"

    with pytest.raises(ValidationError):
        AllocationSimulationRequest.model_validate(payload)


def test_allocation_request_does_not_mutate_caller_input() -> None:
    payload = _allocation_request_payload()
    allocation = payload["modified_allocation"]
    assert isinstance(allocation, list)
    snapshot = deepcopy(payload)
    allocation_identity = id(allocation)

    AllocationSimulationRequest.model_validate(payload)

    assert payload == snapshot
    assert id(payload["modified_allocation"]) == allocation_identity


def test_valid_allocation_results_reuse_metrics_and_trajectory_models() -> None:
    response = AllocationSimulationResponse.model_validate(
        _allocation_response_payload()
    )

    assert isinstance(response.original.metrics, HistoricalScenarioMetrics)
    assert isinstance(
        response.original.trajectory[0],
        HistoricalScenarioTrajectoryPoint,
    )
    assert response.original.metrics.maximum_drawdown.max_drawdown == -0.25
    assert response.original.metrics.sharpe_ratio is None
    assert response.modified.metrics.maximum_drawdown.max_drawdown == -0.1
    assert response.modified.metrics.sharpe_ratio == 1.2


def test_allocation_response_preserves_each_allocation_order() -> None:
    payload = _allocation_response_payload()
    modified = payload["modified"]
    assert isinstance(modified, dict)
    modified["allocation"] = [
        {"symbol": "AAPL", "weight": 0.7},
        {"symbol": "MSFT", "weight": 0.3},
    ]

    response = AllocationSimulationResponse.model_validate(payload)

    assert [holding.symbol for holding in response.original.allocation] == [
        "MSFT",
        "AAPL",
    ]
    assert [holding.symbol for holding in response.modified.allocation] == [
        "AAPL",
        "MSFT",
    ]


def test_allocation_response_has_one_shared_requested_and_effective_period() -> None:
    response = AllocationSimulationResponse.model_validate(
        _allocation_response_payload()
    )

    assert response.start_date == date(2020, 2, 1)
    assert response.end_date == date(2020, 4, 30)
    assert response.metadata.effective_start_date == date(2020, 2, 3)
    assert response.metadata.effective_end_date == date(2020, 4, 30)
    assert [point.date for point in response.original.trajectory] == [
        point.date for point in response.modified.trajectory
    ]
    dumped = response.model_dump()
    assert list(dumped).count("metadata") == 1


@pytest.mark.parametrize("bad_value", [float("nan"), float("inf"), -float("inf")])
def test_allocation_result_rejects_nonfinite_trajectory_values(
    bad_value: float,
) -> None:
    payload = _allocation_result_payload()
    trajectory = payload["trajectory"]
    assert isinstance(trajectory, list)
    trajectory[1]["normalized_value"] = bad_value

    with pytest.raises(ValidationError):
        AllocationSimulationResult.model_validate(payload)


@pytest.mark.parametrize(
    "field_name",
    [
        "normalized_ending_value_delta",
        "cumulative_return_delta",
        "annualized_volatility_delta",
        "sharpe_ratio_delta",
        "maximum_drawdown_delta",
    ],
)
@pytest.mark.parametrize("bad_value", [float("nan"), float("inf"), -float("inf")])
def test_allocation_comparison_rejects_nonfinite_deltas(
    field_name: str,
    bad_value: float,
) -> None:
    payload = _comparison_payload()
    payload[field_name] = bad_value

    with pytest.raises(ValidationError):
        AllocationSimulationComparison.model_validate(payload)


@pytest.mark.parametrize("delta", [-0.25, 0.0, 0.25])
def test_allocation_comparison_accepts_signed_and_zero_deltas(
    delta: float,
) -> None:
    payload = {
        field_name: delta
        for field_name in _comparison_payload()
    }

    comparison = AllocationSimulationComparison.model_validate(payload)

    assert comparison.maximum_drawdown_delta == delta
    assert comparison.sharpe_ratio_delta == delta


def test_allocation_comparison_accepts_nullable_sharpe_delta() -> None:
    comparison = AllocationSimulationComparison.model_validate(
        _comparison_payload()
    )

    assert comparison.sharpe_ratio_delta is None
    assert json.loads(comparison.model_dump_json())["sharpe_ratio_delta"] is None


def test_allocation_response_rejects_different_trajectory_dates() -> None:
    payload = _allocation_response_payload()
    modified = payload["modified"]
    assert isinstance(modified, dict)
    trajectory = modified["trajectory"]
    assert isinstance(trajectory, list)
    trajectory[1]["date"] = "2020-03-03"

    with pytest.raises(ValidationError, match="trajectory dates must match"):
        AllocationSimulationResponse.model_validate(payload)


def test_allocation_response_rejects_effective_dates_outside_request() -> None:
    payload = _allocation_response_payload()
    payload["start_date"] = "2020-02-04"

    with pytest.raises(ValidationError, match="effective dates"):
        AllocationSimulationResponse.model_validate(payload)


def test_allocation_response_round_trip_is_deterministic() -> None:
    response = AllocationSimulationResponse.model_validate(
        _allocation_response_payload()
    )

    serialized = response.model_dump_json()
    round_tripped = AllocationSimulationResponse.model_validate_json(serialized)

    assert round_tripped == response
    assert round_tripped.model_dump_json() == serialized


def test_allocation_response_validation_does_not_mutate_input() -> None:
    payload = _allocation_response_payload()
    snapshot = deepcopy(payload)

    AllocationSimulationResponse.model_validate(payload)

    assert payload == snapshot


def test_direct_simulation_module_exports_are_importable() -> None:
    expected_names = [
        "HistoricalScenarioResponse",
        "HistoricalScenarioListResponse",
        "HistoricalScenarioSimulationRequest",
        "HistoricalScenarioSimulationMetadata",
        "HistoricalScenarioTrajectoryPoint",
        "HistoricalScenarioMetrics",
        "HistoricalScenarioSimulationResponse",
        "AllocationSimulationRequest",
        "AllocationSimulationResult",
        "AllocationSimulationComparison",
        "AllocationSimulationResponse",
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
