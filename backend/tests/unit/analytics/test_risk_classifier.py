from collections.abc import Callable
from dataclasses import FrozenInstanceError

import numpy as np
import pytest

from backend.app.analytics.risk_classifier import (
    AssetRiskClassificationResult,
    RiskClassificationResult,
    analyze_asset_risk_classification,
    analyze_risk_classification,
    calculate_asset_risk_score,
    calculate_overall_risk_score,
    classify_risk_score,
    score_concentration,
    score_diversification_risk,
    score_max_drawdown,
    score_volatility,
)


@pytest.mark.parametrize(
    ("annualized_volatility", "max_drawdown", "expected"),
    [
        (0.05, -0.05, 0.0),
        (0.15, -0.15, 100.0 / 3.0),
        (0.25, -0.25, 200.0 / 3.0),
        (0.35, -0.40, 100.0),
    ],
)
def test_asset_risk_score_normalizes_applicable_components(
    annualized_volatility: float,
    max_drawdown: float,
    expected: float,
) -> None:
    result = calculate_asset_risk_score(
        annualized_volatility,
        max_drawdown,
    )

    assert result == pytest.approx(expected)


def test_asset_risk_classification_uses_asset_only_metrics() -> None:
    result = analyze_asset_risk_classification(0.25, -0.40)

    assert isinstance(result, AssetRiskClassificationResult)
    assert result.risk_score == pytest.approx(250.0 / 3.0)
    assert result.risk_level == "Very High"
    assert result.volatility_points == 2
    assert result.drawdown_points == 3
    assert result.metrics_used == ("volatility", "maximum_drawdown")
    assert result.reasons == (
        "Elevated historical volatility",
        "Severe historical drawdown",
    )


def test_asset_risk_classification_has_low_risk_fallback_reason() -> None:
    result = analyze_asset_risk_classification(0.05, -0.05)

    assert result.risk_level == "Low"
    assert result.reasons == (
        "No major risk flags under Aura's current asset thresholds",
    )


@pytest.mark.parametrize(
    ("annualized_volatility", "expected"),
    [
        (0.0, 0),
        (0.099999, 0),
        (0.10, 1),
        (0.199999, 1),
        (0.20, 2),
        (0.299999, 2),
        (0.30, 3),
        (100.0, 3),
    ],
)
def test_score_volatility_thresholds(
    annualized_volatility: float,
    expected: int,
) -> None:
    result = score_volatility(annualized_volatility)

    assert type(result) is int
    assert result == expected


@pytest.mark.parametrize(
    ("max_drawdown", "expected"),
    [
        (0.0, 0),
        (-0.099999, 0),
        (-0.10, 1),
        (-0.199999, 1),
        (-0.20, 2),
        (-0.349999, 2),
        (-0.35, 3),
        (-1.0, 3),
    ],
)
def test_score_max_drawdown_thresholds(
    max_drawdown: float,
    expected: int,
) -> None:
    result = score_max_drawdown(max_drawdown)

    assert type(result) is int
    assert result == expected


@pytest.mark.parametrize(
    ("largest_weight", "expected"),
    [
        (0.0, 0),
        (0.249999, 0),
        (0.25, 1),
        (0.399999, 1),
        (0.40, 2),
        (0.599999, 2),
        (0.60, 3),
        (1.0, 3),
    ],
)
def test_score_concentration_thresholds(
    largest_weight: float,
    expected: int,
) -> None:
    result = score_concentration(largest_weight)

    assert type(result) is int
    assert result == expected


@pytest.mark.parametrize(
    ("diversification_score", "expected"),
    [
        (None, None),
        (100.0, 0),
        (70.0, 0),
        (69.999, 1),
        (40.0, 1),
        (39.999, 2),
        (20.0, 2),
        (19.999, 3),
        (0.0, 3),
    ],
)
def test_score_diversification_risk_thresholds(
    diversification_score: float | None,
    expected: int | None,
) -> None:
    result = score_diversification_risk(diversification_score)

    assert result is None or type(result) is int
    assert result == expected


