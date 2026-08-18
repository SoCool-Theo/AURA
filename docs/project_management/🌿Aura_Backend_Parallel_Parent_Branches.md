# Aura Backend Parallel Parent Branches

**Project:** Aura — AI-Powered Portfolio Risk Intelligence  
**Integration branch:** `develop`  
**Release branch:** `main`

---

## Purpose of This Document

This document tracks Aura's major backend workstreams, their ownership boundaries,
their current status, and the dependencies between parent branches and later
integration branches.

The backend should continue through focused branches created from the latest
`develop`.

Each branch should:

- Be created directly from the latest `develop`
- Own a clearly separated backend responsibility
- Avoid depending on unfinished work from another branch
- Be reviewed and merged through a Pull Request into `develop`
- Avoid unnecessary changes to shared integration files
- Preserve the public contracts of completed components unless a change is
  explicitly approved

Standard feature-branch flow:

```text
develop
   ↓ create branch
feat/backend-...
   ↓ Pull Request
develop
```

Supporting cleanup branches may use prefixes such as:

```text
refactor/...
docs/...
test/...
chore/...
```

Feature branches should not be opened directly against `main`.

The normal release flow is:

```text
feature/refactor/docs branch
              ↓
           develop
              ↓
       release Pull Request
              ↓
            main
```

---

# Current Backend Workstream Status

| Branch | Type | Status | Main Responsibility |
|---|---|---|---|
| `feat/fastapi-foundation` | Foundation | Completed | FastAPI application foundation and health endpoint |
| `feat/backend-analytics-core` | Parent feature | Completed | Deterministic portfolio-risk analytics engine |
| `refactor/analytics-validation` | Supporting refactor | Completed | Shared private validation for analytics modules |
| `feat/backend-schemas-contracts` | Parent feature | Completed | Pydantic schemas and stable backend data contracts |
| `feat/backend-market-data-pipeline` | Parent feature | Completed | Fetch, clean, validate, normalize, and locally persist market data |
| `feat/backend-database-foundation` | Parent feature | Completed | PostgreSQL connection, models, migrations, repositories, and live integration verification |
| `feat/backend-market-data-storage` | Integration feature | Completed | Save and retrieve processed historical data through PostgreSQL |
| `feat/backend-analysis-service` | Integration feature | Completed | Coordinate validated portfolio-analysis input, PostgreSQL historical data, existing analytics, and response schemas |
| `feat/backend-portfolio-api` | Integration feature | Completed and merged into `develop` | Frontend-neutral portfolio and holding CRUD service/API |
| `feat/backend-quality-ci` | Optional support | Optional | Automated testing and code-quality checks |

---

# Completed Foundation Work

## `feat/fastapi-foundation`

**Status:** Completed and merged into `develop`

### Purpose

Establish a stable FastAPI backend foundation before feature-specific backend
development begins.

### Completed Work

- FastAPI application foundation
- Initial application structure
- Health endpoint
- Initial integration test
- Backend test setup

### Boundary

The foundation branch provides application startup and basic API health
verification. It does not own portfolio analytics, database models, market-data
processing, schemas, simulations, or the AI agent.

---

# Completed Parent Workstreams

## 1. `feat/backend-analytics-core`

**Status:** Completed and merged into `develop`

### Purpose

Provide deterministic portfolio-risk calculations using prepared Pandas price
data and portfolio weights.

The analytics layer is a pure calculation layer. It does not fetch market data,
access PostgreSQL, create API routes, or call the AI agent.

### Calculations Implemented

- Asset returns
- Portfolio returns
- Cumulative return
- Annualized return
- Annualized volatility
- Maximum drawdown
- Maximum-drawdown peak and trough dates
- Sharpe ratio
- Asset correlation matrix
- Unique asset-correlation pairs
- Portfolio concentration
- Herfindahl-Hirschman Index
- Effective number of assets
- Diversification score and level
- Covariance-based risk contributions
- Risk-driver ranking
- Overall portfolio risk score
- Overall risk classification
- Individual asset metrics

