import json
from copy import deepcopy
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pytest
from pydantic import ValidationError

from backend.app.schemas.analytics import PortfolioAnalysisResponse
from backend.app.schemas.reporting import (
    PortfolioReportListResponse,
    PortfolioReportResponse,
    PortfolioReportSummary,
    PortfolioReportV2Response,
    PortfolioReportV3Response,
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


def _valid_v2_report_data() -> dict[str, object]:
    analysis = _valid_analysis_data()
    metrics = analysis["asset_metrics"]
    risk_drivers = analysis["risk_drivers"]
    assert isinstance(metrics, list)
    assert isinstance(risk_drivers, dict)
    risk_entries = risk_drivers["entries"]
    assert isinstance(risk_entries, list)
    risks_by_symbol = {entry["symbol"]: entry for entry in risk_entries}
    holdings = []
    for position, metric in enumerate(metrics):
        symbol = metric["symbol"]
        holdings.append(
            {
                "id": f"30000000-0000-0000-0000-{position + 1:012d}",
                "symbol": symbol,
                "invested_amount": "1000.000000000000",
                "invested_currency": "USD",
                "shares": "5.000000000000",
                "purchase_date": "2025-01-01",
                "position": position,
                "asset_price": "200.000000000000",
                "asset_quote_currency": "USD",
                "price_as_of": "2026-09-11",
                "current_value_usd": "1000.000000000000",
                "current_value": "1000.000000000000",
                "current_allocation": str(metric["weight"]),
                "asset_metrics": deepcopy(metric),
                "risk_driver": deepcopy(risks_by_symbol[symbol]),
            }
        )
    return {
        "id": _REPORT_ID,
        "portfolio_id": _PORTFOLIO_ID,
        "created_at": "2026-09-12T10:00:00+00:00",
        "schema_version": "portfolio-analysis-response-v2",
        "analysis": analysis,
        "valuation": {
            "valuation_currency": "USD",
            "requested_date": "2026-09-12",
            "oldest_price_as_of": "2026-09-10",
            "newest_price_as_of": "2026-09-11",
            "total_current_value_usd": "3000.000000000000",
            "total_current_value": "3000.000000000000",
            "fx": None,
        },
        "holdings": holdings,
    }


def _valid_v3_report_data() -> dict[str, object]:
    analysis = _valid_analysis_data()
    symbols = ["AAPL", "MSFT", "BND"]
    amounts = ["5000", "3000", "2000"]
    allocations = ["0.5", "0.3", "0.2"]
    return {
        "id": _REPORT_ID,
        "portfolio_id": _PORTFOLIO_ID,
        "created_at": "2026-09-13T10:00:00+00:00",
        "schema_version": "portfolio-analysis-response-v3",
        "analysis": analysis,
        "baseline": {
            "portfolio_type": "PLANNED",
            "baseline_source": "proposed-amount-target-allocation",
            "plan_currency": "USD",
            "total_proposed_amount": "10000",
            "hypothetical_notice": (
                "Hypothetical historical analysis only; not a forecast, "
                "recommendation, or executable order."
            ),
            "holdings": [
                {
                    "id": f"40000000-0000-0000-0000-{index + 1:012d}",
                    "symbol": symbol,
                    "proposed_amount": amounts[index],
                    "target_allocation": allocations[index],
                    "position": index,
                }
                for index, symbol in enumerate(symbols)
            ],
        },
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


def test_v2_response_accepts_strict_immutable_real_holding_report() -> None:
    result = PortfolioReportV2Response.model_validate(_valid_v2_report_data())

    assert result.schema_version == "portfolio-analysis-response-v2"
    assert result.valuation.valuation_currency == "USD"
    assert result.valuation.fx is None
    assert [holding.symbol for holding in result.holdings] == [
        "AAPL",
        "MSFT",
        "BND",
    ]
    assert result.holdings[0].asset_metrics.symbol == "AAPL"
    assert result.holdings[0].risk_driver.rank == 1
    json.dumps(result.model_dump(mode="json"), allow_nan=False)


def test_v2_response_requires_fx_for_thb_and_rejects_unknown_fields() -> None:
    missing_fx = _valid_v2_report_data()
    valuation = missing_fx["valuation"]
    assert isinstance(valuation, dict)
    valuation["valuation_currency"] = "THB"
    with pytest.raises(ValidationError, match="THB valuation requires FX"):
        PortfolioReportV2Response.model_validate(missing_fx)

    extra = _valid_v2_report_data()
    extra["unexpected"] = True
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        PortfolioReportV2Response.model_validate(extra)


def test_v3_response_accepts_strict_immutable_planned_report() -> None:
    result = PortfolioReportV3Response.model_validate(_valid_v3_report_data())

    assert result.schema_version == "portfolio-analysis-response-v3"
    assert result.baseline.portfolio_type == "PLANNED"
    assert result.baseline.plan_currency == "USD"
    assert result.baseline.total_proposed_amount == 10000
    assert [holding.target_allocation for holding in result.baseline.holdings] == [
        Decimal("0.5"),
        Decimal("0.3"),
        Decimal("0.2"),
    ]
    serialized = result.model_dump(mode="json")
    assert "estimated_shares" not in serialized["baseline"]["holdings"][0]
    json.dumps(serialized, allow_nan=False)


@pytest.mark.parametrize(
    ("field", "value", "error"),
    [
        ("portfolio_type", "CURRENT", "PLANNED"),
        ("baseline_source", "saved-weights", "proposed-amount"),
        ("hypothetical_notice", "Buy this now", "Hypothetical historical"),
    ],
)
def test_v3_response_rejects_non_planned_baseline_discriminators(
    field: str,
    value: str,
    error: str,
) -> None:
    data = _valid_v3_report_data()
    baseline = data["baseline"]
    assert isinstance(baseline, dict)
    baseline[field] = value

    with pytest.raises(ValidationError, match=error):
        PortfolioReportV3Response.model_validate(data)


def test_v3_response_rejects_inconsistent_planned_totals() -> None:
    data = _valid_v3_report_data()
    baseline = data["baseline"]
    assert isinstance(baseline, dict)
    baseline["total_proposed_amount"] = "9999"

    with pytest.raises(ValidationError, match="proposed total is inconsistent"):
        PortfolioReportV3Response.model_validate(data)


def test_v3_response_rejects_analysis_weights_that_do_not_match_plan() -> None:
    data = _valid_v3_report_data()
    baseline = data["baseline"]
    assert isinstance(baseline, dict)
    holdings = baseline["holdings"]
    assert isinstance(holdings, list)
    first_holding = holdings[0]
    second_holding = holdings[1]
    assert isinstance(first_holding, dict)
    assert isinstance(second_holding, dict)
    first_holding["proposed_amount"] = "4000"
    first_holding["target_allocation"] = "0.4"
    second_holding["proposed_amount"] = "4000"
    second_holding["target_allocation"] = "0.4"

    with pytest.raises(
        ValidationError,
        match="baseline weight does not match analysis",
    ):
        PortfolioReportV3Response.model_validate(data)


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
