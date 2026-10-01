"""Finite JSON and provenance invariants for portfolio forecast responses."""

from copy import deepcopy
from datetime import date
from uuid import uuid4

import pytest
from pydantic import ValidationError

from backend.app.forecasting.inference import AssetForecast
from backend.app.forecasting.portfolio import PortfolioForecast, PortfolioForecastComponent
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
