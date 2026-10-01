from collections.abc import Iterator
from dataclasses import replace
from datetime import date
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.orm import Session

import app.api.dependencies as dependency_module
import app.api.routes.forecasting as route_module
from app.core.config import settings
from app.core.instruments import USER_ASSET_SYMBOLS
from app.core.security import create_access_token
from app.database.models import User
from app.forecasting.inference import AssetForecast
from app.forecasting.inference_errors import (
    ForecastArtifactInvalidError, ForecastArtifactMissingError, ForecastArtifactVersionError,
    ForecastDataStaleError, ForecastHistoryInsufficientError, ForecastInferenceError,
    ForecastMarketDataUnavailableError, ForecastPredictionError, ForecastSymbolUnsupportedError,
)
from app.main import app
from app.schemas.forecasting import FORECAST_LIMITATIONS


USER_ID = UUID("82000000-0000-0000-0000-000000000001")
JWT_SECRET = "forecast-api-synthetic-jwt-secret-at-least-32-bytes"
PRIVATE_DETAILS = "C:/private/models/model.joblib postgresql://user:private-password@host/db traceback"


def outlook(symbol="AAPL"):
    return AssetForecast(
        symbol, date(2026, 10, 1), 30, 0.032, -0.087, 0.14, 0.063, 0.0, 0.18,
        0.80, "historical_average", "volatility_linear_regression_v1",
        "forecast-v1-20260917", "forecast-features-v1", "forecast-targets-v1",
        date(2026, 10, 1), 0,
    )


