from collections.abc import Mapping
from dataclasses import FrozenInstanceError

import numpy as np
import pytest

from backend.app.analytics.concentration import (
    ConcentrationResult,
    analyze_concentration,
    calculate_effective_number_of_assets,
    calculate_hhi,
    calculate_largest_weight,
    calculate_top_n_concentration,
)


def _weights() -> dict[str, float]:
    return {"AAPL": 0.50, "MSFT": 0.30, "BND": 0.20}


@pytest.mark.parametrize(
    ("weights", "expected"),
    [
        ({"AAPL": 0.50, "MSFT": 0.30, "BND": 0.20}, 0.50),
        ({"AAPL": 1.0}, 1.0),
        ({"A": 0.25, "B": 0.25, "C": 0.25, "D": 0.25}, 0.25),
        ({"A": 0.60, "B": 0.40, "ZERO": 0.0}, 0.60),
    ],
)
def test_calculate_largest_weight(
    weights: dict[str, float], expected: float
) -> None:
    result = calculate_largest_weight(weights)

    assert type(result) is float
    assert result == pytest.approx(expected)


def test_calculate_largest_weight_does_not_mutate_input() -> None:
    weights = _weights()
    original = weights.copy()

    calculate_largest_weight(weights)

    assert weights == original
    assert list(weights) == list(original)


@pytest.mark.parametrize(
    ("top_n", "expected"),
    [
        (1, 0.50),
        (2, 0.80),
        (3, 0.95),
        (4, 1.0),
        (10, 1.0),
    ],
)
def test_calculate_top_n_concentration(
    top_n: int, expected: float
) -> None:
    weights = {
        "AAPL": 0.50,
        "MSFT": 0.30,
        "BND": 0.15,
        "CASH": 0.05,
    }

    result = calculate_top_n_concentration(weights, top_n=top_n)

    assert type(result) is float
    assert result == pytest.approx(expected)


def test_calculate_top_n_concentration_defaults_to_three() -> None:
    result = calculate_top_n_concentration(
        {"A": 0.40, "B": 0.30, "C": 0.20, "D": 0.10}
    )

    assert result == pytest.approx(0.90)


def test_calculate_top_n_concentration_handles_zero_weight() -> None:
    result = calculate_top_n_concentration(
        {"A": 0.60, "B": 0.40, "ZERO": 0.0}, top_n=2
    )

    assert result == pytest.approx(1.0)


def test_top_n_concentration_is_independent_of_mapping_order() -> None:
    first = {"A": 0.50, "B": 0.30, "C": 0.20}
    reordered = {"C": 0.20, "A": 0.50, "B": 0.30}

    assert calculate_top_n_concentration(
        first, top_n=2
    ) == pytest.approx(
        calculate_top_n_concentration(reordered, top_n=2)
    )


def test_calculate_top_n_concentration_does_not_mutate_input() -> None:
    weights = _weights()
    original = weights.copy()

    calculate_top_n_concentration(weights, top_n=2)

    assert weights == original
    assert list(weights) == list(original)


@pytest.mark.parametrize(
    ("weights", "expected"),
    [
        ({"A": 1.0}, 1.0),
        ({"A": 0.50, "B": 0.50}, 0.50),
        ({"A": 0.25, "B": 0.25, "C": 0.25, "D": 0.25}, 0.25),
        ({"A": 0.50, "B": 0.30, "C": 0.20}, 0.38),
        ({"A": 0.60, "B": 0.40, "ZERO": 0.0}, 0.52),
    ],
)
def test_calculate_hhi(
    weights: dict[str, float], expected: float
) -> None:
    result = calculate_hhi(weights)

    assert type(result) is float
    assert result == pytest.approx(expected)


def test_calculate_hhi_does_not_mutate_input() -> None:
    weights = _weights()
    original = weights.copy()

    calculate_hhi(weights)

    assert weights == original


@pytest.mark.parametrize(
    ("weights", "expected"),
    [
        ({"A": 1.0}, 1.0),
        ({"A": 0.50, "B": 0.50}, 2.0),
        ({"A": 0.25, "B": 0.25, "C": 0.25, "D": 0.25}, 4.0),
        ({"A": 0.50, "B": 0.30, "C": 0.20}, 1.0 / 0.38),
        ({"A": 0.50, "B": 0.50, "ZERO": 0.0}, 2.0),
    ],
)
def test_calculate_effective_number_of_assets(
    weights: dict[str, float], expected: float
) -> None:
    result = calculate_effective_number_of_assets(weights)

    assert type(result) is float
    assert result == pytest.approx(expected)


