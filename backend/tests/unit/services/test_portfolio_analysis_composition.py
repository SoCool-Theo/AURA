from dataclasses import FrozenInstanceError, replace
from datetime import date
from decimal import Decimal
from uuid import UUID

import pytest

from backend.app.schemas import (
    AssetMetrics,
    PortfolioAnalysisRequest,
    PortfolioAnalysisResponse,
    RiskDriverEntry,
)
from backend.app.services.portfolio_analysis_composition import (
    PortfolioAnalysisCompositionError,
    PortfolioEnrichedAnalysisResult,
    compose_portfolio_analysis,
)
from backend.app.services.portfolio_analysis_preparation_service import (
    PortfolioAnalysisBaselineKind,
    PortfolioAnalysisPreparationResult,
    ResolvedPortfolioAnalysisWeight,
)
from backend.app.services.portfolio_planned_allocation_service import (
    PlannedAllocationHolding,
    PlannedPortfolioAllocation,
)
from backend.app.services.portfolio_valuation_service import (
    HoldingValuationResult,
    PortfolioDisplayCurrency,
    PortfolioFxContext,
    PortfolioValuationResult,
)


VALUATION_DATE = date(2026, 9, 12)
BASELINE_WEIGHTS = (
    ResolvedPortfolioAnalysisWeight("AAPL", Decimal("0.600000000000")),
    ResolvedPortfolioAnalysisWeight("BND", Decimal("0.400000000000")),
)


def _analysis_request() -> PortfolioAnalysisRequest:
    return PortfolioAnalysisRequest.model_validate(
        {
            "portfolio_name": "Current Core",
            "holdings": [
                {"symbol": "AAPL", "weight": 0.6},
                {"symbol": "BND", "weight": 0.4},
            ],
            "start_date": "2022-01-01",
            "end_date": "2022-12-31",
        }
    )


def _analysis_response() -> PortfolioAnalysisResponse:
    return PortfolioAnalysisResponse.model_validate(
        {
            "portfolio_name": "Current Core",
            "start_date": "2022-01-01",
            "end_date": "2022-12-31",
            "metadata": {
                "analysis_start": "2022-01-02",
                "analysis_end": "2022-01-04",
                "price_observation_count": 3,
                "return_observation_count": 2,
                "asset_count": 2,
            },
            "portfolio_metrics": {
                "cumulative_return": 0.071,
                "annualized_return": 0.193,
                "annualized_volatility": 0.287,
                "sharpe_ratio": 0.413,
            },
            "max_drawdown": {
                "max_drawdown": -0.173,
                "peak_date": "2022-03-10",
                "trough_date": "2022-06-14",
            },
            "concentration": {
                "largest_weight": 0.6,
                "top_n_weight": 1.0,
                "hhi": 0.52,
                "effective_number_of_assets": 1.923,
                "top_n": 2,
            },
            "diversification": {
                "active_asset_count": 2,
                "effective_number_of_assets": 1.923,
                "weight_score": 64.25,
                "average_pairwise_correlation": -0.17,
                "correlation_score": 88.5,
                "overall_score": 76.125,
                "level": "Strong",
                "defined_pair_count": 1,
                "total_pair_count": 1,
            },
            "risk_classification": {
                "risk_score": 47.0,
                "risk_level": "Moderate",
                "volatility_points": 2,
                "drawdown_points": 1,
                "concentration_points": 2,
                "diversification_points": 0,
                "metrics_used": [
                    "volatility",
                    "maximum_drawdown",
                    "concentration",
                    "diversification",
                ],
                "reasons": ["Distinctive fixture result"],
            },
            "risk_drivers": {
                "portfolio_volatility": 0.287,
                "top_driver": "BND",
                "entries": [
                    {
                        "rank": 1,
                        "symbol": "BND",
                        "weight": 0.4,
                        "annualized_asset_volatility": 0.119,
                        "marginal_volatility_contribution": 0.713,
                        "component_volatility_contribution": 0.281,
                        "percentage_volatility_contribution": 0.979,
                    },
                    {
                        "rank": 2,
                        "symbol": "AAPL",
                        "weight": 0.6,
                        "annualized_asset_volatility": 0.431,
                        "marginal_volatility_contribution": 0.009,
                        "component_volatility_contribution": 0.006,
                        "percentage_volatility_contribution": 0.021,
                    },
                ],
            },
            "asset_metrics": [
                {
                    "symbol": "BND",
                    "weight": 0.4,
                    "cumulative_return": -0.037,
                    "annualized_return": -0.041,
                    "annualized_volatility": 0.119,
                    "max_drawdown": -0.091,
                    "sharpe_ratio": -0.611,
                },
                {
                    "symbol": "AAPL",
                    "weight": 0.6,
                    "cumulative_return": 0.137,
                    "annualized_return": 0.251,
                    "annualized_volatility": 0.431,
                    "max_drawdown": -0.327,
                    "sharpe_ratio": 0.777,
                },
            ],
            "correlation_matrix": {
                "symbols": ["BND", "AAPL"],
                "values": [[1.0, -0.17], [-0.17, 1.0]],
            },
            "correlation_pairs": [
                {
                    "asset_a": "BND",
                    "asset_b": "AAPL",
                    "correlation": -0.17,
                }
            ],
            "portfolio_returns": [
                {"date": "2022-01-03", "portfolio_return": 0.013},
                {"date": "2022-01-04", "portfolio_return": -0.007},
            ],
        }
    )


