"""Asset-correlation calculations for validated periodic returns."""

import math
from numbers import Real

import numpy as np
import pandas as pd


_CORRELATION_TOLERANCE = 1e-12
_PAIR_COLUMNS = ["asset_1", "asset_2", "correlation"]


def _validate_datetime_index(index: pd.Index) -> None:
    if not isinstance(index, pd.DatetimeIndex):
        raise TypeError("asset_returns index must be a pandas DatetimeIndex")
    if index.hasnans:
        raise ValueError("asset_returns index cannot contain NaT")
    if index.tz is not None:
        raise ValueError("asset_returns index must be timezone-naive")
    if index.has_duplicates:
        raise ValueError(
            "asset_returns index cannot contain duplicate timestamps"
        )
    if not index.is_monotonic_increasing:
        raise ValueError("asset_returns index must be strictly increasing")


def _validate_symbols(
    symbols: pd.Index, input_name: str, label_name: str
) -> None:
    if not symbols.is_unique:
        raise ValueError(f"{input_name} {label_name} must be unique")

    for symbol in symbols:
        if not isinstance(symbol, str):
            raise TypeError("asset symbols must be strings")
        if not symbol:
            raise ValueError("asset symbols cannot be empty")
        if not symbol.strip():
            raise ValueError("asset symbols cannot be whitespace-only")
        if symbol != symbol.strip():
            raise ValueError(
                "asset symbols cannot contain leading or trailing whitespace"
            )


def _validated_asset_return_values(asset_returns: pd.DataFrame) -> np.ndarray:
    if not isinstance(asset_returns, pd.DataFrame):
        raise TypeError("asset_returns must be a pandas DataFrame")
    if len(asset_returns.index) < 2:
        raise ValueError("asset_returns must contain at least two rows")
    if len(asset_returns.columns) == 0:
        raise ValueError("asset_returns must contain at least one asset column")

    _validate_datetime_index(asset_returns.index)
    _validate_symbols(asset_returns.columns, "asset_returns", "symbols")

    validated: list[float] = []
    for value in np.asarray(asset_returns.to_numpy(), dtype=object).flat:
        if isinstance(value, (bool, np.bool_)):
            raise TypeError("asset_returns values cannot be Boolean")
        if isinstance(value, (complex, np.complexfloating)):
            raise TypeError("asset_returns values cannot be complex")
        if pd.isna(value):
            raise ValueError("asset_returns values cannot be missing")
        if not isinstance(value, Real):
            raise TypeError(
                "asset_returns values must be real numeric values"
            )

        numeric_value = float(value)
        if not math.isfinite(numeric_value):
            raise ValueError("asset_returns values must be finite")
        if numeric_value <= -1.0:
            raise ValueError(
                "asset_returns values must be greater than -1.0"
            )
        validated.append(numeric_value)

    return np.asarray(validated, dtype=float).reshape(asset_returns.shape)


def _validated_correlation_values(
    correlation_matrix: pd.DataFrame,
) -> np.ndarray:
    if not isinstance(correlation_matrix, pd.DataFrame):
        raise TypeError("correlation_matrix must be a pandas DataFrame")
    if len(correlation_matrix.columns) == 0:
        raise ValueError(
            "correlation_matrix must contain at least one asset"
        )
    if correlation_matrix.shape[0] != correlation_matrix.shape[1]:
        raise ValueError("correlation_matrix must be square")

    _validate_symbols(
        correlation_matrix.index, "correlation_matrix", "row labels"
    )
    _validate_symbols(
        correlation_matrix.columns, "correlation_matrix", "column labels"
    )
    if not correlation_matrix.index.equals(correlation_matrix.columns):
        raise ValueError(
            "correlation_matrix row and column labels must match "
            "exactly and in the same order"
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

    diagonal = np.diag(values)
    undefined_assets = np.isnan(diagonal)
    for position, diagonal_value in enumerate(diagonal):
        if not math.isnan(diagonal_value) and not math.isclose(
            diagonal_value,
            1.0,
            rel_tol=0.0,
            abs_tol=_CORRELATION_TOLERANCE,
        ):
            raise ValueError(
                "non-NaN correlation_matrix diagonal values must equal 1.0"
            )
        if undefined_assets[position] and not nan_positions[position].all():
            raise ValueError(
                "an asset with undefined self-correlation must have only "
                "undefined correlations"
            )

    for row_position in range(len(values)):
        for column_position in range(row_position + 1, len(values)):
            if nan_positions[row_position, column_position] and not (
                undefined_assets[row_position]
                or undefined_assets[column_position]
            ):
                raise ValueError(
                    "NaN is allowed only for undefined asset correlations"
                )

    return values


def calculate_correlation_matrix(
    asset_returns: pd.DataFrame,
) -> pd.DataFrame:
    """Calculate the Pearson correlation matrix for asset returns."""
    _validated_asset_return_values(asset_returns)
    return asset_returns.corr(method="pearson")


def extract_correlation_pairs(
    correlation_matrix: pd.DataFrame,
) -> pd.DataFrame:
    """Extract each unique asset pair in the matrix's label order."""
    values = _validated_correlation_values(correlation_matrix)
    symbols = correlation_matrix.columns
    pairs = [
        (symbols[first], symbols[second], values[first, second])
        for first in range(len(symbols))
        for second in range(first + 1, len(symbols))
    ]
    return pd.DataFrame(pairs, columns=_PAIR_COLUMNS)
