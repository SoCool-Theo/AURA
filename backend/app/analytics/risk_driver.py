"""Portfolio volatility risk-contribution calculations."""

import math
from collections.abc import Mapping
from dataclasses import dataclass
from numbers import Integral, Real

import numpy as np
import pandas as pd

from ._validation import _validate_datetime_index


_WEIGHT_TOLERANCE = 1e-6
_CONTRIBUTION_TOLERANCE = 1e-6
_ZERO_VARIANCE_TOLERANCE = 1e-15
_CONTRIBUTION_COLUMNS = [
    "weight",
    "annualized_asset_volatility",
    "marginal_volatility_contribution",
    "component_volatility_contribution",
    "percentage_volatility_contribution",
]


@dataclass(frozen=True, slots=True)
class RiskDriverResult:
    """Contain portfolio volatility and ranked risk contributions."""

    portfolio_volatility: float
    top_driver: str
    ranked_contributions: pd.DataFrame


def _validate_symbols(symbols: pd.Index, input_name: str) -> None:
    if not symbols.is_unique:
        raise ValueError(f"{input_name} asset symbols must be unique")

    for symbol in symbols:
        if not isinstance(symbol, str):
            raise TypeError(f"{input_name} asset symbols must be strings")
        if not symbol:
            raise ValueError(f"{input_name} asset symbols cannot be empty")
        if not symbol.strip():
            raise ValueError(
                f"{input_name} asset symbols cannot be whitespace-only"
            )
        if symbol != symbol.strip():
            raise ValueError(
                f"{input_name} asset symbols cannot contain leading or "
                "trailing whitespace"
            )


def _validated_asset_return_values(
    asset_returns: pd.DataFrame,
) -> np.ndarray:
    if not isinstance(asset_returns, pd.DataFrame):
        raise TypeError("asset_returns must be a pandas DataFrame")
    if len(asset_returns.index) < 2:
        raise ValueError("asset_returns must contain at least two rows")
    if len(asset_returns.columns) == 0:
        raise ValueError(
            "asset_returns must contain at least one asset column"
        )

    _validate_datetime_index(asset_returns.index, "asset_returns")
    _validate_symbols(asset_returns.columns, "asset_returns")

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


def _validated_weights(
    weights: Mapping[str, float],
    asset_symbols: pd.Index,
) -> np.ndarray:
    if not isinstance(weights, Mapping):
        raise TypeError("weights must implement Mapping")

    weight_items = list(weights.items())
    if not weight_items:
        raise ValueError("weights must contain at least one asset")

    weight_symbols = [symbol for symbol, _ in weight_items]
    _validate_symbols(pd.Index(weight_symbols), "weight")
    if set(weight_symbols) != set(asset_symbols):
        raise ValueError(
            "weight symbols must exactly match the asset-return columns"
        )

    validated: dict[str, float] = {}
    for symbol, value in weight_items:
        if isinstance(value, (bool, np.bool_)):
            raise TypeError("weight values cannot be Boolean")
        if isinstance(value, (complex, np.complexfloating)):
            raise TypeError("weight values cannot be complex")
        if not isinstance(value, Real):
            raise TypeError("weight values must be real numeric values")

        numeric_value = float(value)
        if not math.isfinite(numeric_value):
            raise ValueError("weight values must be finite")
        if numeric_value < 0.0 or numeric_value > 1.0:
            raise ValueError(
                "each weight must be between 0.0 and 1.0 inclusive"
            )
        validated[symbol] = numeric_value

    if not any(weight > 0.0 for weight in validated.values()):
        raise ValueError("at least one weight must be greater than zero")
    if abs(math.fsum(validated.values()) - 1.0) > _WEIGHT_TOLERANCE:
        raise ValueError(
            "total weight must equal 1.0 within a tolerance of 1e-6"
        )

    return np.asarray(
        [validated[symbol] for symbol in asset_symbols],
        dtype=float,
    )


def _validated_periods_per_year(periods_per_year: int) -> int:
    if isinstance(periods_per_year, (bool, np.bool_)) or not isinstance(
        periods_per_year, Integral
    ):
        raise TypeError("periods_per_year must be an integer")
    if periods_per_year <= 0:
        raise ValueError("periods_per_year must be greater than zero")
    return int(periods_per_year)


def _calculate_portfolio_volatility(
    annualized_covariance: np.ndarray,
    aligned_weights: np.ndarray,
) -> tuple[float, np.ndarray]:
    covariance_weight_product = annualized_covariance @ aligned_weights
    portfolio_variance = float(aligned_weights @ covariance_weight_product)

    if not math.isfinite(portfolio_variance):
        raise ValueError("calculated portfolio variance must be finite")
    if portfolio_variance < -_ZERO_VARIANCE_TOLERANCE:
        raise ValueError(
            "calculated portfolio variance is materially negative"
        )
    if portfolio_variance <= _ZERO_VARIANCE_TOLERANCE:
        raise ValueError(
            "risk contribution is undefined for a zero-volatility portfolio"
        )

    portfolio_volatility = math.sqrt(portfolio_variance)
    if portfolio_volatility <= math.sqrt(_ZERO_VARIANCE_TOLERANCE):
        raise ValueError(
            "risk contribution is undefined for a zero-volatility portfolio"
        )
    return float(portfolio_volatility), covariance_weight_product