def _valuation_holding(
    symbol: str,
    *,
    position: int,
    allocation: Decimal,
    invested_amount: Decimal,
    currency: str,
    shares: Decimal,
    asset_price: Decimal,
    current_value_usd: Decimal,
) -> HoldingValuationResult:
    return HoldingValuationResult(
        holding_id=UUID(
            f"61000000-0000-0000-0000-{position + 1:012d}"
        ),
        symbol=symbol,
        invested_amount=invested_amount,
        invested_currency=currency,
        shares=shares,
        purchase_date=date(2026, 1, position + 10),
        position=position,
        asset_price=asset_price,
        asset_quote_currency="USD",
        price_as_of=date(2026, 9, 11 - position),
        current_value_usd=current_value_usd,
        current_value=current_value_usd,
        current_allocation=allocation,
    )


def _valuation() -> PortfolioValuationResult:
    return PortfolioValuationResult(
        display_currency=PortfolioDisplayCurrency.USD,
        requested_date=VALUATION_DATE,
        oldest_price_as_of=date(2026, 9, 10),
        newest_price_as_of=date(2026, 9, 11),
        total_current_value_usd=Decimal("10000.000000000000"),
        total_current_value=Decimal("10000.000000000000"),
        fx_context=None,
        holdings=(
            _valuation_holding(
                "BND",
                position=1,
                allocation=Decimal("0.400000000000"),
                invested_amount=Decimal("90000.000000000000"),
                currency="THB",
                shares=Decimal("50.000000000000"),
                asset_price=Decimal("80.000000000000"),
                current_value_usd=Decimal("4000.000000000000"),
            ),
            _valuation_holding(
                "AAPL",
                position=0,
                allocation=Decimal("0.600000000000"),
                invested_amount=Decimal("1500.000000000000"),
                currency="USD",
                shares=Decimal("30.000000000000"),
                asset_price=Decimal("200.000000000000"),
                current_value_usd=Decimal("6000.000000000000"),
            ),
        ),
    )


def _real_preparation() -> PortfolioAnalysisPreparationResult:
    valuation = _valuation()
    return PortfolioAnalysisPreparationResult(
        baseline_kind=PortfolioAnalysisBaselineKind.REAL,
        resolved_weights=BASELINE_WEIGHTS,
        valuation=valuation,
        valuation_as_of=VALUATION_DATE,
        analysis_request=_analysis_request(),
    )


def test_real_thb_composition_preserves_one_coherent_valuation() -> None:
    preparation = _real_preparation()
    assert preparation.valuation is not None
    thb_holdings = tuple(
        replace(
            holding,
            current_value=holding.current_value_usd * Decimal("32.50"),
        )
        for holding in preparation.valuation.holdings
    )
    thb_valuation = replace(
        preparation.valuation,
        display_currency=PortfolioDisplayCurrency.THB,
        total_current_value=Decimal("325000.000000000000"),
        fx_context=PortfolioFxContext(
            pair="USD/THB",
            provider_symbol="THB=X",
            rate=Decimal("32.50"),
            as_of=VALUATION_DATE,
        ),
        holdings=thb_holdings,
    )
    thb_preparation = replace(preparation, valuation=thb_valuation)

    result = compose_portfolio_analysis(thb_preparation, _analysis_response())

    assert result.valuation is thb_valuation
    assert result.holdings[0].current_value == Decimal(
        "195000.00000000000000"
    )
    assert result.holdings[0].current_allocation == Decimal("0.600000000000")


