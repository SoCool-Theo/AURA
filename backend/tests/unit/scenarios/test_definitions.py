from dataclasses import FrozenInstanceError
from datetime import date

import pytest

from backend.app.scenarios.definitions import (
    HISTORICAL_SCENARIOS,
    HistoricalScenarioDefinition,
    get_historical_scenario,
)


_EXPECTED_SCENARIOS = (
    HistoricalScenarioDefinition(
        id="covid-19-shock-2020",
        display_name="COVID-19 Market Shock",
        description=(
            "A sharp market shock and early recovery period during the "
            "COVID-19 disruption."
        ),
        requested_start_date=date(2020, 2, 1),
        requested_end_date=date(2020, 4, 30),
    ),
    HistoricalScenarioDefinition(
        id="inflation-rate-shock-2022",
        display_name="2022 Inflation and Rate Shock",
        description=(
            "An extended cross-asset stress period associated with inflation "
            "and rising interest rates."
        ),
        requested_start_date=date(2022, 1, 1),
        requested_end_date=date(2022, 12, 31),
    ),
    HistoricalScenarioDefinition(
        id="dot-com-bust-2000-2002",
        display_name="Dot-Com Bust",
        description=(
            "A prolonged technology-led market decline following the "
            "dot-com bubble."
        ),
        requested_start_date=date(2000, 3, 10),
        requested_end_date=date(2002, 10, 9),
    ),
    HistoricalScenarioDefinition(
        id="global-financial-crisis-2007-2009",
        display_name="Global Financial Crisis",
        description=(
            "A severe global market downturn during the 2007–2009 "
            "financial crisis."
        ),
        requested_start_date=date(2007, 10, 9),
        requested_end_date=date(2009, 3, 9),
    ),
    HistoricalScenarioDefinition(
        id="q4-market-selloff-2018",
        display_name="Q4 2018 Market Selloff",
        description=(
            "A sharp late-2018 market selloff marked by elevated volatility."
        ),
        requested_start_date=date(2018, 10, 1),
        requested_end_date=date(2018, 12, 31),
    ),
)


def test_catalogue_contains_exactly_the_five_approved_scenarios() -> None:
    assert isinstance(HISTORICAL_SCENARIOS, tuple)
    assert len(HISTORICAL_SCENARIOS) == 5
    assert HISTORICAL_SCENARIOS == _EXPECTED_SCENARIOS


def test_existing_scenarios_remain_first_second_and_unchanged() -> None:
    assert HISTORICAL_SCENARIOS[:2] == _EXPECTED_SCENARIOS[:2]


def test_new_scenarios_have_exact_approved_content_and_order() -> None:
    assert HISTORICAL_SCENARIOS[2:] == _EXPECTED_SCENARIOS[2:]


def test_catalogue_order_is_deterministic() -> None:
    first_read = tuple(HISTORICAL_SCENARIOS)
    second_read = tuple(HISTORICAL_SCENARIOS)

    assert first_read == second_read
    assert first_read == _EXPECTED_SCENARIOS


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


@pytest.mark.parametrize("scenario", _EXPECTED_SCENARIOS)
def test_lookup_returns_exact_catalogue_definition(
    scenario: HistoricalScenarioDefinition,
) -> None:
    resolved = get_historical_scenario(scenario.id)

    assert resolved == scenario
    assert resolved is HISTORICAL_SCENARIOS[
        _EXPECTED_SCENARIOS.index(scenario)
    ]


def test_unknown_id_lookup_returns_none() -> None:
    assert get_historical_scenario("unknown-scenario") is None
