"""Finite JSON and provenance invariants for portfolio forecast responses."""

from copy import deepcopy
from dataclasses import asdict
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from backend.app.forecasting.inference import AssetForecast
from backend.app.forecasting.portfolio import PortfolioForecast, PortfolioForecastComponent
from backend.app.forecasting.monetary_projection import PortfolioMonetaryProjection
from backend.app.schemas.forecasting import PortfolioOutlookResponse
from backend.app.services.forecasting_response_mapper import map_portfolio_outlook


def payload():
    day = date(2026,10,1)
    asset = AssetForecast("AAPL",day,30,.03,-.1,.2,.05,0,.2,.8,
        "historical_average","historical_average","forecast-v1-20260917",
        "forecast-features-v1","forecast-targets-v1",day,0)
    forecast = PortfolioForecast(uuid4(),"Synthetic","legacy",.03,.05,day,60,day,
        asset.artifact_version,(PortfolioForecastComponent(asset,1.,.05,1.),))
    return map_portfolio_outlook(forecast).model_dump(mode="json")


def test_strict_json_round_trip_no_portfolio_interval_or_input_mutation():
    body = payload(); before = deepcopy(body)
    response = PortfolioOutlookResponse.model_validate(body)
    assert PortfolioOutlookResponse.model_validate_json(response.model_dump_json()) == response
    assert body == before
    assert not any("interval" in key for key in body)


@pytest.mark.parametrize("field,value", [
    ("expected_return_30d",float("nan")),("forecast_realized_volatility_30d",float("inf")),
    ("forecast_realized_volatility_30d",-.1),("horizon_days",31),
    ("correlation_observation_count",59),("correlation_observation_count",253),
    ("correlation_observation_count",True),("components",[]),("limitations",[]),
    ("baseline_kind","unknown"),("market_data_as_of","2026-09-30"),
    ("correlation_as_of_date","2026-09-30"),("artifact_version","private/path"),
])
def test_portfolio_invalid_values_rejected(field,value):
    body = payload(); body[field] = value
    with pytest.raises(ValidationError):
        PortfolioOutlookResponse.model_validate(body)


@pytest.mark.parametrize("field,value", [
    ("current_weight",.9),("current_weight",-1),("current_weight",float("nan")),
    ("forecast_volatility_contribution",float("inf")),
    ("forecast_volatility_contribution_share",float("nan")),
    ("expected_return_30d",float("inf")),("return_model_id","private/path"),
    ("artifact_version","forecast-v2-20260917"),("market_data_age_days",5),
    ("market_data_as_of","2026-09-30"),
])
def test_component_invalid_values_rejected(field,value):
    body = payload(); body["components"][0][field] = value
    with pytest.raises(ValidationError):
        PortfolioOutlookResponse.model_validate(body)


def test_component_negative_contributions_are_not_clipped():
    body = payload()
    body["components"][0]["forecast_volatility_contribution"] = -.01
    body["components"][0]["forecast_volatility_contribution_share"] = -.2
    response = PortfolioOutlookResponse.model_validate(body)
    assert response.components[0].forecast_volatility_contribution == -.01


def test_unknown_fields_and_duplicate_components_rejected():
    body = payload(); body["return_prediction_interval"] = {"lower":0,"upper":1,"coverage":.8}
    with pytest.raises(ValidationError):
        PortfolioOutlookResponse.model_validate(body)
    body = payload(); body["components"] *= 2
    with pytest.raises(ValidationError):
        PortfolioOutlookResponse.model_validate(body)


def monetary_payload(kind="current"):
    body = payload()
    day = date(2026,10,1)
    body["baseline_kind"] = kind
    body["monetary_projection"] = asdict(PortfolioMonetaryProjection(
        "USD", "current_market_value", Decimal("10000"), Decimal("300"), Decimal("10300"),
        False, False, day, day, day))
    body["components"][0]["monetary_projection"] = deepcopy(body["monetary_projection"])
    return body


def test_money_schema_round_trip_and_input_nonmutation():
    body = monetary_payload()
    before = deepcopy(body)
    response = PortfolioOutlookResponse.model_validate(body)
    assert PortfolioOutlookResponse.model_validate_json(response.model_dump_json()) == response
    assert body == before


@pytest.mark.parametrize("kind", ["current", "planned"])
def test_actual_amount_portfolios_require_money_context(kind):
    body = payload()
    body["baseline_kind"] = kind
    with pytest.raises(ValidationError):
        PortfolioOutlookResponse.model_validate(body)


@pytest.mark.parametrize("field,value", [("expected_change_amount","299.99"),
    ("estimated_ending_value","10301"), ("baseline_amount","9999")])
def test_amounts_must_match_portfolio_return(field, value):
    body = monetary_payload()
    body["monetary_projection"][field] = value
    with pytest.raises(ValidationError):
        PortfolioOutlookResponse.model_validate(body)


@pytest.mark.parametrize("kind", ["legacy", "planned"])
def test_money_source_must_match_portfolio_kind(kind):
    with pytest.raises(ValidationError):
        PortfolioOutlookResponse.model_validate(monetary_payload(kind))


@pytest.mark.parametrize("field,value", [("monetary_projection",None),
    ("expected_return_30d",.04), ("current_weight",.5)])
def test_component_money_is_required_and_matches_its_own_return_and_allocation(field, value):
    body = monetary_payload()
    body["components"][0][field] = value
    with pytest.raises(ValidationError):
        PortfolioOutlookResponse.model_validate(body)


def test_legacy_cannot_expose_component_money():
    body = monetary_payload()
    body["baseline_kind"] = "legacy"
    body["monetary_projection"] = None
    with pytest.raises(ValidationError):
        PortfolioOutlookResponse.model_validate(body)
