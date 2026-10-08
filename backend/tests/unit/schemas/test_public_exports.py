import backend.app.schemas as schemas_package
from backend.app.schemas.analytics import (
    AnalysisMetadata,
    AssetMetrics,
    ConcentrationMetrics,
    CorrelationMatrix,
    CorrelationPair,
    DiversificationMetrics,
    MaximumDrawdownMetrics,
    PortfolioAnalysisResponse,
    PortfolioMetrics,
    PortfolioReturnPoint,
    RiskClassification,
    RiskDriverAnalysis,
    RiskDriverEntry,
)
from backend.app.schemas.common import AnalysisPeriod, AssetSymbol
from backend.app.schemas.market_data import (
    AssetPriceSeries,
    HistoricalMarketDataRequest,
    HistoricalMarketDataResponse,
    HistoricalPricePoint,
)
from backend.app.schemas.portfolio import (
    PortfolioAnalysisRequest,
    PortfolioHoldingInput,
)


_EXPECTED_EXPORTS = [
    "AssetSymbol",
    "AnalysisPeriod",
    "PortfolioHoldingInput",
    "PortfolioAnalysisRequest",
    "HistoricalMarketDataRequest",
    "HistoricalPricePoint",
    "AssetPriceSeries",
    "HistoricalMarketDataResponse",
    "MaximumDrawdownMetrics",
    "ConcentrationMetrics",
    "DiversificationMetrics",
    "RiskDriverEntry",
    "RiskClassification",
    "AssetMetrics",
    "CorrelationPair",
    "CorrelationMatrix",
    "AnalysisMetadata",
    "PortfolioMetrics",
    "PortfolioReturnPoint",
    "RiskDriverAnalysis",
    "PortfolioAnalysisResponse",
]

_SOURCE_OBJECTS = {
    "AssetSymbol": AssetSymbol,
    "AnalysisPeriod": AnalysisPeriod,
    "PortfolioHoldingInput": PortfolioHoldingInput,
    "PortfolioAnalysisRequest": PortfolioAnalysisRequest,
    "HistoricalMarketDataRequest": HistoricalMarketDataRequest,
    "HistoricalPricePoint": HistoricalPricePoint,
    "AssetPriceSeries": AssetPriceSeries,
    "HistoricalMarketDataResponse": HistoricalMarketDataResponse,
    "MaximumDrawdownMetrics": MaximumDrawdownMetrics,
    "ConcentrationMetrics": ConcentrationMetrics,
    "DiversificationMetrics": DiversificationMetrics,
    "RiskDriverEntry": RiskDriverEntry,
    "RiskClassification": RiskClassification,
    "AssetMetrics": AssetMetrics,
    "CorrelationPair": CorrelationPair,
    "CorrelationMatrix": CorrelationMatrix,
    "AnalysisMetadata": AnalysisMetadata,
    "PortfolioMetrics": PortfolioMetrics,
    "PortfolioReturnPoint": PortfolioReturnPoint,
    "RiskDriverAnalysis": RiskDriverAnalysis,
    "PortfolioAnalysisResponse": PortfolioAnalysisResponse,
}


def test_package_exports_exact_approved_public_names() -> None:
    assert schemas_package.__all__ == _EXPECTED_EXPORTS
    assert len(schemas_package.__all__) == len(set(schemas_package.__all__))


def test_every_public_name_is_importable_from_package() -> None:
    for name in _EXPECTED_EXPORTS:
        assert getattr(schemas_package, name) is _SOURCE_OBJECTS[name]


def test_package_exports_are_the_source_module_objects() -> None:
    assert {
        name: getattr(schemas_package, name)
        for name in schemas_package.__all__
    } == _SOURCE_OBJECTS


def test_base_and_simulation_contracts_are_not_publicly_exported() -> None:
    assert "AuraBaseModel" not in schemas_package.__all__
    assert not any(
        "Simulation" in name for name in schemas_package.__all__
    )


def test_importing_schema_package_requires_no_application_startup() -> None:
    assert schemas_package.PortfolioAnalysisRequest is PortfolioAnalysisRequest
    assert schemas_package.PortfolioAnalysisResponse is PortfolioAnalysisResponse
