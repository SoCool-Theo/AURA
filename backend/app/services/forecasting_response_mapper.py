"""Pure mapping of internal forecasts to the public asset outlook contract."""

from dataclasses import asdict

from ..forecasting.inference import AssetForecast
from ..forecasting.portfolio import PortfolioForecast
from ..schemas.forecasting import (
    FORECAST_LIMITATIONS,
    AssetOutlookResponse,
    ForecastPredictionInterval,
    VolatilityPredictionInterval,
    PORTFOLIO_FORECAST_LIMITATIONS,
    PortfolioOutlookComponent,
    PortfolioOutlookResponse,
)


def map_asset_outlook(forecast: AssetForecast) -> AssetOutlookResponse:
    """Copy model-owned numbers without rounding or recalculating them."""
    return AssetOutlookResponse(
        symbol=forecast.symbol,
        forecast_origin_date=forecast.origin_date,
        horizon_days=forecast.horizon_days,
        expected_return_30d=forecast.expected_return_30d,
        return_prediction_interval=ForecastPredictionInterval(
            lower=forecast.return_interval_lower,
            upper=forecast.return_interval_upper,
            coverage=forecast.interval_coverage,
        ),
        forecast_realized_volatility_30d=forecast.forecast_realized_volatility_30d,
        volatility_prediction_interval=VolatilityPredictionInterval(
            lower=forecast.volatility_interval_lower,
            upper=forecast.volatility_interval_upper,
            coverage=forecast.interval_coverage,
        ),
        market_data_as_of=forecast.market_data_as_of,
        market_data_age_days=forecast.market_data_age_days,
        artifact_version=forecast.artifact_version,
        return_model_id=forecast.return_model_id,
        volatility_model_id=forecast.volatility_model_id,
        limitations=list(FORECAST_LIMITATIONS),
    )


def map_portfolio_outlook(forecast: PortfolioForecast) -> PortfolioOutlookResponse:
    """Copy composition and component results without recalculation."""
    return PortfolioOutlookResponse(
        portfolio_id=forecast.portfolio_id,
        portfolio_name=forecast.portfolio_name,
        baseline_kind=forecast.baseline_kind,
        horizon_days=30,
        expected_return_30d=forecast.expected_return_30d,
        forecast_realized_volatility_30d=forecast.forecast_realized_volatility_30d,
        correlation_as_of_date=forecast.correlation_as_of_date,
        correlation_observation_count=forecast.correlation_observation_count,
        market_data_as_of=forecast.market_data_as_of,
        artifact_version=forecast.artifact_version,
        components=[
            PortfolioOutlookComponent(
                **map_asset_outlook(component.forecast).model_dump(),
                current_weight=component.current_weight,
                forecast_volatility_contribution=component.forecast_volatility_contribution,
                forecast_volatility_contribution_share=component.forecast_volatility_contribution_share,
                monetary_projection=asdict(component.monetary_projection) if component.monetary_projection is not None else None,
            )
            for component in forecast.components
        ],
        monetary_projection=asdict(forecast.monetary_projection) if forecast.monetary_projection is not None else None,
        limitations=list(PORTFOLIO_FORECAST_LIMITATIONS),
    )