@pytest.fixture
def api_harness() -> Iterator:
    session = MagicMock(spec=Session)
    session.get.side_effect = lambda model, user_id: User(id=user_id)
    factory = MagicMock(return_value=session)
    service = MagicMock(spec=route_module.ForecastInferenceService)
    service.predict.return_value = outlook()
    previous_secret = settings.jwt_secret_key
    with (
        patch.object(dependency_module, "_get_session_factory", return_value=factory),
        patch.object(route_module, "ForecastInferenceService", return_value=service) as construct,
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        settings.jwt_secret_key = SecretStr(JWT_SECRET)
        try:
            yield client, session, service, construct
        finally:
            settings.jwt_secret_key = previous_secret


def headers():
    return {"Authorization": f"Bearer {create_access_token(USER_ID)}"}


def test_authenticated_outlook_delegates_and_exposes_only_public_fields(api_harness):
    client, session, service, construct = api_harness
    with (
        patch("app.forecasting.finalization.train_deployment_artifact", side_effect=AssertionError("training")),
        patch("app.forecasting.registry.joblib.load", side_effect=AssertionError("route deserialization")),
        patch("app.forecasting.features.build_feature_rows", side_effect=AssertionError("route features")),
    ):
        response = client.get("/api/forecasting/assets/AAPL/outlook", headers=headers())
    assert response.status_code == 200
    construct.assert_called_once_with(session)
    service.predict.assert_called_once_with("AAPL")
    assert response.json() == {
        "symbol": "AAPL", "forecast_origin_date": "2026-10-01", "horizon_days": 30,
        "expected_return_30d": 0.032,
        "return_prediction_interval": {"lower": -0.087, "upper": 0.14, "coverage": 0.80},
        "forecast_realized_volatility_30d": 0.063,
        "volatility_prediction_interval": {"lower": 0.0, "upper": 0.18, "coverage": 0.80},
        "market_data_as_of": "2026-10-01", "market_data_age_days": 0,
        "artifact_version": "forecast-v1-20260917", "return_model_id": "historical_average",
        "volatility_model_id": "volatility_linear_regression_v1", "limitations": list(FORECAST_LIMITATIONS),
    }
    for name in ("commit", "add", "delete", "execute"):
        getattr(session, name).assert_not_called()


@pytest.mark.parametrize("request_headers", [{}, {"X-User-ID": str(USER_ID)}, {"Authorization": "Bearer invalid"}])
def test_outlook_requires_existing_bearer_authentication(api_harness, request_headers):
    client, session, service, construct = api_harness
    response = client.get("/api/forecasting/assets/AAPL/outlook", headers=request_headers)
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or missing authentication credentials"}
    assert response.headers["www-authenticate"] == "Bearer"
    construct.assert_not_called()
    service.predict.assert_not_called()


def test_unknown_authenticated_user_is_rejected(api_harness):
    client, session, service, construct = api_harness
    session.get.side_effect = None
    session.get.return_value = None
    assert client.get("/api/forecasting/assets/AAPL/outlook", headers=headers()).status_code == 401
    construct.assert_not_called()


@pytest.mark.parametrize("symbol", USER_ASSET_SYMBOLS)
def test_supported_symbols_are_normalized_and_delegated(api_harness, symbol):
    client, session, service, construct = api_harness
    service.predict.return_value = outlook(symbol)
    response = client.get(f"/api/forecasting/assets/%20{symbol.lower()}%20/outlook", headers=headers())
    assert response.status_code == 200
    service.predict.assert_called_once_with(symbol)


@pytest.mark.parametrize("symbol", ["ASDF", "THB=X", "%20%20"])
def test_unsupported_symbols_return_404_without_constructing_inference(api_harness, symbol):
    client, session, service, construct = api_harness
    response = client.get(f"/api/forecasting/assets/{symbol}/outlook", headers=headers())
    assert response.status_code == 404
    assert response.json() == {"detail": "Unsupported asset symbol"}
    construct.assert_not_called()


@pytest.mark.parametrize("error_type, status_code, detail", [
    (ForecastSymbolUnsupportedError, 404, "Unsupported asset symbol"),
    (ForecastDataStaleError, 503, "Forecast unavailable because current market data is stale."),
    (ForecastHistoryInsufficientError, 503, "Forecast unavailable because market history is insufficient."),
    (ForecastArtifactMissingError, 503, "Forecast is currently unavailable."),
    (ForecastArtifactInvalidError, 503, "Forecast is currently unavailable."),
    (ForecastArtifactVersionError, 503, "Forecast is currently unavailable."),
    (ForecastPredictionError, 503, "Forecast is currently unavailable."),
    (ForecastMarketDataUnavailableError, 503, "Forecast is currently unavailable."),
    (ForecastInferenceError, 503, "Forecast is currently unavailable."),
    (RuntimeError, 500, "Unable to retrieve asset outlook"),
])
def test_forecasting_errors_are_safely_mapped_without_internal_leakage(api_harness, error_type, status_code, detail):
    client, session, service, construct = api_harness
    service.predict.side_effect = error_type(PRIVATE_DETAILS)
    response = client.get("/api/forecasting/assets/AAPL/outlook", headers=headers())
    assert response.status_code == status_code
    assert response.json() == {"detail": detail}
    assert "private" not in response.text
    assert "joblib" not in response.text
    session.commit.assert_not_called()


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_invalid_inference_values_are_rejected_as_unavailable(api_harness, value):
    client, session, service, construct = api_harness
    service.predict.return_value = replace(outlook(), expected_return_30d=value)
    response = client.get("/api/forecasting/assets/AAPL/outlook", headers=headers())
    assert response.status_code == 503
    assert response.json() == {"detail": "Forecast is currently unavailable."}


def test_inference_construction_errors_are_sanitized(api_harness):
    client, session, service, construct = api_harness
    construct.side_effect = ForecastArtifactVersionError(PRIVATE_DETAILS)
    response = client.get("/api/forecasting/assets/AAPL/outlook", headers=headers())
    assert response.status_code == 503
    assert response.json() == {"detail": "Forecast is currently unavailable."}


def test_openapi_exposes_only_current_authenticated_asset_outlook():
    schema = app.openapi()
    paths = {path for path in schema["paths"] if path.startswith("/api/forecasting")}
    assert paths == {"/api/forecasting/assets/{symbol}/outlook", "/api/forecasting/portfolios/{portfolio_id}/outlook"}
    operation = schema["paths"]["/api/forecasting/assets/{symbol}/outlook"]
    assert set(operation) == {"get"}
    assert operation["get"]["security"] == [{"HTTPBearer": []}]
    assert "requestBody" not in operation["get"]
    assert [(item["name"], item["in"]) for item in operation["get"]["parameters"]] == [("symbol", "path")]
    assert {"401", "404", "503"} <= set(operation["get"]["responses"])
    public_properties = schema["components"]["schemas"]["AssetOutlookResponse"]["properties"]
    assert "directional_accuracy" not in public_properties
    assert "calibration_residual_q10" not in public_properties
    assert "feature_version" not in public_properties
