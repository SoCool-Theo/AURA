import numpy as np
import pandas as pd
import pytest

from backend.app.analytics._validation import (
    _validate_datetime_index,
    _validate_positive_integer,
    _validated_finite_real_values,
)


def test_validate_datetime_index_accepts_valid_increasing_index() -> None:
    index = pd.date_range("2026-01-01", periods=3, freq="D")

    _validate_datetime_index(index, "prices")


def test_validate_datetime_index_accepts_empty_index() -> None:
    index = pd.DatetimeIndex([])

    result = _validate_datetime_index(index, "prices")

    assert result is None


def test_validate_datetime_index_rejects_non_datetime_index() -> None:
    index = pd.Index([0, 1])

    with pytest.raises(TypeError) as error:
        _validate_datetime_index(index, "returns")

    assert str(error.value) == (
        "returns index must be a pandas DatetimeIndex"
    )


def test_validate_datetime_index_rejects_nat() -> None:
    index = pd.DatetimeIndex(["2026-01-01", pd.NaT])

    with pytest.raises(ValueError) as error:
        _validate_datetime_index(index, "returns")

    assert str(error.value) == "returns index cannot contain NaT"


def test_validate_datetime_index_rejects_timezone_aware_index() -> None:
    index = pd.date_range("2026-01-01", periods=2, tz="UTC")

    with pytest.raises(ValueError) as error:
        _validate_datetime_index(index, "returns")

    assert str(error.value) == "returns index must be timezone-naive"


def test_validate_datetime_index_rejects_duplicate_timestamps() -> None:
    index = pd.to_datetime(["2026-01-01", "2026-01-01"])

    with pytest.raises(ValueError) as error:
        _validate_datetime_index(index, "returns")

    assert str(error.value) == (
        "returns index cannot contain duplicate timestamps"
    )


def test_validate_datetime_index_rejects_non_increasing_index() -> None:
    index = pd.to_datetime(["2026-01-02", "2026-01-01"])

    with pytest.raises(ValueError) as error:
        _validate_datetime_index(index, "returns")

    assert str(error.value) == "returns index must be strictly increasing"


def test_validate_datetime_index_uses_custom_input_name() -> None:
    index = pd.Index([0, 1])

    with pytest.raises(TypeError) as error:
        _validate_datetime_index(index, "custom_input")

    assert str(error.value) == (
        "custom_input index must be a pandas DatetimeIndex"
    )


def test_validate_datetime_index_returns_none() -> None:
    index = pd.date_range("2026-01-01", periods=2)

    result = _validate_datetime_index(index, "returns")

    assert result is None


def test_validate_datetime_index_does_not_mutate_input() -> None:
    index = pd.date_range("2026-01-01", periods=3, name="date")
    original = index.copy(deep=True)

    _validate_datetime_index(index, "returns")

    pd.testing.assert_index_equal(index, original, exact=True)


def test_validate_datetime_index_reports_nat_before_timezone() -> None:
    index = pd.DatetimeIndex(["2026-01-01", pd.NaT], tz="UTC")

    with pytest.raises(ValueError) as error:
        _validate_datetime_index(index, "returns")

    assert str(error.value) == "returns index cannot contain NaT"


def test_validate_datetime_index_reports_timezone_before_duplicates() -> None:
    index = pd.DatetimeIndex(
        ["2026-01-01", "2026-01-01"],
        tz="UTC",
    )

    with pytest.raises(ValueError) as error:
        _validate_datetime_index(index, "returns")

    assert str(error.value) == "returns index must be timezone-naive"


def test_validate_datetime_index_reports_duplicates_before_order() -> None:
    index = pd.to_datetime(
        ["2026-01-02", "2026-01-01", "2026-01-01"]
    )

    with pytest.raises(ValueError) as error:
        _validate_datetime_index(index, "returns")

    assert str(error.value) == (
        "returns index cannot contain duplicate timestamps"
    )


def test_validate_positive_integer_accepts_positive_python_integer() -> None:
    assert _validate_positive_integer(252, "periods_per_year") == 252


def test_validate_positive_integer_accepts_positive_numpy_integer() -> None:
    assert _validate_positive_integer(
        np.int64(12),
        "periods_per_year",
    ) == 12


def test_validate_positive_integer_returns_python_integer() -> None:
    result = _validate_positive_integer(np.int64(3), "top_n")

    assert type(result) is int


def test_validate_positive_integer_rejects_true() -> None:
    with pytest.raises(TypeError) as error:
        _validate_positive_integer(True, "periods_per_year")

    assert str(error.value) == "periods_per_year must be an integer"


def test_validate_positive_integer_rejects_false() -> None:
    with pytest.raises(TypeError) as error:
        _validate_positive_integer(False, "periods_per_year")

    assert str(error.value) == "periods_per_year must be an integer"


def test_validate_positive_integer_rejects_zero() -> None:
    with pytest.raises(ValueError) as error:
        _validate_positive_integer(0, "periods_per_year")

    assert str(error.value) == "periods_per_year must be greater than zero"


