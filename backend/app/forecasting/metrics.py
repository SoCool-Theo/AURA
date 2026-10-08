"""Finite deterministic metrics for forecast candidate evaluation."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import math
from numbers import Real


RETURN_MAPE_MINIMUM_ABSOLUTE_ACTUAL = 0.01


class ForecastMetricError(ValueError):
    """Raised when metric inputs are empty, misaligned, or non-finite."""


@dataclass(frozen=True, slots=True)
class DirectionalAccuracyResult:
    """Three-state sign agreement for evaluated return forecasts."""

    value: float
    evaluated_count: int


@dataclass(frozen=True, slots=True)
class SafeMapeResult:
    """Supplemental MAPE with explicit near-zero exclusions."""

    value: float | None
    included_count: int
    excluded_count: int
    minimum_absolute_actual: float

    @property
    def available(self) -> bool:
        return self.value is not None


def _validated_pairs(
    actual: Sequence[float],
    predicted: Sequence[float],
) -> tuple[tuple[float, float], ...]:
    if len(actual) != len(predicted):
        raise ForecastMetricError("actual and predicted lengths must match")
    if len(actual) == 0:
        raise ForecastMetricError("metric inputs cannot be empty")

    pairs: list[tuple[float, float]] = []
    for actual_value, predicted_value in zip(actual, predicted, strict=True):
        if (
            isinstance(actual_value, bool)
            or isinstance(predicted_value, bool)
            or not isinstance(actual_value, Real)
            or not isinstance(predicted_value, Real)
        ):
            raise ForecastMetricError("metric inputs must be real numbers")
        normalized_actual = float(actual_value)
        normalized_predicted = float(predicted_value)
        if not (
            math.isfinite(normalized_actual)
            and math.isfinite(normalized_predicted)
        ):
            raise ForecastMetricError("metric inputs must be finite")
        pairs.append((normalized_actual, normalized_predicted))
    return tuple(pairs)


def mean_absolute_error(
    actual: Sequence[float],
    predicted: Sequence[float],
) -> float:
    """Return mean absolute prediction error."""
    pairs = _validated_pairs(actual, predicted)
    value = math.fsum(abs(left - right) for left, right in pairs) / len(pairs)
    if not math.isfinite(value):
        raise ForecastMetricError("metric result must be finite")
    return value


def root_mean_squared_error(
    actual: Sequence[float],
    predicted: Sequence[float],
) -> float:
    """Return root mean squared prediction error."""
    pairs = _validated_pairs(actual, predicted)
    errors = tuple(left - right for left, right in pairs)
    if not all(math.isfinite(error) for error in errors):
        raise ForecastMetricError("metric result must be finite")
    scale = max(abs(error) for error in errors)
    value = (
        0.0
        if scale == 0.0
        else scale
        * math.sqrt(
            math.fsum((error / scale) ** 2 for error in errors)
            / len(errors)
        )
    )
    if not math.isfinite(value):
        raise ForecastMetricError("metric result must be finite")
    return value


def _three_state_sign(value: float) -> int:
    if value < 0.0:
        return -1
    if value > 0.0:
        return 1
    return 0


def directional_accuracy(
    actual: Sequence[float],
    predicted: Sequence[float],
) -> DirectionalAccuracyResult:
    """Return exact negative/zero/positive sign agreement for returns."""
    pairs = _validated_pairs(actual, predicted)
    correct = sum(
        _three_state_sign(left) == _three_state_sign(right)
        for left, right in pairs
    )
    return DirectionalAccuracyResult(
        value=correct / len(pairs),
        evaluated_count=len(pairs),
    )


def safe_return_mape(
    actual: Sequence[float],
    predicted: Sequence[float],
    *,
    minimum_absolute_actual: float = RETURN_MAPE_MINIMUM_ABSOLUTE_ACTUAL,
) -> SafeMapeResult:
    """Return supplemental percentage error after excluding returns below 1%."""
    if (
        isinstance(minimum_absolute_actual, bool)
        or not isinstance(minimum_absolute_actual, Real)
        or not math.isfinite(float(minimum_absolute_actual))
        or minimum_absolute_actual <= 0.0
    ):
        raise ForecastMetricError(
            "minimum_absolute_actual must be positive and finite"
        )
    threshold = float(minimum_absolute_actual)
    pairs = _validated_pairs(actual, predicted)
    included = tuple(pair for pair in pairs if abs(pair[0]) >= threshold)
    excluded_count = len(pairs) - len(included)
    if not included:
        return SafeMapeResult(
            value=None,
            included_count=0,
            excluded_count=excluded_count,
            minimum_absolute_actual=threshold,
        )
    value = (
        math.fsum(abs((left - right) / left) for left, right in included)
        / len(included)
        * 100.0
    )
    if not math.isfinite(value):
        raise ForecastMetricError("metric result must be finite")
    return SafeMapeResult(
        value=value,
        included_count=len(included),
        excluded_count=excluded_count,
        minimum_absolute_actual=threshold,
    )
