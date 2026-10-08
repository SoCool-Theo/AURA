from dataclasses import FrozenInstanceError

import numpy as np
import pandas as pd
import pytest

from backend.app.analytics.diversification import (
    DiversificationResult,
    analyze_diversification,
    calculate_average_pairwise_correlation,
    calculate_correlation_diversification_score,
    calculate_diversification_score,
    calculate_weight_diversification_score,
    classify_diversification,
)


def _three_asset_matrix() -> pd.DataFrame:
    symbols = ["A", "B", "C"]
    return pd.DataFrame(
        [
            [1.0, 0.20, 0.40],
            [0.20, 1.0, 0.60],
            [0.40, 0.60, 1.0],
        ],
        index=symbols,
        columns=symbols,
    )


def _two_asset_matrix(correlation: float) -> pd.DataFrame:
    return pd.DataFrame(
        [[1.0, correlation], [correlation, 1.0]],
        index=["A", "B"],
        columns=["A", "B"],
    )


@pytest.mark.parametrize(
    ("weights", "expected"),
    [
        ({"A": 1.0}, 0.0),
        ({"A": 0.50, "B": 0.50}, 100.0),
        ({"A": 0.25, "B": 0.25, "C": 0.25, "D": 0.25}, 100.0),
        ({"A": 0.50, "B": 0.30, "C": 0.20}, 81.57894736842105),
    ],
)
def test_weight_diversification_score(
    weights: dict[str, float], expected: float
) -> None:
    result = calculate_weight_diversification_score(weights)

    assert type(result) is float
    assert result == pytest.approx(expected)


def test_higher_weight_concentration_lowers_score() -> None:
    balanced = calculate_weight_diversification_score(
        {"A": 1 / 3, "B": 1 / 3, "C": 1 / 3}
    )
    concentrated = calculate_weight_diversification_score(
        {"A": 0.80, "B": 0.10, "C": 0.10}
    )

    assert concentrated == pytest.approx(25.75757575757576)
    assert concentrated < balanced


def test_zero_weight_asset_does_not_improve_weight_score() -> None:
    without_zero = calculate_weight_diversification_score(
        {"A": 0.50, "B": 0.50}
    )
    with_zero = calculate_weight_diversification_score(
        {"A": 0.50, "B": 0.50, "ZERO": 0.0}
    )

    assert with_zero == pytest.approx(without_zero)


def test_weight_score_does_not_mutate_input() -> None:
    weights = {"A": 0.50, "B": 0.30, "C": 0.20}
    original = weights.copy()

    calculate_weight_diversification_score(weights)

    assert weights == original
    assert list(weights) == list(original)


def test_average_pairwise_correlation_uses_known_unique_pairs() -> None:
    result = calculate_average_pairwise_correlation(
        _three_asset_matrix(),
        {"A": 0.40, "B": 0.35, "C": 0.25},
    )

    assert type(result) is float
    assert result == pytest.approx(0.40)


def test_average_pairwise_correlation_excludes_diagonal() -> None:
    matrix = _two_asset_matrix(0.20)

    result = calculate_average_pairwise_correlation(
        matrix, {"A": 0.50, "B": 0.50}
    )

    assert result == pytest.approx(0.20)
    assert result != pytest.approx(0.60)


def test_average_pairwise_correlation_uses_only_active_assets() -> None:
    result = calculate_average_pairwise_correlation(
        _three_asset_matrix(),
        {"A": 0.50, "B": 0.50, "C": 0.0},
    )

    assert result == pytest.approx(0.20)


def test_zero_weight_undefined_correlations_do_not_affect_average() -> None:
    matrix = pd.DataFrame(
        [
            [1.0, 0.30, np.nan],
            [0.30, 1.0, np.nan],
            [np.nan, np.nan, 1.0],
        ],
        index=["A", "B", "ZERO"],
        columns=["A", "B", "ZERO"],
    )

    result = calculate_average_pairwise_correlation(
        matrix, {"A": 0.50, "B": 0.50, "ZERO": 0.0}
    )

    assert result == pytest.approx(0.30)


