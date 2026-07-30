"""Internal validation primitives for Aura analytics."""

import math
from numbers import Integral, Real

import numpy as np
import pandas as pd


def _validate_datetime_index(index: pd.Index, input_name: str) -> None:
    if not isinstance(index, pd.DatetimeIndex):
        raise TypeError(f"{input_name} index must be a pandas DatetimeIndex")
    if index.hasnans:
        raise ValueError(f"{input_name} index cannot contain NaT")
    if index.tz is not None:
        raise ValueError(f"{input_name} index must be timezone-naive")
    if index.has_duplicates:
        raise ValueError(
            f"{input_name} index cannot contain duplicate timestamps"
        )
    if not index.is_monotonic_increasing:
        raise ValueError(f"{input_name} index must be strictly increasing")


def _validate_positive_integer(value: object, input_name: str) -> int:
    if isinstance(value, (bool, np.bool_)):
        raise TypeError(f"{input_name} must be an integer")
    if not isinstance(value, Integral):
        raise TypeError(f"{input_name} must be an integer")

    validated_value = int(value)
    if validated_value <= 0:
        raise ValueError(f"{input_name} must be greater than zero")
    return validated_value


def _validated_finite_real_values(
    values: object,
    input_name: str,
) -> np.ndarray:
    inspected_values = np.asarray(values, dtype=object)
    validated: list[float] = []

    for value in inspected_values.flat:
        if isinstance(value, (bool, np.bool_)):
            raise TypeError(f"{input_name} values cannot be Boolean")
        if isinstance(value, (complex, np.complexfloating)):
            raise TypeError(f"{input_name} values cannot be complex")
        if pd.isna(value):
            raise ValueError(f"{input_name} values cannot be missing")
        if not isinstance(value, Real):
            raise TypeError(
                f"{input_name} values must be real numeric values"
            )

        numeric_value = float(value)
        if not math.isfinite(numeric_value):
            raise ValueError(f"{input_name} values must be finite")
        validated.append(numeric_value)

    return np.asarray(validated, dtype=float).reshape(inspected_values.shape)