def _legacy_preparation() -> PortfolioAnalysisPreparationResult:
    return PortfolioAnalysisPreparationResult(
        baseline_kind=PortfolioAnalysisBaselineKind.LEGACY,
        resolved_weights=BASELINE_WEIGHTS,
        valuation=None,
        valuation_as_of=None,
        analysis_request=_analysis_request(),
    )


def _planned_preparation() -> PortfolioAnalysisPreparationResult:
    allocation = PlannedPortfolioAllocation(
        portfolio_id=UUID("62000000-0000-0000-0000-000000000001"),
        plan_currency="USD",
        total_proposed_amount=Decimal("1000"),
        holdings=(
            PlannedAllocationHolding(
                holding_id=UUID("63000000-0000-0000-0000-000000000001"),
                symbol="AAPL",
                proposed_amount=Decimal("600"),
                target_allocation=Decimal("0.600000000000"),
                position=0,
            ),
            PlannedAllocationHolding(
                holding_id=UUID("63000000-0000-0000-0000-000000000002"),
                symbol="BND",
                proposed_amount=Decimal("400"),
                target_allocation=Decimal("0.400000000000"),
                position=1,
            ),
        ),
    )
    return PortfolioAnalysisPreparationResult(
        baseline_kind=PortfolioAnalysisBaselineKind.PLANNED,
        resolved_weights=BASELINE_WEIGHTS,
        valuation=None,
        valuation_as_of=None,
        analysis_request=_analysis_request(),
        planned_allocation=allocation,
    )


def _asset_metric(symbol: str, weight: float) -> AssetMetrics:
    return AssetMetrics(
        symbol=symbol,
        weight=weight,
        cumulative_return=0.111,
        annualized_return=0.222,
        annualized_volatility=0.333,
        max_drawdown=-0.444,
        sharpe_ratio=0.555,
    )


def _risk_driver(symbol: str, weight: float, rank: int) -> RiskDriverEntry:
    return RiskDriverEntry(
        rank=rank,
        symbol=symbol,
        weight=weight,
        annualized_asset_volatility=0.333,
        marginal_volatility_contribution=0.222,
        component_volatility_contribution=0.111,
        percentage_volatility_contribution=0.387,
    )


def test_real_composition_joins_by_symbol_in_saved_baseline_order() -> None:
    preparation = _real_preparation()
    analysis = _analysis_response()
    valuation = preparation.valuation
    assert valuation is not None

    result = compose_portfolio_analysis(preparation, analysis)

    assert result.baseline_kind is PortfolioAnalysisBaselineKind.REAL
    assert result.analysis is analysis
    assert result.valuation is valuation
    assert [holding.symbol for holding in result.holdings] == ["AAPL", "BND"]
    assert [holding.position for holding in result.holdings] == [0, 1]

    aapl, bnd = result.holdings
    assert aapl.holding_id == UUID("61000000-0000-0000-0000-000000000001")
    assert aapl.invested_amount == Decimal("1500.000000000000")
    assert aapl.invested_currency == "USD"
    assert aapl.shares == Decimal("30.000000000000")
    assert aapl.purchase_date == date(2026, 1, 10)
    assert aapl.asset_price == Decimal("200.000000000000")
    assert aapl.asset_quote_currency == "USD"
    assert aapl.price_as_of == date(2026, 9, 11)
    assert aapl.current_value_usd == Decimal("6000.000000000000")
    assert aapl.current_value == Decimal("6000.000000000000")
    assert aapl.current_allocation == Decimal("0.600000000000")
    assert aapl.resolved_weight == Decimal("0.600000000000")
    assert aapl.asset_metrics is analysis.asset_metrics[1]
    assert aapl.asset_metrics.annualized_volatility == 0.431
    assert aapl.asset_metrics.max_drawdown == -0.327
    assert aapl.risk_driver_entry is analysis.risk_drivers.entries[1]
    assert aapl.risk_driver_entry.rank == 2
    assert aapl.risk_driver_entry.component_volatility_contribution == 0.006

    assert bnd.asset_metrics is analysis.asset_metrics[0]
    assert bnd.risk_driver_entry is analysis.risk_drivers.entries[0]
    assert bnd.risk_driver_entry.rank == 1
    assert bnd.current_allocation == Decimal("0.400000000000")