def test_scorers_accept_compatible_numpy_scalars() -> None:
    assert score_volatility(np.float64(0.20)) == 2
    assert score_max_drawdown(np.float32(-0.20)) == 2
    assert score_concentration(np.int64(1)) == 3
    assert score_diversification_risk(np.float64(70.0)) == 0


def test_overall_score_is_zero_for_all_low_risk_inputs() -> None:
    result = calculate_overall_risk_score(
        annualized_volatility=0.05,
        max_drawdown=-0.05,
        largest_weight=0.10,
        diversification_score=80.0,
    )

    assert type(result) is float
    assert result == pytest.approx(0.0)


def test_overall_score_is_100_for_all_maximum_risk_inputs() -> None:
    result = calculate_overall_risk_score(
        annualized_volatility=0.50,
        max_drawdown=-1.0,
        largest_weight=1.0,
        diversification_score=0.0,
    )

    assert type(result) is float
    assert result == pytest.approx(100.0)


def test_overall_score_uses_specified_component_weights() -> None:
    result = calculate_overall_risk_score(
        annualized_volatility=0.25,
        max_drawdown=-0.25,
        largest_weight=0.50,
        diversification_score=50.0,
    )

    assert result == pytest.approx(61.666666666666664)


def test_overall_score_renormalizes_without_diversification() -> None:
    result = calculate_overall_risk_score(
        annualized_volatility=0.35,
        max_drawdown=-0.05,
        largest_weight=0.10,
        diversification_score=None,
    )

    assert result == pytest.approx(41.17647058823529)


def test_unavailable_diversification_is_not_treated_as_zero_points() -> None:
    unavailable = calculate_overall_risk_score(0.35, -0.05, 0.10, None)
    available_strong = calculate_overall_risk_score(
        0.35,
        -0.05,
        0.10,
        100.0,
    )

    assert unavailable == pytest.approx(41.17647058823529)
    assert available_strong == pytest.approx(35.0)
    assert unavailable != pytest.approx(available_strong)


@pytest.mark.parametrize(
    ("inputs",),
    [
        ((0.0, 0.0, 0.0, 100.0),),
        ((0.15, -0.15, 0.30, 50.0),),
        ((0.25, -0.25, 0.50, 30.0),),
        ((0.50, -1.0, 1.0, 0.0),),
        ((0.30, -0.20, 0.40, None),),
    ],
)
def test_overall_score_remains_in_range(
    inputs: tuple[float, float, float, float | None],
) -> None:
    result = calculate_overall_risk_score(*inputs)

    assert type(result) is float
    assert 0.0 <= result <= 100.0


@pytest.mark.parametrize(
    ("risk_score", "expected"),
    [
        (0.0, "Low"),
        (24.999, "Low"),
        (25.0, "Moderate"),
        (49.999, "Moderate"),
        (50.0, "High"),
        (74.999, "High"),
        (75.0, "Very High"),
        (100.0, "Very High"),
    ],
)
def test_classify_risk_score_thresholds(
    risk_score: float,
    expected: str,
) -> None:
    assert classify_risk_score(risk_score) == expected


def test_analyze_classification_returns_consistent_result() -> None:
    result = analyze_risk_classification(
        annualized_volatility=0.25,
        max_drawdown=-0.25,
        largest_weight=0.50,
        diversification_score=50.0,
    )

    assert isinstance(result, RiskClassificationResult)
    assert result.risk_score == pytest.approx(61.666666666666664)
    assert result.risk_level == "High"
    assert result.volatility_points == 2
    assert result.drawdown_points == 2
    assert result.concentration_points == 2
    assert result.diversification_points == 1
    assert result.metrics_used == (
        "volatility",
        "maximum_drawdown",
        "concentration",
        "diversification",
    )
    assert type(result.metrics_used) is tuple
    assert type(result.reasons) is tuple


