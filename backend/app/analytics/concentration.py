"""Portfolio concentration calculations for validated decimal weights."""

import math
from collections.abc import Mapping
from dataclasses import dataclass

from ._validation import (
    _validate_positive_integer,
    _validated_weight_mapping,
)


@dataclass(frozen=True, slots=True)
class ConcentrationResult:
    """Contain quantitative portfolio concentration metrics."""

    largest_weight: float
    top_n_weight: float
    hhi: float
    effective_number_of_assets: float
    top_n: int


def _validated_weights(weights: Mapping[str, float]) -> list[float]:
    return list(_validated_weight_mapping(weights).values())


def calculate_largest_weight(weights: Mapping[str, float]) -> float:
    """Return the portfolio's largest individual asset weight."""
    validated_weights = _validated_weights(weights)
    return float(max(validated_weights))


def calculate_top_n_concentration(
    weights: Mapping[str, float], top_n: int = 3
) -> float:
    """Sum the largest requested number of validated portfolio weights."""
    validated_weights = _validated_weights(weights)
    validated_top_n = _validate_positive_integer(top_n, "top_n")
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
    validated_top_n = _validate_positive_integer(top_n, "top_n")
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