def test_legacy_composition_retains_analytics_without_fabricating_facts() -> None:
    preparation = _legacy_preparation()
    analysis = _analysis_response()

    result = compose_portfolio_analysis(preparation, analysis)

    assert result.baseline_kind is PortfolioAnalysisBaselineKind.LEGACY
    assert result.valuation is None
    assert [holding.symbol for holding in result.holdings] == ["AAPL", "BND"]
    assert [holding.resolved_weight for holding in result.holdings] == [
        Decimal("0.600000000000"),
        Decimal("0.400000000000"),
    ]
    for holding in result.holdings:
        assert holding.holding_id is None
        assert holding.invested_amount is None
        assert holding.invested_currency is None
        assert holding.shares is None
        assert holding.purchase_date is None
        assert holding.position is None
        assert holding.asset_price is None
        assert holding.asset_quote_currency is None
        assert holding.price_as_of is None
        assert holding.current_value_usd is None
        assert holding.current_value is None
        assert holding.current_allocation is None
    assert result.holdings[0].asset_metrics is analysis.asset_metrics[1]
    assert result.holdings[0].risk_driver_entry is (
        analysis.risk_drivers.entries[1]
    )


def test_planned_composition_preserves_amounts_without_ownership_facts() -> None:
    preparation = _planned_preparation()
    analysis = _analysis_response()

    result = compose_portfolio_analysis(preparation, analysis)

    assert result.baseline_kind is PortfolioAnalysisBaselineKind.PLANNED
    assert result.valuation is None
    assert [holding.symbol for holding in result.holdings] == ["AAPL", "BND"]
    assert [holding.proposed_amount for holding in result.holdings] == [
        Decimal("600"),
        Decimal("400"),
    ]
    assert [holding.position for holding in result.holdings] == [0, 1]
    assert [holding.holding_id for holding in result.holdings] == [
        UUID("63000000-0000-0000-0000-000000000001"),
        UUID("63000000-0000-0000-0000-000000000002"),
    ]
    for holding in result.holdings:
        assert holding.invested_amount is None
        assert holding.invested_currency is None
        assert holding.shares is None
        assert holding.purchase_date is None
        assert holding.asset_price is None
        assert holding.current_value_usd is None
        assert holding.current_allocation is None


def test_planned_composition_rejects_target_weight_mismatch() -> None:
    preparation = _planned_preparation()
    assert preparation.planned_allocation is not None
    invalid = replace(
        preparation.planned_allocation.holdings[0],
        target_allocation=Decimal("0.61"),
    )
    invalid_allocation = replace(
        preparation.planned_allocation,
        holdings=(invalid, preparation.planned_allocation.holdings[1]),
    )

    with pytest.raises(
        PortfolioAnalysisCompositionError,
        match="planned allocation does not match prepared baseline: AAPL",
    ):
        compose_portfolio_analysis(
            replace(preparation, planned_allocation=invalid_allocation),
            _analysis_response(),
        )


@pytest.mark.parametrize(
    ("items", "message"),
    [
        (
            lambda analysis: [analysis.asset_metrics[0]],
            "missing asset metrics for symbols: AAPL",
        ),
        (
            lambda analysis: [
                analysis.asset_metrics[0],
                analysis.asset_metrics[1],
                analysis.asset_metrics[1],
            ],
            "duplicate asset-metric symbol: AAPL",
        ),
        (
            lambda analysis: [
                *analysis.asset_metrics,
                _asset_metric("GLD", 0.0),
            ],
            "unexpected asset metrics for symbols: GLD",
        ),
    ],
    ids=["missing", "duplicate", "unexpected"],
)
def test_composition_rejects_invalid_asset_metric_coverage(
    items: object,
    message: str,
) -> None:
    analysis = _analysis_response()
    invalid_items = items(analysis)  # type: ignore[operator]
    invalid_analysis = analysis.model_copy(
        update={"asset_metrics": invalid_items}
    )

    with pytest.raises(PortfolioAnalysisCompositionError, match=message):
        compose_portfolio_analysis(_real_preparation(), invalid_analysis)