def test_analyze_classification_excludes_unavailable_diversification() -> None:
    result = analyze_risk_classification(
        annualized_volatility=0.35,
        max_drawdown=-0.05,
        largest_weight=0.10,
        diversification_score=None,
    )

    assert result.risk_score == pytest.approx(41.17647058823529)
    assert result.risk_level == "Moderate"
    assert result.diversification_points is None
    assert result.metrics_used == (
        "volatility",
        "maximum_drawdown",
        "concentration",
    )
    assert "diversification" not in result.metrics_used


def test_analyze_classification_reasons_follow_required_order() -> None:
    result = analyze_risk_classification(
        annualized_volatility=0.25,
        max_drawdown=-0.40,
        largest_weight=0.50,
        diversification_score=10.0,
    )

    assert result.reasons == (
        "Elevated historical volatility",
        "Severe historical drawdown",
        "Large single-asset concentration",
        "Very weak portfolio diversification",
    )


def test_analyze_classification_uses_point_two_reasons() -> None:
    result = analyze_risk_classification(
        annualized_volatility=0.20,
        max_drawdown=-0.20,
        largest_weight=0.40,
        diversification_score=20.0,
    )

    assert result.reasons == (
        "Elevated historical volatility",
        "Significant historical drawdown",
        "Large single-asset concentration",
        "Weak portfolio diversification",
    )


def test_analyze_classification_uses_point_three_reasons() -> None:
    result = analyze_risk_classification(
        annualized_volatility=0.30,
        max_drawdown=-0.35,
        largest_weight=0.60,
        diversification_score=0.0,
    )

    assert result.reasons == (
        "High historical volatility",
        "Severe historical drawdown",
        "Very large single-asset concentration",
        "Very weak portfolio diversification",
    )


def test_analyze_classification_uses_default_reason_without_flags() -> None:
    result = analyze_risk_classification(
        annualized_volatility=0.05,
        max_drawdown=-0.05,
        largest_weight=0.10,
        diversification_score=80.0,
    )

    assert result.reasons == (
        "No major risk flags under Aura's current thresholds",
    )


def test_analyze_classification_reports_unavailable_diversification() -> None:
    result = analyze_risk_classification(
        annualized_volatility=0.05,
        max_drawdown=-0.05,
        largest_weight=0.10,
        diversification_score=None,
    )

    assert result.reasons == ("Diversification score unavailable",)


def test_risk_classification_result_is_immutable() -> None:
    result = analyze_risk_classification(0.05, -0.05, 0.10, 80.0)

    with pytest.raises(FrozenInstanceError):
        result.risk_level = "High"  # type: ignore[misc]


def test_analyze_classification_has_no_investment_advice() -> None:
    result = analyze_risk_classification(0.30, -0.35, 0.60, 0.0)
    rendered = " ".join(result.reasons).lower()

    for prohibited_text in ("buy", "sell", "recommend", "advice"):
        assert prohibited_text not in rendered


def test_analyze_classification_does_not_modify_external_values() -> None:
    inputs: list[float | None] = [0.25, -0.25, 0.50, 50.0]
    original = inputs.copy()

    analyze_risk_classification(*inputs)  # type: ignore[arg-type]

    assert inputs == original


ScalarScorer = Callable[[object], object]


