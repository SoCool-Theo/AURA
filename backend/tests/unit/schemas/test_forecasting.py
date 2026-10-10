from copy import deepcopy
from dataclasses import replace
from datetime import date
import json

import pytest
from pydantic import ValidationError

from backend.app.forecasting.inference import AssetForecast
from backend.app.schemas.forecasting import FORECAST_LIMITATIONS, AssetOutlookResponse
from backend.app.services.forecasting_response_mapper import map_asset_outlook


def forecast():
    return AssetForecast(
        symbol="AAPL", origin_date=date(2026, 10, 1), horizon_days=30,
        expected_return_30d=0.032, return_interval_lower=-0.087,
        return_interval_upper=0.14, forecast_realized_volatility_30d=0.063,
        volatility_interval_lower=0.0, volatility_interval_upper=0.18,
        interval_coverage=0.80, return_model_id="historical_average",
        volatility_model_id="volatility_linear_regression_v1",
        artifact_version="forecast-v1-20260917", feature_version="forecast-features-v1",
        target_version="forecast-targets-v1", market_data_as_of=date(2026, 10, 1),
        market_data_age_days=0,
    )


def test_valid_outlook_nested_intervals_numeric_serialization_and_pure_mapping():
    original = forecast()
    before = deepcopy(original)
    response = map_asset_outlook(original)
    assert original == before
    payload = json.loads(response.model_dump_json())
    assert payload["expected_return_30d"] == 0.032
    assert type(payload["expected_return_30d"]) is float
    assert payload["return_prediction_interval"] == {"lower": -0.087, "upper": 0.14, "coverage": 0.80}
    assert payload["volatility_prediction_interval"] == {"lower": 0.0, "upper": 0.18, "coverage": 0.80}
    assert payload["forecast_origin_date"] == payload["market_data_as_of"] == "2026-10-01"
    assert payload["limitations"] == list(FORECAST_LIMITATIONS)
    assert response == map_asset_outlook(original)
    assert set(payload) == {
        "symbol", "forecast_origin_date", "horizon_days", "expected_return_30d",
        "return_prediction_interval", "forecast_realized_volatility_30d",
        "volatility_prediction_interval", "market_data_as_of", "market_data_age_days",
        "artifact_version", "return_model_id", "volatility_model_id", "limitations",
    }


@pytest.mark.parametrize("field", [
    "artifact_version", "return_model_id", "volatility_model_id",
    "forecast_origin_date", "market_data_as_of", "market_data_age_days",
])
def test_provenance_fields_are_required(field):
    payload = map_asset_outlook(forecast()).model_dump()
    payload.pop(field)
    with pytest.raises(ValidationError):
        AssetOutlookResponse.model_validate(payload)


@pytest.mark.parametrize("field", [
    "expected_return_30d", "return_interval_lower", "return_interval_upper",
    "forecast_realized_volatility_30d", "volatility_interval_lower", "volatility_interval_upper",
])
@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_model_values_are_rejected(field, value):
    with pytest.raises(ValidationError):
        map_asset_outlook(replace(forecast(), **{field: value}))


@pytest.mark.parametrize("updates", [
    {"horizon_days": 31}, {"interval_coverage": 0.95},
    {"return_interval_lower": 1.0}, {"forecast_realized_volatility_30d": -0.01},
    {"volatility_interval_lower": -0.01}, {"volatility_interval_upper": -0.01},
    {"market_data_age_days": -1}, {"market_data_age_days": 5},
    {"market_data_as_of": date(2026, 9, 30)},
    {"artifact_version": "/private/path"}, {"return_model_id": "unknown"},
    {"volatility_model_id": "linear_regression_v1"},
])
def test_locked_contract_and_volatility_constraints(updates):
    with pytest.raises(ValidationError):
        map_asset_outlook(replace(forecast(), **updates))


@pytest.mark.parametrize("value", [-2.5, 4.125])
def test_return_values_are_not_clamped(value):
    response = map_asset_outlook(replace(forecast(), expected_return_30d=value))
    assert response.expected_return_30d == value


def test_symbol_normalization_and_unknown_fields():
    payload = map_asset_outlook(forecast()).model_dump()
    payload["symbol"] = " aapl "
    assert AssetOutlookResponse.model_validate(payload).symbol == "AAPL"
    payload["symbol"] = "THB=X"
    with pytest.raises(ValidationError):
        AssetOutlookResponse.model_validate(payload)
    payload["symbol"] = "AAPL"
    payload["calibration_residual_q10"] = -0.1
    with pytest.raises(ValidationError):
        AssetOutlookResponse.model_validate(payload)


def test_limitations_cannot_be_replaced_with_advice():
    payload = map_asset_outlook(forecast()).model_dump()
    payload["limitations"] = ["Buy this asset"]
    with pytest.raises(ValidationError):
        AssetOutlookResponse.model_validate(payload)