@pytest.mark.parametrize(
    ("items", "message"),
    [
        (
            lambda analysis: [analysis.risk_drivers.entries[0]],
            "missing risk drivers for symbols: AAPL",
        ),
        (
            lambda analysis: [
                analysis.risk_drivers.entries[0],
                analysis.risk_drivers.entries[1],
                analysis.risk_drivers.entries[1],
            ],
            "duplicate risk-driver symbol: AAPL",
        ),
        (
            lambda analysis: [
                *analysis.risk_drivers.entries,
                _risk_driver("GLD", 0.0, 3),
            ],
            "unexpected risk drivers for symbols: GLD",
        ),
    ],
    ids=["missing", "duplicate", "unexpected"],
)
def test_composition_rejects_invalid_risk_driver_coverage(
    items: object,
    message: str,
) -> None:
    analysis = _analysis_response()
    invalid_entries = items(analysis)  # type: ignore[operator]
    invalid_drivers = analysis.risk_drivers.model_copy(
        update={"entries": invalid_entries}
    )
    invalid_analysis = analysis.model_copy(
        update={"risk_drivers": invalid_drivers}
    )

    with pytest.raises(PortfolioAnalysisCompositionError, match=message):
        compose_portfolio_analysis(_real_preparation(), invalid_analysis)


@pytest.mark.parametrize(
    ("holdings", "message"),
    [
        (
            lambda valuation: [valuation.holdings[0]],
            "missing valuation for symbols: AAPL",
        ),
        (
            lambda valuation: [
                valuation.holdings[0],
                valuation.holdings[1],
                valuation.holdings[1],
            ],
            "duplicate valuation symbol: AAPL",
        ),
        (
            lambda valuation: [
                *valuation.holdings,
                replace(valuation.holdings[0], symbol="GLD"),
            ],
            "unexpected valuation for symbols: GLD",
        ),
    ],
    ids=["missing", "duplicate", "unexpected"],
)
def test_real_composition_rejects_invalid_valuation_coverage(
    holdings: object,
    message: str,
) -> None:
    preparation = _real_preparation()
    assert preparation.valuation is not None
    invalid_holdings = holdings(preparation.valuation)  # type: ignore[operator]
    invalid_valuation = replace(
        preparation.valuation,
        holdings=tuple(invalid_holdings),
    )
    invalid_preparation = replace(
        preparation,
        valuation=invalid_valuation,
    )

    with pytest.raises(PortfolioAnalysisCompositionError, match=message):
        compose_portfolio_analysis(invalid_preparation, _analysis_response())


def test_real_composition_requires_valuation_context() -> None:
    preparation = replace(
        _real_preparation(),
        valuation=None,
        valuation_as_of=None,
    )

    with pytest.raises(
        PortfolioAnalysisCompositionError,
        match="real preparation requires valuation context",
    ):
        compose_portfolio_analysis(preparation, _analysis_response())


def test_legacy_composition_rejects_real_valuation_context() -> None:
    preparation = replace(
        _legacy_preparation(),
        valuation=_valuation(),
        valuation_as_of=VALUATION_DATE,
    )

    with pytest.raises(
        PortfolioAnalysisCompositionError,
        match="legacy preparation must not contain valuation context",
    ):
        compose_portfolio_analysis(preparation, _analysis_response())


def test_composition_rejects_prepared_baseline_symbol_mismatch() -> None:
    preparation = replace(
        _real_preparation(),
        resolved_weights=(
            ResolvedPortfolioAnalysisWeight("GLD", Decimal("0.6")),
            BASELINE_WEIGHTS[1],
        ),
    )

    with pytest.raises(
        PortfolioAnalysisCompositionError,
        match="analysis request symbols do not match prepared baseline order",
    ):
        compose_portfolio_analysis(preparation, _analysis_response())


def test_composition_preserves_exact_values_without_recalculation() -> None:
    result = compose_portfolio_analysis(
        _real_preparation(),
        _analysis_response(),
    )
    aapl = result.holdings[0]

    assert aapl.asset_price == Decimal("200.000000000000")
    assert aapl.current_value_usd == Decimal("6000.000000000000")
    assert aapl.current_allocation == Decimal("0.600000000000")
    assert aapl.asset_metrics.annualized_return == 0.251
    assert aapl.asset_metrics.annualized_volatility == 0.431
    assert aapl.asset_metrics.max_drawdown == -0.327
    assert aapl.asset_metrics.sharpe_ratio == 0.777
    assert aapl.risk_driver_entry.rank == 2
    assert aapl.risk_driver_entry.marginal_volatility_contribution == 0.009
    assert aapl.risk_driver_entry.component_volatility_contribution == 0.006
    assert (
        aapl.risk_driver_entry.percentage_volatility_contribution
        == 0.021
    )