def test_effective_number_uses_unrounded_hhi() -> None:
    result = calculate_effective_number_of_assets(
        {"A": 0.40, "B": 0.30, "C": 0.20, "D": 0.10}
    )

    assert result == pytest.approx(10.0 / 3.0)
    assert result != pytest.approx(3.33, abs=1e-4)


def test_analyze_concentration_returns_complete_result() -> None:
    result = analyze_concentration(_weights(), top_n=2)

    assert isinstance(result, ConcentrationResult)
    assert result == ConcentrationResult(
        largest_weight=pytest.approx(0.50),
        top_n_weight=pytest.approx(0.80),
        hhi=pytest.approx(0.38),
        effective_number_of_assets=pytest.approx(1.0 / 0.38),
        top_n=2,
    )
    assert not hasattr(result, "risk_label")
    assert not hasattr(result, "concentration_label")


def test_concentration_result_is_immutable() -> None:
    result = analyze_concentration(_weights())

    with pytest.raises(FrozenInstanceError):
        result.hhi = 0.50  # type: ignore[misc]


def test_analyze_concentration_does_not_mutate_input() -> None:
    weights = _weights()
    original = weights.copy()

    analyze_concentration(weights, top_n=2)

    assert weights == original
    assert list(weights) == list(original)


def test_weight_total_exactly_one_is_accepted() -> None:
    assert calculate_hhi({"A": 0.40, "B": 0.60}) == pytest.approx(0.52)


def test_weight_total_just_inside_tolerance_is_accepted() -> None:
    result = calculate_top_n_concentration(
        {"A": 0.50, "B": 0.5000005}, top_n=2
    )

    assert result == pytest.approx(1.0000005)


def test_weight_total_outside_tolerance_is_rejected() -> None:
    with pytest.raises(ValueError, match="total weight"):
        calculate_hhi({"A": 0.50, "B": 0.5000011})


def test_numpy_numeric_scalars_are_accepted() -> None:
    weights = {
        "A": np.float64(0.50),
        "B": np.float32(0.50),
        "ZERO": np.int64(0),
    }

    assert calculate_hhi(weights) == pytest.approx(0.50)
    assert calculate_top_n_concentration(
        weights, top_n=np.int64(2)
    ) == pytest.approx(1.0)


def test_concentration_functions_reject_wrong_weights_type() -> None:
    with pytest.raises(TypeError, match="Mapping"):
        calculate_largest_weight(  # type: ignore[arg-type]
            [0.50, 0.30, 0.20]
        )


def test_concentration_functions_reject_empty_mapping() -> None:
    with pytest.raises(ValueError, match="at least one asset"):
        calculate_largest_weight({})


def test_concentration_functions_reject_non_string_symbol() -> None:
    with pytest.raises(TypeError, match="strings"):
        calculate_largest_weight(  # type: ignore[arg-type]
            {1: 1.0}
        )


@pytest.mark.parametrize("symbol", ["", " ", " A", "A "])
def test_concentration_functions_reject_invalid_symbol(symbol: str) -> None:
    with pytest.raises(ValueError, match="weight symbols"):
        calculate_largest_weight({symbol: 1.0})


@pytest.mark.parametrize(
    ("weights", "exception_type", "message"),
    [
        ({"A": 1.0, "B": -0.10}, ValueError, "between"),
        ({"A": 1.0, "B": 1.10}, ValueError, "between"),
        ({"A": 0.0, "B": 0.0}, ValueError, "greater than zero"),
        ({"A": 0.60, "B": 0.30}, ValueError, "total weight"),
        ({"A": np.nan}, ValueError, "finite"),
        ({"A": np.inf}, ValueError, "finite"),
        ({"A": -np.inf}, ValueError, "finite"),
        ({"A": True}, TypeError, "Boolean"),
        ({"A": 1.0 + 0.0j}, TypeError, "complex"),
        ({"A": "1.0"}, TypeError, "real numeric"),
        ({"A": 40}, ValueError, "between"),
    ],
)
def test_concentration_functions_reject_invalid_weights(
    weights: Mapping[str, object],
    exception_type: type[Exception],
    message: str,
) -> None:
    with pytest.raises(exception_type, match=message):
        calculate_largest_weight(weights)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("top_n", "exception_type", "message"),
    [
        (0, ValueError, "greater than zero"),
        (-1, ValueError, "greater than zero"),
        (1.0, TypeError, "integer"),
        ("1", TypeError, "integer"),
        (True, TypeError, "integer"),
    ],
)
def test_top_n_concentration_rejects_invalid_top_n(
    top_n: object,
    exception_type: type[Exception],
    message: str,
) -> None:
    with pytest.raises(exception_type, match=message):
        calculate_top_n_concentration(
            _weights(), top_n=top_n  # type: ignore[arg-type]
        )
