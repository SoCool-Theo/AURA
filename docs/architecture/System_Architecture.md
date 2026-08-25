# Aura System Architecture

## Project Structure

```text
AURA/
│
├── .venv/                         ← Virtual Environment
├── AGENTS.md                      ← Tells Codex how to work on Aura
├── PROJECT_CONTEXT.md             ← What Aura is and why it is being built
├── CURRENT_STATUS.md              ← Tells Codex what has actually been completed
├── backend/                       ← FastAPI backend, analytics, database, simulations, AI later
├── web-prototype-react/            ← Customer React web application
├── mobile/                        ← Customer mobile application / later work
├── data/                          ← Shared market data
├── docs/                          ← Project documentation
├── .gitignore
└── README.md
```

## Main Decisions Reflected Here

- Customer website uses React and TypeScript and lives under `web-prototype-react/`.
- Website first, mobile later.
- FastAPI remains the shared backend.
- PostgreSQL remains the backend persistence layer.
- Clean historical data is used directly for calculations.
- Automatic market-data updates.
- Backend analytics and simulation calculations are the source of truth; the React frontend does not duplicate financial formulas.
- React uses a dedicated API layer rather than scattered network calls in page components.
- Bearer authentication is handled through a dedicated frontend authentication layer, with the backend remaining authoritative.
- Analytics engine first.
- Historical simulator after core analytics.
- AI agent later.
- The dashboard remains concise while detailed analytics live on dedicated pages.
- Frontend mock data is separated from production API data.
- Shared components, charts, styles, and types are separated from feature-specific pages.
- Frontend AI architecture may be planned, but real AI integration is not complete until the backend AI Agent is implemented.
- No ML training folder yet.

---

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
│   │   │       └── agent.py                  ← Later
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
│   │   │   └── agent.py                     ← Later
│   │   │
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── market_data_service.py
│   │   │   ├── portfolio_service.py
│   │   │   └── analysis_service.py
│   │   │
│   │   ├── agents/                           ← Later
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
│   │       ├── api/
│   │       │   ├── test_portfolio_api.py
│   │       │   └── test_simulation_api.py
│   │       │
│   │       └── database/
│   │           └── test_database.py
│   │
│   ├── scripts/
│   │   ├── seed_historical_data.py
│   │   ├── update_market_data.py
│   │   └── test_engine.py
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
| `agents/` | AI explanation later |
| `core/` | Global settings and constants |
| `utils/` | Small reusable helper functions |

---

## React Web Frontend Architecture

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

### Main Frontend Folder Definitions

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

### Frontend-to-Backend Responsibility Boundary

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

### Frontend API Layer

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

### Frontend Authentication Architecture

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

### Page Responsibilities

| Page | Main Responsibility |
|---|---|
| Dashboard | Shows a concise portfolio overview, performance, risk summary, top risk drivers, allocation, AI insight preview, and current analysis state. |
| Portfolios | Creates, lists, opens, renames, edits, duplicates, and deletes user portfolios and holdings. |
| Analytics | Shows detailed portfolio risk analysis including volatility, drawdown, Sharpe ratio, correlation, diversification, risk drivers, and individual asset analysis. |
| Simulations | Runs Historical Scenario, Allocation Change, and Combined Simulation workflows and displays simulation history. |
| AI Assistant | Provides the conversational explanation interface once the backend AI Agent is implemented. |
| Reports | Lists and displays saved immutable portfolio-analysis reports. |
| Settings | Handles frontend profile and application settings. |
| Watchlist | Optional or later market watchlist functionality. |
| Learn | Optional or later educational content functionality. |

Watchlist and Learn may exist as routes or frontend features without appearing in the current primary top navigation.

### Dashboard Design Boundary

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

### Reusable UI and Chart Architecture

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

### Frontend Styling Architecture

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

### Frontend Assets

`src/assets/images/aura-market-background.png` is the approved subtle financial-market background visual for the React web interface. It remains secondary to content and must not interfere with text readability or dashboard cards.

### Frontend Mock-Data Boundary

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

### Frontend Implementation Status Boundary

This section documents the planned architecture. Individual frontend pages or prototype interactions may already exist, but the target folder split, production API integration, authentication layer, protected routes, and backend AI Agent integration must not be treated as complete until repository evidence and status documentation confirm them.

---

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
- `agents/` — AI explanation layer to be developed later.
- `utils/` — small reusable helper functions.

### Tests

- `tests/unit/` — tests individual functions and modules.
- `tests/integration/` — tests how multiple components work together.

### Scripts

- `seed_historical_data.py` — manually loads initial historical market data.
- `update_market_data.py` — manually triggers a market-data update.
- `test_engine.py` — manually runs the analytics engine for testing.

### Shared Data

- `data/raw/` — original market-data files.
- `data/processed/` — cleaned and prepared market-data files.

### Documentation

- `docs/api_contracts/` — API request and response documentation.
- `docs/architecture/` — system architecture documents.
- `docs/data_dictionary/` — definitions of stored data fields.