### Analytics Engine

- Added `analyze_portfolio(...)`
- Added `PortfolioAnalyticsResult`
- Added stable public analytics imports
- Added deterministic manual engine verification:

```bash
python -m backend.scripts.run_engine_check
```

### Main Files

```text
backend/app/analytics/
├── __init__.py
├── returns.py
├── volatility.py
├── drawdown.py
├── sharpe.py
├── correlation.py
├── concentration.py
├── diversification.py
├── risk_driver.py
├── risk_classifier.py
└── engine.py

backend/tests/unit/analytics/
backend/scripts/run_engine_check.py
```

### Final Analytics-Core Verification

- Analytics tests: 704 passed
- Full backend tests: 705 passed
- Failed tests: 0
- Manual engine check: passed
- Dependency check: passed
- Python compilation check: passed
- Git whitespace check: passed

### Branch Boundary

The analytics core:

- Accepts prepared market data and portfolio weights
- Produces deterministic calculation results
- Does not fetch market data
- Does not read from or write to PostgreSQL
- Does not create FastAPI routes
- Does not run historical-scenario workflows
- Does not call the AI agent
- Does not provide buy/sell recommendations

---

## 2. `feat/backend-schemas-contracts`

**Status:** Completed and merged into `develop`

### Purpose

Define stable Pydantic request and response structures shared by future API,
service, analytics, market-data, database-mapping, simulation, and frontend
integration work.

This branch defines contracts only. It does not implement business workflows.

### Completed Contracts

Common:

- `AuraBaseModel`, internal only
- `AssetSymbol`
- `AnalysisPeriod`

Portfolio:

- `PortfolioHoldingInput`
- `PortfolioAnalysisRequest`

Market data:

- `HistoricalMarketDataRequest`
- `HistoricalPricePoint`
- `AssetPriceSeries`
- `HistoricalMarketDataResponse`

Analytics:

- `MaximumDrawdownMetrics`
- `ConcentrationMetrics`
- `DiversificationMetrics`
- `RiskDriverEntry`
- `RiskClassification`
- `AssetMetrics`
- `CorrelationPair`
- `CorrelationMatrix`
- `AnalysisMetadata`
- `PortfolioMetrics`
- `PortfolioReturnPoint`
- `RiskDriverAnalysis`
- `PortfolioAnalysisResponse`

### Contract Behavior

- Unknown fields are rejected
- Portfolio weights use decimal values
- Total portfolio weight is validated
- Symbols are trimmed and normalized to uppercase
- Date ranges are inclusive
- Public JSON numbers must be finite
- Intentionally unavailable values use JSON `null`
- Negative maximum drawdowns are preserved
- Signed risk contributions are preserved
- Ordered collections are preserved
- Caller-owned inputs are not mutated
- Contracts remain provider-independent
- Contracts remain database-independent

### Examples and Documentation

- Four canonical JSON examples
- Direct example-validation tests
- API-contract documentation in `docs/api_contracts/`
- Exactly 21 approved public package exports
- Simulation contracts remain deferred and unexported

### Main Files

```text
backend/app/schemas/
backend/tests/unit/schemas/
backend/examples/
docs/api_contracts/
```

### Final Verification

- Schema tests: 301 passed
- Analytics tests: 820 passed
- Full backend tests: 1,122 passed
- Failed tests: 0
- Canonical example tests: 4 passed
- Public-export tests: 5 passed
- Public import check: passed
- Exactly 21 approved public exports
- Strict JSON validation: passed
- Manual analytics engine check: passed
- Compilation check: passed
- Dependency check: passed
- Dependency versions changed: none
- Documentation consistency check: passed
- Git whitespace check: passed
- Existing warning: one Starlette/httpx deprecation warning

### Branch Boundary

The schemas-contract branch did not:

- Create FastAPI routes
- Implement services
- Query PostgreSQL
- Define SQLAlchemy models
- Fetch or clean market data
- Add provider integrations
- Implement production analytics adapters
- Implement simulation calculations
- Implement AI-agent behavior
- Add investment recommendations
- Change dependency files or versions

