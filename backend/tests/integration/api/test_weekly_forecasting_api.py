"""Mocked authenticated weekly APIs; no real DB, fitting or artifact loading."""

from unittest.mock import MagicMock, patch
from uuid import UUID

from fastapi.testclient import TestClient
from pydantic import SecretStr
import pytest
from sqlalchemy.orm import Session

import app.api.dependencies as dependencies
import app.api.routes.weekly_forecasting as route
from app.core.config import settings
from app.core.instruments import USER_ASSET_SYMBOLS
from app.core.security import create_access_token
from app.database.models import Portfolio, User
from app.forecasting.inference_errors import (
    ForecastArtifactInvalidError, ForecastArtifactMissingError, ForecastDataStaleError,
    ForecastHistoryInsufficientError, ForecastPredictionError,
)
from app.forecasting.portfolio import InvalidForecastPortfolioError
from app.forecasting.weekly_portfolio import WeeklyPortfolioForecast, WeeklyPortfolioComponent
from app.main import app
from backend.tests.unit.forecasting.test_weekly_inference import asset


OWNER = UUID("99000000-0000-0000-0000-000000000001")
OTHER = UUID("99000000-0000-0000-0000-000000000002")
PORTFOLIO = UUID("99000000-0000-0000-0000-000000000003")
PRIVATE = "C:/private/model.joblib postgresql://user:secret@host/db traceback"


def asset_url(horizon=7, symbol="AAPL"):
    return f"/api/forecasting/assets/{symbol}/horizons/{horizon}/outlook"


def portfolio_url(horizon=7):
    return f"/api/forecasting/portfolios/{PORTFOLIO}/horizons/{horizon}/outlook"


def headers(user=OWNER):
    return {"Authorization": f"Bearer {create_access_token(user)}"}


def portfolio_forecast(portfolio, *, horizon_days):
    component = asset(horizon=horizon_days)
    return WeeklyPortfolioForecast(portfolio.id, portfolio.name, "current", horizon_days,
        component.expected_return, component.forecast_realized_volatility, component.origin_date,
        60, component.market_data_as_of, component.artifact_version,
        (WeeklyPortfolioComponent(component, 1., component.forecast_realized_volatility, 1.),))


