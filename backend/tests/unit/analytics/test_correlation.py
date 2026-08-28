import numpy as np
import pandas as pd
import pytest

from backend.app.analytics.correlation import (
    calculate_correlation_matrix,
    extract_correlation_pairs,
)


def _asset_returns() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ALPHA": [-0.10, 0.0, 0.10],
            "BETA": [0.20, 0.0, -0.20],
            "GAMMA": [-0.10, 0.10, 0.0],
        },
        index=pd.date_range("2026-01-01", periods=3, freq="D"),
    )


def _correlation_matrix() -> pd.DataFrame:
    symbols = ["BETA", "ALPHA", "GAMMA"]
    return pd.DataFrame(
        [
            [1.0, 0.25, np.nan],
            [0.25, 1.0, np.nan],
            [np.nan, np.nan, np.nan],
        ],
        index=symbols,
        columns=symbols,
    )


def test_correlation_matrix_has_known_pearson_values() -> None:
    expected = pd.DataFrame(
        [
            [1.0, -1.0, 0.5],
            [-1.0, 1.0, -0.5],
            [0.5, -0.5, 1.0],
        ],
        index=["ALPHA", "BETA", "GAMMA"],
        columns=["ALPHA", "BETA", "GAMMA"],
    )

    result = calculate_correlation_matrix(_asset_returns())

    pd.testing.assert_frame_equal(
        result, expected, check_exact=False, rtol=1e-12, atol=1e-12
    )


def test_correlation_matrix_preserves_labels_order_and_structure() -> None:
    asset_returns = _asset_returns()

    result = calculate_correlation_matrix(asset_returns)

    assert isinstance(result, pd.DataFrame)
    assert list(result.index) == ["ALPHA", "BETA", "GAMMA"]
    assert list(result.columns) == ["ALPHA", "BETA", "GAMMA"]
    assert result.index.equals(result.columns)
    np.testing.assert_allclose(result, result.T)
    np.testing.assert_allclose(np.diag(result), [1.0, 1.0, 1.0])


def test_correlation_matrix_includes_perfect_positive_correlation() -> None:
    asset_returns = pd.DataFrame(
        {
            "A": [-0.10, 0.0, 0.10],
            "B": [-0.20, 0.0, 0.20],
        },
        index=pd.date_range("2026-01-01", periods=3),
    )

    result = calculate_correlation_matrix(asset_returns)

    assert result.loc["A", "B"] == pytest.approx(1.0)


def test_correlation_matrix_includes_perfect_negative_correlation() -> None:
    result = calculate_correlation_matrix(_asset_returns())

    assert result.loc["ALPHA", "BETA"] == pytest.approx(-1.0)


def test_correlation_matrix_does_not_mutate_input() -> None:
    asset_returns = _asset_returns()
    original = asset_returns.copy(deep=True)

    calculate_correlation_matrix(asset_returns)

    pd.testing.assert_frame_equal(asset_returns, original)


def test_correlation_matrix_allows_constant_asset() -> None:
    asset_returns = pd.DataFrame(
        {
            "ALPHA": [-0.10, 0.0, 0.10],
            "CONSTANT": [0.02, 0.02, 0.02],
            "BETA": [0.10, 0.0, -0.10],
        },
        index=pd.date_range("2026-01-01", periods=3),
    )

    result = calculate_correlation_matrix(asset_returns)

    assert result.loc["ALPHA", "BETA"] == pytest.approx(-1.0)
    assert result.loc["CONSTANT"].isna().all()
    assert result["CONSTANT"].isna().all()
    assert not (result.loc["CONSTANT"].fillna(1.0) == 0.0).any()


def test_extract_correlation_pairs_returns_unique_ordered_pairs() -> None:
    matrix = _correlation_matrix()
    expected = pd.DataFrame(
        {
            "asset_1": ["BETA", "BETA", "ALPHA"],
            "asset_2": ["ALPHA", "GAMMA", "GAMMA"],
            "correlation": [0.25, np.nan, np.nan],
        }
    )

    result = extract_correlation_pairs(matrix)

    pd.testing.assert_frame_equal(result, expected)
    assert not (result["asset_1"] == result["asset_2"]).any()
    assert len(result) == 3


def test_extract_correlation_pairs_uses_source_values() -> None:
    matrix = pd.DataFrame(
        [[1.0, -0.75], [-0.75, 1.0]],
        index=["B", "A"],
        columns=["B", "A"],
    )

    result = extract_correlation_pairs(matrix)

    assert result.to_dict("records") == [
        {"asset_1": "B", "asset_2": "A", "correlation": -0.75}
    ]


def test_extract_correlation_pairs_has_no_reverse_duplicates() -> None:
    result = extract_correlation_pairs(_correlation_matrix())
    pairs = list(zip(result["asset_1"], result["asset_2"], strict=True))

    assert ("ALPHA", "BETA") not in pairs
    assert len(pairs) == len(set(pairs))