def _validated_contribution_values(
    contributions: pd.DataFrame,
) -> np.ndarray:
    if not isinstance(contributions, pd.DataFrame):
        raise TypeError("contributions must be a pandas DataFrame")
    if contributions.empty:
        raise ValueError("contributions must contain at least one asset")
    if (
        not contributions.columns.is_unique
        or set(contributions.columns) != set(_CONTRIBUTION_COLUMNS)
        or len(contributions.columns) != len(_CONTRIBUTION_COLUMNS)
    ):
        raise ValueError(
            "contributions must contain exactly the required contribution "
            "columns"
        )
    if contributions.index.name != "asset":
        raise ValueError("contributions index name must be 'asset'")

    _validate_symbols(contributions.index, "contributions")

    validated: list[float] = []
    for value in np.asarray(contributions.to_numpy(), dtype=object).flat:
        if isinstance(value, (bool, np.bool_)):
            raise TypeError("contribution values cannot be Boolean")
        if isinstance(value, (complex, np.complexfloating)):
            raise TypeError("contribution values cannot be complex")
        if pd.isna(value):
            raise ValueError("contribution values cannot be missing")
        if not isinstance(value, Real):
            raise TypeError(
                "contribution values must be real numeric values"
            )

        numeric_value = float(value)
        if not math.isfinite(numeric_value):
            raise ValueError("contribution values must be finite")
        validated.append(numeric_value)

    values = np.asarray(validated, dtype=float).reshape(contributions.shape)
    column_positions = {
        column: contributions.columns.get_loc(column)
        for column in _CONTRIBUTION_COLUMNS
    }
    weight_values = values[:, column_positions["weight"]]
    if np.any((weight_values < 0.0) | (weight_values > 1.0)):
        raise ValueError(
            "contribution weights must be between 0.0 and 1.0 inclusive"
        )

    volatility_values = values[
        :, column_positions["annualized_asset_volatility"]
    ]
    if np.any(volatility_values < 0.0):
        raise ValueError(
            "annualized asset volatility values cannot be negative"
        )

    component_values = values[
        :, column_positions["component_volatility_contribution"]
    ]
    if math.fsum(component_values) <= 0.0:
        raise ValueError(
            "component volatility contributions must sum to a positive value"
        )

    percentage_values = values[
        :, column_positions["percentage_volatility_contribution"]
    ]
    if (
        abs(math.fsum(percentage_values) - 1.0)
        > _CONTRIBUTION_TOLERANCE
    ):
        raise ValueError(
            "percentage volatility contributions must sum to 1.0 within "
            "a tolerance of 1e-6"
        )
    return values


def calculate_risk_contributions(
    asset_returns: pd.DataFrame,
    weights: Mapping[str, float],
    periods_per_year: int = 252,
) -> pd.DataFrame:
    """Calculate signed asset contributions to portfolio volatility."""
    return_values = _validated_asset_return_values(asset_returns)
    aligned_weights = _validated_weights(weights, asset_returns.columns)
    annualization_factor = _validated_periods_per_year(periods_per_year)

    numeric_returns = pd.DataFrame(
        return_values,
        index=asset_returns.index,
        columns=asset_returns.columns,
    )
    periodic_covariance = numeric_returns.cov(ddof=1)
    annualized_covariance = (
        periodic_covariance.to_numpy(dtype=float) * annualization_factor
    )
    if not np.isfinite(annualized_covariance).all():
        raise ValueError("calculated annualized covariance must be finite")

    diagonal = np.diag(annualized_covariance)
    if np.any(diagonal < -_ZERO_VARIANCE_TOLERANCE):
        raise ValueError(
            "calculated annualized asset variance cannot be negative"
        )
    annualized_asset_volatility = np.sqrt(np.maximum(diagonal, 0.0))

    portfolio_volatility, covariance_weight_product = (
        _calculate_portfolio_volatility(
            annualized_covariance,
            aligned_weights,
        )
    )
    marginal_contribution = (
        covariance_weight_product / portfolio_volatility
    )
    component_contribution = aligned_weights * marginal_contribution
    percentage_contribution = (
        component_contribution / portfolio_volatility
    )

    values = np.column_stack(
        [
            aligned_weights,
            annualized_asset_volatility,
            marginal_contribution,
            component_contribution,
            percentage_contribution,
        ]
    ).astype(float, copy=False)
    return pd.DataFrame(
        values,
        index=pd.Index(asset_returns.columns, name="asset"),
        columns=_CONTRIBUTION_COLUMNS,
    )


def rank_risk_drivers(
    contributions: pd.DataFrame,
) -> pd.DataFrame:
    """Rank assets by signed component volatility contribution."""
    _validated_contribution_values(contributions)
    ranked = contributions.sort_values(
        "component_volatility_contribution",
        ascending=False,
        kind="stable",
    ).copy()
    ranked.insert(0, "rank", np.arange(1, len(ranked) + 1, dtype=int))
    return ranked


def analyze_risk_drivers(
    asset_returns: pd.DataFrame,
    weights: Mapping[str, float],
    periods_per_year: int = 252,
) -> RiskDriverResult:
    """Calculate and rank portfolio volatility risk drivers."""
    contributions = calculate_risk_contributions(
        asset_returns,
        weights,
        periods_per_year=periods_per_year,
    )
    ranked = rank_risk_drivers(contributions)
    portfolio_volatility = float(
        math.fsum(ranked["component_volatility_contribution"])
    )
    return RiskDriverResult(
        portfolio_volatility=portfolio_volatility,
        top_driver=str(ranked.index[0]),
        ranked_contributions=ranked,
    )
