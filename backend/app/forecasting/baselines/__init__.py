"""Simple deterministic forecast baselines for chronological evaluation."""

from .historical_mean import HistoricalMeanBaseline
from .moving_average import MovingAverageBaseline

__all__ = ["HistoricalMeanBaseline", "MovingAverageBaseline"]