def test_average_pairwise_correlation_excludes_undefined_pairs() -> None:
    matrix = pd.DataFrame(
        [
            [1.0, 0.20, np.nan],
            [0.20, 1.0, 0.60],
            [np.nan, 0.60, 1.0],
        ],
        index=["A", "B", "C"],
        columns=["A", "B", "C"],
    )

    result = calculate_average_pairwise_correlation(
        matrix, {"A": 0.40, "B": 0.30, "C": 0.30}
    )

    assert result == pytest.approx(0.40)
    assert result != pytest.approx(0.80 / 3.0)


def test_average_pairwise_correlation_is_none_for_one_active_asset() -> None:
    result = calculate_average_pairwise_correlation(
        _two_asset_matrix(0.50), {"A": 1.0, "B": 0.0}
    )

    assert result is None


def test_average_pairwise_correlation_is_none_when_all_pairs_undefined() -> None:
    matrix = pd.DataFrame(
        [[1.0, np.nan], [np.nan, 1.0]],
        index=["A", "B"],
        columns=["A", "B"],
    )

    result = calculate_average_pairwise_correlation(
        matrix, {"A": 0.50, "B": 0.50}
    )

    assert result is None


def test_average_pairwise_correlation_does_not_mutate_inputs() -> None:
    weights = {"C": 0.20, "A": 0.50, "B": 0.30}
    original_weights = weights.copy()
    matrix = _three_asset_matrix()
    original_matrix = matrix.copy(deep=True)

    calculate_average_pairwise_correlation(matrix, weights)

    assert weights == original_weights
    assert list(weights) == list(original_weights)
    pd.testing.assert_frame_equal(matrix, original_matrix)


@pytest.mark.parametrize(
    ("average", "expected"),
    [
        (1.0, 0.0),
        (0.80, 20.0),
        (0.30, 70.0),
        (0.0, 100.0),
        (-0.50, 100.0),
    ],
)
def test_correlation_diversification_score(
    average: float, expected: float
) -> None:
    result = calculate_correlation_diversification_score(average)

    assert type(result) is float
    assert result == pytest.approx(expected)


@pytest.mark.parametrize("average", [1.0001, -1.0001])
def test_correlation_score_rejects_out_of_range_average(
    average: float,
) -> None:
    with pytest.raises(ValueError, match="between -1.0 and 1.0"):
        calculate_correlation_diversification_score(average)


@pytest.mark.parametrize(
    ("average", "exception_type", "message"),
    [
        (True, TypeError, "Boolean"),
        (0.20 + 0.0j, TypeError, "complex"),
        ("0.20", TypeError, "real numeric"),
        (np.nan, ValueError, "finite"),
        (np.inf, ValueError, "finite"),
    ],
)
def test_correlation_score_rejects_invalid_average(
    average: object,
    exception_type: type[Exception],
    message: str,
) -> None:
    with pytest.raises(exception_type, match=message):
        calculate_correlation_diversification_score(  # type: ignore[arg-type]
            average
        )


def test_balanced_uncorrelated_portfolio_has_full_overall_score() -> None:
    result = calculate_diversification_score(
        {"A": 0.50, "B": 0.50}, _two_asset_matrix(0.0)
    )

    assert result == pytest.approx(100.0)


def test_balanced_perfectly_correlated_portfolio_has_zero_score() -> None:
    result = calculate_diversification_score(
        {"A": 0.50, "B": 0.50}, _two_asset_matrix(1.0)
    )

    assert result == pytest.approx(0.0)


def test_concentrated_portfolio_has_lower_overall_score() -> None:
    matrix = _two_asset_matrix(0.0)

    balanced = calculate_diversification_score(
        {"A": 0.50, "B": 0.50}, matrix
    )
    concentrated = calculate_diversification_score(
        {"A": 0.80, "B": 0.20}, matrix
    )

    assert concentrated == pytest.approx(47.05882352941177)
    assert balanced is not None
    assert concentrated < balanced


def test_one_active_asset_has_zero_overall_score() -> None:
    result = calculate_diversification_score(
        {"A": 1.0, "B": 0.0}, _two_asset_matrix(0.50)
    )

    assert result == pytest.approx(0.0)


