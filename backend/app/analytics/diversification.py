"""Aura's educational portfolio-diversification scoring calculations."""

import math
from collections.abc import Mapping
from dataclasses import dataclass
from numbers import Real

import numpy as np
import pandas as pd


_WEIGHT_TOLERANCE = 1e-6
_CORRELATION_TOLERANCE = 1e-12
_WEIGHT_SCORE_TOLERANCE = 1e-3
_SCORE_TOLERANCE = 1e-9


@dataclass(frozen=True, slots=True)
class DiversificationResult:
    """Contain quantitative diversification metrics and coverage."""

    active_asset_count: int
    effective_number_of_assets: float
    weight_score: float
    average_pairwise_correlation: float | None
    correlation_score: float | None
    overall_score: float | None
    level: str
    defined_pair_count: int
    total_pair_count: int


def _validated_weights(
    weights: Mapping[str, float],
) -> dict[str, float]:
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

    validated: dict[str, float] = {}
    for symbol, value in weight_items:
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
        validated[symbol] = numeric_value

    if not any(weight > 0.0 for weight in validated.values()):
        raise ValueError("at least one weight must be greater than zero")
    if abs(math.fsum(validated.values()) - 1.0) > _WEIGHT_TOLERANCE:
        raise ValueError(
            "total weight must equal 1.0 within a tolerance of 1e-6"
        )
    return validated


def _validate_symbols(symbols: pd.Index, label_name: str) -> None:
    if not symbols.is_unique:
        raise ValueError(f"correlation_matrix {label_name} must be unique")

    for symbol in symbols:
        if not isinstance(symbol, str):
            raise TypeError("correlation_matrix asset symbols must be strings")
        if not symbol:
            raise ValueError(
                "correlation_matrix asset symbols cannot be empty"
            )
        if not symbol.strip():
            raise ValueError(
                "correlation_matrix asset symbols cannot be whitespace-only"
            )
        if symbol != symbol.strip():
            raise ValueError(
                "correlation_matrix asset symbols cannot contain leading "
                "or trailing whitespace"
            )


def _validated_correlation_matrix(
    correlation_matrix: pd.DataFrame,
    weight_symbols: set[str],
) -> np.ndarray:
    if not isinstance(correlation_matrix, pd.DataFrame):
        raise TypeError("correlation_matrix must be a pandas DataFrame")
    if len(correlation_matrix.columns) == 0:
        raise ValueError(
            "correlation_matrix must contain at least one asset"
        )
    if correlation_matrix.shape[0] != correlation_matrix.shape[1]:
        raise ValueError("correlation_matrix must be square")

    _validate_symbols(correlation_matrix.index, "row labels")
    _validate_symbols(correlation_matrix.columns, "column labels")
    if not correlation_matrix.index.equals(correlation_matrix.columns):
        raise ValueError(
            "correlation_matrix row and column labels must match "
            "exactly and in the same order"
        )
    if set(correlation_matrix.columns) != weight_symbols:
        raise ValueError(
            "correlation_matrix symbols must exactly match weight symbols"
        )

    validated: list[float] = []
    for value in np.asarray(correlation_matrix.to_numpy(), dtype=object).flat:
        if isinstance(value, (bool, np.bool_)):
            raise TypeError("correlation_matrix values cannot be Boolean")
        if isinstance(value, (complex, np.complexfloating)):
            raise TypeError("correlation_matrix values cannot be complex")
        if not isinstance(value, Real):
            raise TypeError(
                "correlation_matrix values must be real numeric values or NaN"
            )

        numeric_value = float(value)
        if math.isnan(numeric_value):
            validated.append(numeric_value)
            continue
        if not math.isfinite(numeric_value):
            raise ValueError("correlation_matrix values must be finite or NaN")
        if (
            numeric_value < -1.0 - _CORRELATION_TOLERANCE
            or numeric_value > 1.0 + _CORRELATION_TOLERANCE
        ):
            raise ValueError(
                "correlation_matrix values must be between -1.0 and 1.0"
            )
        validated.append(numeric_value)

    values = np.asarray(validated, dtype=float).reshape(
        correlation_matrix.shape
    )
    nan_positions = np.isnan(values)
    if not np.array_equal(nan_positions, nan_positions.T):
        raise ValueError(
            "correlation_matrix NaN positions must be symmetric"
        )
    if not np.allclose(
        values,
        values.T,
        rtol=0.0,
        atol=_CORRELATION_TOLERANCE,
        equal_nan=True,
    ):
        raise ValueError("correlation_matrix must be symmetric")

    for diagonal_value in np.diag(values):
        if not math.isnan(diagonal_value) and not math.isclose(
            diagonal_value,
            1.0,
            rel_tol=0.0,
            abs_tol=_CORRELATION_TOLERANCE,
        ):
            raise ValueError(
                "non-NaN correlation_matrix diagonal values must equal 1.0"
            )
    return values