def test_validate_positive_integer_rejects_negative_python_integer() -> None:
    with pytest.raises(ValueError) as error:
        _validate_positive_integer(-1, "periods_per_year")

    assert str(error.value) == "periods_per_year must be greater than zero"


def test_validate_positive_integer_rejects_negative_numpy_integer() -> None:
    with pytest.raises(ValueError) as error:
        _validate_positive_integer(np.int64(-1), "periods_per_year")

    assert str(error.value) == "periods_per_year must be greater than zero"


def test_validate_positive_integer_rejects_positive_float() -> None:
    with pytest.raises(TypeError) as error:
        _validate_positive_integer(1.5, "periods_per_year")

    assert str(error.value) == "periods_per_year must be an integer"


def test_validate_positive_integer_rejects_integer_valued_float() -> None:
    with pytest.raises(TypeError) as error:
        _validate_positive_integer(252.0, "periods_per_year")

    assert str(error.value) == "periods_per_year must be an integer"


def test_validate_positive_integer_rejects_numpy_float() -> None:
    with pytest.raises(TypeError) as error:
        _validate_positive_integer(np.float64(252.0), "periods_per_year")

    assert str(error.value) == "periods_per_year must be an integer"


def test_validate_positive_integer_rejects_string() -> None:
    with pytest.raises(TypeError) as error:
        _validate_positive_integer("252", "periods_per_year")

    assert str(error.value) == "periods_per_year must be an integer"


def test_validate_positive_integer_rejects_complex_value() -> None:
    with pytest.raises(TypeError) as error:
        _validate_positive_integer(252 + 0j, "periods_per_year")

    assert str(error.value) == "periods_per_year must be an integer"


def test_validate_positive_integer_rejects_none() -> None:
    with pytest.raises(TypeError) as error:
        _validate_positive_integer(None, "periods_per_year")

    assert str(error.value) == "periods_per_year must be an integer"


def test_validate_positive_integer_uses_custom_type_error_name() -> None:
    with pytest.raises(TypeError) as error:
        _validate_positive_integer(1.0, "custom_count")

    assert str(error.value) == "custom_count must be an integer"


def test_validate_positive_integer_uses_custom_value_error_name() -> None:
    with pytest.raises(ValueError) as error:
        _validate_positive_integer(0, "custom_count")

    assert str(error.value) == "custom_count must be greater than zero"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (7, 7.0),
        (2.5, 2.5),
        (np.int64(11), 11.0),
        (np.float32(1.25), 1.25),
    ],
)
def test_validated_finite_real_values_accepts_real_scalars(
    value: object,
    expected: float,
) -> None:
    result = _validated_finite_real_values(value, "metric")

    assert result.shape == ()
    assert result.item() == expected


def test_validated_finite_real_values_accepts_one_dimensional_array() -> None:
    values = np.array([1, 2.5, 3])

    result = _validated_finite_real_values(values, "metric")

    np.testing.assert_array_equal(result, np.array([1.0, 2.5, 3.0]))


def test_validated_finite_real_values_accepts_two_dimensional_array() -> None:
    values = np.array([[1, 2], [3, 4]])

    result = _validated_finite_real_values(values, "metric")

    np.testing.assert_array_equal(
        result,
        np.array([[1.0, 2.0], [3.0, 4.0]]),
    )


def test_validated_finite_real_values_accepts_valid_object_array() -> None:
    values = np.array(
        [1, np.int64(2), np.float32(3.5)],
        dtype=object,
    )

    result = _validated_finite_real_values(values, "metric")

    np.testing.assert_array_equal(result, np.array([1.0, 2.0, 3.5]))


def test_validated_finite_real_values_accepts_empty_array() -> None:
    values = np.empty((0, 2), dtype=object)

    result = _validated_finite_real_values(values, "metric")

    assert result.shape == (0, 2)
    assert result.size == 0


def test_validated_finite_real_values_accepts_zero_dimensional_array() -> None:
    values = np.array(-3.5)

    result = _validated_finite_real_values(values, "metric")

    assert result.shape == ()
    assert result.item() == -3.5


def test_validated_finite_real_values_accepts_negative_and_zero_values() -> None:
    values = np.array([-4.5, 0.0])

    result = _validated_finite_real_values(values, "metric")

    np.testing.assert_array_equal(result, values)


def test_validated_finite_real_values_returns_float_ndarray() -> None:
    result = _validated_finite_real_values([1, 2], "metric")

    assert isinstance(result, np.ndarray)
    assert np.issubdtype(result.dtype, np.floating)


def test_validated_finite_real_values_preserves_shape() -> None:
    values = np.arange(24).reshape(2, 3, 4)

    result = _validated_finite_real_values(values, "metric")

    assert result.shape == values.shape


def test_validated_finite_real_values_returns_independent_array() -> None:
    values = np.array([1.0, 2.0])

    result = _validated_finite_real_values(values, "metric")

    assert result is not values
    assert not np.shares_memory(result, values)


def test_validated_finite_real_values_does_not_mutate_source() -> None:
    values = np.array([1.0, 2.0])
    original = values.copy()

    result = _validated_finite_real_values(values, "metric")
    result[0] = 99.0

    np.testing.assert_array_equal(values, original)