def test_overall_score_is_none_without_defined_active_correlation() -> None:
    matrix = pd.DataFrame(
        [[1.0, np.nan], [np.nan, 1.0]],
        index=["A", "B"],
        columns=["A", "B"],
    )

    result = calculate_diversification_score(
        {"A": 0.50, "B": 0.50}, matrix
    )

    assert result is None


def test_overall_score_aligns_weights_by_labels() -> None:
    matrix = _two_asset_matrix(0.25)

    result = calculate_diversification_score(
        {"B": 0.50, "A": 0.50}, matrix
    )

    assert result == pytest.approx(75.0)


def test_overall_score_does_not_mutate_inputs() -> None:
    weights = {"B": 0.50, "A": 0.50}
    original_weights = weights.copy()
    matrix = _two_asset_matrix(0.25)
    original_matrix = matrix.copy(deep=True)

    calculate_diversification_score(weights, matrix)

    assert weights == original_weights
    assert list(weights) == list(original_weights)
    pd.testing.assert_frame_equal(matrix, original_matrix)


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (None, "Unavailable"),
        (0.0, "Weak"),
        (39.999, "Weak"),
        (40.0, "Moderate"),
        (69.999, "Moderate"),
        (70.0, "Strong"),
        (100.0, "Strong"),
    ],
)
def test_classify_diversification(
    score: float | None, expected: str
) -> None:
    assert classify_diversification(score) == expected


@pytest.mark.parametrize("score", [-0.01, 100.01, np.nan, np.inf])
def test_classify_diversification_rejects_invalid_value(score: float) -> None:
    with pytest.raises(ValueError, match="finite|between"):
        classify_diversification(score)


@pytest.mark.parametrize(
    ("score", "message"),
    [
        (True, "Boolean"),
        (50.0 + 0.0j, "complex"),
        ("50", "real numeric"),
    ],
)
def test_classify_diversification_rejects_invalid_type(
    score: object, message: str
) -> None:
    with pytest.raises(TypeError, match=message):
        classify_diversification(score)  # type: ignore[arg-type]


def test_analyze_diversification_returns_consistent_result() -> None:
    result = analyze_diversification(
        {"A": 0.50, "B": 0.30, "C": 0.20},
        _three_asset_matrix(),
    )

    assert isinstance(result, DiversificationResult)
    assert result == DiversificationResult(
        active_asset_count=3,
        effective_number_of_assets=pytest.approx(1.0 / 0.38),
        weight_score=pytest.approx(81.57894736842105),
        average_pairwise_correlation=pytest.approx(0.40),
        correlation_score=pytest.approx(60.0),
        overall_score=pytest.approx(48.94736842105263),
        level="Moderate",
        defined_pair_count=3,
        total_pair_count=3,
    )


def test_analyze_diversification_reports_pair_coverage() -> None:
    matrix = pd.DataFrame(
        [
            [1.0, 0.20, np.nan],
            [0.20, 1.0, 0.60],
            [np.nan, 0.60, 1.0],
        ],
        index=["A", "B", "C"],
        columns=["A", "B", "C"],
    )

    result = analyze_diversification(
        {"A": 1 / 3, "B": 1 / 3, "C": 1 / 3}, matrix
    )

    assert result.active_asset_count == 3
    assert result.defined_pair_count == 2
    assert result.total_pair_count == 3
    assert result.average_pairwise_correlation == pytest.approx(0.40)
    assert result.overall_score == pytest.approx(60.0)
    assert result.level == "Moderate"


def test_analyze_diversification_one_active_asset_counts_no_pairs() -> None:
    result = analyze_diversification(
        {"A": 1.0, "B": 0.0}, _two_asset_matrix(0.50)
    )

    assert result.active_asset_count == 1
    assert result.defined_pair_count == 0
    assert result.total_pair_count == 0
    assert result.average_pairwise_correlation is None
    assert result.correlation_score is None
    assert result.overall_score == pytest.approx(0.0)
    assert result.level == "Weak"


def test_diversification_result_is_immutable() -> None:
    result = analyze_diversification(
        {"A": 0.50, "B": 0.50}, _two_asset_matrix(0.0)
    )

    with pytest.raises(FrozenInstanceError):
        result.level = "Weak"  # type: ignore[misc]


