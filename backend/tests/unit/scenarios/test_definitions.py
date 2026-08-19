from dataclasses import FrozenInstanceError
from datetime import date

import pytest

from backend.app.scenarios.definitions import (
    HISTORICAL_SCENARIOS,
    HistoricalScenarioDefinition,
    get_historical_scenario,
)


def test_catalogue_contains_exactly_the_two_approved_scenarios() -> None:
    assert isinstance(HISTORICAL_SCENARIOS, tuple)
    assert len(HISTORICAL_SCENARIOS) == 2
    assert [scenario.id for scenario in HISTORICAL_SCENARIOS] == [
        "covid-19-shock-2020",
        "inflation-rate-shock-2022",
    ]


def test_catalogue_preserves_exact_approved_content_and_order() -> None:
    covid, inflation = HISTORICAL_SCENARIOS

    assert covid == HistoricalScenarioDefinition(
        id="covid-19-shock-2020",
        display_name="COVID-19 Market Shock",
        description=(
            "A sharp market shock and early recovery period during the "
            "COVID-19 disruption."
        ),
        requested_start_date=date(2020, 2, 1),
        requested_end_date=date(2020, 4, 30),
    )
    assert inflation == HistoricalScenarioDefinition(
        id="inflation-rate-shock-2022",
        display_name="2022 Inflation and Rate Shock",
        description=(
            "An extended cross-asset stress period associated with inflation "
            "and rising interest rates."
        ),
        requested_start_date=date(2022, 1, 1),
        requested_end_date=date(2022, 12, 31),
    )


def test_catalogue_order_is_deterministic() -> None:
    first_read = tuple(HISTORICAL_SCENARIOS)
    second_read = tuple(HISTORICAL_SCENARIOS)

    assert first_read == second_read
    assert [scenario.id for scenario in first_read] == [
        "covid-19-shock-2020",
        "inflation-rate-shock-2022",
    ]


def test_catalogue_ids_are_unique_and_date_ranges_are_valid() -> None:
    scenario_ids = [scenario.id for scenario in HISTORICAL_SCENARIOS]

    assert len(scenario_ids) == len(set(scenario_ids))
    assert all(
        scenario.requested_start_date <= scenario.requested_end_date
        for scenario in HISTORICAL_SCENARIOS
    )


def test_definition_rejects_reversed_date_range() -> None:
    with pytest.raises(ValueError, match="requested_start_date"):
        HistoricalScenarioDefinition(
            id="invalid-period",
            display_name="Invalid Period",
            description="An invalid test definition.",
            requested_start_date=date(2022, 2, 1),
            requested_end_date=date(2022, 1, 1),
        )


def test_definitions_are_immutable() -> None:
    scenario = HISTORICAL_SCENARIOS[0]

    with pytest.raises(FrozenInstanceError):
        scenario.display_name = "Changed"  # type: ignore[misc]


@pytest.mark.parametrize("scenario", HISTORICAL_SCENARIOS)
def test_lookup_returns_exact_catalogue_definition(
    scenario: HistoricalScenarioDefinition,
) -> None:
    assert get_historical_scenario(scenario.id) is scenario


def test_unknown_id_lookup_returns_none() -> None:
    assert get_historical_scenario("unknown-scenario") is None


def test_catalogue_contains_no_2008_scenario() -> None:
    assert all(
        "2008" not in scenario.id
        and scenario.requested_start_date.year != 2008
        for scenario in HISTORICAL_SCENARIOS
    )