---

# Completed Supporting Refactor

## `refactor/analytics-validation`

**Status:** Completed and merged into `develop`

### Purpose

Consolidate repeated private input-validation logic in the analytics package
without changing public behavior or analytics formulas.

### Shared Private Helpers Added

- Datetime-index validation
- Positive-integer validation
- Finite real-value validation and normalization
- Portfolio weight-mapping validation

### Modules Migrated

- `returns.py`
- `volatility.py`
- `drawdown.py`
- `sharpe.py`
- `correlation.py`
- `concentration.py`
- `diversification.py`
- `risk_driver.py`

### Validation Boundaries Preserved

Specialized validation remains local where behavior intentionally differs:

- Sharpe zero-volatility handling
- Return lower-bound rules
- Portfolio-weight alignment
- Correlation-matrix `NaN` behavior
- Diversification coverage rules
- Risk-classification thresholds
- Drawdown calculation conventions
- Analytics-engine consistency checks

### Compatibility Preserved

The refactor did not change:

- Public analytics APIs
- Public function signatures
- Analytics formulas
- Result dataclasses
- Returned structures
- Exception behavior
- Validation order
- Input non-mutation behavior
- Correlation undefined-value behavior
- Risk-driver ranking behavior

### Final Refactor Verification

- Shared validation tests: 116 passed
- Analytics tests: 820 passed
- Full backend tests: 821 passed
- Failed tests: 0
- Manual engine check: passed
- Dependency check: passed
- Public analytics import check: passed
- Python compilation check: passed
- Git whitespace check: passed

### Refactor Boundary

This supporting branch did not add a new product feature. It improved internal
maintainability while preserving the completed analytics-core contract.

---

# Completed Market-Data Parent Workstream

## 3. `feat/backend-market-data-pipeline`

**Status:** Completed and merged into `develop`

### Purpose

Fetch, clean, validate, normalize, and locally persist historical market data
for use by the analytics engine and later historical simulations.

### Completed Work

- Added a market-data provider interface and Yahoo Finance implementation using
  `yfinance==1.5.1`.
- Added historical price fetching for a default set of 17 stock, ETF, bond,
  metal, and cryptocurrency symbols.
- Preserved Aura's inclusive date ranges when calling the provider.
- Normalized provider data to `date`, `symbol`, `adjusted_close`, `volume`, and
  `source`.
- Added missing-value handling, duplicate removal, column normalization, and
  data-quality validation for prices, symbols, dates, volume, duplicates, and
  per-symbol ordering.
- Added partial provider-failure reporting.
- Added atomic raw and processed CSV persistence under `data/` and excluded
  generated market-data files from Git.
- Added the `update_market_data()` workflow and manual update CLI in
  `backend/scripts/update_market_data.py`.
- Added deterministic unit tests using mocked provider and network responses.

### Main Files

```text
backend/app/data_pipeline/
├── __init__.py
├── providers/
│   ├── __init__.py
│   └── market_provider.py
├── fetcher.py
├── cleaner.py
├── validator.py
└── updater.py

backend/tests/unit/data_pipeline/
```

### Suggested Normalized Data Shape

```text
date
symbol
adjusted_close
volume
source
```

The pipeline implementation uses this canonical internal shape. Database
mapping is owned by the completed storage integration workstream documented
below.

### Update Behavior

- Updates are live on demand through manual invocation.
- Each execution replaces the requested historical CSV dataset.
- Automatic background scheduling is not implemented.
- Incremental append or update optimization is not implemented.

### Final Verification

- Focused market-data pipeline tests: 23 passed
- Full backend tests: 1,145 passed
- Dependency check: passed
- Git whitespace check: passed
- Working tree: clean
- Existing warning: one Starlette/httpx deprecation warning
- Live Yahoo Finance network smoke test: not recorded

### Branch Boundary

This branch produces validated market data.

It should not:

- Calculate portfolio risk
- Store production records in PostgreSQL
- Create portfolio API routes
- Implement analysis-service orchestration
- Run complete historical simulations
- Call the AI agent
- Automatically schedule market-data updates

Database persistence is handled separately by the completed
`feat/backend-market-data-storage` integration branch.

---

# Completed Database Parent Workstream

## 4. `feat/backend-database-foundation`

**Status:** Completed and merged into `develop`

### Purpose

Provide the PostgreSQL persistence foundation used by later storage, service,
reporting, and API integration work.

### Completed Work

- PostgreSQL configuration using synchronous SQLAlchemy 2.x and Psycopg 3
- Explicit lazy engine creation and caller-controlled sessions and transactions
- Alembic migration infrastructure and one initial PostgreSQL schema migration
- `User`, `Portfolio`, `Holding`, `MarketData`, and `Analysis` ORM models
- `PortfolioRepository`, `MarketDataRepository`, and `AnalysisRepository`
- Isolated live PostgreSQL migration and repository integration tests

### Initial Models

```text
User
Portfolio
Holding
MarketData
Analysis
```

Simulation-history and AI-conversation persistence remain deferred until their
feature requirements become stable.

### Stable Persistence Decisions

- User-owned domain resources use UUID identifiers.
- Holdings persist ordered weights; shares and invested amounts remain deferred.
- Total Holding weight is validated transactionally at repository level.
- MarketData identity is `(symbol, date)` and uses the normalized pipeline shape.
- Analysis reports use relational metadata plus a JSONB result snapshot.
- Repositories receive caller-owned sessions and do not automatically commit or
  roll back transactions.
- PostgreSQL implements ownership cascades, and Alembic owns schema migrations.

### Main Files

```text
backend/app/database/
├── __init__.py
├── connection.py
├── models/
│   ├── __init__.py
│   ├── user.py
│   ├── portfolio.py
│   ├── holding.py
│   ├── market_data.py
│   └── analysis.py
└── repositories/
    ├── __init__.py
    ├── market_data_repository.py
    ├── portfolio_repository.py
    └── analysis_repository.py

backend/tests/integration/database/
```

### Final Verification

- PostgreSQL version: 18.4
- Database unit tests: 93 passed
- Live PostgreSQL integration tests: 5 passed, 0 skipped
- Schema tests: 301 passed
- Market-data pipeline tests: 23 passed
- Analytics tests: 820 passed
- Full backend tests: 1,243 passed, 0 failed, 0 skipped
- Live Alembic upgrade, repository integration, and downgrade: passed
- Compilation, dependency, and Git diff checks: passed
- Existing warning: one unrelated Starlette/httpx deprecation warning

### Branch Boundary

This branch used generated records and an isolated PostgreSQL test database.

It did not implement:

- Market-data pipeline-to-PostgreSQL integration
- Portfolio API routes
- Analysis or reporting services
- Historical simulations or simulation history
- Automatic market-data scheduling
- AI conversation persistence
- Full backend API integration

---

# Completed Market-Data Storage Integration Workstream

## 5. `feat/backend-market-data-storage`

**Status:** Completed and merged into `develop`

### Purpose

Connect Aura's validated historical market-data pipeline to PostgreSQL storage
and retrieval while preserving the completed pipeline and database contracts.

### Completed Work

- Added pure canonical DataFrame-to-repository mapping with `pd.Timestamp` to
  Python `date`, adjusted close to explicitly quantized 12-place `Decimal`
  using `ROUND_HALF_UP`, nullable volume to `None`, and preserved symbols,
  sources, row order, and caller-owned input data.
- Added `MarketDataService` using a caller-owned SQLAlchemy session, the
  existing `MarketDataRepository`, 1,000-record storage batches, and inclusive,
  deterministic historical range retrieval.
- Added a manual processed-CSV seed/backfill workflow that reuses the existing
  validator and performs one outer commit after successful storage.
- Added a private handoff for the updater's already-cleaned and validated
  DataFrame while preserving the public
  `update_market_data(...) -> MarketDataUpdateResult` contract.
