# Aura System Architecture

This document defines Aura's backend, customer web, mobile, and shared
client-backend architecture. Proposed structures are targets unless current
repository evidence or `CURRENT_STATUS.md` identifies them as implemented.

## Quick Navigation

- [Backend Architecture](#backend-architecture)
- [Frontend Web Architecture](#frontend-web-architecture)
- [Mobile App Architecture](#mobile-app-architecture)
- [Shared Client-Backend Architecture](#shared-client-backend-architecture)
- [Project Folder Definitions](#project-folder-definitions)
- [Architecture Decisions](#architecture-decisions)

## Project Structure

```text
AURA/
│
├── .venv/                         ← Virtual Environment
├── AGENTS.md                      ← Tells Codex how to work on Aura
├── PROJECT_CONTEXT.md             ← What Aura is and why it is being built
├── CURRENT_STATUS.md              ← Tells Codex what has actually been completed
├── backend/                       ← FastAPI backend, analytics, database, simulations, AI
├── web-prototype-react/            ← Customer React web application
├── mobile/                        ← Customer mobile application
├── data/                          ← Shared market data
├── docs/                          ← Project documentation
├── .gitignore
└── README.md
```

# Architecture Decisions

- Customer website uses React and TypeScript and lives under `web-prototype-react/`.
- The customer mobile application uses React Native and TypeScript and lives under `mobile/`.
- The website and mobile application share one backend contract.
- FastAPI remains the shared backend for the React web and React Native clients; there is no separate mobile backend.
- PostgreSQL remains the backend persistence layer.
- Clean historical data is used directly for calculations.
- Automatic market-data updates.
- Backend analytics and simulation calculations are the source of truth; web and mobile clients do not duplicate financial formulas.
- Both customer clients use dedicated API layers rather than scattered network calls in pages or screens.
- Bearer authentication is shared through the backend and handled through dedicated client authentication layers, with the backend remaining authoritative.
- Web and mobile may use different backend URLs during local development while preserving the same API contracts.
- Analytics engine first.
- Historical simulator after core analytics.
- The AI agent explains backend-owned deterministic results and remains
  educational and non-advisory.
- The dashboard remains concise while detailed analytics live on dedicated pages.
- Web and mobile mock data is development/test data and remains separate from production API data.
- Shared components, charts, styles, and types are separated from feature-specific pages.
- The backend AI Agent and the current customer web/mobile AI integrations are
  implemented; saved resources are grounded from frozen snapshots.
- No ML training folder yet.

---

# Backend Architecture

## Detailed Backend Folder Structure

```text
AURA/
│
├── .venv/
├── AGENTS.md
├── PROJECT_CONTEXT.md
├── CURRENT_STATUS.md
│
├── backend/
│   │
│   ├── app/
│   │   │
│   │   ├── __init__.py
│   │   ├── main.py
│   │   │
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   ├── constants.py
│   │   │   └── logging.py
│   │   │
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── router.py
│   │   │   │
│   │   │   └── routes/
│   │   │       ├── __init__.py
│   │   │       ├── health.py
│   │   │       ├── portfolio.py
│   │   │       ├── simulation.py
│   │   │       └── agent.py
│   │   │
│   │   ├── analytics/
│   │   │   ├── __init__.py
│   │   │   ├── returns.py
│   │   │   ├── volatility.py
│   │   │   ├── drawdown.py
│   │   │   ├── sharpe.py
│   │   │   ├── correlation.py
│   │   │   ├── concentration.py
│   │   │   ├── diversification.py
│   │   │   ├── risk_driver.py
│   │   │   ├── risk_classifier.py
│   │   │   └── engine.py
│   │   │
│   │   ├── scenarios/
│   │   │   ├── __init__.py
│   │   │   ├── definitions.py
│   │   │   └── simulator.py
│   │   │
│   │   ├── data_pipeline/
│   │   │   ├── __init__.py
│   │   │   ├── providers/
│   │   │   │   ├── __init__.py
│   │   │   │   └── market_provider.py
│   │   │   ├── fetcher.py
│   │   │   ├── cleaner.py
│   │   │   ├── validator.py
│   │   │   └── updater.py
│   │   │
│   │   ├── database/
│   │   │   ├── __init__.py
│   │   │   ├── connection.py
│   │   │   │
│   │   │   ├── models/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── user.py
│   │   │   │   ├── portfolio.py
│   │   │   │   ├── holding.py
│   │   │   │   ├── market_data.py
│   │   │   │   ├── analysis.py
│   │   │   │   └── conversation.py          ← Later
│   │   │   │
│   │   │   └── repositories/
│   │   │       ├── __init__.py
│   │   │       ├── market_data_repository.py
│   │   │       ├── portfolio_repository.py
│   │   │       └── analysis_repository.py
│   │   │
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── portfolio.py
│   │   │   ├── analytics.py
│   │   │   ├── market_data.py
│   │   │   ├── simulation.py
│   │   │   └── agent.py
│   │   │
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── market_data_service.py
│   │   │   ├── portfolio_service.py
│   │   │   └── analysis_service.py
│   │   │
│   │   ├── agents/
│   │   │   ├── __init__.py
│   │   │   ├── agent.py
│   │   │   ├── tools.py
│   │   │   └── prompts.py
│   │   │
│   │   └── utils/
│   │       ├── __init__.py
│   │       └── date_utils.py
│   │
│   ├── tests/
│   │   │
│   │   ├── __init__.py
│   │   │
│   │   ├── unit/
│   │   │   │
│   │   │   ├── analytics/
│   │   │   │   ├── test_returns.py
│   │   │   │   ├── test_volatility.py
│   │   │   │   ├── test_drawdown.py
│   │   │   │   ├── test_sharpe.py
│   │   │   │   ├── test_correlation.py
│   │   │   │   └── test_engine.py
│   │   │   │
│   │   │   └── data_pipeline/
│   │   │       ├── test_cleaner.py
│   │   │       └── test_validator.py
│   │   │
│   │   └── integration/
│   │       ├── __init__.py
│   │       │
│   │       ├── api/
│   │       │   ├── __init__.py
│   │       │   ├── test_health_api.py
│   │       │   ├── test_portfolio_api.py
│   │       │   └── test_simulation_api.py
│   │       │
│   │       └── database/
│   │           └── test_database.py
│   │
│   ├── scripts/
│   │   ├── seed_historical_data.py
│   │   ├── update_market_data.py
│   │   └── run_engine_check.py
│   │
│   ├── examples/
│   │   ├── portfolio_request.json
│   │   ├── analysis_response.json
│   │   └── simulation_response.json
│   │
│   ├── .env.example
│   ├── requirements.txt
│   └── README.md
│
├── web-prototype-react/            ← Customer React web application
│
├── mobile/
│
├── data/
│   ├── raw/
│   ├── processed/
│   └── README.md
│
├── docs/
│   ├── api_contracts/
│   ├── architecture/
│   └── data_dictionary/
│
├── .gitignore
└── README.md
```

---

## Backend Folder Definitions

| Folder | Simple Meaning |
|---|---|
| `api/` | Receives frontend requests |
| `analytics/` | Calculates portfolio risk |
| `scenarios/` | Runs historical What-If simulations |
| `data_pipeline/` | Automatically updates market data |
| `database/` | Reads and saves stored data |
| `schemas/` | Defines data input/output format |
| `services/` | Coordinates the whole process |
| `agents/` | Grounded educational AI explanation layer |
| `core/` | Global settings and constants |
| `utils/` | Small reusable helper functions |

## Current Holding and Valuation Architecture

The currently implemented compatibility architecture below is being extended
by the approved [planned-portfolio target contract](../api_contracts/planned_portfolios.md).
Type-aware CRUD exposes user-facing `CURRENT` and `PLANNED` portfolio types
while retaining `LEGACY` as internal compatibility state. The shared baseline
resolver, analysis composition, reporting, simulations, and AI grounding now
support all three modes.

Aura supports three complete, mutually exclusive persisted holding modes:

| Mode | Persisted holding state | Current valuation |
| --- | --- | --- |
| `LEGACY` | `weight` is present; real-holding fields and `proposed_amount` are `NULL` | Not available |
| `CURRENT` | `weight` and `proposed_amount` are `NULL`; `shares` is present; investment provenance is either complete or absent | Available from persisted current market data |
| `PLANNED` | `proposed_amount` is present; `weight` and real-holding fields are `NULL` | Target allocation is derived without current prices; current valuation is not ownership-authoritative |

For a current holding, the normal customer write contract is `symbol` plus
positive `shares` (the quantity owned). The backend controls the zero-based
`position` used to preserve order. Existing/full current records may also carry
`invested_amount`, `invested_currency`, and `purchase_date` as one complete
optional provenance group; Aura never fabricates those facts for new
quantity-only rows. Aura does not persist manual weight, current allocation,
current price, current value, or FX rate for current holdings.

For a planned holding, the user controls `symbol` and positive
`proposed_amount` in the portfolio's single `plan_currency`. The backend derives
the total and exact canonical target allocation without market or FX data.
`GET /api/portfolios/{portfolio_id}/planned-preview` may also derive estimated
shares from a best-effort current USD asset price and, for THB plans, USD/THB
FX. Each estimate carries explicit availability and provenance; estimates are
never persisted and never influence canonical weights or analytics.

`PortfolioBaselineResolutionService` is the sole analysis baseline resolver:

```text
CURRENT -> current valuation -> dynamic weights
PLANNED -> proposed amounts -> target weights
LEGACY  -> saved weights
                            |
                            v
                   canonical weights
                            |
                            v
                 analysis composition
```

Planned analysis therefore does not require current-price or FX availability.
It still requires sufficient aligned historical price data under the same
no-fabrication rules as other portfolio modes.

Current valuation is calculated once in `PortfolioValuationService`:

```text
current_value_usd = shares × latest valid USD market price
total_current_value_usd = sum(current_value_usd)
current_allocation = current_value_usd / total_current_value_usd
```

The maximum accepted age for each required current observation is four
calendar days. USD is canonical. THB is an optional display currency using the
internal `THB=X` series as USD/THB (THB per USD). Missing or stale `THB=X`
disables THB display but does not affect USD valuation.

The instrument registry deliberately separates 17 user-selectable assets from
the internal `THB=X` market instrument. Default/scheduled updates cover both
groups, while explicit user asset selection remains limited to the 17 assets.

## Analysis, Reporting, Simulation, and AI Composition

For a real portfolio, Aura applies the current dynamic allocation to the
user-selected historical price period and then reuses the existing fixed-weight,
periodically rebalanced analytics engine. This is not a historical share-count
backtest: `purchase_date` does not establish historical ownership and no
analytics formula changed.

Individual-asset return, volatility, maximum drawdown, and Sharpe describe the
asset over the analysis period. Portfolio risk contribution additionally
depends on portfolio allocation and covariance/correlation. Investing more does
not make the asset itself more volatile, although a larger current allocation
can increase its contribution to portfolio risk.

Report persistence supports `portfolio-analysis-response-v1` for legacy
portfolios, `portfolio-analysis-response-v2` for current portfolios, and
`portfolio-analysis-response-v3` for planned portfolios. V2 freezes the
valuation currency/date, price dates, USD/display totals, optional FX, holding
facts, prices, values, dynamic allocations, complete analytics, per-asset
metrics, and risk contribution/rank. V3 freezes the plan currency, ordered
proposed amounts, exact backend target weights, complete analytics, and the
hypothetical/non-forecast limitation. It does not store estimated shares.

Simulation history supports the existing V1 formats and these V2 formats:

- `historical-scenario-simulation-response-v2`
- `allocation-simulation-response-v2`
- `combined-simulation-response-v2`

Planned simulation history uses separate V3 formats:

- `historical-scenario-simulation-response-v3`
- `allocation-simulation-response-v3`
- `combined-simulation-response-v3`

The real simulation's original allocation is the current canonical USD
allocation. Allocation and Combined retain the user's hypothetical percentages
as the modified allocation. For planned simulations, the original allocation
is the target allocation resolved from proposed amounts; modified percentages
remain separate hypothetical input. V2 and V3 history freeze their baseline at
creation. Opening a saved report or simulation restores the JSONB snapshot and
never revalues or reruns it.

AI grounding follows the same source boundary: live legacy portfolios use
saved weights, live current portfolios use current USD valuation, and live
planned portfolios use proposed amounts and their exact target weights. Report
V2/V3 and Simulation V2/V3 use their frozen snapshots. Saved resources do not
require current market prices. Context carries `portfolio_type`,
`baseline_source`, and snapshot version so the model uses current, planned, or
saved-allocation language correctly. Planned context excludes estimated shares
and adds an explicit hypothetical/non-forecast limitation. AI remains
educational, non-advisory, cannot claim proposed assets are currently owned,
and cannot produce buy/sell recommendations.

## Transaction Ownership

- Repositories and services do not commit.
- The successful API/request boundary commits writes.
- Current valuation is read-only and persists nothing.
- Reports and simulations save immutable snapshots at the successful outer
  transaction boundary.
- A failed valuation, analysis, or simulation does not commit a partial
  snapshot.

[↑ Back to Quick Navigation](#quick-navigation)

---

# Frontend Web Architecture

The customer website uses React and TypeScript under `web-prototype-react/`. The structure below is the **target frontend architecture** agreed for the application. It describes intended responsibilities and planned separation; it does not claim that every listed file, integration, or feature is already implemented.

```text
web-prototype-react/
├─ public/
│  └─ favicon.svg
│
├─ src/
│  ├─ app/
│  │  ├─ App.tsx
│  │  ├─ AppLayout.tsx
│  │  ├─ navigation.ts
│  │  └─ routes.ts
│  │
│  ├─ api/
│  │  ├─ apiClient.ts
│  │  ├─ authApi.ts
│  │  ├─ portfoliosApi.ts
│  │  ├─ analyticsApi.ts
│  │  ├─ reportsApi.ts
│  │  └─ simulationsApi.ts
│  │
│  ├─ auth/
│  │  ├─ AuthContext.tsx
│  │  ├─ useAuth.ts
│  │  ├─ authStorage.ts
│  │  └─ ProtectedRoute.tsx
│  │
│  ├─ config/
│  │  └─ environment.ts
│  │
│  ├─ assets/
│  │  ├─ images/
│  │  │  └─ aura-market-background.png
│  │  └─ icons/
│  │
│  ├─ components/
│  │  ├─ navigation/
│  │  │  ├─ TopNavigation.tsx
│  │  │  ├─ ProfileMenu.tsx
│  │  │  └─ TopNavigation.module.css
│  │  │
│  │  ├─ ui/
│  │  │  ├─ Button.tsx
│  │  │  ├─ Card.tsx
│  │  │  ├─ Icon.tsx
│  │  │  ├─ Input.tsx
│  │  │  ├─ Select.tsx
│  │  │  ├─ Modal.tsx
│  │  │  ├─ Spinner.tsx
│  │  │  ├─ EmptyState.tsx
│  │  │  ├─ ErrorState.tsx
│  │  │  ├─ PageHeader.tsx
│  │  │  ├─ RiskPill.tsx
│  │  │  ├─ SymbolBadge.tsx
│  │  │  └─ ui.module.css
│  │  │
│  │  ├─ charts/
│  │  │  ├─ DonutChart.tsx
│  │  │  ├─ GaugeChart.tsx
│  │  │  ├─ LineChart.tsx
│  │  │  ├─ MiniLineChart.tsx
│  │  │  └─ charts.module.css
│  │  │
│  │  └─ portfolio/
│  │     ├─ PortfolioMetric.tsx
│  │     ├─ PortfolioCard.tsx
│  │     ├─ HoldingsTable.tsx
│  │     └─ AllocationLegend.tsx
│  │
│  ├─ pages/
│  │  ├─ auth/
│  │  │  ├─ LoginPage.tsx
│  │  │  ├─ RegisterPage.tsx
│  │  │  └─ AuthPage.module.css
│  │  │
│  │  ├─ dashboard/
│  │  │  ├─ DashboardPage.tsx
│  │  │  ├─ DashboardPage.module.css
│  │  │  └─ components/
│  │  │     ├─ DashboardHeader.tsx
│  │  │     ├─ DashboardKpiGrid.tsx
│  │  │     ├─ PortfolioPerformance.tsx
│  │  │     ├─ RiskDrivers.tsx
│  │  │     ├─ PortfolioAllocation.tsx
│  │  │     ├─ AiInsight.tsx
│  │  │     ├─ PortfolioAnalysisCard.tsx
│  │  │     ├─ PortfolioSelector.tsx
│  │  │     └─ DateRangeSelector.tsx
│  │  │
│  │  ├─ portfolios/
│  │  │  ├─ PortfoliosPage.tsx
│  │  │  ├─ PortfolioDetailPage.tsx
│  │  │  ├─ CreatePortfolioPage.tsx
│  │  │  ├─ portfolios.module.css
│  │  │  └─ components/
│  │  │     ├─ PortfolioListCard.tsx
│  │  │     ├─ PortfolioOverviewTab.tsx
│  │  │     ├─ HoldingsTab.tsx
│  │  │     ├─ PerformanceTab.tsx
│  │  │     └─ ActivityTab.tsx
│  │  │
│  │  ├─ analytics/
│  │  │  ├─ AnalyticsPage.tsx
│  │  │  ├─ AnalyticsPage.module.css
│  │  │  └─ components/
│  │  │     ├─ AnalysisSummary.tsx
│  │  │     ├─ RiskDriverTable.tsx
│  │  │     ├─ CorrelationHeatmap.tsx
│  │  │     └─ AssetAnalysisCard.tsx
│  │  │
│  │  ├─ simulations/
│  │  │  ├─ SimulationsPage.tsx
│  │  │  ├─ SimulationsPage.module.css
│  │  │  └─ components/
│  │  │     ├─ SimulationModeSelector.tsx
│  │  │     ├─ HistoricalScenarioSelector.tsx
│  │  │     ├─ SimulationSetup.tsx
│  │  │     ├─ AllocationEditor.tsx
│  │  │     ├─ SimulationResults.tsx
│  │  │     ├─ SimulationComparison.tsx
│  │  │     └─ SimulationHistory.tsx
│  │  │
│  │  ├─ assistant/
│  │  │  ├─ AssistantPage.tsx
│  │  │  ├─ AssistantPage.module.css
│  │  │  └─ components/
│  │  │     ├─ ConversationList.tsx
│  │  │     ├─ ChatWorkspace.tsx
│  │  │     └─ PortfolioContext.tsx
│  │  │
│  │  ├─ reports/
│  │  │  ├─ ReportsPage.tsx
│  │  │  ├─ ReportDetailPage.tsx
│  │  │  ├─ ReportsPage.module.css
│  │  │  └─ components/
│  │  │     ├─ ReportSummary.tsx
│  │  │     ├─ ReportFilters.tsx
│  │  │     └─ ReportTable.tsx
│  │  │
│  │  ├─ watchlist/
│  │  ├─ learn/
│  │  └─ settings/
│  │
│  ├─ hooks/
│  │  ├─ useHashRoute.ts
│  │  └─ usePersistedState.ts
│  │
│  ├─ mocks/
│  │  ├─ dashboard.mock.ts
│  │  ├─ portfolios.mock.ts
│  │  ├─ analytics.mock.ts
│  │  └─ simulations.mock.ts
│  │
│  ├─ types/
│  │  ├─ api.ts
│  │  ├─ auth.ts
│  │  ├─ portfolio.ts
│  │  ├─ analytics.ts
│  │  ├─ report.ts
│  │  ├─ simulation.ts
│  │  └─ settings.ts
│  │
│  ├─ utils/
│  │  ├─ formatting.ts
│  │  └─ uiCalculations.ts
│  │
│  ├─ styles/
│  │  ├─ tokens.css
│  │  ├─ globals.css
│  │  ├─ accessibility.css
│  │  └─ responsive.css
│  │
│  └─ main.tsx
│
├─ index.html
├─ package.json
├─ tsconfig.json
└─ vite.config.ts
```

## Frontend Web Folder Definitions

| Folder | Simple Meaning |
|---|---|
| `app/` | Controls the overall React application structure, routing, navigation configuration, and shared page layout. |
| `api/` | Handles communication between the React frontend and the FastAPI backend. |
| `auth/` | Manages frontend authentication state, Bearer token handling, current-user access, and protected routes. |
| `config/` | Stores frontend environment and application configuration such as the backend API base URL. |
| `assets/` | Stores visual resources such as images, the Aura market background, and custom icons. |
| `components/` | Contains reusable UI, navigation, chart, and portfolio components shared across multiple pages. |
| `pages/` | Contains Aura's main user-facing screens organized by product feature. |
| `hooks/` | Contains reusable React state and behavior logic that does not directly render UI. |
| `mocks/` | Contains temporary/demo frontend data used during UI development and testing; it is not production backend data. |
| `types/` | Defines TypeScript interfaces and types for frontend data and backend API contracts. |
| `utils/` | Contains small frontend helper functions such as formatting and UI-only calculations. |
| `styles/` | Defines Aura's shared design tokens, global styling, accessibility rules, and responsive behavior. |

| Shared Component Folder | Simple Meaning |
|---|---|
| `components/navigation/` | Shared top navigation and profile-menu components. |
| `components/ui/` | Generic reusable UI components such as buttons, cards, inputs, selectors, loading states, and risk badges. |
| `components/charts/` | Reusable chart-rendering components such as line, donut, gauge, and mini charts. |
| `components/portfolio/` | Reusable components that specifically represent portfolios, holdings, metrics, and allocation information. |

## Frontend-to-Backend Responsibility Boundary

```text
React Page
    ↓
Reusable Component
    ↓
Frontend API Module
    ↓
FastAPI REST API
    ↓
Backend Service
    ↓
Repository / Analytics / Simulation
    ↓
PostgreSQL
```

React is responsible for presentation, interaction, navigation, form handling, loading and error states, and displaying results returned by the backend. FastAPI remains responsible for portfolio ownership rules, analytics calculations, simulation calculations, reporting behavior, authentication verification, and database operations.

Backend calculations are the source of truth. The frontend must not independently calculate or duplicate Aura's official:

- risk score;
- volatility;
- Sharpe ratio;
- maximum drawdown;
- diversification score;
- correlation;
- risk drivers; or
- historical simulation results.

Frontend utilities may perform display-only work such as currency formatting, percentage formatting, chart display transformations, and basic visual or UI derivations. Portfolio-specific financial formulas remain in the backend.

## Frontend API Layer

`src/api/` is the single frontend integration boundary for the FastAPI backend. It owns API base URL handling, HTTP requests, JSON request and response handling, Bearer authentication headers, and standardized frontend API errors.

Feature API modules remain separated by responsibility:

```text
authApi.ts
portfoliosApi.ts
analyticsApi.ts
reportsApi.ts
simulationsApi.ts
```

React pages should use these modules rather than scattering hard-coded `fetch()` calls throughout page components.

## Frontend Authentication Architecture

The intended frontend authentication flow is:

```text
Login / Register Page
        ↓
authApi
        ↓
FastAPI Authentication API
        ↓
Bearer JWT received
        ↓
Frontend Auth State
        ↓
Protected Routes
        ↓
Authenticated API Requests
```

- `AuthContext.tsx` manages frontend authentication state.
- `useAuth.ts` exposes authentication behavior to React components.
- `authStorage.ts` owns the agreed frontend token or session persistence behavior.
- `ProtectedRoute.tsx` prevents unauthenticated access to protected frontend pages.
- Backend authentication remains authoritative.
- The frontend must not use `X-User-ID` as authentication.

This is a target architecture. It does not imply that refresh tokens, OAuth, MFA, password reset, logout revocation, or every authentication screen is already implemented.

## Page Responsibilities

| Page | Main Responsibility |
|---|---|
| Dashboard | Shows a concise portfolio overview, performance, risk summary, top risk drivers, allocation, AI insight preview, and current analysis state. |
| Portfolios | Creates, lists, opens, renames, edits, duplicates, and deletes user portfolios and holdings. |
| Analytics | Shows detailed portfolio risk analysis including volatility, drawdown, Sharpe ratio, correlation, diversification, risk drivers, and individual asset analysis. |
| Simulations | Runs Historical Scenario, Allocation Change, and Combined Simulation workflows and displays simulation history. |
| AI Assistant | Provides grounded educational explanations through the backend AI Agent. |
| Reports | Lists and displays saved immutable portfolio-analysis reports. |
| Settings | Handles frontend profile and application settings. |
| Watchlist | Optional or later market watchlist functionality. |
| Learn | Optional or later educational content functionality. |

Watchlist and Learn may exist as routes or frontend features without appearing in the current primary top navigation.

## Dashboard Design Boundary

The Dashboard remains intentionally concise:

```text
Top Navigation
        ↓
Dashboard Header
        ↓
4 KPI Cards
        ↓
Portfolio Performance + Top Risk Drivers
        ↓
Portfolio Allocation + AI Insight + Portfolio Analysis
```

The four Dashboard KPI cards are:

1. Total Portfolio Value
2. Risk Score
3. Annualized Return
4. Maximum Drawdown

Detailed volatility, Sharpe ratio, correlation, diversification, complete risk-driver tables, and individual asset analysis belong on Analytics rather than the main Dashboard. Simulation history belongs to Simulations, report history belongs to Reports, and portfolio management belongs to Portfolios.

## Reusable UI and Chart Architecture

Generic UI components remain independent from feature-specific business logic:

```text
Button
Card
Input
Select
Modal
Spinner
EmptyState
ErrorState
RiskPill
SymbolBadge
```

Generic chart components are:

```text
LineChart
MiniLineChart
DonutChart
GaugeChart
```

Feature components compose these shared primitives:

```text
PortfolioPerformance
        ↓
LineChart

PortfolioAllocation
        ↓
DonutChart

Risk Score KPI
        ↓
GaugeChart
```

Generic charts render data but do not contain portfolio-specific business calculations.

## Frontend Styling Architecture

```text
styles/
├─ tokens.css
├─ globals.css
├─ accessibility.css
└─ responsive.css
```

- `tokens.css` — Aura design tokens such as colors, spacing, typography, borders, and shared visual constants.
- `globals.css` — global page, body, and default application styling.
- `accessibility.css` — focus states, reduced motion, visibility, and accessibility-related rules.
- `responsive.css` — shared breakpoint and responsive-layout behavior.

Feature and page-specific styling remains in CSS modules near the related component or page. Reusable design values should use tokens rather than being hard-coded across unrelated components.

The agreed customer-web design direction is a professional dark fintech theme with a dark navy and blue background, teal and cyan primary accents, restrained amber and red risk-state colors, and subtle financial-market background imagery. Information hierarchy remains stronger than decoration. Large decorative cryptocurrency artwork and childish visual themes are not part of this direction.

## Frontend Assets

`src/assets/images/aura-market-background.png` is the approved subtle financial-market background visual for the React web interface. It remains secondary to content and must not interfere with text readability or dashboard cards.

## Frontend Mock-Data Boundary

`mocks/` contains frontend development and test data only. It is not the production source of portfolio, analysis, report, simulation, or authentication data.

During real backend integration:

```text
Mock data
   ↓ replaced by
src/api/*
   ↓
FastAPI
```

Mocks may remain for deterministic frontend testing or isolated UI development. Production data and official calculations come from FastAPI and its backend services.

## Frontend Implementation Status Boundary

This section documents the architecture and responsibility boundaries. The
current customer web app has backend authentication, portfolio, report,
simulation, and AI integration, but it still requires the real-holding and V2
contract work listed in `docs/frontend_mobile_integration_backlog.md`.

[↑ Back to Quick Navigation](#quick-navigation)

---

# Mobile App Architecture

Aura's customer mobile application uses React Native and TypeScript under
`mobile/`. It connects to the same FastAPI backend as the React web application
and does not introduce a separate mobile backend. The structure below defines
the target responsibilities; completed and deferred capabilities are tracked in
`CURRENT_STATUS.md` and `docs/frontend_mobile_integration_backlog.md`.

## Target Mobile Structure

```text
mobile/
├─ assets/
│  ├─ images/
│  └─ icons/
│
├─ src/
│  ├─ app/
│  │  ├─ App.tsx
│  │  └─ AppProviders.tsx
│  │
│  ├─ navigation/
│  │  ├─ RootNavigator.tsx
│  │  ├─ AuthNavigator.tsx
│  │  ├─ MainTabNavigator.tsx
│  │  └─ navigationTypes.ts
│  │
│  ├─ api/
│  │  ├─ apiClient.ts
│  │  ├─ authApi.ts
│  │  ├─ portfoliosApi.ts
│  │  ├─ analyticsApi.ts
│  │  ├─ reportsApi.ts
│  │  └─ simulationsApi.ts
│  │
│  ├─ auth/
│  │  ├─ AuthProvider.tsx
│  │  ├─ useAuth.ts
│  │  └─ authStorage.ts
│  │
│  ├─ config/
│  │  └─ environment.ts
│  │
│  ├─ components/
│  │  ├─ ui/
│  │  ├─ charts/
│  │  └─ portfolio/
│  │
│  ├─ screens/
│  │  ├─ auth/
│  │  ├─ dashboard/
│  │  ├─ portfolios/
│  │  ├─ analytics/
│  │  ├─ simulations/
│  │  ├─ reports/
│  │  ├─ assistant/
│  │  └─ settings/
│  │
│  ├─ hooks/
│  ├─ storage/
│  ├─ types/
│  ├─ utils/
│  ├─ theme/
│  └─ mocks/
│
├─ app.json
├─ package.json
├─ tsconfig.json
└─ .env.example
```

## Mobile App Folder Definitions

| Folder | Simple Meaning |
|---|---|
| `app/` | Starts the React Native application and installs global providers. |
| `navigation/` | Controls authentication flow, screen navigation, and bottom-tab navigation. |
| `api/` | Communicates with the shared Aura FastAPI backend. |
| `auth/` | Manages login state, JWT authentication, and current-user state. |
| `config/` | Stores environment configuration such as the backend API URL. |
| `components/` | Contains reusable mobile UI, charts, and portfolio components. |
| `screens/` | Contains the main mobile screens shown to the user. |
| `hooks/` | Contains reusable React Native logic and state behavior. |
| `storage/` | Handles device-local and secure authentication storage. |
| `types/` | Contains TypeScript structures matching backend API contracts. |
| `utils/` | Contains formatting and UI-only helper functions. |
| `theme/` | Defines Aura mobile colors, typography, spacing, and shared visual rules. |
| `mocks/` | Contains temporary frontend development/test data only. |
| `assets/` | Stores mobile images, icons, and visual resources. |

## Mobile Authentication and Secure Storage

The intended mobile authentication flow is:

```text
Login / Register Screen
        ↓
authApi
        ↓
FastAPI
        ↓
Bearer JWT
        ↓
Secure Mobile Storage
        ↓
Authenticated API Requests
```

- `AuthProvider.tsx` manages current-user and authentication state for the React Native application.
- `useAuth.ts` exposes authentication behavior to screens and components.
- `authStorage.ts` coordinates the agreed persistence behavior with secure device storage where appropriate.
- Authentication tokens or other sensitive session material must not be placed in ordinary mock data or hard-coded in source files.
- FastAPI remains authoritative for authentication, portfolio ownership, and access control.

This is an intended boundary. It does not imply that registration, secure token persistence, refresh tokens, OAuth, MFA, password reset, logout revocation, or mobile/backend authentication integration is already complete.

## Mobile Financial Calculation Boundary

React Native is responsible for mobile presentation, interaction, navigation, form handling, loading and error states, and displaying backend results. It must not independently calculate or duplicate Aura's official:

- risk score;
- volatility;
- Sharpe ratio;
- maximum drawdown;
- correlation;
- diversification score;
- risk drivers; or
- historical, allocation, or combined simulation results.

The mobile app receives these values from FastAPI. Mobile utilities may perform presentation-only work such as currency, percentage, and date formatting, chart presentation transformations, and basic visual derivations. Backend analytics and simulation services remain the financial source of truth.

## Mobile Navigation

Mobile navigation should be optimized for phone interaction rather than copying the web application's top navigation. The recommended primary bottom navigation is:

```text
Home
Portfolio
Simulate
AI
More
```

Additional destinations may be grouped under `More` or reached through feature-specific screens:

```text
Analytics
Reports
Settings
Learn
Watchlist
```

Navigation placement does not claim that every listed screen or its backend
functionality is currently implemented. The AI interface is integrated; optional
features such as Watchlist and Notifications remain deferred.

## Mobile Environment Configuration

Web and mobile may use different backend URLs during local development while connecting to the same FastAPI application and using the same API contracts:

```text
Web development:
http://localhost:8000

Physical mobile device:
http://<development-PC-LAN-IP>:8000

Production:
https://<Aura-API-domain>
```

Backend URLs must not be hard-coded inside screens. `src/config/environment.ts` and environment variables provide the mobile configuration boundary.

## Mobile Mock-Data and Implementation Status Boundary

Mobile `mocks/` data is limited to development, testing, and isolated screen work. It is not a production source for authentication, portfolios, analysis, reports, simulations, or AI responses.

The mobile tree documents responsibility boundaries. Authentication,
portfolio/report/simulation flows, secure token storage, and the AI Assistant
are integrated against the pre-real-holding contract. Real-holding/valuation and
V2 history parity plus production deployment remain incomplete.

[↑ Back to Quick Navigation](#quick-navigation)

---

# Shared Client-Backend Architecture

Aura's React web and React Native applications use the same FastAPI backend and
PostgreSQL persistence layer:

```text
React Web App ───────────┐
                         │
                         ▼
                  FastAPI Backend
                         │
                         ▼
                     PostgreSQL
                         ▲
                         │
React Native App ────────┘
```

Both clients use the same backend API contracts for:

- authentication;
- portfolios;
- holdings;
- analysis;
- reports;
- historical simulations;
- allocation simulations;
- combined simulations;
- simulation history; and
- grounded AI explanations.

Separate `/api/web/...` and `/api/mobile/...` endpoint families should not be created without a real technical requirement. Both applications should receive consistent ownership decisions, financial calculations, simulation results, reports, and authentication outcomes from the shared backend.

Each client may adapt backend responses for its presentation needs, but neither client replaces backend business rules or official calculations. Different local-development API URLs identify how each device reaches the same FastAPI application; they do not create different backend architectures or contracts.

[↑ Back to Quick Navigation](#quick-navigation)

---

# Project Folder Definitions

Platform-specific folder definitions are available in their corresponding sections:

- [Backend Folder Definitions](#backend-folder-definitions)
- [Frontend Web Folder Definitions](#frontend-web-folder-definitions)
- [Mobile App Folder Definitions](#mobile-app-folder-definitions)

## Important File and Folder Roles

### Root Files

- `AGENTS.md` — tells Codex how to work on Aura.
- `PROJECT_CONTEXT.md` — explains what Aura is, why it exists, and the main project direction.
- `CURRENT_STATUS.md` — tracks what is completed, what is currently being worked on, and what comes next.
- `.gitignore` — prevents local, generated, private, and unnecessary files from being uploaded to GitHub.
- `README.md` — gives the main project overview and setup instructions.

### Backend

- `core/` — application settings, constants, and logging.
- `api/` — FastAPI routes and request handling.
- `analytics/` — portfolio risk calculations.
- `scenarios/` — historical What-If simulation logic.
- `data_pipeline/` — market-data fetching, cleaning, validation, and updating.
- `database/` — database connection, models, and repository actions.
- `schemas/` — expected data structures for input and output.
- `services/` — coordinates workflows between different backend parts.
- `agents/` — grounded educational AI explanation layer.
- `utils/` — small reusable helper functions.

### Tests

- `tests/unit/` — tests individual functions and modules.
- `tests/integration/` — tests how multiple components work together.
- `test_health_api.py` — verifies the implemented health endpoint.

### Scripts

- `seed_historical_data.py` — manually loads initial historical market data.
- `update_market_data.py` — manually triggers a market-data update.
- `run_engine_check.py` — reserved for manually checking the analytics engine.

### Shared Data

- `data/raw/` — original market-data files.
- `data/processed/` — cleaned and prepared market-data files.

### Documentation

- `docs/api_contracts/` — API request and response documentation.
- `docs/architecture/` — system architecture documents.
- `docs/data_dictionary/` — definitions of stored data fields.