def _calculate_weight_metrics(
    validated_weights: Mapping[str, float],
) -> tuple[int, float, float]:
    active_asset_count = sum(
        weight > 0.0 for weight in validated_weights.values()
    )
    hhi = math.fsum(weight**2 for weight in validated_weights.values())
    effective_assets = float(1.0 / hhi)
    if active_asset_count == 1:
        return active_asset_count, effective_assets, 0.0

    weight_score = (
        (effective_assets - 1.0) / (active_asset_count - 1.0) * 100.0
    )
    if -_WEIGHT_SCORE_TOLERANCE <= weight_score < 0.0:
        weight_score = 0.0
    elif 100.0 < weight_score <= 100.0 + _WEIGHT_SCORE_TOLERANCE:
        weight_score = 100.0
    elif weight_score < 0.0 or weight_score > 100.0:
        raise ValueError(
            "calculated weight diversification score must be between "
            "0.0 and 100.0"
        )
    return active_asset_count, effective_assets, float(weight_score)


def _calculate_pairwise_summary(
    correlation_values: np.ndarray,
    matrix_symbols: pd.Index,
    validated_weights: Mapping[str, float],
) -> tuple[float | None, int, int]:
    active_positions = [
        position
        for position, symbol in enumerate(matrix_symbols)
        if validated_weights[symbol] > 0.0
    ]
    total_pair_count = (
        len(active_positions) * (len(active_positions) - 1) // 2
    )
    defined_correlations = [
        correlation_values[first, second]
        for first_offset, first in enumerate(active_positions)
        for second in active_positions[first_offset + 1 :]
        if not math.isnan(correlation_values[first, second])
    ]
    defined_pair_count = len(defined_correlations)
    if defined_pair_count == 0:
        return None, 0, total_pair_count

    average = math.fsum(defined_correlations) / defined_pair_count
    return float(average), defined_pair_count, total_pair_count


def _validated_inputs(
    weights: Mapping[str, float],
    correlation_matrix: pd.DataFrame,
) -> tuple[dict[str, float], np.ndarray]:
    validated_weights = _validated_weights(weights)
    correlation_values = _validated_correlation_matrix(
        correlation_matrix, set(validated_weights)
    )
    return validated_weights, correlation_values


def _validated_average_correlation(average_correlation: float) -> float:
    if isinstance(average_correlation, (bool, np.bool_)):
        raise TypeError("average_correlation cannot be Boolean")
    if isinstance(average_correlation, (complex, np.complexfloating)):
        raise TypeError("average_correlation cannot be complex")
    if not isinstance(average_correlation, Real):
        raise TypeError("average_correlation must be a real numeric value")

    validated_average = float(average_correlation)
    if not math.isfinite(validated_average):
        raise ValueError("average_correlation must be finite")
    if (
        validated_average < -1.0 - _CORRELATION_TOLERANCE
        or validated_average > 1.0 + _CORRELATION_TOLERANCE
    ):
        raise ValueError("average_correlation must be between -1.0 and 1.0")
    return validated_average


