"""Internal validation primitives for Aura analytics."""

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