def test_extract_correlation_pairs_preserves_undefined_correlation() -> None:
    result = extract_correlation_pairs(_correlation_matrix())

    undefined_pairs = result[result["asset_2"] == "GAMMA"]
    assert undefined_pairs["correlation"].isna().all()


def test_extract_correlation_pairs_returns_expected_empty_frame_for_one_asset() -> None:
    matrix = pd.DataFrame([[1.0]], index=["ALPHA"], columns=["ALPHA"])

    result = extract_correlation_pairs(matrix)

    assert result.empty
    assert list(result.columns) == ["asset_1", "asset_2", "correlation"]


def test_extract_correlation_pairs_does_not_mutate_input() -> None:
    matrix = _correlation_matrix()
    original = matrix.copy(deep=True)

    extract_correlation_pairs(matrix)

    pd.testing.assert_frame_equal(matrix, original)


def test_correlation_matrix_rejects_wrong_input_type() -> None:
    with pytest.raises(TypeError, match="pandas DataFrame"):
        calculate_correlation_matrix(  # type: ignore[arg-type]
            [[0.10], [0.20]]
        )


@pytest.mark.parametrize(
    "asset_returns",
    [
        pd.DataFrame(index=pd.DatetimeIndex([])),
        pd.DataFrame(
            {"A": [0.10]},
            index=pd.to_datetime(["2026-01-01"]),
        ),
    ],
)
def test_correlation_matrix_requires_two_rows(
    asset_returns: pd.DataFrame,
) -> None:
    with pytest.raises(ValueError, match="at least two rows"):
        calculate_correlation_matrix(asset_returns)


def test_correlation_matrix_requires_asset_column() -> None:
    asset_returns = pd.DataFrame(
        index=pd.date_range("2026-01-01", periods=2)
    )

    with pytest.raises(ValueError, match="asset column"):
        calculate_correlation_matrix(asset_returns)


@pytest.mark.parametrize(
    ("index", "exception_type", "message"),
    [
        (pd.Index([0, 1]), TypeError, "DatetimeIndex"),
        (
            pd.to_datetime(["2026-01-01", "2026-01-01"]),
            ValueError,
            "duplicate",
        ),
        (
            pd.to_datetime(["2026-01-02", "2026-01-01"]),
            ValueError,
            "strictly increasing",
        ),
        (
            pd.DatetimeIndex(["2026-01-01", pd.NaT]),
            ValueError,
            "NaT",
        ),
        (
            pd.date_range("2026-01-01", periods=2, tz="UTC"),
            ValueError,
            "timezone-naive",
        ),
    ],
)
def test_correlation_matrix_rejects_invalid_index(
    index: pd.Index,
    exception_type: type[Exception],
    message: str,
) -> None:
    asset_returns = pd.DataFrame({"A": [0.10, 0.20]}, index=index)

    with pytest.raises(exception_type, match=message):
        calculate_correlation_matrix(asset_returns)


def test_correlation_matrix_rejects_duplicate_symbols() -> None:
    asset_returns = pd.DataFrame(
        [[0.10, 0.20], [0.20, 0.30]],
        index=pd.date_range("2026-01-01", periods=2),
        columns=["A", "A"],
    )

    with pytest.raises(ValueError, match="unique"):
        calculate_correlation_matrix(asset_returns)


@pytest.mark.parametrize("symbol", ["", " ", " A", "A "])
def test_correlation_matrix_rejects_invalid_symbols(symbol: str) -> None:
    asset_returns = pd.DataFrame(
        {symbol: [0.10, 0.20]},
        index=pd.date_range("2026-01-01", periods=2),
    )

    with pytest.raises(ValueError, match="symbol"):
        calculate_correlation_matrix(asset_returns)


def test_correlation_matrix_rejects_non_string_symbol() -> None:
    asset_returns = pd.DataFrame(
        {1: [0.10, 0.20]},
        index=pd.date_range("2026-01-01", periods=2),
    )

    with pytest.raises(TypeError, match="strings"):
        calculate_correlation_matrix(asset_returns)


@pytest.mark.parametrize(
    ("invalid_value", "exception_type", "message"),
    [
        (np.nan, ValueError, "missing"),
        (np.inf, ValueError, "finite"),
        (-np.inf, ValueError, "finite"),
        (True, TypeError, "Boolean"),
        (0.10 + 0.0j, TypeError, "complex"),
        ("0.10", TypeError, "real numeric"),
        (-1.0, ValueError, "greater than -1.0"),
        (-1.01, ValueError, "greater than -1.0"),
    ],
)
def test_correlation_matrix_rejects_invalid_values(
    invalid_value: object,
    exception_type: type[Exception],
    message: str,
) -> None:
    asset_returns = pd.DataFrame(
        {"A": [0.10, invalid_value]},
        index=pd.date_range("2026-01-01", periods=2),
    )

    with pytest.raises(exception_type, match=message):
        calculate_correlation_matrix(asset_returns)


def test_extract_correlation_pairs_rejects_wrong_input_type() -> None:
    with pytest.raises(TypeError, match="pandas DataFrame"):
        extract_correlation_pairs(  # type: ignore[arg-type]
            [[1.0, 0.5], [0.5, 1.0]]
        )


