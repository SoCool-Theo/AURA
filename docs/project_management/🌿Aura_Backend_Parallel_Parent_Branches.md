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
| `feat/backend-analysis-reporting` | Integration feature | Completed and merged into `develop` | Save, retrieve, and expose immutable portfolio-analysis reports using the existing analysis service and PostgreSQL Analysis snapshot infrastructure |
| `feat/backend-authentication` | Integration feature | Completed and merged into `develop` | Bearer JWT authentication, credential persistence, and authenticated portfolio/report ownership boundaries |
| `feat/backend-historical-scenario-simulator` | Integration feature | Completed and merged into `develop` | Deterministic historical simulation of an owned saved portfolio against predefined market events |
| `feat/backend-allocation-simulator` | Integration feature | Completed and merged into `develop` | Compare saved and modified weights for the same owned portfolio over one arbitrary historical period |
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

- At this workstream's completion, `X-User-ID` was a temporary ownership
  selector that validated an existing `User`; the later authentication
  workstream removed it from production authentication.
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
persistence, mapping, orchestration, and exposure were completed later by the
reporting workstream documented below.

---

## 8. `feat/backend-analysis-reporting`

**Status:** Completed and merged into `develop`

### Purpose

Save, retrieve, and expose immutable portfolio-analysis reports using the
existing `AnalysisService` and PostgreSQL `Analysis` snapshot infrastructure.

### Completed Work

- Added module-level report response, summary, and list schemas without
  expanding the stable 21-name package-level schema export surface.
- Added pure validated snapshot/report mapping using
  `portfolio-analysis-response-v1`, including relational/snapshot analysis-date
  consistency checks.
- Added `AnalysisReportingService` coordination across owned portfolios,
  ordered holdings, the unchanged read-only `AnalysisService`, and the existing
  `AnalysisRepository`.
- Reused the existing `Analysis` model and JSONB persistence without a new
  migration or repository API expansion.
- Added report creation, deterministic history, and detail endpoints:
  - `POST /api/portfolios/{portfolio_id}/reports`
  - `GET /api/portfolios/{portfolio_id}/reports`
  - `GET /api/portfolios/{portfolio_id}/reports/{report_id}`
- POST reuses `AnalysisPeriod` and returns HTTP 201 after persistence; report
  GETs remain read-only.
- Preserved private ownership semantics, immutable saved snapshots, existing
  analytics values/order, and caller-owned transaction boundaries.
- Missing/wrong-owner portfolios return `Portfolio not found`, while
  missing/wrong-associated reports return `Report not found` without exposing
  resource ownership.
- Repositories and services do not commit, roll back, or close sessions;
  successful POST creation commits at the request boundary.
- At this workstream's completion, `X-User-ID` remained a temporary ownership
  selector; the later authentication workstream removed it from production
  authentication.

### Live PostgreSQL and Final Verification

Live tests covered the complete FastAPI-to-PostgreSQL reporting workflow, JSONB
snapshot validation, fresh-session retrieval, history ordering, ownership
isolation, failed-analysis rollback, saved-report immutability, date and
ordering consistency, and read-only GET behavior.

- Reporting schema tests: 23 passed
- Reporting mapper tests: 14 passed
- Reporting service tests: 13 passed
- Reporting API tests: 20 passed
- Reporting live PostgreSQL tests: 2 passed
- Service suite: 88 passed
- API integration suite: 66 passed
- Schema suite: 374 passed
- Analytics suite: 820 passed
- Full backend suite: 1,499 passed, 0 failed, 0 errors, 0 skipped
- Manual analytics engine, compilation, dependency, and Git diff checks: passed
- Existing warning: one non-blocking Starlette/httpx TestClient deprecation
  warning

### Branch Boundary

This workstream did not implement secure authentication, user registration,
simulations or simulation history, AI-agent behavior, PDF generation, report
sharing, frontend work, automatic market-data scheduling, or deployment.

---

## 9. `feat/backend-authentication`