def test_analyze_diversification_does_not_mutate_inputs() -> None:
    weights = {"C": 0.20, "A": 0.50, "B": 0.30}
    original_weights = weights.copy()
    matrix = _three_asset_matrix()
    original_matrix = matrix.copy(deep=True)

    analyze_diversification(weights, matrix)

    assert weights == original_weights
    assert list(weights) == list(original_weights)
    pd.testing.assert_frame_equal(matrix, original_matrix)


def test_weight_validation_accepts_numpy_scalars_and_tolerance() -> None:
    result = calculate_weight_diversification_score(
        {"A": np.float64(0.50), "B": np.float32(0.5000005)}
    )

    assert type(result) is float
    assert 0.0 <= result <= 100.0


def test_weight_validation_rejects_wrong_type() -> None:
    with pytest.raises(TypeError, match="Mapping"):
        calculate_weight_diversification_score(  # type: ignore[arg-type]
            [0.50, 0.50]
        )


def test_weight_validation_rejects_empty_mapping() -> None:
    with pytest.raises(ValueError, match="at least one asset"):
        calculate_weight_diversification_score({})


def test_weight_validation_rejects_non_string_symbol() -> None:
    with pytest.raises(TypeError, match="strings"):
        calculate_weight_diversification_score(  # type: ignore[arg-type]
            {1: 1.0}
        )


@pytest.mark.parametrize("symbol", ["", " ", " A", "A "])
def test_weight_validation_rejects_invalid_symbol(symbol: str) -> None:
    with pytest.raises(ValueError, match="weight symbols"):
        calculate_weight_diversification_score({symbol: 1.0})


@pytest.mark.parametrize(
    ("weights", "exception_type", "message"),
    [
        ({"A": 1.0, "B": -0.10}, ValueError, "between"),
        ({"A": 1.0, "B": 1.10}, ValueError, "between"),
        ({"A": 0.0, "B": 0.0}, ValueError, "greater than zero"),
        ({"A": 0.60, "B": 0.30}, ValueError, "total weight"),
        ({"A": np.nan}, ValueError, "finite"),
        ({"A": np.inf}, ValueError, "finite"),
        ({"A": True}, TypeError, "Boolean"),
        ({"A": 1.0 + 0.0j}, TypeError, "complex"),
        ({"A": 40}, ValueError, "between"),
    ],
)
def test_weight_validation_rejects_invalid_values(
    weights: dict[str, object],
    exception_type: type[Exception],
    message: str,
) -> None:
    with pytest.raises(exception_type, match=message):
        calculate_weight_diversification_score(  # type: ignore[arg-type]
            weights
        )


def test_matrix_validation_rejects_wrong_type() -> None:
    with pytest.raises(TypeError, match="pandas DataFrame"):
        calculate_average_pairwise_correlation(  # type: ignore[arg-type]
            [[1.0]], {"A": 1.0}
        )


def test_matrix_validation_rejects_empty_matrix() -> None:
    with pytest.raises(ValueError, match="at least one asset"):
        calculate_average_pairwise_correlation(pd.DataFrame(), {"A": 1.0})


def test_matrix_validation_rejects_non_square_matrix() -> None:
    matrix = pd.DataFrame([[1.0, 0.20]], index=["A"], columns=["A", "B"])

    with pytest.raises(ValueError, match="square"):
        calculate_average_pairwise_correlation(
            matrix, {"A": 0.50, "B": 0.50}
        )


@pytest.mark.parametrize(
    ("index", "columns"),
    [
        (["A", "B"], ["A", "C"]),
        (["A", "B"], ["B", "A"]),
    ],
)
def test_matrix_validation_requires_matching_label_order(
    index: list[str], columns: list[str]
) -> None:
    matrix = pd.DataFrame(
        [[1.0, 0.20], [0.20, 1.0]], index=index, columns=columns
    )

    with pytest.raises(ValueError, match="match exactly"):
        calculate_average_pairwise_correlation(
            matrix, {"A": 0.50, "B": 0.50}
        )