- Preserved CSV-only updater behavior by default and added explicit
  `--persist-database` PostgreSQL persistence after successful processing.
- Preserved caller-controlled transaction ownership across service and
  repository batches.

### Main Integration Boundary

```text
market-data pipeline
        ↓ validated canonical DataFrame
MarketDataService
        ↓ bounded repository batches
MarketDataRepository
        ↓ caller-controlled transaction
PostgreSQL
```

CSV persistence and PostgreSQL persistence remain separate transactions by
design. The updater creates its database session only after the market-data
processing workflow succeeds.

### Final Verification

- PostgreSQL version: 18.4
- Market-data service tests: 15 passed
- Market-data pipeline tests: 27 passed
- Script tests: 16 passed
- Database unit and repository tests: 93 passed
- Live PostgreSQL integration tests: 11 passed, 0 skipped
- Schema tests: 301 passed
- Analytics tests: 820 passed
- Full backend tests: 1,284 passed, 0 skipped
- Live verification covered persistence/retrieval, inclusive ordering, nullable
  volume, Decimal/Numeric persistence, repeat upserts, existing-row updates,
  1,001-row batching, caller commit/rollback, processed-CSV seeding, and updater
  `--persist-database` persistence.
- Compilation, dependency, and Git diff checks: passed

The existing processed historical dataset was confirmed to exist and validate
with 69,449 rows across 17 symbols. It was not automatically seeded into
PostgreSQL during branch verification.

### Branch Boundary

This branch did not implement automatic scheduling, portfolio APIs,
analysis-service orchestration, analysis reporting, historical simulation or
simulation history, AI-agent behavior, full backend API integration,
frontend/backend integration, or deployment.

---

## 6. `feat/backend-analysis-service`

**Status:** Completed and merged into `develop`

### Purpose

Coordinate validated portfolio-analysis requests, PostgreSQL-backed historical
market data, the existing analytics engine, and validated response schemas.

### Completed Work

- Added a pure database-record to analytics-price-frame adapter.
- Preserved requested holding/symbol order and used the exact common-date
  intersection across requested assets.
- Added missing-symbol validation and adjusted-close `Decimal` to float
  conversion without forward-fill, backfill, interpolation, or synthesized
  prices.
- Added a pure analytics-result to response mapper that preserves negative
  maximum drawdown, signed risk contributions, and all defined collection
  ordering.
- Converted only intentionally unavailable analytics values, such as undefined
  Sharpe ratios or correlations, to schema `null`.
- Added production `AnalysisService` using caller-owned SQLAlchemy session and
  transaction control, `MarketDataService`, and the existing
  `analyze_portfolio(...)` defaults.
- Kept analysis execution read-only with no `Analysis` snapshot/report
  persistence and no analytics-formula duplication.

### Production Dependency Flow

```text
PortfolioAnalysisRequest
        ↓
AnalysisService
        ↓
MarketDataService
        ↓
MarketDataRepository
        ↓
PostgreSQL historical market data
        ↓
analytics input adapter
        ↓
analyze_portfolio(...)
        ↓
PortfolioAnalyticsResult
        ↓
response mapper
        ↓
PortfolioAnalysisResponse
```

### Final Verification

- AnalysisService unit tests: 25 passed
- Analytics tests: 820 passed
- Schema tests: 301 passed
- MarketDataService tests: 15 passed
- Database unit tests: 93 passed
- Live PostgreSQL integration tests: 13 passed, 0 skipped
- Full backend tests: 1,311 passed, 0 failed, 0 errors, 0 skipped
- Compilation, dependency, direct-import smoke, and Git integrity checks:
  passed
- Existing warning: one unrelated Starlette/httpx deprecation warning

Live PostgreSQL verification covered multi-asset analysis, inclusive dates,
requested ordering despite repository ordering, exact common-date intersection,
missing requested symbols, caller-owned transaction/session behavior, and no
`Analysis` snapshot creation. It used focused test records rather than a
permanently seeded full historical CSV.

### Branch Boundary