**Status:** Completed and merged into `develop`

### Purpose

Add real Bearer authentication while preserving Aura's existing User ownership,
privacy, transaction, and lazy-initialization boundaries.

### Completed Work

- Extended the existing `User` persistence with canonical email and
  password-hash credentials while preserving credential-less legacy/internal
  users. PostgreSQL enforces unique canonical email and credential-pair
  integrity.
- Added a second reversible Alembic revision without rewriting the original
  database-foundation revision.
- Added Argon2 password hashing through `pwdlib`; plaintext passwords are never
  persisted, and generic/dummy verification avoids exposing unknown-account
  differences.
- Added 30-minute HS256 Bearer JWT access tokens using the authenticated User
  UUID as `sub`, with required `sub`, `iat`, and `exp` claims. The signing
  secret is environment/configuration driven and no usable secret is committed.
- Added `POST /api/auth/register`, `POST /api/auth/login`, and
  `GET /api/auth/me`. Duplicate canonical email returns `409`; invalid
  credentials and invalid or missing Bearer authentication return generic
  `401` responses through the Bearer boundary. Public User responses do not
  expose password hashes.
- Replaced production `X-User-ID` authentication across all portfolio and
  analysis-reporting APIs with Bearer authentication. The authenticated User
  UUID continues into existing service ownership checks.
- Preserved `404 Portfolio not found` for wrong-owner portfolios and existing
  report privacy behavior, without introducing private-resource disclosure
  through `403`.
- Repositories do not commit, roll back, or close caller sessions, and services
  do not own commits or rollbacks. Successful writes commit at the API/request
  boundary; failure rollback and cleanup remain request-boundary-owned.
  Current-user lookup remains read-only, initialization remains lazy, and
  `/api/health` remains public.

### Live PostgreSQL and Final Verification

End-to-end coverage included registration, canonical credential and Argon2 hash
persistence, login, JWT/Bearer authentication, `/api/auth/me`, authenticated
portfolio and report workflows, two-user ownership isolation, immutable report
snapshots, fresh-session persistence, and rejection of `X-User-ID` as
authentication.

- Live PostgreSQL integration tests: 27 passed
- Complete API tests: 94 passed
- Schema tests: 386 passed
- Analytics tests: 820 passed
- Full backend tests: 1,588 passed, 0 failed
- Manual analytics engine, Python compilation, dependency consistency,
  application import smoke, public health, and Git integrity/diff checks:
  passed
- Existing warning: one non-blocking Starlette/httpx TestClient deprecation
  warning; it is not an authentication defect

### Branch Boundary

This workstream did not implement email verification, password reset, refresh
tokens, logout/token revocation, OAuth/social login, MFA, RBAC/admin
authorization, frontend/mobile authentication integration, historical
simulations, AI-agent functionality, full backend integration, or deployment.

---

## 10. `feat/backend-historical-scenario-simulator`

**Status:** Completed and merged into `develop`

### Purpose

Answer this completed educational what-if question:

> **How would the user's current saved portfolio have behaved during a selected
> predefined historical market event?**

The simulator applies the user's saved/current portfolio allocation unchanged.
It is deterministic, does not forecast future prices, and does not provide
buy/sell recommendations.

### Initial Predefined Scenario Catalogue

- **COVID-19 Market Shock**
  - ID: `covid-19-shock-2020`
  - Requested period: `2020-02-01` through `2020-04-30`
- **2022 Inflation and Rate Shock**
  - ID: `inflation-rate-shock-2022`
  - Requested period: `2022-01-01` through `2022-12-31`

The catalogue is immutable, deterministic, code-owned, and not stored in
PostgreSQL. These are the only currently implemented scenarios.

### Completed Contracts and Calculation Behavior

- Added strict historical-simulation Pydantic contracts, imported directly from
  `backend.app.schemas.simulation` without expanding the stable 21-name
  package-level schema export contract.