def _clamp_score(score: float) -> float:
    if -_SCORE_TOLERANCE <= score < 0.0:
        return 0.0
    if 100.0 < score <= 100.0 + _SCORE_TOLERANCE:
        return 100.0
    if score < 0.0 or score > 100.0:
        raise ValueError("calculated diversification score is out of range")
    return float(score)


def calculate_weight_diversification_score(
    weights: Mapping[str, float],
) -> float:
    """Score diversification implied by effective asset count."""
    validated_weights = _validated_weights(weights)
    _, _, weight_score = _calculate_weight_metrics(validated_weights)
    return weight_score


def calculate_average_pairwise_correlation(
    correlation_matrix: pd.DataFrame,
    weights: Mapping[str, float],
) -> float | None:
    """Average defined correlations across unique active-asset pairs."""
    validated_weights, correlation_values = _validated_inputs(
        weights, correlation_matrix
    )
    average, _, _ = _calculate_pairwise_summary(
        correlation_values,
        correlation_matrix.columns,
        validated_weights,
    )
    return average


def calculate_correlation_diversification_score(
    average_correlation: float,
) -> float:
    """Apply Aura's educational correlation-diversification convention."""
    validated_average = _validated_average_correlation(average_correlation)
    score = (1.0 - max(validated_average, 0.0)) * 100.0
    return _clamp_score(score)


def calculate_diversification_score(
    weights: Mapping[str, float],
    correlation_matrix: pd.DataFrame,
) -> float | None:
    """Combine weight and correlation diversification scores."""
    validated_weights, correlation_values = _validated_inputs(
        weights, correlation_matrix
    )
    active_count, _, weight_score = _calculate_weight_metrics(
        validated_weights
    )
    if active_count == 1:
        return 0.0

    average, _, _ = _calculate_pairwise_summary(
        correlation_values,
        correlation_matrix.columns,
        validated_weights,
    )
    if average is None:
        return None

    correlation_score = calculate_correlation_diversification_score(average)
    return _clamp_score(weight_score * correlation_score / 100.0)


def classify_diversification(score: float | None) -> str:
    """Classify an Aura diversification score into its display level."""
    if score is None:
        return "Unavailable"
    if isinstance(score, (bool, np.bool_)):
        raise TypeError("score cannot be Boolean")
    if isinstance(score, (complex, np.complexfloating)):
        raise TypeError("score cannot be complex")
    if not isinstance(score, Real):
        raise TypeError("score must be a real numeric value or None")

    validated_score = float(score)
    if not math.isfinite(validated_score):
        raise ValueError("score must be finite")
    if validated_score < 0.0 or validated_score > 100.0:
        raise ValueError("score must be between 0.0 and 100.0")
    if validated_score < 40.0:
        return "Weak"
    if validated_score < 70.0:
        return "Moderate"
    return "Strong"


def analyze_diversification(
    weights: Mapping[str, float],
    correlation_matrix: pd.DataFrame,
) -> DiversificationResult:
    """Calculate diversification metrics, coverage, score, and level."""
    validated_weights, correlation_values = _validated_inputs(
        weights, correlation_matrix
    )
    active_count, effective_assets, weight_score = _calculate_weight_metrics(
        validated_weights
    )
    average, defined_pairs, total_pairs = _calculate_pairwise_summary(
        correlation_values,
        correlation_matrix.columns,
        validated_weights,
    )
    correlation_score = (
        None
        if average is None
        else calculate_correlation_diversification_score(average)
    )
    if active_count == 1:
        overall_score: float | None = 0.0
    elif correlation_score is None:
        overall_score = None
    else:
        overall_score = _clamp_score(
            weight_score * correlation_score / 100.0
        )

    return DiversificationResult(
        active_asset_count=active_count,
        effective_number_of_assets=effective_assets,
        weight_score=weight_score,
        average_pairwise_correlation=average,
        correlation_score=correlation_score,
        overall_score=overall_score,
        level=classify_diversification(overall_score),
        defined_pair_count=defined_pairs,
        total_pair_count=total_pairs,
    )