This branch did not add FastAPI portfolio-analysis routes, portfolio CRUD APIs,
report persistence/history, simulations, automatic market-data scheduling,
AI-agent behavior, frontend/backend integration, or deployment. It does not
own market-data fetching or updating.

---

## 7. `feat/backend-portfolio-api`

**Status:** Completed and merged into `develop`

### Purpose

Expose persisted portfolio and holding CRUD behavior through a frontend-neutral
service and REST API shared by Aura's web and mobile clients.

### Completed Work

- Added CRUD-oriented schemas for portfolio creation, rename/update, holdings
  replacement, duplication, full portfolio responses, holding responses,
  summaries, and list responses.
- Preserved the existing 21-name package-level schema export contract and did
  not add simulation schemas.
- Added `PortfolioService` coordination for create, get, list, rename, replace
  holdings, duplicate, and delete.
- Enforced ownership at the service boundary for ID-based portfolio operations.
- Added these routes under the existing `/api` prefix:
  - `POST /api/portfolios`
  - `GET /api/portfolios`
  - `GET /api/portfolios/{portfolio_id}`
  - `PATCH /api/portfolios/{portfolio_id}`
  - `PUT /api/portfolios/{portfolio_id}/holdings`
  - `POST /api/portfolios/{portfolio_id}/duplicate`
  - `DELETE /api/portfolios/{portfolio_id}`

These are shared REST endpoints, not separate web and mobile API variants. No
portfolio-analysis HTTP endpoint was added.

### Ownership, Persistence, and Transaction Boundaries

- `X-User-ID` is a temporary ownership selector. It validates that the supplied
  UUID identifies an existing `User`, but it is not secure authentication.
- Owner-scoped ID access returns the same client-visible `404` for missing and
  wrong-owner portfolios.
- Portfolios and holdings preserve UUID identities, user ownership, ordered
  positions, and symbol/weight allocations.
- Holdings can be replaced as a complete ordered allocation. Duplication creates
  new portfolio and holding identities, and portfolio deletion uses the existing
  persistence cascade.
- Shares, invested amounts, and current-value fields are not persisted.
- `PortfolioRepository` does not commit or roll back. `PortfolioService` does
  not commit, roll back, or close sessions. Successful writes commit at the
  request/API boundary, while failure rollback and cleanup are handled by the
  request-scoped database dependency.
- Database setup remains lazy; application import and `/api/health` do not
  require portfolio data or a live PostgreSQL connection.

### Final Post-Synchronization Verification

- Portfolio API integration tests: 42 passed
- PortfolioService tests: 21 passed
- Portfolio schema tests: 84 passed
- Complete schema suite: 351 passed
- PortfolioRepository tests: 17 passed
- AnalysisService tests: 25 passed
- Analytics tests: 820 passed
- Live PostgreSQL integration tests: 16 passed, 0 skipped
- Full backend tests: 1,427 passed, 0 failed, 0 errors, 0 skipped
- Compilation, dependency, direct-import, health, and API-surface checks: passed
- Existing warning: one Starlette TestClient/httpx deprecation warning

Live portfolio tests exercised the real FastAPI → request dependency →
PortfolioService → PortfolioRepository → PostgreSQL stack. Coverage included
the CRUD lifecycle, portfolio and ordered-holding persistence, duplication,
ownership isolation, fresh-session persistence, and existing-user validation.

### Branch Boundary

This workstream did not implement secure authentication, JWT/login/user
registration, a portfolio-analysis HTTP endpoint, report persistence/history,
historical/allocation/combined simulations, simulation history, automatic
market-data scheduling, AI-agent behavior, full backend API integration,
frontend implementation, or deployment.

Analysis execution remains a separate completed service capability. Reporting
persistence, mapping, orchestration, and exposure remain owned by a later
workstream.

---

## 8. Optional: `feat/backend-quality-ci`

**Status:** Optional

### Purpose

Add automated testing and code-quality checks without changing product behavior.

### Possible Work

- GitHub Actions test workflow
- Automatic `pytest`
- Ruff or another Python linter
- Type checking
- Coverage configuration
- Pull-request checks
- Dependency verification

