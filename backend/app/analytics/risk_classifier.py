"""Aura's educational portfolio-risk scoring convention."""

import math
from dataclasses import dataclass
from numbers import Real

import numpy as np


_COMPONENT_WEIGHTS = {
    "volatility": 0.35,
    "maximum_drawdown": 0.35,
    "concentration": 0.15,
    "diversification": 0.15,
}
_SCORE_TOLERANCE = 1e-12


@dataclass(frozen=True, slots=True)
class RiskClassificationResult:
    """Contain Aura's deterministic educational risk classification."""

    risk_score: float
    risk_level: str
    volatility_points: int
    drawdown_points: int
    concentration_points: int
    diversification_points: int | None
    metrics_used: tuple[str, ...]
    reasons: tuple[str, ...]


def _validated_real_scalar(value: float, input_name: str) -> float:
    if isinstance(value, (bool, np.bool_)):
        raise TypeError(f"{input_name} cannot be Boolean")
    if isinstance(value, (complex, np.complexfloating)):
        raise TypeError(f"{input_name} cannot be complex")
    if not isinstance(value, Real):
        raise TypeError(f"{input_name} must be a real numeric scalar")

    validated = float(value)
    if not math.isfinite(validated):
        raise ValueError(f"{input_name} must be finite")
    return validated


def _validated_closed_range(
    value: float,
    input_name: str,
    lower: float,
    upper: float,
) -> float:
    validated = _validated_real_scalar(value, input_name)
    if validated < lower or validated > upper:
        raise ValueError(
            f"{input_name} must be between {lower} and {upper} inclusive"
        )
    return validated


def _points_from_thresholds(
    value: float,
    first: float,
    second: float,
    third: float,
) -> int:
    if value < first:
        return 0
    if value < second:
        return 1
    if value < third:
        return 2
    return 3


def _calculate_weighted_score(
    volatility_points: int,
    drawdown_points: int,
    concentration_points: int,
    diversification_points: int | None,
) -> tuple[float, tuple[str, ...]]:
    components: list[tuple[str, int]] = [
        ("volatility", volatility_points),
        ("maximum_drawdown", drawdown_points),
        ("concentration", concentration_points),
    ]
    if diversification_points is not None:
        components.append(("diversification", diversification_points))

    weighted_total = math.fsum(
        _COMPONENT_WEIGHTS[name] * (points / 3.0 * 100.0)
        for name, points in components
    )
    available_weight = math.fsum(
        _COMPONENT_WEIGHTS[name] for name, _ in components
    )
    score = weighted_total / available_weight
    if -_SCORE_TOLERANCE <= score < 0.0:
        score = 0.0
    elif 100.0 < score <= 100.0 + _SCORE_TOLERANCE:
        score = 100.0
    elif score < 0.0 or score > 100.0:
        raise ValueError("calculated overall risk score is out of range")

    return float(score), tuple(name for name, _ in components)


def _risk_reasons(
    volatility_points: int,
    drawdown_points: int,
    concentration_points: int,
    diversification_points: int | None,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if volatility_points == 2:
        reasons.append("Elevated historical volatility")
    elif volatility_points == 3:
        reasons.append("High historical volatility")

    if drawdown_points == 2:
        reasons.append("Significant historical drawdown")
    elif drawdown_points == 3:
        reasons.append("Severe historical drawdown")

    if concentration_points == 2:
        reasons.append("Large single-asset concentration")
    elif concentration_points == 3:
        reasons.append("Very large single-asset concentration")

    if diversification_points == 2:
        reasons.append("Weak portfolio diversification")
    elif diversification_points == 3:
        reasons.append("Very weak portfolio diversification")
    elif diversification_points is None:
        reasons.append("Diversification score unavailable")

    if not reasons:
        return ("No major risk flags under Aura's current thresholds",)
    return tuple(reasons)


def score_volatility(annualized_volatility: float) -> int:
    """Assign educational risk points for annualized volatility."""
    validated = _validated_real_scalar(
        annualized_volatility,
        "annualized_volatility",
    )
    if validated < 0.0:
        raise ValueError(
            "annualized_volatility must be greater than or equal to 0.0"
        )
    return _points_from_thresholds(validated, 0.10, 0.20, 0.30)


def score_max_drawdown(max_drawdown: float) -> int:
    """Assign educational risk points for maximum-drawdown magnitude."""
    validated = _validated_closed_range(
        max_drawdown,
        "max_drawdown",
        -1.0,
        0.0,
    )
    return _points_from_thresholds(abs(validated), 0.10, 0.20, 0.35)


def score_concentration(largest_weight: float) -> int:
    """Assign educational risk points for the largest holding weight."""
    validated = _validated_closed_range(
        largest_weight,
        "largest_weight",
        0.0,
        1.0,
    )
    return _points_from_thresholds(validated, 0.25, 0.40, 0.60)


def score_diversification_risk(
    diversification_score: float | None,
) -> int | None:
    """Assign risk points inversely from an available diversification score."""
    if diversification_score is None:
        return None

    validated = _validated_closed_range(
        diversification_score,
        "diversification_score",
        0.0,
        100.0,
    )
    if validated >= 70.0:
        return 0
    if validated >= 40.0:
        return 1
    if validated >= 20.0:
        return 2
    return 3


def calculate_overall_risk_score(
    annualized_volatility: float,
    max_drawdown: float,
    largest_weight: float,
    diversification_score: float | None,
) -> float:
    """Calculate Aura's weighted educational portfolio-risk score."""
    volatility_points = score_volatility(annualized_volatility)
    drawdown_points = score_max_drawdown(max_drawdown)
    concentration_points = score_concentration(largest_weight)
    diversification_points = score_diversification_risk(
        diversification_score
    )
    score, _ = _calculate_weighted_score(
        volatility_points,
        drawdown_points,
        concentration_points,
        diversification_points,
    )
    return score


def classify_risk_score(risk_score: float) -> str:
    """Classify a validated Aura risk score into its educational level."""
    validated = _validated_closed_range(
        risk_score,
        "risk_score",
        0.0,
        100.0,
    )
    if validated < 25.0:
        return "Low"
    if validated < 50.0:
        return "Moderate"
    if validated < 75.0:
        return "High"
    return "Very High"


def analyze_risk_classification(
    annualized_volatility: float,
    max_drawdown: float,
    largest_weight: float,
    diversification_score: float | None,
) -> RiskClassificationResult:
    """Return component points, weighted risk level, and fixed reasons."""
    volatility_points = score_volatility(annualized_volatility)
    drawdown_points = score_max_drawdown(max_drawdown)
    concentration_points = score_concentration(largest_weight)
    diversification_points = score_diversification_risk(
        diversification_score
    )
    risk_score, metrics_used = _calculate_weighted_score(
        volatility_points,
        drawdown_points,
        concentration_points,
        diversification_points,
    )
    return RiskClassificationResult(
        risk_score=risk_score,
        risk_level=classify_risk_score(risk_score),
        volatility_points=volatility_points,
        drawdown_points=drawdown_points,
        concentration_points=concentration_points,
        diversification_points=diversification_points,
        metrics_used=metrics_used,
        reasons=_risk_reasons(
            volatility_points,
            drawdown_points,
            concentration_points,
            diversification_points,
        ),
    )