- Preserved unknown-field rejection, finite public numerical values, negative
  maximum drawdown, and JSON `null` for intentionally undefined Sharpe ratios.
- Reused Aura's periodically rebalanced fixed-weight portfolio-return semantics;
  buy-and-hold/share-count behavior is not used.
- Kept the saved allocation unchanged and preserved ordered holdings, including
  zero-weight holdings.
- Required at least three aligned price observations and used the exact
  common-date intersection without forward-fill, backfill, interpolation,
  synthesized prices, or silently dropped holdings.
- Started normalized portfolio value at exactly `1.0` and returned a
  deterministic trajectory, cumulative return, annualized volatility, Sharpe
  ratio using existing analytics behavior, and signed maximum drawdown with
  existing peak/trough semantics.
- Preserved requested scenario dates separately from effective aligned dates.
  Recovery-time calculations remain deferred.

### Production Flow and Service Boundaries

```text
authenticated User
        ↓
owned Portfolio
        ↓
ordered Holdings
        ↓
predefined Historical Scenario
        ↓
MarketDataService / PostgreSQL
        ↓
exact common-date alignment
        ↓
pure historical simulator
        ↓
validated simulation response
```

Production simulation uses Aura's existing PostgreSQL-backed market-data and
service infrastructure. It does not read CSV files or call Yahoo Finance
directly, and no new external API key was required.

Ownership is checked through the existing portfolio boundary. Missing and
wrong-owner portfolios both return `404 Portfolio not found`. Services remain
caller-session based, and simulation is read-only: the service does not commit,
roll back, close the caller session, or persist results. The service
intentionally reuses AnalysisService's existing private exact-date alignment
seam rather than duplicating the algorithm. This accepted internal coupling is
protected by regression tests and is not a public API.

### Completed HTTP Surface

- `GET /api/simulations/historical-scenarios` publicly returns the deterministic
  catalogue without requiring authentication or database access merely to list
  definitions.
- `POST /api/portfolios/{portfolio_id}/simulations/historical-scenarios` uses
  existing Bearer authentication and runs the selected event against the
  authenticated user's owned portfolio. It remains read-only despite using
  POST and does not save simulation history.
- Missing/wrong-owner portfolio: `404 Portfolio not found`
- Unknown scenario: `404 Historical scenario not found`
- Expected missing/insufficient historical data: `422`
- Invalid/missing Bearer authentication: existing `401`
- Unexpected internal failure: `500 Unable to run historical scenario`
- `X-User-ID` is not accepted as authentication.

### Persistence and Deferred Boundaries

This workstream added no Simulation ORM model, Simulation repository, Alembic
migration, database schema change, JSONB simulation snapshot,
simulation-history persistence, or dependency change. Simulation history,
allocation simulation, and combined simulation were separate future
workstreams at this branch's completion; Allocation Simulation and Combined
Simulation have since been completed. Historical coverage expansion is planned
under
`feat/backend-market-data-historical-backfill`; the dependent educational event
expansion is planned under `feat/backend-historical-scenario-catalog`. Neither
future branch changes the completed simulator's calculations.

### Final Verification

- Historical scenario focused live PostgreSQL tests: 5 passed, 0 skipped
- Complete live PostgreSQL integration suite: 25 passed, 0 skipped
- Simulation API tests: 22 passed
- Complete API integration suite: 116 passed
- Historical scenario service tests: 21 passed
- Scenario tests: 35 passed
- Schema tests: 440 passed
- Analytics tests: 820 passed
- Full backend suite: 1,725 passed, 0 failed, 0 skipped
- Manual analytics engine, Python compilation, dependency consistency,
  application import, public health, and Git diff/whitespace/scope checks:
  passed
- Existing warning: one non-blocking Starlette TestClient/httpx deprecation
  warning; it is not a historical-simulator defect

---

## 11. `feat/backend-allocation-simulator`

**Status:** Completed and merged into `develop`

### Purpose

Implement Aura's Allocation Change mode, which answers:

