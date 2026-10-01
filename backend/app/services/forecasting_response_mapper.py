"""Pure mapping of internal forecasts to the public asset outlook contract."""

from ..forecasting.inference import AssetForecast
from ..schemas.forecasting import (
    FORECAST_LIMITATIONS,
    AssetOutlookResponse,
    ForecastPredictionInterval,
    VolatilityPredictionInterval,
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