def test_extract_correlation_pairs_rejects_empty_matrix() -> None:
    with pytest.raises(ValueError, match="at least one asset"):
        extract_correlation_pairs(pd.DataFrame())


def test_extract_correlation_pairs_rejects_non_square_matrix() -> None:
    matrix = pd.DataFrame(
        [[1.0, 0.5]],
        index=["A"],
        columns=["A", "B"],
    )

    with pytest.raises(ValueError, match="square"):
        extract_correlation_pairs(matrix)


@pytest.mark.parametrize(
    ("index", "columns"),
    [
        (["A", "B"], ["A", "C"]),
        (["A", "B"], ["B", "A"]),
    ],
)
def test_extract_correlation_pairs_requires_matching_label_order(
    index: list[str],
    columns: list[str],
) -> None:
    matrix = pd.DataFrame(
        [[1.0, 0.5], [0.5, 1.0]],
        index=index,
        columns=columns,
    )

    with pytest.raises(ValueError, match="match exactly"):
        extract_correlation_pairs(matrix)


def test_extract_correlation_pairs_rejects_duplicate_labels() -> None:
    matrix = pd.DataFrame(
        [[1.0, 0.5], [0.5, 1.0]],
        index=["A", "A"],
        columns=["A", "A"],
    )

    with pytest.raises(ValueError, match="unique"):
        extract_correlation_pairs(matrix)


@pytest.mark.parametrize("symbol", ["", " ", " A", "A "])
def test_extract_correlation_pairs_rejects_invalid_symbols(symbol: str) -> None:
    matrix = pd.DataFrame([[1.0]], index=[symbol], columns=[symbol])

    with pytest.raises(ValueError, match="symbol"):
        extract_correlation_pairs(matrix)


def test_extract_correlation_pairs_rejects_non_string_symbol() -> None:
    matrix = pd.DataFrame([[1.0]], index=[1], columns=[1])

    with pytest.raises(TypeError, match="strings"):
        extract_correlation_pairs(matrix)


def test_extract_correlation_pairs_rejects_non_symmetric_values() -> None:
    matrix = pd.DataFrame(
        [[1.0, 0.25], [0.50, 1.0]],
        index=["A", "B"],
        columns=["A", "B"],
    )

    with pytest.raises(ValueError, match="symmetric"):
        extract_correlation_pairs(matrix)


def test_extract_correlation_pairs_rejects_mismatched_nan_symmetry() -> None:
    matrix = pd.DataFrame(
        [[1.0, np.nan], [0.25, 1.0]],
        index=["A", "B"],
        columns=["A", "B"],
    )

    with pytest.raises(ValueError, match="NaN positions.*symmetric"):
        extract_correlation_pairs(matrix)


@pytest.mark.parametrize("invalid_value", [1.0001, -1.0001])
def test_extract_correlation_pairs_rejects_out_of_range_value(
    invalid_value: float,
) -> None:
    matrix = pd.DataFrame(
        [[1.0, invalid_value], [invalid_value, 1.0]],
        index=["A", "B"],
        columns=["A", "B"],
    )

    with pytest.raises(ValueError, match="between -1.0 and 1.0"):
        extract_correlation_pairs(matrix)


@pytest.mark.parametrize("invalid_value", [np.inf, -np.inf])
def test_extract_correlation_pairs_rejects_infinity(
    invalid_value: float,
) -> None:
    matrix = pd.DataFrame(
        [[1.0, invalid_value], [invalid_value, 1.0]],
        index=["A", "B"],
        columns=["A", "B"],
    )

    with pytest.raises(ValueError, match="finite"):
        extract_correlation_pairs(matrix)


@pytest.mark.parametrize(
    ("invalid_value", "message"),
    [(True, "Boolean"), (0.25 + 0.0j, "complex")],
)
def test_extract_correlation_pairs_rejects_invalid_value_types(
    invalid_value: object,
    message: str,
) -> None:
    matrix = pd.DataFrame(
        [[1.0, invalid_value], [invalid_value, 1.0]],
        index=["A", "B"],
        columns=["A", "B"],
    )

    with pytest.raises(TypeError, match=message):
        extract_correlation_pairs(matrix)


def test_extract_correlation_pairs_rejects_invalid_diagonal() -> None:
    matrix = pd.DataFrame(
        [[0.90, 0.25], [0.25, 1.0]],
        index=["A", "B"],
        columns=["A", "B"],
    )

    with pytest.raises(ValueError, match="diagonal.*1.0"):
        extract_correlation_pairs(matrix)


def test_extract_correlation_pairs_rejects_nan_without_undefined_asset() -> None:
    matrix = pd.DataFrame(
        [[1.0, np.nan], [np.nan, 1.0]],
        index=["A", "B"],
        columns=["A", "B"],
    )

    with pytest.raises(ValueError, match="only for undefined"):
        extract_correlation_pairs(matrix)
