import json
from copy import deepcopy
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

import pytest
from pydantic import ValidationError

from backend.app.database.models import Analysis
from backend.app.schemas.analytics import PortfolioAnalysisResponse
from backend.app.schemas.reporting import (
    PortfolioReportResponse,
    PortfolioReportSummary,
    PortfolioReportV2Response,
    PortfolioReportV2Snapshot,
    PortfolioReportV3Response,
    PortfolioReportV3Snapshot,
)
from backend.app.services.analysis_reporting_mapper import (
    PORTFOLIO_ANALYSIS_RESPONSE_SCHEMA_VERSION,
    PORTFOLIO_ANALYSIS_RESPONSE_V2_SCHEMA_VERSION,
    PORTFOLIO_ANALYSIS_RESPONSE_V3_SCHEMA_VERSION,
    analysis_to_asset_report_monetary_metrics,
    analysis_to_report_monetary_metrics,
    analysis_record_to_report_response,
    analysis_record_to_report_summary,
    analysis_response_to_snapshot,
    enriched_analysis_to_v2_snapshot,
    enriched_analysis_to_v3_snapshot,
)
from backend.app.services.portfolio_analysis_composition import (
    compose_portfolio_analysis,
)
from backend.app.services.portfolio_valuation_service import (
    PortfolioDisplayCurrency,
    PortfolioFxContext,
)
from backend.tests.unit.services.test_portfolio_analysis_composition import (
    _analysis_response as _real_analysis_response,
    _real_preparation,
    _planned_preparation,
)
from backend.tests.unit.schemas.test_reporting import _valid_analysis_data


_REPORT_ID = UUID("10000000-0000-0000-0000-000000000001")
_PORTFOLIO_ID = UUID("20000000-0000-0000-0000-000000000001")
_CREATED_AT = datetime(2026, 8, 18, 10, 30, tzinfo=UTC)


def _valid_response() -> PortfolioAnalysisResponse:
    return PortfolioAnalysisResponse.model_validate(_valid_analysis_data())


def _analysis_record(
    *,
    result_snapshot: dict[str, object] | None = None,
    schema_version: str = PORTFOLIO_ANALYSIS_RESPONSE_SCHEMA_VERSION,
    start_date: date = date(2026, 1, 1),
    end_date: date = date(2026, 1, 31),
    created_at: datetime = _CREATED_AT,
) -> Analysis:
    snapshot = (
        analysis_response_to_snapshot(_valid_response())
        if result_snapshot is None
        else result_snapshot
    )
    return Analysis(
        id=_REPORT_ID,
        portfolio_id=_PORTFOLIO_ID,
        start_date=start_date,
        end_date=end_date,
        schema_version=schema_version,
        result_snapshot=snapshot,
        created_at=created_at,
    )


def test_snapshot_version_constant_uses_approved_token() -> None:
    assert PORTFOLIO_ANALYSIS_RESPONSE_SCHEMA_VERSION == (
        "portfolio-analysis-response-v1"
    )


def _valid_v2_snapshot() -> dict[str, object]:
    enriched = compose_portfolio_analysis(
        _real_preparation(),
        _real_analysis_response(),
    )
    return enriched_analysis_to_v2_snapshot(enriched)


def _valid_v2_report() -> PortfolioReportV2Response:
    analysis = _analysis_record(
        result_snapshot=_valid_v2_snapshot(),
        schema_version=PORTFOLIO_ANALYSIS_RESPONSE_V2_SCHEMA_VERSION,
        start_date=date(2022, 1, 1),
        end_date=date(2022, 12, 31),
    )
    result = analysis_record_to_report_response(analysis)
    assert isinstance(result, PortfolioReportV2Response)
    return result


def test_v2_snapshot_version_constant_uses_approved_token() -> None:
    assert PORTFOLIO_ANALYSIS_RESPONSE_V2_SCHEMA_VERSION == (
        "portfolio-analysis-response-v2"
    )


def _valid_v3_snapshot() -> dict[str, object]:
    enriched = compose_portfolio_analysis(
        _planned_preparation(),
        _real_analysis_response(),
    )
    return enriched_analysis_to_v3_snapshot(enriched)


def test_v3_snapshot_version_constant_uses_approved_token() -> None:
    assert PORTFOLIO_ANALYSIS_RESPONSE_V3_SCHEMA_VERSION == (
        "portfolio-analysis-response-v3"
    )


