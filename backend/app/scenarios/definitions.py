"""Immutable predefined historical scenarios for Aura simulations."""

from dataclasses import dataclass
from datetime import date
from types import MappingProxyType
from typing import Mapping


@dataclass(frozen=True, slots=True)
class HistoricalScenarioDefinition:
    """Describe one code-owned historical event over a calendar period."""

    id: str
    display_name: str
    description: str
    requested_start_date: date
    requested_end_date: date

    def __post_init__(self) -> None:
        for field_name in ("id", "display_name", "description"):
            value = getattr(self, field_name)
            if not isinstance(value, str):
                raise TypeError(f"{field_name} must be a string")
            if not value.strip():
                raise ValueError(f"{field_name} cannot be empty")
            if value != value.strip():
                raise ValueError(
                    f"{field_name} cannot contain leading or trailing whitespace"
                )

        if not isinstance(self.requested_start_date, date):
            raise TypeError("requested_start_date must be a date")
        if not isinstance(self.requested_end_date, date):
            raise TypeError("requested_end_date must be a date")
        if self.requested_start_date > self.requested_end_date:
            raise ValueError(
                "requested_start_date must be on or before requested_end_date"
            )


HISTORICAL_SCENARIOS: tuple[HistoricalScenarioDefinition, ...] = (
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


def _build_scenario_lookup(
    definitions: tuple[HistoricalScenarioDefinition, ...],
) -> Mapping[str, HistoricalScenarioDefinition]:
    lookup = {definition.id: definition for definition in definitions}
    if len(lookup) != len(definitions):
        raise ValueError("historical scenario IDs must be unique")
    return MappingProxyType(lookup)


_HISTORICAL_SCENARIOS_BY_ID = _build_scenario_lookup(HISTORICAL_SCENARIOS)


def get_historical_scenario(
    scenario_id: str,
) -> HistoricalScenarioDefinition | None:
    """Return one predefined scenario by exact ID, or ``None`` if unknown."""
    return _HISTORICAL_SCENARIOS_BY_ID.get(scenario_id)
