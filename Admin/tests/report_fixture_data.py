"""Existing canonical example snapshots for disposable admin report checks."""

from backend.tests.unit.schemas.test_reporting import _valid_analysis_data, _valid_v2_report_data, _valid_v3_report_data


def snapshots():
    result = [("portfolio-analysis-response-v1", _valid_analysis_data())]
    for version, factory in ((2, _valid_v2_report_data), (3, _valid_v3_report_data)):
        data = factory()
        for field in ("id", "portfolio_id", "created_at"):
            data.pop(field)
        result.append((f"portfolio-analysis-response-v{version}", data))
    return result