This branch is useful, but schemas, data, database, services, and integration
work have higher immediate product priority.

---

# Later Integration and Feature Branches

These branches should begin only after their required parent components are
stable in `develop`.

## Readiness Table

| Later Branch | Main Responsibility | Dependencies | Current Readiness |
|---|---|---|---|
| `feat/backend-analysis-service` | Coordinate validated input, PostgreSQL market data, analytics, and response schemas | Analytics + schemas + data access | Completed and merged into `develop` |
| `feat/backend-portfolio-api` | Portfolio and holding CRUD endpoints | Schemas + database | Completed and merged into `develop` |
| `feat/backend-market-data-storage` | Save and retrieve processed historical data | Data pipeline + database | Completed and merged into `develop` |
| `feat/backend-historical-scenario-simulator` | Test the current portfolio during a selected past event | Analytics + historical data + simulation schemas | Historical acquisition and PostgreSQL access are complete; simulation schemas and finalized requirements remain deferred |
| `feat/backend-allocation-simulator` | Compare original and modified allocations over the same period | Analytics + historical data + simulation schemas | Historical acquisition and PostgreSQL access are complete; simulation schemas and finalized requirements remain deferred |
| `feat/backend-combined-simulator` | Compare original and modified allocations during one event | Historical scenario + allocation simulator | Not ready |
| `feat/backend-analysis-reporting` | Save and retrieve analysis reports | Analytics + schemas + database + analysis service | Analytics/service/schema/database prerequisites are available; report persistence and reporting mapping remain unimplemented |
| `feat/backend-simulation-history` | Save and retrieve simulation results | Simulators + schemas + database | Not ready |
| `feat/backend-market-data-scheduler` | Automate market-data updates | Data pipeline + database/storage | Prerequisites are complete; automatic scheduling remains unimplemented and deferred |
| `feat/backend-ai-agent` | Explain stable analysis and simulation results | Stable reports and simulations + schemas + database | Not ready; stable reporting and simulation outputs remain unavailable |
| `feat/backend-api-integration` | Connect routes, services, schemas, repositories, and agent | Completed feature branches | Not ready; portfolio CRUD routes exist, but reporting, simulations, AI, and other full integration work remain incomplete |
| `feat/backend-deployment` | Containerization and deployment | Stable backend integration | Not ready |

---

# Recommended Simulation Order

Aura's Historical What-If Simulator contains three planned modes:

```text
Historical Scenario
        ↓
Allocation Change
        ↓
Combined Simulation
```

## Historical Scenario

Answers:

> How did the current portfolio behave during a selected historical event?

## Allocation Change

Answers:

> How would different asset percentages change the portfolio's historical risk?

## Combined Simulation

Answers:

> How would the original and modified allocations compare during the same
> historical event?

The combined mode should reuse the earlier simulation logic rather than
duplicate it.

---

# Recommended Backend Dependency Flow

```text
feat/backend-analytics-core ────────────────┐
                                            │
feat/backend-schemas-contracts ─────────────┼── ✅ feat/backend-analysis-service
                                            │
completed backend-market-data-storage ──────┘

feat/backend-schemas-contracts ─────────────┐
                                            ├── ✅ feat/backend-portfolio-api
feat/backend-database-foundation ───────────┘

feat/backend-market-data-pipeline
                +
feat/backend-database-foundation
                ↓
✅ feat/backend-market-data-storage
                ↓
market-data scheduler / later historical-data consumers

Stable analytics + schemas + historical data
                ↓
Historical simulation branches
                ↓
Reporting and history branches
                ↓
AI agent
                ↓
API integration
                ↓
Deployment
```

The completed analytics-validation refactor supports the analytics branch
internally but does not change this dependency flow.

The completed schemas-contract branch remains in the flow as a stable
dependency for later services, APIs, reporting, simulations, and AI
integration. AnalysisService and the Portfolio API are complete, but their
presence does not imply that reporting, simulation, AI, or full integration
work exists.

