"""Provider-neutral failures for internal forecasting inference."""


class ForecastInferenceError(ValueError):
    """Base controlled inference failure."""


class ForecastArtifactMissingError(ForecastInferenceError):
    """Required artifact files are missing."""


class ForecastArtifactInvalidError(ForecastInferenceError):
    """Artifact integrity or its internal contract is invalid."""


class ForecastArtifactVersionError(ForecastArtifactInvalidError):
    """Configured and deployed versions differ."""


class ForecastSymbolUnsupportedError(ForecastInferenceError):
    """Symbol is outside Aura's supported asset set."""


class ForecastHistoryInsufficientError(ForecastInferenceError):
    """Persisted observations cannot construct current forecast input."""


class ForecastDataStaleError(ForecastInferenceError):
    """Latest persisted market observation exceeds the freshness limit."""


class ForecastMarketDataUnavailableError(ForecastInferenceError):
    """Application persistence cannot supply forecast observations."""


class ForecastPredictionError(ForecastInferenceError):
    """Selected model failed or returned invalid output."""
