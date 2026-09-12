"""Pure composition of prepared portfolio context and existing analytics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
import math
from typing import TypeVar
from uuid import UUID

from ..schemas import AssetMetrics, PortfolioAnalysisResponse, RiskDriverEntry
from .portfolio_analysis_preparation_service import (
    PortfolioAnalysisBaselineKind,
    PortfolioAnalysisPreparationResult,
)
from .portfolio_valuation_service import (
    HoldingValuationResult,
    PortfolioDisplayCurrency,
    PortfolioValuationResult,
)


_WEIGHT_TOLERANCE = 1e-9
_SymbolItem = TypeVar(
    "_SymbolItem",
    AssetMetrics,
    RiskDriverEntry,
    HoldingValuationResult,
)


class PortfolioAnalysisCompositionError(ValueError):
    """Raised when prepared, valuation, and analytics results disagree."""


@dataclass(frozen=True, slots=True)
class PortfolioEnrichedHoldingAnalysis:
    """One saved-order holding joined to its existing analysis results."""

    symbol: str
    resolved_weight: Decimal
    asset_metrics: AssetMetrics
    risk_driver_entry: RiskDriverEntry
    holding_id: UUID | None
    invested_amount: Decimal | None
    invested_currency: str | None
    shares: Decimal | None
    purchase_date: date | None
    position: int | None
    asset_price: Decimal | None
    asset_quote_currency: str | None
    price_as_of: date | None
    current_value_usd: Decimal | None
    current_value: Decimal | None
    current_allocation: Decimal | None


@dataclass(frozen=True, slots=True)
class PortfolioEnrichedAnalysisResult:
    """Immutable composed source for a later report snapshot contract."""

    baseline_kind: PortfolioAnalysisBaselineKind
    analysis: PortfolioAnalysisResponse
    valuation: PortfolioValuationResult | None
    holdings: tuple[PortfolioEnrichedHoldingAnalysis, ...]


def _index_unique_by_symbol(
    items: tuple[_SymbolItem, ...],
    *,
    label: str,
) -> dict[str, _SymbolItem]:
    indexed: dict[str, _SymbolItem] = {}
    for item in items:
        if item.symbol in indexed:
            raise PortfolioAnalysisCompositionError(
                f"duplicate {label} symbol: {item.symbol}"
            )
        indexed[item.symbol] = item
    return indexed


def _validate_symbol_coverage(
    *,
    expected_symbols: tuple[str, ...],
    actual_symbols: tuple[str, ...],
    label: str,
) -> None:
    expected_set = set(expected_symbols)
    actual_set = set(actual_symbols)
    missing = [
        symbol for symbol in expected_symbols if symbol not in actual_set
    ]
    if missing:
        raise PortfolioAnalysisCompositionError(
            f"missing {label} for symbols: {', '.join(missing)}"
        )
    unexpected = [
        symbol for symbol in actual_symbols if symbol not in expected_set
    ]
    if unexpected:
        raise PortfolioAnalysisCompositionError(
            f"unexpected {label} for symbols: {', '.join(unexpected)}"
        )


def _validate_analysis_identity(
    preparation: PortfolioAnalysisPreparationResult,
    analysis: PortfolioAnalysisResponse,
) -> None:
    request = preparation.analysis_request
    if analysis.portfolio_name != request.portfolio_name:
        raise PortfolioAnalysisCompositionError(
            "analysis portfolio name does not match preparation"
        )
    if (
        analysis.start_date != request.start_date
        or analysis.end_date != request.end_date
    ):
        raise PortfolioAnalysisCompositionError(
            "analysis period does not match preparation"
        )


def _validate_baseline_request(
    preparation: PortfolioAnalysisPreparationResult,
) -> tuple[str, ...]:
    baseline_symbols = tuple(
        holding.symbol for holding in preparation.resolved_weights
    )
    if len(baseline_symbols) != len(set(baseline_symbols)):
        raise PortfolioAnalysisCompositionError(
            "duplicate prepared baseline symbol"
        )

    request_holdings = tuple(preparation.analysis_request.holdings)
    request_symbols = tuple(holding.symbol for holding in request_holdings)
    if request_symbols != baseline_symbols:
        raise PortfolioAnalysisCompositionError(
            "analysis request symbols do not match prepared baseline order"
        )
    for resolved, requested in zip(
        preparation.resolved_weights,
        request_holdings,
        strict=True,
    ):
        if not math.isclose(
            float(resolved.weight),
            requested.weight,
            rel_tol=0.0,
            abs_tol=_WEIGHT_TOLERANCE,
        ):
            raise PortfolioAnalysisCompositionError(
                f"analysis request weight does not match baseline: "
                f"{resolved.symbol}"
            )
    return baseline_symbols


def _validate_analytics_weights(
    *,
    preparation: PortfolioAnalysisPreparationResult,
    asset_metrics_by_symbol: dict[str, AssetMetrics],
    risk_drivers_by_symbol: dict[str, RiskDriverEntry],
) -> None:
    request_weights = {
        holding.symbol: holding.weight
        for holding in preparation.analysis_request.holdings
    }
    for symbol, request_weight in request_weights.items():
        if not math.isclose(
            asset_metrics_by_symbol[symbol].weight,
            request_weight,
            rel_tol=0.0,
            abs_tol=_WEIGHT_TOLERANCE,
        ):
            raise PortfolioAnalysisCompositionError(
                f"asset-metric weight does not match analysis request: "
                f"{symbol}"
            )
        if not math.isclose(
            risk_drivers_by_symbol[symbol].weight,
            request_weight,
            rel_tol=0.0,
            abs_tol=_WEIGHT_TOLERANCE,
        ):
            raise PortfolioAnalysisCompositionError(
                f"risk-driver weight does not match analysis request: "
                f"{symbol}"
            )


def _validate_valuation_context(
    preparation: PortfolioAnalysisPreparationResult,
    baseline_symbols: tuple[str, ...],
) -> dict[str, HoldingValuationResult] | None:
    valuation = preparation.valuation
    if preparation.baseline_kind is PortfolioAnalysisBaselineKind.LEGACY:
        if valuation is not None or preparation.valuation_as_of is not None:
            raise PortfolioAnalysisCompositionError(
                "legacy preparation must not contain valuation context"
            )
        return None

    if preparation.baseline_kind is not PortfolioAnalysisBaselineKind.REAL:
        raise PortfolioAnalysisCompositionError(
            "unsupported portfolio analysis baseline kind"
        )
    if valuation is None or preparation.valuation_as_of is None:
        raise PortfolioAnalysisCompositionError(
            "real preparation requires valuation context"
        )
    if (
        valuation.display_currency is not PortfolioDisplayCurrency.USD
        or valuation.fx_context is not None
    ):
        raise PortfolioAnalysisCompositionError(
            "real analysis requires canonical USD valuation context"
        )
    if preparation.valuation_as_of != valuation.requested_date:
        raise PortfolioAnalysisCompositionError(
            "valuation date does not match preparation"
        )

    valuation_holdings = tuple(valuation.holdings)
    valuation_by_symbol = _index_unique_by_symbol(
        valuation_holdings,
        label="valuation",
    )
    valuation_symbols = tuple(
        holding.symbol for holding in valuation_holdings
    )
    _validate_symbol_coverage(
        expected_symbols=baseline_symbols,
        actual_symbols=valuation_symbols,
        label="valuation",
    )
    for resolved in preparation.resolved_weights:
        if (
            valuation_by_symbol[resolved.symbol].current_allocation
            != resolved.weight
        ):
            raise PortfolioAnalysisCompositionError(
                "valuation allocation does not match prepared baseline: "
                f"{resolved.symbol}"
            )
    return valuation_by_symbol


def compose_portfolio_analysis(
    preparation: PortfolioAnalysisPreparationResult,
    analysis: PortfolioAnalysisResponse,
) -> PortfolioEnrichedAnalysisResult:
    """Join validated upstream values without recalculating financial data."""
    baseline_symbols = _validate_baseline_request(preparation)
    _validate_analysis_identity(preparation, analysis)

    asset_metrics = tuple(analysis.asset_metrics)
    asset_metrics_by_symbol = _index_unique_by_symbol(
        asset_metrics,
        label="asset-metric",
    )
    _validate_symbol_coverage(
        expected_symbols=baseline_symbols,
        actual_symbols=tuple(item.symbol for item in asset_metrics),
        label="asset metrics",
    )

    risk_drivers = tuple(analysis.risk_drivers.entries)
    risk_drivers_by_symbol = _index_unique_by_symbol(
        risk_drivers,
        label="risk-driver",
    )
    _validate_symbol_coverage(
        expected_symbols=baseline_symbols,
        actual_symbols=tuple(item.symbol for item in risk_drivers),
        label="risk drivers",
    )
    _validate_analytics_weights(
        preparation=preparation,
        asset_metrics_by_symbol=asset_metrics_by_symbol,
        risk_drivers_by_symbol=risk_drivers_by_symbol,
    )
    valuation_by_symbol = _validate_valuation_context(
        preparation,
        baseline_symbols,
    )

    enriched_holdings = []
    for resolved in preparation.resolved_weights:
        valuation_holding = (
            None
            if valuation_by_symbol is None
            else valuation_by_symbol[resolved.symbol]
        )
        enriched_holdings.append(
            PortfolioEnrichedHoldingAnalysis(
                symbol=resolved.symbol,
                resolved_weight=resolved.weight,
                asset_metrics=asset_metrics_by_symbol[resolved.symbol],
                risk_driver_entry=risk_drivers_by_symbol[resolved.symbol],
                holding_id=(
                    None
                    if valuation_holding is None
                    else valuation_holding.holding_id
                ),
                invested_amount=(
                    None
                    if valuation_holding is None
                    else valuation_holding.invested_amount
                ),
                invested_currency=(
                    None
                    if valuation_holding is None
                    else valuation_holding.invested_currency
                ),
                shares=(
                    None
                    if valuation_holding is None
                    else valuation_holding.shares
                ),
                purchase_date=(
                    None
                    if valuation_holding is None
                    else valuation_holding.purchase_date
                ),
                position=(
                    None
                    if valuation_holding is None
                    else valuation_holding.position
                ),
                asset_price=(
                    None
                    if valuation_holding is None
                    else valuation_holding.asset_price
                ),
                asset_quote_currency=(
                    None
                    if valuation_holding is None
                    else valuation_holding.asset_quote_currency
                ),
                price_as_of=(
                    None
                    if valuation_holding is None
                    else valuation_holding.price_as_of
                ),
                current_value_usd=(
                    None
                    if valuation_holding is None
                    else valuation_holding.current_value_usd
                ),
                current_value=(
                    None
                    if valuation_holding is None
                    else valuation_holding.current_value
                ),
                current_allocation=(
                    None
                    if valuation_holding is None
                    else valuation_holding.current_allocation
                ),
            )
        )

    return PortfolioEnrichedAnalysisResult(
        baseline_kind=preparation.baseline_kind,
        analysis=analysis,
        valuation=preparation.valuation,
        holdings=tuple(enriched_holdings),
    )


__all__ = [
    "PortfolioAnalysisCompositionError",
    "PortfolioEnrichedAnalysisResult",
    "PortfolioEnrichedHoldingAnalysis",
    "compose_portfolio_analysis",
]