---

# Recommended Current Work

The analytics, schema, database, historical market-data, AnalysisService, and
Portfolio API foundations are complete. The recommended next focused backend
workstream is:

```text
feat/backend-analysis-reporting
```

Analysis persistence infrastructure already exists, but reporting persistence
orchestration, service mapping, and API exposure remain unfinished. Simulation
requirements and contracts remain deferred, and market-data scheduling remains
a separate deferred workstream.

---

# Correct Git Branch Structure

All independent feature branches start from the latest `develop`.

```text
develop
├── feat/backend-analytics-core                # completed
├── refactor/analytics-validation              # completed support branch
├── feat/backend-schemas-contracts             # completed
├── feat/backend-market-data-pipeline          # completed
├── feat/backend-database-foundation            # completed
├── feat/backend-market-data-storage            # completed
├── feat/backend-analysis-service                # completed
├── feat/backend-portfolio-api                   # completed
└── feat/backend-quality-ci                     # optional
```

Do not create a permanent shared backend parent branch such as:

```text
develop
└── backend
    ├── analytics
    ├── schemas
    ├── database
    └── data-pipeline
```

The project plan calls them parent workstreams because they are independently
owned areas. In Git, each still branches directly from `develop`.

## Frontend branches use the same integration structure

```text
develop
├── feat/frontend-dashboard
├── feat/frontend-portfolio-management
├── feat/frontend-risk-report
└── feat/frontend-simulation
```

A permanent `frontend` or `backend` integration branch is unnecessary because
`develop` is the shared integration branch for the whole project.

---

# Commands Before Creating a New Branch

Update local `develop`:

```bash
git switch develop
git pull origin develop
git status
```

General branch creation:

```bash
git switch -c <branch-name>
git push -u origin <branch-name>
```

---

# Shared-File Rule

To reduce merge conflicts, feature contributors should avoid editing shared
integration files unless their branch explicitly owns the integration change.

Common shared files include:

```text
backend/app/main.py
backend/app/api/router.py
backend/app/services/
CURRENT_STATUS.md
```

Each parent branch should mainly modify its owned folder, tests, examples, and
branch-specific documentation.

After a feature branch is merged, project status documentation should be
updated from the latest `develop`, either directly according to team rules or
through a small documentation branch such as:

```text
docs/update-backend-status
```

Documentation changes should not be added to `main` directly.

---

# Recommended Development Order

## Completed Foundation, Analytics, Contracts, Market Data, Database, and Storage Stage

```text
✅ feat/fastapi-foundation
✅ feat/backend-analytics-core
✅ refactor/analytics-validation
✅ feat/backend-schemas-contracts
✅ feat/backend-market-data-pipeline
✅ feat/backend-database-foundation
✅ feat/backend-market-data-storage
```

## First Integration Stage

```text
✅ feat/backend-analysis-service
✅ feat/backend-portfolio-api
```

## Simulation and Reporting Stage

```text
feat/backend-analysis-reporting             # recommended next
feat/backend-historical-scenario-simulator  # requirements/contracts deferred
feat/backend-allocation-simulator           # requirements/contracts deferred
feat/backend-combined-simulator             # requirements/contracts deferred
feat/backend-simulation-history
feat/backend-market-data-scheduler          # scheduling deferred
```

## AI and Full Integration Stage

```text
feat/backend-ai-agent
feat/backend-api-integration
```

## Final Stage

```text
feat/backend-deployment
final backend integration tests
develop → main release Pull Request
```

---

# Current Recommended Next Step

With analytics, schemas, the market-data pipeline, the database foundation,
market-data storage, AnalysisService, and the Portfolio API merged into
`develop`, begin the recommended backend workstream:

```text
feat/backend-analysis-reporting
```

Analysis persistence infrastructure already exists, but reporting persistence
orchestration, service mapping, and API exposure remain unfinished. Simulation
requirements/contracts and automatic market-data scheduling remain deferred.
AI, full integration, frontend/backend integration, and deployment remain
governed by their listed unfinished dependencies.