@pytest.mark.parametrize(
    "value",
    [True, False, np.bool_(True)],
)
def test_validated_finite_real_values_rejects_boolean_scalar(
    value: object,
) -> None:
    with pytest.raises(TypeError) as error:
        _validated_finite_real_values(value, "metric")

    assert str(error.value) == "metric values cannot be Boolean"


def test_validated_finite_real_values_rejects_embedded_boolean() -> None:
    values = np.array([1.0, True], dtype=object)

    with pytest.raises(TypeError) as error:
        _validated_finite_real_values(values, "metric")

    assert str(error.value) == "metric values cannot be Boolean"


def test_validated_finite_real_values_uses_custom_boolean_message() -> None:
    with pytest.raises(TypeError) as error:
        _validated_finite_real_values(True, "custom_input")

    assert str(error.value) == "custom_input values cannot be Boolean"


@pytest.mark.parametrize(
    "value",
    [1 + 2j, np.complex128(2 + 3j), 1 + 0j],
)
def test_validated_finite_real_values_rejects_complex_scalar(
    value: object,
) -> None:
    with pytest.raises(TypeError) as error:
        _validated_finite_real_values(value, "metric")

    assert str(error.value) == "metric values cannot be complex"


def test_validated_finite_real_values_rejects_embedded_complex() -> None:
    values = np.array([1.0, np.complex64(2 + 0j)], dtype=object)

    with pytest.raises(TypeError) as error:
        _validated_finite_real_values(values, "metric")

    assert str(error.value) == "metric values cannot be complex"


def test_validated_finite_real_values_uses_custom_complex_message() -> None:
    with pytest.raises(TypeError) as error:
        _validated_finite_real_values(1 + 0j, "custom_input")

    assert str(error.value) == "custom_input values cannot be complex"


@pytest.mark.parametrize(
    "value",
    [None, np.nan, pd.NA, pd.NaT],
)
def test_validated_finite_real_values_rejects_missing_scalar(
    value: object,
) -> None:
    with pytest.raises(ValueError) as error:
        _validated_finite_real_values(value, "metric")

    assert str(error.value) == "metric values cannot be missing"


def test_validated_finite_real_values_rejects_embedded_missing_value() -> None:
    values = np.array([1.0, None], dtype=object)

    with pytest.raises(ValueError) as error:
        _validated_finite_real_values(values, "metric")

    assert str(error.value) == "metric values cannot be missing"


def test_validated_finite_real_values_uses_custom_missing_message() -> None:
    with pytest.raises(ValueError) as error:
        _validated_finite_real_values(pd.NA, "custom_input")

    assert str(error.value) == "custom_input values cannot be missing"


@pytest.mark.parametrize(
    "value",
    ["1.25", "not-a-number", object()],
)
def test_validated_finite_real_values_rejects_non_real_value(
    value: object,
) -> None:
    with pytest.raises(TypeError) as error:
        _validated_finite_real_values(value, "metric")

    assert str(error.value) == (
        "metric values must be real numeric values"
    )


def test_validated_finite_real_values_uses_custom_real_numeric_message() -> None:
    with pytest.raises(TypeError) as error:
        _validated_finite_real_values("1.25", "custom_input")

    assert str(error.value) == (
        "custom_input values must be real numeric values"
    )


@pytest.mark.parametrize(
    "value",
    [np.inf, -np.inf],
)
def test_validated_finite_real_values_rejects_nonfinite_scalar(
    value: object,
) -> None:
    with pytest.raises(ValueError) as error:
        _validated_finite_real_values(value, "metric")

    assert str(error.value) == "metric values must be finite"


def test_validated_finite_real_values_rejects_embedded_infinity() -> None:
    values = np.array([1.0, np.inf])

    with pytest.raises(ValueError) as error:
        _validated_finite_real_values(values, "metric")

    assert str(error.value) == "metric values must be finite"


def test_validated_finite_real_values_uses_custom_finite_message() -> None:
    with pytest.raises(ValueError) as error:
        _validated_finite_real_values(np.inf, "custom_input")

    assert str(error.value) == "custom_input values must be finite"


@pytest.mark.parametrize(
    ("values", "exception_type", "message"),
    [
        (
            np.array([True, 1 + 0j], dtype=object),
            TypeError,
            "ordered values cannot be Boolean",
        ),
        (
            np.array([1 + 0j, None], dtype=object),
            TypeError,
            "ordered values cannot be complex",
        ),
        (
            np.array([None, "invalid"], dtype=object),
            ValueError,
            "ordered values cannot be missing",
        ),
        (
            np.array(["invalid", np.inf], dtype=object),
            TypeError,
            "ordered values must be real numeric values",
        ),
    ],
)
def test_validated_finite_real_values_reports_first_invalid_element(
    values: np.ndarray,
    exception_type: type[Exception],
    message: str,
) -> None:
    with pytest.raises(exception_type) as error:
        _validated_finite_real_values(values, "ordered")

    assert str(error.value) == message