def test_matrix_validation_rejects_duplicate_labels() -> None:
    matrix = pd.DataFrame(
        [[1.0, 0.20], [0.20, 1.0]],
        index=["A", "A"],
        columns=["A", "A"],
    )

    with pytest.raises(ValueError, match="unique"):
        calculate_average_pairwise_correlation(matrix, {"A": 1.0})


@pytest.mark.parametrize("symbol", ["", " ", " A", "A "])
def test_matrix_validation_rejects_invalid_symbol(symbol: str) -> None:
    matrix = pd.DataFrame([[1.0]], index=[symbol], columns=[symbol])

    with pytest.raises(ValueError, match="asset symbols"):
        calculate_average_pairwise_correlation(matrix, {"A": 1.0})


def test_matrix_validation_rejects_non_string_symbol() -> None:
    matrix = pd.DataFrame([[1.0]], index=[1], columns=[1])

    with pytest.raises(TypeError, match="strings"):
        calculate_average_pairwise_correlation(matrix, {"A": 1.0})


def test_matrix_validation_requires_exact_weight_symbols() -> None:
    with pytest.raises(ValueError, match="exactly match"):
        calculate_average_pairwise_correlation(
            _two_asset_matrix(0.20), {"A": 0.50, "C": 0.50}
        )


def test_matrix_validation_rejects_non_symmetric_values() -> None:
    matrix = pd.DataFrame(
        [[1.0, 0.20], [0.30, 1.0]],
        index=["A", "B"],
        columns=["A", "B"],
    )

    with pytest.raises(ValueError, match="symmetric"):
        calculate_average_pairwise_correlation(
            matrix, {"A": 0.50, "B": 0.50}
        )


def test_matrix_validation_rejects_mismatched_nan_symmetry() -> None:
    matrix = pd.DataFrame(
        [[1.0, np.nan], [0.20, 1.0]],
        index=["A", "B"],
        columns=["A", "B"],
    )

    with pytest.raises(ValueError, match="NaN positions.*symmetric"):
        calculate_average_pairwise_correlation(
            matrix, {"A": 0.50, "B": 0.50}
        )


@pytest.mark.parametrize("invalid_value", [1.0001, -1.0001])
def test_matrix_validation_rejects_out_of_range_values(
    invalid_value: float,
) -> None:
    matrix = pd.DataFrame(
        [[1.0, invalid_value], [invalid_value, 1.0]],
        index=["A", "B"],
        columns=["A", "B"],
    )

    with pytest.raises(ValueError, match="between -1.0 and 1.0"):
        calculate_average_pairwise_correlation(
            matrix, {"A": 0.50, "B": 0.50}
        )


@pytest.mark.parametrize("invalid_value", [np.inf, -np.inf])
def test_matrix_validation_rejects_infinity(invalid_value: float) -> None:
    matrix = pd.DataFrame(
        [[1.0, invalid_value], [invalid_value, 1.0]],
        index=["A", "B"],
        columns=["A", "B"],
    )

    with pytest.raises(ValueError, match="finite"):
        calculate_average_pairwise_correlation(
            matrix, {"A": 0.50, "B": 0.50}
        )


@pytest.mark.parametrize(
    ("invalid_value", "message"),
    [(True, "Boolean"), (0.20 + 0.0j, "complex")],
)
def test_matrix_validation_rejects_invalid_value_type(
    invalid_value: object, message: str
) -> None:
    matrix = pd.DataFrame(
        [[1.0, invalid_value], [invalid_value, 1.0]],
        index=["A", "B"],
        columns=["A", "B"],
    )

    with pytest.raises(TypeError, match=message):
        calculate_average_pairwise_correlation(
            matrix, {"A": 0.50, "B": 0.50}
        )


def test_matrix_validation_rejects_invalid_diagonal() -> None:
    matrix = pd.DataFrame(
        [[0.90, 0.20], [0.20, 1.0]],
        index=["A", "B"],
        columns=["A", "B"],
    )

    with pytest.raises(ValueError, match="diagonal.*1.0"):
        calculate_average_pairwise_correlation(
            matrix, {"A": 0.50, "B": 0.50}
        )