> **How would different weights for the same saved portfolio assets have
> changed the portfolio's historical behavior over an arbitrary historical
> period?**

This mode is separate from the completed Historical Scenario and Combined
Simulation modes.

### Completed Contracts and Ordering Behavior

- Added strict request, result, comparison, and response contracts imported
  directly from `backend.app.schemas.simulation` without expanding the stable
  package-level schema export contract.
- Allowed modified weights over an arbitrary requested start/end period without
  accepting a predefined scenario ID.
- Required the complete normalized modified symbol set to match the saved
  portfolio exactly. Request order may differ; service output is canonicalized
  to saved holding order.
- Preserved existing symbol normalization, duplicate rejection, `[0, 1]` weight
  bounds, total-weight tolerance, zero-weight behavior, strict unknown-field
  rejection, finite-number behavior, and input non-mutation.

### Pure Comparison and Historical Data

Allocation comparison uses one already-aligned historical price frame and runs
the existing historical simulator once for the original saved weights and once
for the modified weights. It does not duplicate portfolio returns, normalized
trajectory, cumulative return, annualized volatility, Sharpe ratio, or maximum
drawdown formulas. Both calculations share the same prices, effective dates,
fixed-weight / periodically rebalanced semantics, and existing analytics
behavior.

Comparison deltas are `modified - original` for normalized ending value,
cumulative return, annualized volatility, Sharpe ratio when both values exist,
and maximum drawdown. If either Sharpe ratio is undefined, the Sharpe delta is
JSON `null`. Existing signed negative maximum-drawdown behavior is preserved.

Production data comes through the PostgreSQL-backed `MarketDataService`.
Alignment remains the exact common-date intersection across all saved holdings,
with no forward fill, backfill, interpolation, synthesized prices, or silently
dropped holdings. Saved order is preserved, zero-weight holdings still require
historical data, and requested dates remain separate from effective aligned
dates.

### Completed Production Flow

```text
Bearer-authenticated User
        ↓
owned Portfolio
        ↓
ordered saved Holdings
        ↓
exact modified symbol-set validation
        ↓
saved-order canonicalization
        ↓
one PostgreSQL historical-data retrieval
        ↓
one exact common-date alignment
        ↓
pure original-versus-modified comparison
        ↓
validated AllocationSimulationResponse
```

`AllocationSimulationService` reuses existing portfolio ownership, market-data,
and exact-date alignment infrastructure. It is caller-session based and
read-only: it does not commit, roll back, close the caller-owned session,
persist a simulation, or persist an Analysis snapshot.

### Completed HTTP Surface and Privacy

- `POST /api/portfolios/{portfolio_id}/simulations/allocations` uses existing
  Bearer authentication and returns `200` for success.
- Missing or invalid Bearer authentication returns the existing `401`;
  `X-User-ID` is not accepted as authentication.
- Missing and wrong-owner portfolios are client-indistinguishable as
  `404 Portfolio not found`, never `403`.
- Expected allocation or historical-data failures return `422`.
- Unexpected failures return
  `500 Unable to run allocation simulation` without exposing internal details.
- The POST remains read-only and creates no simulation history.

### Persistence and Deferred Boundaries

This workstream added no Simulation ORM model, Simulation repository, Alembic
migration, simulation snapshot/history persistence, or dependency change.
Combined Simulation was completed later as a separate workstream. Simulation
history remains unfinished. Historical backfill and the dependent
scenario-catalog expansion remain later workstreams and were not prerequisites
for Allocation Simulation.

### Final Verification

- Dedicated live PostgreSQL coverage verified authenticated success,
  saved-order canonicalization, reordered modified input, zero-weight behavior,
  ownership privacy, authentication, expected data failures, and read-only
  persistence through fresh sessions.
- Live PostgreSQL integration suite: 29 passed
- Full backend suite: 1,828 passed, 0 failed, 0 errors, 0 skipped
- Manual analytics engine, Python compilation, import/application smoke,
  public health, dependency consistency, schema export compatibility, and Git
  diff/whitespace checks: passed
