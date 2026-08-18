import json
from copy import deepcopy
from datetime import timedelta
from pathlib import Path
from uuid import UUID

import pytest
from pydantic import ValidationError

from backend.app.schemas.analytics import PortfolioAnalysisResponse
from backend.app.schemas.reporting import (
    PortfolioReportListResponse,
    PortfolioReportResponse,
    PortfolioReportSummary,
)


_ANALYSIS_EXAMPLE_PATH = (
    Path(__file__).resolve().parents[3] / "examples" / "analysis_response.json"
)
_REPORT_ID = "10000000-0000-0000-0000-000000000001"
_PORTFOLIO_ID = "20000000-0000-0000-0000-000000000001"


def _valid_analysis_data() -> dict[str, object]:
    return json.loads(_ANALYSIS_EXAMPLE_PATH.read_text(encoding="utf-8"))


def _valid_report_data() -> dict[str, object]:
    return {
        "id": _REPORT_ID,
        "portfolio_id": _PORTFOLIO_ID,
        "created_at": "2026-08-18T17:30:00+07:00",
        "analysis": _valid_analysis_data(),
    }


def _valid_summary_data(
    *,
    report_id: str = _REPORT_ID,
    created_at: str = "2026-08-18T17:30:00+07:00",
) -> dict[str, object]:
    return {
        "id": report_id,
        "portfolio_id": _PORTFOLIO_ID,
        "start_date": "2026-01-01",
        "end_date": "2026-01-31",
        "created_at": created_at,
    }


def test_report_response_accepts_valid_persisted_report() -> None:
    result = PortfolioReportResponse.model_validate(_valid_report_data())

    assert result.id == UUID(_REPORT_ID)
    assert result.portfolio_id == UUID(_PORTFOLIO_ID)
    assert result.created_at.utcoffset() == timedelta(hours=7)
    assert isinstance(result.analysis, PortfolioAnalysisResponse)
    assert result.analysis.max_drawdown.max_drawdown == -0.01


def test_report_summary_accepts_valid_metadata() -> None:
    result = PortfolioReportSummary.model_validate(_valid_summary_data())

    assert result.id == UUID(_REPORT_ID)
    assert result.start_date.isoformat() == "2026-01-01"
    assert result.end_date.isoformat() == "2026-01-31"


def test_report_list_accepts_valid_summaries() -> None:
    result = PortfolioReportListResponse.model_validate(
        {"reports": [_valid_summary_data()]}
    )

    assert len(result.reports) == 1
    assert isinstance(result.reports[0], PortfolioReportSummary)


@pytest.mark.parametrize(
    "model_type,data",
    [
        (PortfolioReportResponse, _valid_report_data()),
        (PortfolioReportSummary, _valid_summary_data()),
    ],
)
@pytest.mark.parametrize("field_name", ["id", "portfolio_id"])
def test_report_models_reject_invalid_uuids(
    model_type: type,
    data: dict[str, object],
    field_name: str,
) -> None:
    data[field_name] = "not-a-uuid"

    with pytest.raises(ValidationError):
        model_type.model_validate(data)


@pytest.mark.parametrize(
    "model_type,data_factory",
    [
        (PortfolioReportResponse, _valid_report_data),
        (PortfolioReportSummary, _valid_summary_data),
    ],
)
@pytest.mark.parametrize(
    "created_at",
    [
        "2026-08-18T10:30:00+00:00",
        "2026-08-18T17:30:00+07:00",
    ],
)
def test_report_models_accept_timezone_aware_created_at(
    model_type: type,
    data_factory: type,
    created_at: str,
) -> None:
    data = data_factory()
    data["created_at"] = created_at

    result = model_type.model_validate(data)

    assert result.created_at.utcoffset() is not None


@pytest.mark.parametrize(
    "model_type,data_factory",
    [
        (PortfolioReportResponse, _valid_report_data),
        (PortfolioReportSummary, _valid_summary_data),
    ],
)
def test_report_models_reject_naive_created_at(
    model_type: type,
    data_factory: type,
) -> None:
    data = data_factory()
    data["created_at"] = "2026-08-18T10:30:00"

    with pytest.raises(ValidationError):
        model_type.model_validate(data)


@pytest.mark.parametrize(
    "model_type,data",
    [
        (PortfolioReportResponse, _valid_report_data()),
        (PortfolioReportSummary, _valid_summary_data()),
        (PortfolioReportListResponse, {"reports": []}),
    ],
)
def test_report_models_reject_unknown_fields(
    model_type: type,
    data: dict[str, object],
) -> None:
    data["unexpected"] = True

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        model_type.model_validate(data)


def test_report_response_validates_nested_analysis_payload() -> None:
    result = PortfolioReportResponse.model_validate(_valid_report_data())

    assert isinstance(result.analysis, PortfolioAnalysisResponse)
    assert result.analysis.portfolio_name == "Synthetic Balanced Portfolio"


def test_report_response_rejects_invalid_nested_analysis_payload() -> None:
    data = _valid_report_data()
    analysis = data["analysis"]
    assert isinstance(analysis, dict)
    max_drawdown = analysis["max_drawdown"]
    assert isinstance(max_drawdown, dict)
    max_drawdown["max_drawdown"] = 0.1

    with pytest.raises(ValidationError):
        PortfolioReportResponse.model_validate(data)


def test_report_response_json_mode_serialization_is_json_safe() -> None:
    result = PortfolioReportResponse.model_validate(_valid_report_data())

    serialized = result.model_dump(mode="json")
    json.dumps(serialized, allow_nan=False)

    assert serialized == _valid_report_data()


def test_report_list_allows_empty_history() -> None:
    result = PortfolioReportListResponse(reports=[])

    assert result.reports == []


def test_report_list_preserves_exact_input_order() -> None:
    first_id = "00000000-0000-0000-0000-000000000003"
    second_id = "00000000-0000-0000-0000-000000000001"
    third_id = "00000000-0000-0000-0000-000000000002"
    data = {
        "reports": [
            _valid_summary_data(report_id=first_id),
            _valid_summary_data(report_id=second_id),
            _valid_summary_data(report_id=third_id),
        ]
    }

    result = PortfolioReportListResponse.model_validate(data)

    assert [str(report.id) for report in result.reports] == [
        first_id,
        second_id,
        third_id,
    ]


def test_report_validation_does_not_mutate_caller_input() -> None:
    report_data = _valid_report_data()
    summary_data = _valid_summary_data()
    data = {"reports": [summary_data]}
    report_original = deepcopy(report_data)
    list_original = deepcopy(data)

    report = PortfolioReportResponse.model_validate(report_data)
    report_list = PortfolioReportListResponse.model_validate(data)

    assert report_data == report_original
    assert data == list_original
    assert data["reports"][0] is summary_data
    assert isinstance(report.analysis, PortfolioAnalysisResponse)
    assert len(report_list.reports) == 1


def test_report_summary_rejects_reversed_analysis_period() -> None:
    data = _valid_summary_data()
    data["start_date"] = "2026-12-31"
    data["end_date"] = "2026-01-01"

    with pytest.raises(
        ValidationError,
        match="start_date must be on or before end_date",
    ):
        PortfolioReportSummary.model_validate(data)