def test_report_monetary_metrics_use_saved_reference_and_exact_drawdown_path(
) -> None:
    metrics = analysis_to_report_monetary_metrics(
        _valid_response(),
        currency="USD",
        basis="saved-current-valuation",
        reference_amount=Decimal("1000"),
    )

    assert metrics.currency == "USD"
    assert metrics.basis == "saved-current-valuation"
    assert metrics.reference_amount == Decimal("1000")
    assert metrics.cumulative_return_amount == Decimal("40.094000")
    assert metrics.annualized_return_amount == Decimal("200.0")
    assert metrics.maximum_drawdown_amount == Decimal("-10.200000")
    assert metrics.estimated_ending_value is None


def test_planned_report_monetary_metrics_include_estimated_ending_value(
) -> None:
    metrics = analysis_to_report_monetary_metrics(
        _valid_response(),
        currency="USD",
        basis="planned-proposed-amount",
        reference_amount=Decimal("1000"),
    )

    assert metrics.cumulative_return_amount == Decimal("40.094000")
    assert metrics.estimated_ending_value == Decimal("1040.094000")


def test_asset_report_monetary_metrics_use_each_saved_reference_and_path(
) -> None:
    metrics = analysis_to_asset_report_monetary_metrics(
        _valid_response(),
        currency="USD",
        basis="saved-current-value",
        reference_amounts={
            "AAPL": Decimal("1000"),
            "MSFT": Decimal("2000"),
            "BND": Decimal("3000"),
        },
    )

    assert [metric.symbol for metric in metrics] == ["AAPL", "MSFT", "BND"]
    assert metrics[0].currency == "USD"
    assert metrics[0].basis == "saved-current-value"
    assert metrics[0].reference_amount == Decimal("1000")
    assert metrics[0].cumulative_return_amount == Decimal("80.00")
    assert metrics[0].annualized_return_amount == Decimal("240.00")
    assert metrics[0].maximum_drawdown_amount == Decimal("-20.60000")
    assert metrics[1].reference_amount == Decimal("2000")
    assert metrics[1].cumulative_return_amount == Decimal("120.00")
    assert metrics[1].annualized_return_amount == Decimal("360.00")
    assert metrics[1].maximum_drawdown_amount is None


def test_asset_report_monetary_metrics_require_complete_reference_symbols(
) -> None:
    with pytest.raises(
        ValueError,
        match="reference symbols must match analysis assets",
    ):
        analysis_to_asset_report_monetary_metrics(
            _valid_response(),
            currency="USD",
            basis="saved-current-value",
            reference_amounts={"AAPL": Decimal("1000")},
        )


def test_planned_enriched_result_maps_to_complete_json_safe_v3_snapshot() -> None:
    preparation = _planned_preparation()
    analysis = _real_analysis_response()
    enriched = compose_portfolio_analysis(preparation, analysis)

    snapshot = enriched_analysis_to_v3_snapshot(enriched)
    validated = PortfolioReportV3Snapshot.model_validate(snapshot)

    json.dumps(snapshot, allow_nan=False)
    assert validated.schema_version == "portfolio-analysis-response-v3"
    assert validated.analysis == analysis
    assert validated.baseline.portfolio_type == "PLANNED"
    assert validated.baseline.baseline_source == (
        "proposed-amount-target-allocation"
    )
    assert validated.baseline.total_proposed_amount == Decimal("1000")
    assert [holding.symbol for holding in validated.baseline.holdings] == [
        "AAPL",
        "BND",
    ]
    assert [
        holding.proposed_amount for holding in validated.baseline.holdings
    ] == [Decimal("600"), Decimal("400")]
    assert "estimated_shares" not in snapshot["baseline"]["holdings"][0]