- Existing warning: one non-blocking Starlette TestClient/httpx deprecation
  warning; it is not an Allocation Simulator defect

---

## 12. `feat/backend-combined-simulator`

**Status:** Completed and merged into `develop`

### Purpose

Compare the user's original saved portfolio allocation and a modified
allocation during the same predefined historical event.

Combined Simulation completes Aura's three core Historical What-If Simulator
modes. It is a thin composition over the existing immutable Historical
Scenario catalogue and the completed Allocation Simulation workflow, with no
new financial formulas.

### Completed Composition and Data Behavior

- Added strict Combined request and response contracts directly importable
  from `backend.app.schemas.simulation` without expanding the stable 21-name
  package-level schema export surface.
- Resolves the selected predefined scenario and uses its requested start and
  end dates to create one existing `AllocationSimulationRequest`.
- Delegates to `AllocationSimulationService`, preserving its complete saved
  symbol-set validation, symbol normalization, weight rules, and saved-order
  canonicalization.
- Uses one PostgreSQL historical-data retrieval and one exact common-date
  alignment path for both the original and modified allocations.
- Preserves all saved holdings during alignment. Zero-weight modified holdings
  remain supported and still require historical data.
- Keeps requested scenario dates separate from effective aligned dates.

The delegated workflow preserves fixed-weight / periodically rebalanced
semantics, normalized starting value, cumulative return, annualized volatility,
Sharpe ratio, signed maximum drawdown, peak/trough behavior, and
`modified - original` comparison deltas. Nullable Sharpe ratios and nullable
Sharpe deltas remain JSON `null` when either side is undefined.

### Completed Production Flow

```text
Bearer-authenticated User
        ↓
owned Portfolio and ordered Holdings
        ↓
immutable Historical Scenario and requested dates
        ↓
CombinedSimulationService
        ↓
AllocationSimulationService
        ↓
one PostgreSQL retrieval and exact common-date alignment
        ↓
existing original-versus-modified simulator
        ↓
validated CombinedSimulationResponse
```

### Completed HTTP Surface and Privacy

- `POST /api/portfolios/{portfolio_id}/simulations/combined` returns `200` for
  a successful simulation and uses existing Bearer authentication.
- Missing or invalid Bearer authentication returns the existing `401`;
  `X-User-ID` is not accepted as authentication.
- Missing and wrong-owner portfolios remain client-indistinguishable as
  `404 Portfolio not found`, never `403`.
- Unknown scenarios return `404 Historical scenario not found`.
- Expected allocation, data, or simulation failures return the established
  `422`.
- Unexpected failures return the sanitized
  `500 Unable to run combined simulation` response.

### Read-Only Persistence and Dependency Boundary

Combined Simulation added no Simulation ORM model, Simulation repository,
Alembic migration, database schema change, simulation-history persistence,
Analysis snapshot persistence, or new dependency. It does not commit, roll
back, or close the caller-owned session. Simulation history remains a separate
unfinished workstream.

### Final Verification

- Combined schema tests: 26 passed
- Combined service tests: 11 passed
- Combined API tests: 16 passed
- Combined live PostgreSQL tests: 4 passed
- Service suite: 149 passed
- API suite: 144 passed
- Schema suite: 513 passed
- Analytics suite: 820 passed
- Live PostgreSQL suite: 33 passed, 0 skipped
- Full backend suite: 1,886 passed, 0 failed, 0 errors, 0 skipped
- Manual analytics engine, Python compilation, direct imports, application
  import, public health, OpenAPI route, dependency consistency, and Git
  diff/whitespace/scope checks: passed
- Stable package-level schema exports: exactly 21 approved names
- Existing warning: one non-blocking Starlette TestClient/httpx deprecation
  warning; it is not a Combined Simulation defect

---