@pytest.fixture
def harness():
    session = MagicMock(spec=Session)
    session.get.side_effect = lambda model, key: User(id=key)
    owned = Portfolio(id=PORTFOLIO, user_id=OWNER, name="Synthetic")
    assets, portfolios = MagicMock(), MagicMock()
    assets.predict.side_effect = lambda symbol, *, horizon_days: asset(symbol, horizon_days)
    portfolios.predict.side_effect = portfolio_forecast
    secret = settings.jwt_secret_key
    with (
        patch.object(dependencies, "_get_session_factory", return_value=MagicMock(return_value=session)),
        patch("app.services.portfolio_service.PortfolioRepository.get_with_holdings", return_value=owned) as repository,
        patch.object(route, "WeeklyForecastInferenceService", return_value=assets) as asset_constructor,
        patch.object(route, "WeeklyPortfolioForecastService", return_value=portfolios) as portfolio_constructor,
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        settings.jwt_secret_key = SecretStr("weekly-forecast-synthetic-secret-at-least-32-bytes")
        try:
            yield client, session, repository, assets, portfolios, asset_constructor, portfolio_constructor
        finally:
            settings.jwt_secret_key = secret


@pytest.mark.parametrize("horizon", [7,14,21])
@pytest.mark.parametrize("symbol", USER_ASSET_SYMBOLS)
def test_supported_weekly_asset_horizons_normalization_and_no_writes(harness, horizon, symbol):
    client, session, _, assets, _, construct, _ = harness
    response = client.get(asset_url(horizon, f"%20{symbol.lower()}%20"), headers=headers())
    assert response.status_code == 200
    body = response.json()
    assert body["symbol"] == symbol and body["horizon_days"] == horizon
    assert body["experimental"] is True and body["predictive_quality_approved"] is False
    assert body["return_warning_codes"] == ["final_interval_coverage_below_nominal"]
    assert "expected_return_30d" not in body and "calibration_residual_q10" not in body
    construct.assert_called_once_with(session)
    assets.predict.assert_called_once_with(symbol, horizon_days=horizon)
    for name in ("commit", "add", "delete", "execute"):
        getattr(session, name).assert_not_called()


@pytest.mark.parametrize("horizon", [7,14,21])
def test_owner_weekly_portfolio_full_contract_and_no_portfolio_interval(harness, horizon):
    client, session, repository, _, portfolios, _, construct = harness
    response = client.get(portfolio_url(horizon), headers=headers())
    assert response.status_code == 200
    body = response.json()
    assert body["portfolio_id"] == str(PORTFOLIO)
    assert body["horizon_days"] == body["components"][0]["horizon_days"] == horizon
    assert body["components"][0]["current_weight"] == 1.
    assert not any("interval" in key for key in body)
    construct.assert_called_once_with(session)
    assert portfolios.predict.call_args.kwargs == {"horizon_days": horizon}
    repository.assert_called_once_with(PORTFOLIO)
    for name in ("commit", "add", "delete", "execute"):
        getattr(session, name).assert_not_called()


@pytest.mark.parametrize("url", [asset_url(), portfolio_url()])
@pytest.mark.parametrize("auth", [{}, {"X-User-ID":str(OWNER)}, {"Authorization":"Bearer invalid"}])
def test_bearer_auth_required_before_models(harness, url, auth):
    client, _, repository, _, _, assets, portfolios = harness
    response = client.get(url, headers=auth)
    assert response.status_code == 401 and response.headers["www-authenticate"] == "Bearer"
    repository.assert_not_called()
    assets.assert_not_called()
    portfolios.assert_not_called()


@pytest.mark.parametrize("url", [asset_url(), portfolio_url()])
def test_unknown_user_rejected(harness, url):
    client, session, _, _, _, assets, portfolios = harness
    session.get.side_effect = None
    session.get.return_value = None
    assert client.get(url, headers=headers()).status_code == 401
    assets.assert_not_called()
    portfolios.assert_not_called()


@pytest.mark.parametrize("horizon", [0,8,30,"invalid"])
@pytest.mark.parametrize("url_builder", [asset_url, portfolio_url])
def test_bad_horizons_before_artifacts_or_portfolio(harness, horizon, url_builder):
    client, _, repository, _, _, assets, portfolios = harness
    assert client.get(url_builder(horizon), headers=headers()).status_code == 422
    repository.assert_not_called()
    assets.assert_not_called()
    portfolios.assert_not_called()


@pytest.mark.parametrize("symbol", ["THB=X", "INVALID"])
def test_unsupported_asset_no_models(harness, symbol):
    client, _, _, _, _, assets, _ = harness
    assert client.get(asset_url(symbol=symbol), headers=headers()).status_code == 404
    assets.assert_not_called()


@pytest.mark.parametrize("missing", [True, False])
def test_missing_and_wrong_owner_same_private_404(harness, missing):
    client, _, repository, _, _, _, portfolios = harness
    if missing:
        repository.return_value = None
    response = client.get(portfolio_url(), headers=headers(OWNER if missing else OTHER))
    assert response.status_code == 404 and response.json() == {"detail":"Portfolio not found"}
    portfolios.assert_not_called()


@pytest.mark.parametrize("url,index", [(asset_url(),3), (portfolio_url(),4)])
@pytest.mark.parametrize("error,status", [(ForecastArtifactMissingError,503), (ForecastArtifactInvalidError,503),
    (ForecastDataStaleError,503), (ForecastHistoryInsufficientError,503), (ForecastPredictionError,503), (RuntimeError,500)])
def test_failures_sanitized_without_fallback(harness, url, index, error, status):
    client = harness[0]
    harness[index].predict.side_effect = error(PRIVATE)
    response = client.get(url, headers=headers())
    assert response.status_code == status
    assert not any(private in response.text for private in ("private", "secret", "traceback", "joblib", "postgresql"))


def test_invalid_portfolio_state_is_409(harness):
    client, _, _, _, portfolios, _, _ = harness
    portfolios.predict.side_effect = InvalidForecastPortfolioError(PRIVATE)
    assert client.get(portfolio_url(), headers=headers()).status_code == 409


def test_mismatched_service_horizon_not_published(harness):
    client, _, _, assets, portfolios, _, _ = harness
    assets.predict.side_effect = None
    assets.predict.return_value = asset(horizon=14)
    assert client.get(asset_url(7), headers=headers()).status_code == 503
    portfolios.predict.side_effect = lambda portfolio, **kwargs: portfolio_forecast(portfolio, horizon_days=14)
    assert client.get(portfolio_url(7), headers=headers()).status_code == 503


def test_weekly_openapi_is_read_only_authenticated_and_neutral_fields():
    schema = app.openapi()
    paths = ["/api/forecasting/assets/{symbol}/horizons/{horizon_days}/outlook",
             "/api/forecasting/portfolios/{portfolio_id}/horizons/{horizon_days}/outlook"]
    for path in paths:
        operations = schema["paths"][path]
        assert set(operations) == {"get"}
        assert operations["get"]["security"] == [{"HTTPBearer":[]}]
        assert "requestBody" not in operations["get"]
        assert [item["in"] for item in operations["get"]["parameters"]] == ["path","path"]
    properties = schema["components"]["schemas"]["WeeklyAssetOutlookResponse"]["properties"]
    assert "expected_return" in properties and "expected_return_30d" not in properties
    assert properties["horizon_days"]["enum"] == [7,14,21]
    assert not {"model_path", "final_test_evidence", "calibration_residual_q10"} & set(properties)
