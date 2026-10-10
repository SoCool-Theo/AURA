# Aura Mobile — Web Parity Build

This build maps the Aura customer React web application into React Native while keeping the mobile architecture and phone interaction model.

## Web → Mobile screen mapping

| Web area | Mobile implementation |
|---|---|
| Dashboard | Home tab — 4 KPI cards, performance, risk drivers, allocation, AI insight preview, analysis card |
| Portfolios | Portfolio tab — searchable list, create CTA, open/set active |
| Portfolio Detail | Overview / Holdings / Performance / Activity tabs |
| Create Portfolio | Portfolio name + editable holding rows + invested amount + automatic allocation |
| Analytics | Risk score, volatility, Sharpe, drawdown, drivers, diversification, asset relationships, individual assets |
| Simulations | Historical Scenario, Allocation Change, Combined Simulation + history |
| AI Assistant | Portfolio context, suggested prompts, chat composer; no fake backend answers |
| Reports | Search/filter report history + report detail |
| Watchlist | Search/add/remove local watch items |
| Learn | Search/filter lessons + progress |
| Settings | Profile, dark/light mode, privacy, notifications, reset, help/about, sign out |
| Login/Register | Protected mobile authentication flow with local demo mode / API-ready layer |

## Dashboard parity boundary

The Home screen follows the web dashboard structure:

1. Dashboard header and portfolio selector
2. Four KPI cards
   - Total Portfolio Value
   - Risk Score
   - Annualized Return
   - Maximum Drawdown
3. Portfolio Performance
4. Top Risk Drivers
5. Portfolio Allocation
6. AI Insight preview
7. Portfolio Analysis entry point

Detailed volatility, Sharpe ratio, asset relationships, diversification, and asset-level analysis remain on Analytics.

## Mobile navigation

The same product functions are preserved, but navigation is optimized for a phone:

```text
Home | Portfolio | Simulate | AI | More
```

`More` exposes Analytics, Reports, Watchlist, Learn, and Settings. Home remains directly accessible from the bottom navigation.

## Backend boundary

The project keeps the existing API modules and shared FastAPI boundary. Local/demo calculations and persistence exist only so the frontend can be exercised without running the backend.

Production financial results must come from FastAPI for:

- risk score
- volatility
- Sharpe ratio
- maximum drawdown
- correlations / asset relationships
- diversification
- risk drivers
- all three simulation modes
- saved reports/history
- AI explanations

The AI screen intentionally does not fabricate responses before the backend AI Agent is available.
