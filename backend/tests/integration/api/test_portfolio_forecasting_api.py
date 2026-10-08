"""Authenticated synthetic portfolio outlook; no database or model execution."""

from dataclasses import replace
from datetime import date
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.orm import Session

import app.api.dependencies as dependencies
import app.api.routes.forecasting as route
from app.core.config import settings
from app.core.security import create_access_token
from app.database.models import Portfolio, User
from app.forecasting.inference import AssetForecast
from app.forecasting.inference_errors import (
    ForecastArtifactInvalidError, ForecastArtifactMissingError, ForecastDataStaleError,
    ForecastHistoryInsufficientError, ForecastPredictionError, ForecastSymbolUnsupportedError,
)
from app.forecasting.portfolio import InvalidForecastPortfolioError, PortfolioForecast, PortfolioForecastComponent
from app.main import app
from app.schemas.forecasting import PortfolioOutlookResponse, PORTFOLIO_FORECAST_LIMITATIONS
from app.services.market_data_service import MarketDataUnavailableError
from app.services.portfolio_valuation_service import InvalidHoldingModeError


OWNER = UUID("91000000-0000-0000-0000-000000000001")
PORTFOLIO = UUID("91000000-0000-0000-0000-000000000002")
OTHER = UUID("91000000-0000-0000-0000-000000000003")
URL = f"/api/forecasting/portfolios/{PORTFOLIO}/outlook"
PRIVATE = "C:/secret/model.joblib postgresql://user:password@host/db traceback"


def forecast():
    day = date(2026,10,1)
    asset = AssetForecast("AAPL",day,30,.03,-.1,.2,.05,0,.2,.8,
        "historical_average","historical_average","forecast-v1-20260917",
        "forecast-features-v1","forecast-targets-v1",day,0)
    return PortfolioForecast(PORTFOLIO,"Synthetic","current",.03,.05,day,60,day,
                             asset.artifact_version,(PortfolioForecastComponent(asset,1.,.05,1.),))


@pytest.fixture
def harness():
    session = MagicMock(spec=Session)
    session.get.side_effect = lambda model,key: User(id=key)
    owned = Portfolio(id=PORTFOLIO,user_id=OWNER,name="Synthetic")
    service = MagicMock(spec=route.PortfolioForecastService)
    service.predict.return_value = forecast()
    secret = settings.jwt_secret_key
    with (
        patch.object(dependencies,"_get_session_factory",return_value=MagicMock(return_value=session)),
        patch("app.services.portfolio_service.PortfolioRepository.get_with_holdings",return_value=owned) as repository,
        patch.object(route,"PortfolioForecastService",return_value=service) as constructor,
        TestClient(app,raise_server_exceptions=False) as client,
    ):
        settings.jwt_secret_key = SecretStr("synthetic-portfolio-forecast-secret-at-least-32-bytes")
        try:
            yield client,session,owned,repository,service,constructor
        finally:
            settings.jwt_secret_key = secret


def headers(user=OWNER):
    return {"Authorization":f"Bearer {create_access_token(user)}"}


def test_authenticated_success_ownership_and_public_response(harness):
    client,session,owned,repository,service,constructor = harness
    response = client.get(URL,headers=headers())
    assert response.status_code == 200
    constructor.assert_called_once_with(session)
    service.predict.assert_called_once_with(owned)
    repository.assert_called_once_with(PORTFOLIO)
    body = response.json()
    assert body["expected_return_30d"] == .03
    assert body["forecast_realized_volatility_30d"] == .05
    assert body["limitations"] == list(PORTFOLIO_FORECAST_LIMITATIONS)
    assert body["components"][0]["current_weight"] == 1
    assert body["components"][0]["return_prediction_interval"]["coverage"] == .8
    assert not any("interval" in key for key in body)
    PortfolioOutlookResponse.model_validate(body)
    for method in ("commit","add","delete","execute"):
        getattr(session,method).assert_not_called()


@pytest.mark.parametrize("auth", [{},{"X-User-ID":str(OWNER)},{"Authorization":"Bearer invalid"}])
def test_auth_required_before_ownership_or_forecast(harness,auth):
    client,_,_,repository,_,constructor = harness
    response = client.get(URL,headers=auth)
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    repository.assert_not_called(); constructor.assert_not_called()


@pytest.mark.parametrize("missing", [False,True])
def test_missing_and_other_owner_are_same_private_404(harness,missing):
    client,_,_,repository,_,constructor = harness
    if missing:
        repository.return_value = None
    response = client.get(URL,headers=headers(OTHER if not missing else OWNER))
    assert response.status_code == 404
    assert response.json() == {"detail":"Portfolio not found"}
    constructor.assert_not_called()


@pytest.mark.parametrize("error,code", [(InvalidForecastPortfolioError,409),(InvalidHoldingModeError,409),
    (ForecastSymbolUnsupportedError,409),(ForecastDataStaleError,503),(ForecastHistoryInsufficientError,503),
    (ForecastArtifactMissingError,503),(ForecastArtifactInvalidError,503),(ForecastPredictionError,503),
    (MarketDataUnavailableError,503),(RuntimeError,500)])
def test_safe_errors_no_private_details(harness,error,code):
    client,_,_,_,service,_ = harness
    service.predict.side_effect = error(PRIVATE)
    response = client.get(URL,headers=headers())
    assert response.status_code == code
    assert "secret" not in response.text and "postgresql" not in response.text
    assert "joblib" not in response.text and "traceback" not in response.text


def test_safe_ownership_lookup_error(harness):
    client,_,_,repository,_,constructor = harness
    repository.side_effect = RuntimeError(PRIVATE)
    response = client.get(URL,headers=headers())
    assert response.status_code == 500
    assert response.json() == {"detail":"Unable to retrieve portfolio outlook"}
    constructor.assert_not_called()


def test_request_cannot_override_weights_horizon_or_asof(harness):
    client,_,owned,_,service,_ = harness
    response = client.request("GET",URL+"?weights=0&horizon_days=99&as_of=1900-01-01",
                              headers=headers(),json={"weights":[],"portfolio_id":str(OTHER)})
    assert response.status_code == 200
    service.predict.assert_called_once_with(owned)
    assert response.json()["horizon_days"] == 30
    assert response.json()["components"][0]["current_weight"] == 1


@pytest.mark.parametrize("change", [{"expected_return_30d":float("nan")},
    {"forecast_realized_volatility_30d":float("inf")},{"correlation_observation_count":59}])
def test_invalid_composition_safely_unavailable(harness,change):
    client,_,_,_,service,_ = harness
    service.predict.return_value = replace(forecast(),**change)
    response = client.get(URL,headers=headers())
    assert response.status_code == 503
    assert response.json() == {"detail":"Forecast is currently unavailable."}


def test_portfolio_openapi_has_only_uuid_path_and_existing_bearer():
    operation = app.openapi()["paths"]["/api/forecasting/portfolios/{portfolio_id}/outlook"]
    assert set(operation) == {"get"}
    get = operation["get"]
    assert "requestBody" not in get
    assert [(p["name"],p["in"]) for p in get["parameters"]] == [("portfolio_id","path")]
    assert get["security"] == [{"HTTPBearer":[]}]
    assert {"200","401","404","409","422","503"} <= set(get["responses"])