def test_v3_record_restores_frozen_plan_without_recalculation_or_mutation() -> None:
    snapshot = _valid_v3_snapshot()
    frozen_snapshot = deepcopy(snapshot)
    analysis = _analysis_record(
        result_snapshot=snapshot,
        schema_version=PORTFOLIO_ANALYSIS_RESPONSE_V3_SCHEMA_VERSION,
        start_date=date(2022, 1, 1),
        end_date=date(2022, 12, 31),
    )

    result = analysis_record_to_report_response(analysis)

    assert isinstance(result, PortfolioReportV3Response)
    assert result.schema_version == "portfolio-analysis-response-v3"
    assert result.baseline.total_proposed_amount == Decimal("1000")
    assert result.analysis == _real_analysis_response()
    assert result.monetary_metrics is not None
    assert result.monetary_metrics.basis == "planned-proposed-amount"
    assert result.monetary_metrics.reference_amount == Decimal("1000")
    assert result.monetary_metrics.estimated_ending_value == Decimal("1071.000")
    assert [
        metric.symbol for metric in result.asset_monetary_metrics
    ] == ["BND", "AAPL"]
    assert [
        metric.reference_amount for metric in result.asset_monetary_metrics
    ] == [Decimal("400"), Decimal("600")]
    assert all(
        metric.basis == "planned-proposed-amount"
        for metric in result.asset_monetary_metrics
    )
    assert all(
        metric.maximum_drawdown_amount is None
        for metric in result.asset_monetary_metrics
    )
    assert analysis.result_snapshot == frozen_snapshot


def test_real_enriched_result_maps_to_complete_json_safe_v2_snapshot() -> None:
    preparation = _real_preparation()
    analysis = _real_analysis_response()
    enriched = compose_portfolio_analysis(preparation, analysis)

    snapshot = enriched_analysis_to_v2_snapshot(enriched)
    validated = PortfolioReportV2Snapshot.model_validate(snapshot)

    json.dumps(snapshot, allow_nan=False)
    assert validated.schema_version == "portfolio-analysis-response-v2"
    assert validated.analysis is not analysis
    assert validated.analysis == analysis
    assert validated.valuation.valuation_currency == "USD"
    assert validated.valuation.requested_date == date(2026, 9, 12)
    assert validated.valuation.total_current_value_usd == Decimal(
        "10000.000000000000"
    )
    assert validated.valuation.fx is None
    assert [holding.symbol for holding in validated.holdings] == [
        "AAPL",
        "BND",
    ]
    assert validated.holdings[0].asset_price == Decimal("200.000000000000")
    assert validated.holdings[0].current_allocation == Decimal(
        "0.600000000000"
    )
    assert validated.holdings[0].asset_metrics == analysis.asset_metrics[1]
    assert validated.holdings[0].risk_driver == analysis.risk_drivers.entries[1]
    assert validated.holdings[0].risk_driver.rank == 2


def _valid_thb_v2_snapshot() -> dict[str, object]:
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
            as_of=date(2026, 9, 12),
        ),
        holdings=thb_holdings,
    )
    enriched = compose_portfolio_analysis(
        replace(preparation, valuation=thb_valuation),
        _real_analysis_response(),
    )
    return enriched_analysis_to_v2_snapshot(enriched)


def test_thb_v2_snapshot_freezes_fx_usd_values_and_display_values() -> None:
    raw_snapshot = _valid_thb_v2_snapshot()

    snapshot = PortfolioReportV2Snapshot.model_validate(
        raw_snapshot
    )

    assert snapshot.valuation.valuation_currency == "THB"
    assert snapshot.valuation.fx is not None
    assert snapshot.valuation.fx.rate == Decimal("32.50")
    assert snapshot.holdings[0].current_value_usd == Decimal(
        "6000.000000000000"
    )
    assert snapshot.holdings[0].current_value == Decimal(
        "195000.00000000000000"
    )
    assert snapshot.holdings[0].current_allocation == Decimal(
        "0.600000000000"
    )


def test_v2_record_maps_snapshot_without_revaluation_or_mutation() -> None:
    snapshot = _valid_v2_snapshot()
    frozen_snapshot = deepcopy(snapshot)
    analysis = _analysis_record(
        result_snapshot=snapshot,
        schema_version=PORTFOLIO_ANALYSIS_RESPONSE_V2_SCHEMA_VERSION,
        start_date=date(2022, 1, 1),
        end_date=date(2022, 12, 31),
    )

    result = analysis_record_to_report_response(analysis)

    assert isinstance(result, PortfolioReportV2Response)
    assert result.schema_version == "portfolio-analysis-response-v2"
    assert result.valuation.total_current_value == Decimal(
        "10000.000000000000"
    )
    assert result.holdings[0].asset_price == Decimal("200.000000000000")
    assert result.holdings[0].current_allocation == Decimal("0.600000000000")
    assert result.analysis == _real_analysis_response()
    assert result.monetary_metrics is not None
    assert result.monetary_metrics.currency == "USD"
    assert result.monetary_metrics.basis == "saved-current-valuation"
    assert result.monetary_metrics.reference_amount == Decimal(
        "10000.000000000000"
    )
    assert [
        metric.symbol for metric in result.asset_monetary_metrics
    ] == ["BND", "AAPL"]
    assert [
        metric.reference_amount for metric in result.asset_monetary_metrics
    ] == [
        Decimal("4000.000000000000"),
        Decimal("6000.000000000000"),
    ]
    assert all(
        metric.basis == "saved-current-value"
        for metric in result.asset_monetary_metrics
    )
    assert all(
        metric.maximum_drawdown_amount is None
        for metric in result.asset_monetary_metrics
    )
    assert analysis.result_snapshot == frozen_snapshot