## 13. Optional: `feat/backend-quality-ci`

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
| `feat/backend-analysis-reporting` | Save, retrieve, and expose immutable portfolio-analysis reports | Analytics + schemas + database + analysis service + portfolio API | Completed and merged into `develop` |
| `feat/backend-authentication` | Authenticate protected portfolio/report APIs with Bearer JWT access tokens | Existing user ownership + portfolio/report APIs | Completed and merged into `develop` |
| `feat/backend-historical-scenario-simulator` | Test the current saved portfolio during a selected predefined past event | Analytics + PostgreSQL historical data + simulation schemas + portfolio ownership | Completed and merged into `develop` |
| `feat/backend-allocation-simulator` | Compare original and modified allocations over the same period | Completed Historical Scenario Simulator + portfolio/market-data infrastructure | Completed and merged into `develop` |
| `feat/backend-combined-simulator` | Compare original and modified allocations during one event | Completed Historical Scenario Simulator + completed Allocation Simulator | Completed and merged into `develop` |
| `feat/backend-simulation-history` | Save and retrieve simulation results | Completed simulators + schemas + database | Recommended next backend simulation workstream; dependencies satisfied |
| `feat/backend-market-data-historical-backfill` | Extend verified historical market-data coverage toward year 2000 | Completed market-data pipeline + storage/PostgreSQL infrastructure | Planned/deferred; not required for the completed simulators or next simulation-history branch |
| `feat/backend-historical-scenario-catalog` | Expand the predefined educational historical-event catalogue | Historical-simulation foundation + verified historical backfill/coverage | Planned/deferred; should begin after the historical backfill |
| `feat/backend-market-data-scheduler` | Automate market-data updates | Data pipeline + database/storage | Prerequisites are complete; automatic scheduling remains unimplemented and deferred |
| `feat/backend-ai-agent` | Explain stable analysis and simulation results | Stable reports and simulations + schemas + database | Planned later; reporting and all three core simulator modes are complete, but AI requirements remain unfinished |
| `feat/backend-api-integration` | Connect routes, services, schemas, repositories, and agent | Completed feature branches | Not ready; simulation history, AI, and other integration work remain incomplete |
| `feat/backend-deployment` | Containerization and deployment | Stable backend integration | Not ready |

---

# Recommended Simulation Order

Aura's Historical What-If Simulator contains three completed modes in this
development order:

```text
✅ Historical Scenario
        ↓
✅ Allocation Change
        ↓
✅ Combined Simulation
```

## Historical Scenario

Answers:

> **How would the user's current saved portfolio have behaved during a selected
> predefined historical market event?**

This mode is completed and uses the saved allocation unchanged.

## Allocation Change

Answers:

> How would different asset percentages change the portfolio's historical risk?

This mode is completed. It compares saved and modified weights for the same
complete asset set over one arbitrary historical period and canonicalizes both
results to saved holding order.

## Combined Simulation

Answers:

> How would the original and modified allocations compare during the same
> historical event?

This mode is completed. It resolves one predefined scenario and delegates its
requested dates and the modified allocation to the existing Allocation
Simulation workflow without duplicating simulation logic.

---

# Planned Historical Coverage and Catalogue Expansion

These planned branches are deferred future work. They are not implemented and
do not block the recommended next backend simulation workstream,
`feat/backend-simulation-history`.

## `feat/backend-market-data-historical-backfill`

**Status:** Planned/deferred

Extend Aura's verified historical market-data coverage farther back toward
approximately year 2000 so older educational scenarios can later be simulated
where asset data permits. This does not mean every current Aura symbol has data
back to 2000, and the current production dataset is not documented as beginning
in 2000.

The workstream is limited to historical-data coverage expansion. It does not
change the completed Historical Scenario, Allocation Simulation, or Combined
Simulation behavior, and it does not implement simulation history, AI behavior,
frontend work, forecasting, or automatic scheduling unless separately
approved.