@pytest.mark.parametrize(
    ("invalid_value", "exception_type", "message"),
    [
        ("0.20", TypeError, "real numeric"),
        (True, TypeError, "Boolean"),
        (0.20 + 0.0j, TypeError, "complex"),
        (object(), TypeError, "real numeric"),
        (np.nan, ValueError, "finite"),
        (np.inf, ValueError, "finite"),
        (-np.inf, ValueError, "finite"),
        (-0.01, ValueError, "greater than or equal"),
    ],
)
def test_score_volatility_rejects_invalid_input(
    invalid_value: object,
    exception_type: type[Exception],
    message: str,
) -> None:
    with pytest.raises(exception_type, match=message):
        score_volatility(invalid_value)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("invalid_value", "exception_type", "message"),
    [
        ("-0.20", TypeError, "real numeric"),
        (True, TypeError, "Boolean"),
        (-0.20 + 0.0j, TypeError, "complex"),
        (object(), TypeError, "real numeric"),
        (np.nan, ValueError, "finite"),
        (np.inf, ValueError, "finite"),
        (-np.inf, ValueError, "finite"),
        (0.01, ValueError, "between"),
        (-1.01, ValueError, "between"),
    ],
)
def test_score_max_drawdown_rejects_invalid_input(
    invalid_value: object,
    exception_type: type[Exception],
    message: str,
) -> None:
    with pytest.raises(exception_type, match=message):
        score_max_drawdown(invalid_value)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("invalid_value", "exception_type", "message"),
    [
        ("0.50", TypeError, "real numeric"),
        (True, TypeError, "Boolean"),
        (0.50 + 0.0j, TypeError, "complex"),
        (object(), TypeError, "real numeric"),
        (np.nan, ValueError, "finite"),
        (np.inf, ValueError, "finite"),
        (-np.inf, ValueError, "finite"),
        (-0.01, ValueError, "between"),
        (1.01, ValueError, "between"),
    ],
)
def test_score_concentration_rejects_invalid_input(
    invalid_value: object,
    exception_type: type[Exception],
    message: str,
) -> None:
    with pytest.raises(exception_type, match=message):
        score_concentration(invalid_value)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("invalid_value", "exception_type", "message"),
    [
        ("50", TypeError, "real numeric"),
        (True, TypeError, "Boolean"),
        (50.0 + 0.0j, TypeError, "complex"),
        (object(), TypeError, "real numeric"),
        (np.nan, ValueError, "finite"),
        (np.inf, ValueError, "finite"),
        (-np.inf, ValueError, "finite"),
        (-0.01, ValueError, "between"),
        (100.01, ValueError, "between"),
    ],
)
def test_score_diversification_rejects_invalid_input(
    invalid_value: object,
    exception_type: type[Exception],
    message: str,
) -> None:
    with pytest.raises(exception_type, match=message):
        score_diversification_risk(  # type: ignore[arg-type]
            invalid_value
        )


@pytest.mark.parametrize(
    ("invalid_value", "exception_type", "message"),
    [
        ("50", TypeError, "real numeric"),
        (True, TypeError, "Boolean"),
        (50.0 + 0.0j, TypeError, "complex"),
        (object(), TypeError, "real numeric"),
        (np.nan, ValueError, "finite"),
        (np.inf, ValueError, "finite"),
        (-np.inf, ValueError, "finite"),
        (-0.01, ValueError, "between"),
        (100.01, ValueError, "between"),
    ],
)
def test_classify_risk_score_rejects_invalid_input(
    invalid_value: object,
    exception_type: type[Exception],
    message: str,
) -> None:
    with pytest.raises(exception_type, match=message):
        classify_risk_score(invalid_value)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        (("0.20", -0.20, 0.40, 50.0), "annualized_volatility"),
        ((0.20, 0.20, 0.40, 50.0), "max_drawdown"),
        ((0.20, -0.20, 1.10, 50.0), "largest_weight"),
        ((0.20, -0.20, 0.40, 101.0), "diversification_score"),
    ],
)
def test_overall_score_validates_each_metric(
    arguments: tuple[object, object, object, object],
    message: str,
) -> None:
    with pytest.raises((TypeError, ValueError), match=message):
        calculate_overall_risk_score(*arguments)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        ((-0.01, -0.20, 0.40, 50.0), "annualized_volatility"),
        ((0.20, 0.01, 0.40, 50.0), "max_drawdown"),
        ((0.20, -0.20, -0.01, 50.0), "largest_weight"),
        ((0.20, -0.20, 0.40, -0.01), "diversification_score"),
    ],
)
def test_analyze_classification_validates_each_metric(
    arguments: tuple[object, object, object, object],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        analyze_risk_classification(*arguments)  # type: ignore[arg-type]
