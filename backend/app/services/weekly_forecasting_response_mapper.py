"""Copy weekly model-owned numbers and retained warnings into public contracts."""

from dataclasses import asdict

from ..forecasting.weekly_inference import WeeklyAssetForecast
from ..forecasting.weekly_portfolio import WeeklyPortfolioForecast
from ..schemas.weekly_forecasting import (
    WEEKLY_ASSET_LIMITATIONS, WEEKLY_PORTFOLIO_LIMITATIONS,
    WeeklyAssetOutlookResponse, WeeklyPortfolioOutlookComponent, WeeklyPortfolioOutlookResponse,
)


QUALITY_FIELDS = {
    "experimental": True, "predictive_quality_approved": False,
    "quality_status": "experimental_educational_not_predictive_quality_approved",
}


def map_weekly_asset_outlook(forecast: WeeklyAssetForecast) -> WeeklyAssetOutlookResponse:
    return WeeklyAssetOutlookResponse(
        symbol=forecast.symbol, forecast_origin_date=forecast.origin_date,
        horizon_days=forecast.horizon_days, horizon_unit="calendar_days",
        expected_return=forecast.expected_return,
        return_prediction_interval={"lower": forecast.return_interval_lower,
            "upper": forecast.return_interval_upper, "coverage": forecast.interval_coverage},
        forecast_realized_volatility=forecast.forecast_realized_volatility,
        volatility_prediction_interval={"lower": forecast.volatility_interval_lower,
            "upper": forecast.volatility_interval_upper, "coverage": forecast.interval_coverage},
        market_data_as_of=forecast.market_data_as_of, market_data_age_days=forecast.market_data_age_days,
        artifact_version=forecast.artifact_version, return_model_id=forecast.return_model_id,
        volatility_model_id=forecast.volatility_model_id,
        return_warning_codes=list(forecast.return_warning_codes),
        volatility_warning_codes=list(forecast.volatility_warning_codes),
        limitations=list(WEEKLY_ASSET_LIMITATIONS), **QUALITY_FIELDS,
    )


def map_weekly_portfolio_outlook(forecast: WeeklyPortfolioForecast) -> WeeklyPortfolioOutlookResponse:
    return WeeklyPortfolioOutlookResponse(
        portfolio_id=forecast.portfolio_id, portfolio_name=forecast.portfolio_name,
        baseline_kind=forecast.baseline_kind, horizon_days=forecast.horizon_days, horizon_unit="calendar_days",
        expected_return=forecast.expected_return, forecast_realized_volatility=forecast.forecast_realized_volatility,
        correlation_as_of_date=forecast.correlation_as_of_date,
        correlation_observation_count=forecast.correlation_observation_count,
        market_data_as_of=forecast.market_data_as_of, artifact_version=forecast.artifact_version,
        components=[WeeklyPortfolioOutlookComponent(
            **map_weekly_asset_outlook(component.forecast).model_dump(),
            current_weight=component.current_weight,
            forecast_volatility_contribution=component.forecast_volatility_contribution,
            forecast_volatility_contribution_share=component.forecast_volatility_contribution_share,
        ) for component in forecast.components],
        monetary_projection=asdict(forecast.monetary_projection) if forecast.monetary_projection is not None else None,
        limitations=list(WEEKLY_PORTFOLIO_LIMITATIONS), **QUALITY_FIELDS,
    )
