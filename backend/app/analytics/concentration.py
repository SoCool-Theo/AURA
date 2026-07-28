"""Portfolio concentration calculations for validated decimal weights."""

import math
from collections.abc import Mapping
from dataclasses import dataclass
from numbers import Integral, Real

import numpy as np


_WEIGHT_TOLERANCE = 1e-6


@dataclass(frozen=True, slots=True)
class ConcentrationResult:
    """Contain quantitative portfolio concentration metrics."""

    largest_weight: float
    top_n_weight: float
    hhi: float
    effective_number_of_assets: float
    top_n: int


def _validated_weights(weights: Mapping[str, float]) -> list[float]:
    if not isinstance(weights, Mapping):
        raise TypeError("weights must implement Mapping")

    weight_items = list(weights.items())
    if not weight_items:
        raise ValueError("weights must contain at least one asset")

    symbols = [symbol for symbol, _ in weight_items]
    for symbol in symbols:
        if not isinstance(symbol, str):
            raise TypeError("weight symbols must be strings")
        if not symbol:
            raise ValueError("weight symbols cannot be empty")
        if not symbol.strip():
            raise ValueError("weight symbols cannot be whitespace-only")
        if symbol != symbol.strip():
            raise ValueError(
                "weight symbols cannot contain leading or trailing whitespace"
            )
    if len(symbols) != len(set(symbols)):
        raise ValueError("weight symbols must be unique")

    validated: list[float] = []
    for _, value in weight_items:
        if isinstance(value, (bool, np.bool_)):
            raise TypeError("weight values cannot be Boolean")
        if isinstance(value, (complex, np.complexfloating)):
            raise TypeError("weight values cannot be complex")
        if not isinstance(value, Real):
            raise TypeError("weight values must be real numeric values")

        numeric_value = float(value)
        if not math.isfinite(numeric_value):
            raise ValueError("weight values must be finite")
        if numeric_value < 0.0 or numeric_value > 1.0:
            raise ValueError(
                "each weight must be between 0.0 and 1.0 inclusive"
            )
        validated.append(numeric_value)

    if not any(value > 0.0 for value in validated):
        raise ValueError("at least one weight must be greater than zero")

    total_weight = math.fsum(validated)
    if abs(total_weight - 1.0) > _WEIGHT_TOLERANCE:
        raise ValueError(
            "total weight must equal 1.0 within a tolerance of 1e-6"
        )
    return validated


def _validate_top_n(top_n: int) -> int:
    if isinstance(top_n, (bool, np.bool_)) or not isinstance(top_n, Integral):
        raise TypeError("top_n must be an integer")
    if top_n <= 0:
        raise ValueError("top_n must be greater than zero")
    return int(top_n)


def calculate_largest_weight(weights: Mapping[str, float]) -> float:
    """Return the portfolio's largest individual asset weight."""
    validated_weights = _validated_weights(weights)
    return float(max(validated_weights))


def calculate_top_n_concentration(
    weights: Mapping[str, float], top_n: int = 3
) -> float:
    """Sum the largest requested number of validated portfolio weights."""
    validated_weights = _validated_weights(weights)
    validated_top_n = _validate_top_n(top_n)
    largest_weights = sorted(validated_weights, reverse=True)[
        :validated_top_n
    ]
    return float(math.fsum(largest_weights))


def calculate_hhi(weights: Mapping[str, float]) -> float:
    """Calculate unscaled Herfindahl-Hirschman concentration."""
    validated_weights = _validated_weights(weights)
    return float(math.fsum(weight**2 for weight in validated_weights))


def calculate_effective_number_of_assets(
    weights: Mapping[str, float],
) -> float:
    """Calculate the reciprocal of the portfolio's unrounded HHI."""
    hhi = calculate_hhi(weights)
    return float(1.0 / hhi)


def analyze_concentration(
    weights: Mapping[str, float], top_n: int = 3
) -> ConcentrationResult:
    """Calculate the complete quantitative portfolio concentration result."""
    validated_top_n = _validate_top_n(top_n)
    return ConcentrationResult(
        largest_weight=calculate_largest_weight(weights),
        top_n_weight=calculate_top_n_concentration(
            weights, top_n=validated_top_n
        ),
        hhi=calculate_hhi(weights),
        effective_number_of_assets=calculate_effective_number_of_assets(
            weights
        ),
        top_n=validated_top_n,
    )
