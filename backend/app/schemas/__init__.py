"""Stable public interface for Aura's Pydantic data contracts."""

from .analytics import (
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
from .common import AnalysisPeriod, AssetSymbol
from .market_data import (
    AssetPriceSeries,
    HistoricalMarketDataRequest,
    HistoricalMarketDataResponse,
    HistoricalPricePoint,
)
from .portfolio import PortfolioAnalysisRequest, PortfolioHoldingInput


__all__ = [
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
