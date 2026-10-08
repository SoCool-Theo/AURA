"""Run a deterministic end-to-end check of the Aura analytics engine."""

import pandas as pd

from backend.app.analytics import analyze_portfolio


def main() -> int:
    """Run the manual analytics check and print a concise result summary."""
    prices = pd.DataFrame(
        {
            "ALPHA": [100.0, 102.0, 101.0, 105.0, 107.0, 106.0],
            "BETA": [50.0, 49.0, 51.0, 52.0, 51.0, 54.0],
            "GAMMA": [80.0, 81.0, 83.0, 82.0, 85.0, 87.0],
        },
        index=pd.date_range("2026-01-31", periods=6, freq="ME"),
    )
    weights = {"GAMMA": 0.20, "ALPHA": 0.50, "BETA": 0.30}

    result = analyze_portfolio(
        prices,
        weights,
        annual_risk_free_rate=0.02,
        periods_per_year=12,
        concentration_top_n=2,
    )
    diversification_score = (
        "Unavailable"
        if result.diversification.overall_score is None
        else f"{result.diversification.overall_score:.2f}"
    )

    print("Aura Analytics Engine Check")
    print(f"Analysis start: {result.analysis_start.date()}")
    print(f"Analysis end: {result.analysis_end.date()}")
    print(f"Number of assets: {result.asset_count}")
    print(f"Number of price observations: {result.price_observation_count}")
    print(f"Cumulative portfolio return: {result.cumulative_return:.2%}")
    print(f"Annualized portfolio return: {result.annualized_return:.2%}")
    print(f"Annualized volatility: {result.annualized_volatility:.2%}")
    print(f"Maximum drawdown: {result.max_drawdown.max_drawdown:.2%}")
    print(f"Sharpe ratio: {result.sharpe_ratio:.2f}")
    print(f"Diversification level: {result.diversification.level}")
    print(f"Diversification score: {diversification_score}")
    print(f"Overall risk level: {result.risk_classification.risk_level}")
    print(f"Overall risk score: {result.risk_classification.risk_score:.2f}")
    print(f"Top risk driver: {result.risk_drivers.top_driver}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