def test_monetary_context_does_not_change_supplied_individual_metrics() -> None:
    analysis = _analysis_response()
    first = compose_portfolio_analysis(_real_preparation(), analysis)
    preparation = _real_preparation()
    assert preparation.valuation is not None
    changed_valuation = replace(
        preparation.valuation,
        holdings=tuple(
            replace(
                holding,
                invested_amount=holding.invested_amount * Decimal("100"),
                shares=holding.shares * Decimal("5"),
                asset_price=holding.asset_price / Decimal("5"),
            )
            for holding in preparation.valuation.holdings
        ),
    )
    second = compose_portfolio_analysis(
        replace(preparation, valuation=changed_valuation),
        analysis,
    )

    assert second.holdings[0].invested_amount != (
        first.holdings[0].invested_amount
    )
    assert second.holdings[0].shares != first.holdings[0].shares
    assert second.holdings[0].asset_metrics is first.holdings[0].asset_metrics
    assert second.holdings[0].asset_metrics.annualized_volatility == 0.431


def test_composition_preserves_exact_decimal_and_analytics_float_weights() -> None:
    preparation = _real_preparation()
    analysis = _analysis_response()

    result = compose_portfolio_analysis(preparation, analysis)

    assert result.holdings[0].resolved_weight is (
        preparation.resolved_weights[0].weight
    )
    assert result.holdings[0].current_allocation is (
        preparation.valuation.holdings[1].current_allocation
        if preparation.valuation is not None
        else None
    )
    assert result.holdings[0].asset_metrics.weight == 0.6
    assert type(result.holdings[0].asset_metrics.weight) is float
    assert type(result.holdings[0].current_allocation) is Decimal


def test_composition_does_not_mutate_any_input_objects() -> None:
    preparation = _real_preparation()
    analysis = _analysis_response()
    valuation = preparation.valuation
    preparation_snapshot = preparation
    analysis_snapshot = analysis.model_dump()
    valuation_snapshot = valuation
    asset_metrics_ids = [id(item) for item in analysis.asset_metrics]
    risk_driver_ids = [id(item) for item in analysis.risk_drivers.entries]

    result = compose_portfolio_analysis(preparation, analysis)

    assert preparation == preparation_snapshot
    assert preparation.valuation is valuation_snapshot
    assert analysis.model_dump() == analysis_snapshot
    assert [id(item) for item in analysis.asset_metrics] == asset_metrics_ids
    assert [id(item) for item in analysis.risk_drivers.entries] == (
        risk_driver_ids
    )
    assert result.analysis is analysis
    assert result.valuation is valuation


def test_composed_result_contract_is_frozen() -> None:
    result = compose_portfolio_analysis(
        _legacy_preparation(),
        _analysis_response(),
    )

    with pytest.raises(FrozenInstanceError):
        result.baseline_kind = PortfolioAnalysisBaselineKind.REAL
    with pytest.raises(FrozenInstanceError):
        result.holdings[0].resolved_weight = Decimal("1")


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        (
            "asset_metrics",
            [_asset_metric("AAPL", 0.5), _asset_metric("BND", 0.5)],
            "asset-metric weight does not match analysis request: AAPL",
        ),
        (
            "risk_drivers",
            [
                _risk_driver("BND", 0.5, 1),
                _risk_driver("AAPL", 0.5, 2),
            ],
            "risk-driver weight does not match analysis request: AAPL",
        ),
    ],
)
def test_composition_rejects_inconsistent_analytics_weights(
    field: str,
    value: list[object],
    message: str,
) -> None:
    analysis = _analysis_response()
    if field == "asset_metrics":
        invalid_analysis = analysis.model_copy(
            update={"asset_metrics": value}
        )
    else:
        invalid_drivers = analysis.risk_drivers.model_copy(
            update={"entries": value}
        )
        invalid_analysis = analysis.model_copy(
            update={"risk_drivers": invalid_drivers}
        )

    with pytest.raises(PortfolioAnalysisCompositionError, match=message):
        compose_portfolio_analysis(_real_preparation(), invalid_analysis)


def test_composition_rejects_real_allocation_mismatch_without_normalizing() -> None:
    preparation = _real_preparation()
    assert preparation.valuation is not None
    invalid_valuation = replace(
        preparation.valuation,
        holdings=(
            preparation.valuation.holdings[0],
            replace(
                preparation.valuation.holdings[1],
                current_allocation=Decimal("0.61"),
            ),
        ),
    )

    with pytest.raises(
        PortfolioAnalysisCompositionError,
        match="valuation allocation does not match prepared baseline: AAPL",
    ):
        compose_portfolio_analysis(
            replace(preparation, valuation=invalid_valuation),
            _analysis_response(),
        )