def test_malformed_v2_snapshot_is_rejected_strictly() -> None:
    snapshot = _valid_v2_snapshot()
    snapshot["unexpected"] = "not accepted"
    analysis = _analysis_record(
        result_snapshot=snapshot,
        schema_version=PORTFOLIO_ANALYSIS_RESPONSE_V2_SCHEMA_VERSION,
        start_date=date(2022, 1, 1),
        end_date=date(2022, 12, 31),
    )

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        analysis_record_to_report_response(analysis)


def test_analysis_response_serializes_to_json_safe_snapshot_and_round_trips(
) -> None:
    response = _valid_response()

    snapshot = analysis_response_to_snapshot(response)
    serialized = json.dumps(snapshot, allow_nan=False)
    round_tripped = PortfolioAnalysisResponse.model_validate(snapshot)

    assert isinstance(serialized, str)
    assert round_tripped == response
    assert snapshot == response.model_dump(mode="json")


def test_snapshot_freezes_asset_risk_and_historical_series() -> None:
    data = _valid_analysis_data()
    asset_metrics = data["asset_metrics"]
    portfolio_returns = data["portfolio_returns"]
    assert isinstance(asset_metrics, list)
    assert isinstance(portfolio_returns, list)

    for metric in asset_metrics:
        metric["risk_classification"] = {
            "risk_score": 50.0,
            "risk_level": "High",
            "volatility_points": 2,
            "drawdown_points": 1,
            "metrics_used": ["volatility", "maximum_drawdown"],
            "reasons": ["Elevated historical volatility"],
        }
    data["asset_returns"] = [
        {
            "symbol": metric["symbol"],
            "points": [
                {
                    "date": point["date"],
                    "asset_return": 0.01,
                }
                for point in portfolio_returns
            ],
        }
        for metric in asset_metrics
    ]
    response = PortfolioAnalysisResponse.model_validate(data)

    snapshot = analysis_response_to_snapshot(response)

    assert snapshot["asset_metrics"][0]["risk_classification"] == {
        "risk_score": 50.0,
        "risk_level": "High",
        "volatility_points": 2,
        "drawdown_points": 1,
        "metrics_used": ["volatility", "maximum_drawdown"],
        "reasons": ["Elevated historical volatility"],
    }
    assert [series["symbol"] for series in snapshot["asset_returns"]] == [
        metric["symbol"] for metric in asset_metrics
    ]
    assert snapshot["asset_returns"][0]["points"] == [
        {"date": point["date"], "asset_return": 0.01}
        for point in portfolio_returns
    ]


def test_snapshot_serialization_does_not_mutate_source_response() -> None:
    response = _valid_response()
    original = response.model_dump(mode="python")

    analysis_response_to_snapshot(response)

    assert response.model_dump(mode="python") == original


def test_mutating_snapshot_does_not_mutate_source_response() -> None:
    response = _valid_response()
    snapshot = analysis_response_to_snapshot(response)

    snapshot["portfolio_name"] = "Changed"
    snapshot["asset_metrics"][0]["symbol"] = "CHANGED"
    snapshot["risk_drivers"]["entries"][0]["rank"] = 99

    assert response.portfolio_name == "Synthetic Balanced Portfolio"
    assert response.asset_metrics[0].symbol == "AAPL"
    assert response.risk_drivers.entries[0].rank == 1


def test_snapshot_preserves_negative_drawdowns_signed_contributions_and_nulls(
) -> None:
    snapshot = analysis_response_to_snapshot(_valid_response())

    assert snapshot["max_drawdown"]["max_drawdown"] == -0.01
    assert [
        entry["component_volatility_contribution"]
        for entry in snapshot["risk_drivers"]["entries"]
    ] == [0.12, 0.07, -0.01]
    assert snapshot["asset_metrics"][2]["sharpe_ratio"] is None


