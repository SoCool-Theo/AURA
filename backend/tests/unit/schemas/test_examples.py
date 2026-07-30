import json
from pathlib import Path

import pytest

from backend.app.schemas.analytics import PortfolioAnalysisResponse
from backend.app.schemas.market_data import (
    HistoricalMarketDataRequest,
    HistoricalMarketDataResponse,
)
from backend.app.schemas.portfolio import PortfolioAnalysisRequest


_EXAMPLES_DIRECTORY = Path(__file__).resolve().parents[3] / "examples"


@pytest.mark.parametrize(
    ("filename", "model_type"),
    [
        ("portfolio_request.json", PortfolioAnalysisRequest),
        ("market_data_request.json", HistoricalMarketDataRequest),
        ("market_data_response.json", HistoricalMarketDataResponse),
        ("analysis_response.json", PortfolioAnalysisResponse),
    ],
)
def test_json_example_validates_and_matches_normalized_dump(
    filename: str,
    model_type: type,
) -> None:
    example_path = _EXAMPLES_DIRECTORY / filename
    example = json.loads(example_path.read_text(encoding="utf-8"))

    model = model_type.model_validate(example)
    normalized = model.model_dump(mode="json")
    json.dumps(normalized, allow_nan=False)

    assert normalized == example
