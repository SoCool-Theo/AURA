import numpy as np
import pandas as pd
import pytest

from backend.app.analytics._validation import (
    _validate_datetime_index,
    _validate_positive_integer,
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
