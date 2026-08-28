import pandas as pd
import pytest

from backend.app.data_pipeline.providers import market_provider
from backend.app.data_pipeline.providers.market_provider import (
    MarketDataProviderError,
    YFinanceMarketProvider,
)


class FakeYFinance:
    def __init__(self):
        self.calls = []

    def download(self, symbol, **kwargs):
        self.calls.append((symbol, kwargs))
        if symbol == "BAD":
            return pd.DataFrame()
        return pd.DataFrame(
            {
                "Adj Close": [100.0, 101.0],
                "Close": [99.0, 100.0],
                "Volume": [1000, 1100],
            },
            index=pd.DatetimeIndex(["2026-01-02", "2026-01-03"], name="Date"),
        )


def test_yfinance_provider_uses_inclusive_aura_end_date(monkeypatch) -> None:
    fake = FakeYFinance()
    monkeypatch.setattr(market_provider, "_load_yfinance", lambda: fake)

    result = YFinanceMarketProvider().fetch_historical_prices(
        [" aapl "], "2026-01-01", "2026-01-03"
    )

    assert result["symbol"].unique().tolist() == ["AAPL"]
    assert result["source"].unique().tolist() == ["yfinance"]
    _, kwargs = fake.calls[0]
    assert kwargs["start"] == "2026-01-01"
    assert kwargs["end"] == "2026-01-04"


def test_yfinance_provider_reports_partial_symbol_failures(monkeypatch) -> None:
    fake = FakeYFinance()
    monkeypatch.setattr(market_provider, "_load_yfinance", lambda: fake)

    result = YFinanceMarketProvider().fetch_historical_prices(
        ["AAPL", "BAD"], "2026-01-01", "2026-01-03"
    )

    assert result.attrs["failed_symbols"] == ("BAD",)


def test_yfinance_provider_raises_when_every_symbol_fails(monkeypatch) -> None:
    fake = FakeYFinance()
    monkeypatch.setattr(market_provider, "_load_yfinance", lambda: fake)

    with pytest.raises(MarketDataProviderError, match="No historical market data"):
        YFinanceMarketProvider().fetch_historical_prices(
            ["BAD"], "2026-01-01", "2026-01-03"
        )
