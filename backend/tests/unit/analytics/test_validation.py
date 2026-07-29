import pandas as pd
import pytest

from backend.app.analytics._validation import _validate_datetime_index


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
