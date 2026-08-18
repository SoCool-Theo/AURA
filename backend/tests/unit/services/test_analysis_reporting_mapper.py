import json
from copy import deepcopy
from datetime import UTC, date, datetime, timedelta, timezone
from uuid import UUID

import pytest
from pydantic import ValidationError

from backend.app.database.models import Analysis
from backend.app.schemas.analytics import PortfolioAnalysisResponse
from backend.app.schemas.reporting import (
    PortfolioReportResponse,
    PortfolioReportSummary,
)
from backend.app.services.analysis_reporting_mapper import (
    PORTFOLIO_ANALYSIS_RESPONSE_SCHEMA_VERSION,
    analysis_record_to_report_response,
    analysis_record_to_report_summary,
    analysis_response_to_snapshot,
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


def test_analysis_response_serializes_to_json_safe_snapshot_and_round_trips(
) -> None:
    response = _valid_response()

    snapshot = analysis_response_to_snapshot(response)
    serialized = json.dumps(snapshot, allow_nan=False)
    round_tripped = PortfolioAnalysisResponse.model_validate(snapshot)

    assert isinstance(serialized, str)
    assert round_tripped == response
    assert snapshot == response.model_dump(mode="json")


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
    analysis = _analysis_record(schema_version="portfolio-analysis-response-v2")

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