def test_snapshot_preserves_all_defined_collection_ordering() -> None:
    snapshot = analysis_response_to_snapshot(_valid_response())

    assert [entry["symbol"] for entry in snapshot["risk_drivers"]["entries"]] == [
        "AAPL",
        "MSFT",
        "BND",
    ]
    assert [entry["symbol"] for entry in snapshot["asset_metrics"]] == [
        "AAPL",
        "MSFT",
        "BND",
    ]
    assert snapshot["correlation_matrix"]["symbols"] == [
        "AAPL",
        "MSFT",
        "BND",
    ]
    assert [
        (pair["asset_a"], pair["asset_b"])
        for pair in snapshot["correlation_pairs"]
    ] == [("AAPL", "MSFT"), ("AAPL", "BND"), ("MSFT", "BND")]
    assert [point["date"] for point in snapshot["portfolio_returns"]] == [
        "2026-01-03",
        "2026-01-05",
        "2026-01-06",
    ]


def test_analysis_record_maps_to_summary_using_only_relational_metadata() -> None:
    created_at = datetime(
        2026,
        8,
        18,
        17,
        30,
        tzinfo=timezone(timedelta(hours=7)),
    )
    analysis = _analysis_record(
        result_snapshot={"corrupted": True},
        start_date=date(2025, 2, 1),
        end_date=date(2025, 2, 28),
        created_at=created_at,
    )

    result = analysis_record_to_report_summary(analysis)

    assert isinstance(result, PortfolioReportSummary)
    assert result.id == analysis.id
    assert result.portfolio_id == analysis.portfolio_id
    assert result.start_date == date(2025, 2, 1)
    assert result.end_date == date(2025, 2, 28)
    assert result.created_at == created_at
    assert result.model_dump().keys() == {
        "id",
        "portfolio_id",
        "start_date",
        "end_date",
        "created_at",
    }


def test_supported_analysis_record_maps_to_validated_report_response() -> None:
    analysis = _analysis_record()

    result = analysis_record_to_report_response(analysis)

    assert isinstance(result, PortfolioReportResponse)
    assert result.id == analysis.id
    assert result.portfolio_id == analysis.portfolio_id
    assert result.created_at == analysis.created_at
    assert isinstance(result.analysis, PortfolioAnalysisResponse)
    assert result.analysis == _valid_response()


def test_unsupported_snapshot_version_is_rejected() -> None:
    analysis = _analysis_record(schema_version="portfolio-analysis-response-v4")

    with pytest.raises(
        ValueError,
        match="unsupported portfolio analysis snapshot schema version",
    ):
        analysis_record_to_report_response(analysis)


def test_invalid_snapshot_is_rejected_by_canonical_analysis_schema() -> None:
    snapshot = analysis_response_to_snapshot(_valid_response())
    snapshot["unexpected"] = True
    analysis = _analysis_record(result_snapshot=snapshot)

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        analysis_record_to_report_response(analysis)


def test_relational_snapshot_start_date_mismatch_is_rejected() -> None:
    analysis = _analysis_record(start_date=date(2025, 12, 31))

    with pytest.raises(
        ValueError,
        match="snapshot start_date does not match relational start_date",
    ):
        analysis_record_to_report_response(analysis)


def test_relational_snapshot_end_date_mismatch_is_rejected() -> None:
    analysis = _analysis_record(end_date=date(2026, 2, 1))

    with pytest.raises(
        ValueError,
        match="snapshot end_date does not match relational end_date",
    ):
        analysis_record_to_report_response(analysis)


def test_report_mapping_does_not_mutate_orm_snapshot() -> None:
    snapshot = analysis_response_to_snapshot(_valid_response())
    original = deepcopy(snapshot)
    analysis = _analysis_record(result_snapshot=snapshot)

    analysis_record_to_report_response(analysis)

    assert analysis.result_snapshot == original
    assert analysis.result_snapshot is snapshot


def test_report_mapping_preserves_timezone_aware_created_at() -> None:
    created_at = datetime(
        2026,
        8,
        18,
        17,
        30,
        tzinfo=timezone(timedelta(hours=7)),
    )
    analysis = _analysis_record(created_at=created_at)

    summary = analysis_record_to_report_summary(analysis)
    report = analysis_record_to_report_response(analysis)

    assert summary.created_at == created_at
    assert report.created_at == created_at
    assert summary.created_at.utcoffset() == timedelta(hours=7)
    assert report.created_at.utcoffset() == timedelta(hours=7)