Expected future verification includes provider availability, actual supported
asset coverage, cleaning and validation, PostgreSQL backfill/upsert behavior,
batching, duplicate safety, partial-history assets, analytics/simulation
regression, and live PostgreSQL checks. None of that verification is recorded as
completed yet.

## `feat/backend-historical-scenario-catalog`

**Status:** Planned/deferred after historical backfill

Expand Aura's predefined educational historical-event catalogue after the
historical-data backfill and supported coverage are verified. The future
catalogue may include market crash/stress, high-volatility, and normal/growth
periods without changing the completed simulator calculations.

The exact event list and dates are intentionally not defined here. This future
workstream may introduce a dedicated historical-events Markdown reference when
it begins; no such document is created or named by this update.

```text
feat/backend-market-data-historical-backfill
                ↓ verified historical coverage
feat/backend-historical-scenario-catalog
```

The completed Historical Scenario Simulator does not depend on either future
expansion branch.

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

AnalysisService + Portfolio API + Analysis persistence
                ↓
✅ feat/backend-analysis-reporting
                ↓
✅ feat/backend-authentication
                ↓
✅ feat/backend-historical-scenario-simulator
                ↓
✅ feat/backend-allocation-simulator
                ↓
✅ feat/backend-combined-simulator
                ↓
feat/backend-simulation-history
                ↓
feat/backend-market-data-historical-backfill
                ↓
feat/backend-historical-scenario-catalog
                ↓
AI agent
                ↓
full backend API integration
                ↓
deployment
```

The completed analytics-validation refactor supports the analytics branch
internally but does not change this dependency flow.

The completed schemas-contract branch remains in the flow as a stable
dependency for later services, APIs, reporting, simulations, and AI
integration. AnalysisService, the Portfolio API, analysis reporting,
authentication, and all three core simulator modes are complete. Simulation
history is the recommended next backend simulation workstream; AI behavior and
full integration remain separate unfinished workstreams. The historical
backfill and dependent scenario-catalog expansion are planned later and do not
block simulation history.

---

# Recommended Current Work

The analytics, schema, database, historical market-data, AnalysisService,
Portfolio API, analysis-reporting, authentication, Historical Scenario,
Allocation Simulator, and Combined Simulator workstreams are complete. The
recommended next backend simulation workstream is:

```text
feat/backend-simulation-history
```

The completed simulator modes, schemas, and database satisfy simulation
history's current readiness boundary. Historical market-data backfill, the
dependent scenario-catalog expansion, and market-data scheduling remain
separate deferred workstreams.

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
├── feat/backend-analysis-reporting               # completed
├── feat/backend-authentication                   # completed
├── feat/backend-historical-scenario-simulator    # completed
├── feat/backend-allocation-simulator             # completed
├── feat/backend-combined-simulator               # completed
├── feat/backend-simulation-history               # recommended next
├── feat/backend-market-data-historical-backfill  # planned/deferred
├── feat/backend-historical-scenario-catalog      # planned after backfill
└── feat/backend-quality-ci                       # optional
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

## Reporting and Identity Stage

```text
✅ feat/backend-analysis-reporting
✅ feat/backend-authentication
```

## Simulation Stage

```text
✅ feat/backend-historical-scenario-simulator  # completed
✅ feat/backend-allocation-simulator           # completed
✅ feat/backend-combined-simulator              # completed
feat/backend-simulation-history                # recommended next
feat/backend-market-data-historical-backfill  # planned/deferred
feat/backend-historical-scenario-catalog      # planned after backfill
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
market-data storage, AnalysisService, the Portfolio API, analysis reporting,
authentication, and all three core simulator modes merged into `develop`, the
recommended next backend simulation workstream is:

```text
feat/backend-simulation-history
```

Do not treat simulation history, `feat/backend-market-data-historical-backfill`,
`feat/backend-historical-scenario-catalog`, automatic market-data scheduling,
AI, full integration, frontend/mobile integration, or deployment as completed.
The backfill must precede catalogue expansion; both remain separate from the
recommended simulation-history workstream.
