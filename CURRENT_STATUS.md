### Analytics Validation Refactor

**Status:** Completed and merged into `develop`  
**Branch:** `refactor/analytics-validation`

Consolidated repeated analytics input-validation logic into a shared private
validation module while preserving all existing analytics behavior.

#### Shared validation helpers added

- Datetime-index validation
- Positive-integer validation
- Finite real-value validation and normalization
- Portfolio weight-mapping validation

#### Modules migrated

- `returns.py`
- `volatility.py`
- `drawdown.py`
- `sharpe.py`
- `correlation.py`
- `concentration.py`
- `diversification.py`
- `risk_driver.py`

#### Validation boundaries preserved

Specialized validation remains local where behavior intentionally differs,
including:

- Sharpe zero-volatility handling
- Return lower-bound rules
- Portfolio-weight alignment
- Correlation-matrix NaN behavior
- Diversification coverage rules
- Risk-classification thresholds
- Drawdown calculation conventions
- Analytics-engine consistency checks

#### Compatibility preserved

The refactor did not change:

- Public analytics APIs
- Public function signatures
- Analytics formulas
- Result dataclasses or returned structures
- Exception behavior
- Validation order
- Input non-mutation behavior
- Correlation NaN behavior
- Risk-driver ranking behavior

#### Final verification

- Shared validation tests: 116 passed
- Analytics tests: 820 passed
- Full backend tests: 821 passed
- Failed tests: 0
- Manual engine check: passed
- Dependency check: passed
- Public analytics import check: passed
- Python compilation check: passed
- Git whitespace check: passed

## Backend Schemas and Contracts

**Status:** Completed and merged into `develop`  
**Source branch:** `feat/backend-schemas-contracts`

### Completed scope

- Added shared Pydantic schema conventions.
- Added `AuraBaseModel` as an internal schema foundation with unknown-field
  rejection.
- Added normalized `AssetSymbol`.
- Added inclusive `AnalysisPeriod`.
- Added weight-based `PortfolioHoldingInput`.
- Added `PortfolioAnalysisRequest`.
- Added prepared historical market-data request and response contracts.
- Added atomic analytics-result contracts.
- Added complete `PortfolioAnalysisResponse`.
- Added exactly 21 approved package-level public schema exports.
- Added four validated synthetic canonical JSON examples.
- Added API-contract documentation.
- Added direct schema, example, and public-export tests.

### Important contract behavior

- Uses Pydantic 2-compatible models.
- Rejects unknown fields.
- Uses decimal portfolio weights.
- Requires portfolio weights to total `1.0`.
- Normalizes symbols by trimming and uppercasing.
- Uses inclusive date ranges.
- Preserves caller-owned input objects.
- Preserves ordered collections.
- Preserves negative maximum drawdown.
- Preserves signed risk contributions.
- Represents intentionally unavailable values as JSON `null`.
- Prevents Pandas, NumPy, `NaN`, and Infinity from leaking into the public JSON
  contract.
- Remains provider-independent and database-independent.

### Final verification

- Schema tests: 301 passed
- Canonical example tests: 4 passed
- Public-export tests: 5 passed
- Analytics regression tests: 820 passed
- Full backend tests: 1,122 passed
- Failed tests: 0
- Skipped tests: 0
- Existing warnings: 1 Starlette/httpx deprecation warning
- Public schema import check: passed
- Approved public exports: exactly 21
- Strict JSON validation: passed for all four canonical examples
- Manual analytics engine check: passed
- Python compilation check: passed
- Dependency check: passed
- Dependency versions changed: none
- Documentation consistency check: passed
- Git whitespace check: passed

### Branch boundary at completion

The schemas-contract branch itself did not implement:

- FastAPI routes
- Service orchestration
- Production conversion from `PortfolioAnalyticsResult`
- Pandas and NumPy adapter logic
- Market-data provider integration
- Market-data fetching and cleaning
- Database persistence
- Portfolio CRUD
- Amount/share-to-weight conversion
- Historical-simulation contracts and calculations
- AI-agent contracts and explanations

## Historical Market Data Pipeline

**Status:** Completed and merged into `develop`

**Source branch:** `feat/backend-market-data-pipeline`

### Completed scope

- Added a market-data provider interface and a Yahoo Finance implementation
  using `yfinance==1.5.1`.
- Added historical price fetching for a default set of 17 stock, ETF, bond,
  metal, and cryptocurrency symbols.
- Preserved Aura's inclusive requested date ranges when calling the provider.
- Added cleaning and normalization to the canonical columns `date`, `symbol`,
  `adjusted_close`, `volume`, and `source`.
- Added validation for dates, symbols, prices, volume, duplicates, and
  per-symbol ordering.
- Added missing-value handling and partial provider-failure reporting.
- Added atomic raw and processed CSV persistence under `data/`.
- Excluded generated market-data files from Git while retaining their
  directories.
- Added the `update_market_data()` workflow and a manual update CLI in
  `backend/scripts/update_market_data.py`.
- Added deterministic unit tests with mocked provider responses.

### Current update behavior and boundaries

- Updates are live on demand through manual invocation; no automatic
  background schedule is implemented.
- Each run replaces the requested historical CSV dataset; incremental append
  or update optimization is not implemented.
- This branch does not persist production records in PostgreSQL.
- This branch does not implement FastAPI routes, service orchestration,
  portfolio analytics, or historical simulations.
- The automated provider tests mock Yahoo Finance network responses; no live
  Yahoo Finance network smoke-test result is recorded.

### Final verification

- Focused market-data pipeline tests: 23 passed
- Full backend tests: 1,145 passed
- Dependency check: passed
- Git whitespace check: passed
- Working tree: clean
- Existing warning: 1 Starlette/httpx deprecation warning

## Backend Database Foundation

**Status:** Completed and merged into `develop`
**Source branch:** `feat/backend-database-foundation`

### Completed scope

- Added PostgreSQL configuration with SQLAlchemy 2.x and Psycopg 3.
- Added explicit, lazy engine creation and caller-controlled synchronous
  sessions and transactions.
- Added Alembic migration infrastructure and one initial PostgreSQL schema
  migration.
- Added `User`, `Portfolio`, `Holding`, `MarketData`, and `Analysis` ORM models.
- Added `PortfolioRepository`, `MarketDataRepository`, and
  `AnalysisRepository`.
- Added isolated live PostgreSQL migration and repository integration tests.

### Stable persistence boundaries

- User-owned domain resources use UUID identifiers.
- Holdings persist ordered portfolio weights; shares and invested amounts
  remain deferred.
- Total Holding weight is validated transactionally at repository level.
- MarketData uses `(symbol, date)` identity and persists the existing normalized
  market-data shape.
- Analysis reports use relational metadata plus an immutable JSONB snapshot.
- Repositories use caller-owned sessions and do not automatically commit or
  roll back transactions.
- PostgreSQL owns configured ownership cascades, and Alembic owns schema
  migrations.

### Final verification

- PostgreSQL version: 18.4
- Database unit tests: 93 passed
- Live PostgreSQL integration tests: 5 passed, 0 skipped
- Schema tests: 301 passed
- Market-data pipeline tests: 23 passed
- Analytics tests: 820 passed
- Full backend tests: 1,243 passed, 0 failed, 0 skipped
- Live Alembic upgrade, repository integration, and downgrade: passed
- Compilation, dependency, and Git diff checks: passed
- Existing warning: 1 unrelated Starlette/httpx deprecation warning

### Branch boundary at completion

The database-foundation branch itself did not implement:

- Market-data pipeline-to-PostgreSQL integration
- Portfolio API routes
- Analysis and reporting services
- Historical simulations and simulation history
- Automatic market-data scheduling
- AI conversation persistence
- Full backend API integration

## Market-Data Storage Integration

**Status:** Completed and merged into `develop`
**Source branch:** `feat/backend-market-data-storage`

### Completed scope

- Added pure canonical DataFrame-to-repository mapping with `pd.Timestamp` to
  Python `date`, adjusted close to explicitly quantized 12-place `Decimal`
  using `ROUND_HALF_UP`, nullable volume to `None`, and preserved symbol,
  source, row order, and caller-owned input data.
- Added `MarketDataService` using a caller-owned SQLAlchemy session, the
  existing `MarketDataRepository`, 1,000-record write batches, and inclusive,
  deterministic historical range retrieval.
- Added a manual processed-CSV historical seed/backfill workflow that reuses
  existing market-data validation and commits once at the outer script boundary.
- Added a private updater handoff for the already-cleaned and validated
  DataFrame while preserving the public
  `update_market_data(...) -> MarketDataUpdateResult` contract.
- Preserved the updater's default CSV-only behavior and added explicit
  `--persist-database` PostgreSQL persistence after successful processing.
- Preserved caller-controlled commit and rollback behavior across service and
  repository batches.

### Stable integration boundaries

- The market-data pipeline remains responsible for fetch, clean, validate, and
  local CSV persistence.
- CSV and PostgreSQL persistence remain separate transactions by design.
- The full processed historical dataset was not automatically seeded into
  PostgreSQL during verification.
- The existing processed dataset was confirmed to exist and validate with
  69,449 rows across 17 symbols.
- Analysis-service orchestration is owned by the completed separate workstream
  documented below.
- Automatic scheduling, APIs, reporting, simulations, AI behavior, frontend
  integration, and deployment remain separate workstreams.

### Final verification

- PostgreSQL version: 18.4
- Market-data service tests: 15 passed
- Market-data pipeline tests: 27 passed
- Script tests: 16 passed
- Database unit and repository tests: 93 passed
- Live PostgreSQL integration tests: 11 passed, 0 skipped
- Schema tests: 301 passed
- Analytics tests: 820 passed
- Full backend tests: 1,284 passed, 0 skipped
- Live coverage included persistence/retrieval, inclusive ordering, nullable
  volume, Decimal/Numeric persistence, repeat upserts, existing-row updates,
  1,001-row batching, caller commit/rollback, processed-CSV seeding, and updater
  `--persist-database` persistence.
- Compilation, dependency, and Git diff checks: passed

## Backend Analysis Service

**Status:** Completed and merged into `develop`
**Source branch:** `feat/backend-analysis-service`

### Completed scope

- Added a pure adapter from database `MarketData` records to the analytics
  price frame, preserving requested symbol order and converting adjusted-close
  `Decimal` values to analytics floats.
- Uses the exact common-date intersection across all requested assets without
  forward-fill, backfill, interpolation, or synthesized prices.
- Added explicit missing-symbol validation in requested-symbol order.
- Added a pure `PortfolioAnalyticsResult` to `PortfolioAnalysisResponse`
  mapper that preserves negative maximum drawdown, signed risk contributions,
  and risk-driver, asset, correlation, and portfolio-return ordering.
- Converts only intentionally unavailable analytics values, including
  legitimately undefined Sharpe ratios and correlations, to schema `null`.
- Added production `AnalysisService` orchestration from a validated
  `PortfolioAnalysisRequest` through PostgreSQL historical data and the
  existing analytics engine to a validated `PortfolioAnalysisResponse`.

### Stable service boundaries

```text
PortfolioAnalysisRequest
        ↓
AnalysisService
        ↓
MarketDataService → MarketDataRepository → PostgreSQL
        ↓
analytics input adapter → analyze_portfolio(...)
        ↓
PortfolioAnalyticsResult → response mapper
        ↓
PortfolioAnalysisResponse
```

- Historical data retrieval remains owned by `MarketDataService`; the analysis
  service does not fetch or update market data.
- The caller owns the SQLAlchemy session and transaction. The service does not
  commit, roll back, or close the session.
- The service reuses `analyze_portfolio(...)` with its existing defaults and
  does not duplicate or alter analytics formulas.
- Analysis execution is read-only and does not persist an `Analysis` snapshot
  or report.

### Final verification

- AnalysisService unit tests: 25 passed
- Analytics tests: 820 passed
- Schema tests: 301 passed
- MarketDataService tests: 15 passed
- Database unit tests: 93 passed
- Live PostgreSQL integration tests: 13 passed, 0 skipped
- Full backend tests: 1,311 passed, 0 failed, 0 errors, 0 skipped
- Python compilation, dependency check, direct import smoke check, and Git
  integrity/whitespace checks: passed
- Existing warning: 1 unrelated Starlette/httpx deprecation warning

Live PostgreSQL coverage verified successful multi-asset analysis, inclusive
date bounds, requested ordering despite repository ordering, exact common-date
intersection, missing-symbol behavior, caller-owned session/transaction
behavior, and no `Analysis` snapshot creation. Verification used focused test
records and did not require permanently seeding the full historical CSV.

### Deferred work

- FastAPI portfolio-analysis routes; portfolio CRUD APIs were completed later
  by the separate `feat/backend-portfolio-api` workstream documented below
- Persistent analysis reports and report-history retrieval were completed later
  by the separate `feat/backend-analysis-reporting` workstream documented below
- Historical, allocation, and combined simulations and simulation history
- Automatic market-data scheduling
- AI-agent behavior
- Full backend API integration, frontend/backend integration, and deployment

## Backend Portfolio API

**Status:** Completed and merged into `develop`
**Source branch:** `feat/backend-portfolio-api`

### Completed scope

- Added CRUD-oriented contracts for portfolio creation, rename/update, holdings
  replacement, duplication, complete responses, holding responses, summaries,
  and list responses. The existing 21-name package-level schema export contract
  remains unchanged; simulation schemas were not added.
- Added `PortfolioService` coordination for create, get, list, rename, holdings
  replacement, duplicate, and delete. ID-based operations enforce ownership at
  the service boundary.
- Added frontend-neutral REST endpoints usable by web and mobile clients:
  `POST /api/portfolios`, `GET /api/portfolios`,
  `GET /api/portfolios/{portfolio_id}`,
  `PATCH /api/portfolios/{portfolio_id}`,
  `PUT /api/portfolios/{portfolio_id}/holdings`,
  `POST /api/portfolios/{portfolio_id}/duplicate`, and
  `DELETE /api/portfolios/{portfolio_id}`.
- Preserved UUID ownership and ordered symbol/weight holdings. Replacement,
  duplication with new portfolio and holding identities, and deletion are
  supported. Shares, invested amounts, and current values are not persisted.

### Ownership and transaction boundaries

- At this workstream's completion, `X-User-ID` was a temporary ownership
  selector that validated the supplied UUID against an existing `User`; the
  later authentication workstream removed it from production authentication.
- Portfolio access remains owner-scoped, and missing and wrong-owner portfolio
  IDs produce the same client-visible `404`.
- `PortfolioRepository` and `PortfolioService` remain commit/rollback-free,
  and the service does not close sessions. Successful writes commit at the API
  boundary; failure rollback and request-scoped cleanup remain owned by the
  database dependency.
- Database engine/session setup remains lazy, so application import and health
  checks do not require portfolio data or a live PostgreSQL connection.

### Final synchronized verification

- Portfolio API integration tests: 42 passed
- PortfolioService tests: 21 passed
- Portfolio schema tests: 84 passed
- Complete schema suite: 351 passed
- PortfolioRepository tests: 17 passed
- AnalysisService tests: 25 passed
- Analytics tests: 820 passed
- Live PostgreSQL integration: 16 passed, 0 skipped
- Full backend: 1,427 passed, 0 failed, 0 errors, 0 skipped
- Compilation, dependency, import, health, and API-surface checks: passed
- Existing warning: 1 Starlette TestClient/httpx deprecation warning

Live portfolio coverage exercised the real FastAPI → request dependency →
PortfolioService → PortfolioRepository → PostgreSQL path, including CRUD,
ordered holding persistence, duplication, ownership isolation, fresh-session
persistence, and existing-user validation.

### Branch boundary at completion

The Portfolio API workstream did not implement secure authentication,
JWT/login/user registration, a portfolio-analysis HTTP endpoint, report
persistence/history, simulations or simulation history, automatic market-data
scheduling, AI-agent behavior, full backend API integration, frontend work, or
deployment. Analysis execution was subsequently exposed through the completed
reporting workstream documented below.

## Backend Analysis Reporting

**Status:** Completed and merged into `develop`
**Source branch:** `feat/backend-analysis-reporting`

### Completed scope

- Added module-level `PortfolioReportResponse`, `PortfolioReportSummary`, and
  `PortfolioReportListResponse` contracts while retaining
  `PortfolioAnalysisResponse` as the canonical nested analytics result. The
  stable 21-name package-level schema export surface was not expanded.
- Added pure mapping from validated analysis responses to JSON-safe snapshots
  and from persisted `Analysis` records to report summaries and validated full
  reports.
- Added `AnalysisReportingService` orchestration across owned persisted
  portfolios, ordered holdings, the existing read-only `AnalysisService`,
  snapshot serialization, and the existing `AnalysisRepository`.
- Reused the existing PostgreSQL `Analysis` model and repository without a new
  migration or reporting-specific repository expansion.
- Added `POST /api/portfolios/{portfolio_id}/reports`,
  `GET /api/portfolios/{portfolio_id}/reports`, and
  `GET /api/portfolios/{portfolio_id}/reports/{report_id}`.
- POST reuses `AnalysisPeriod` and returns HTTP 201 after persistence. History
  preserves the existing deterministic repository ordering.

### Snapshot, ownership, and transaction boundaries

- Persisted JSONB snapshots use `portfolio-analysis-response-v1` and are
  validated back through `PortfolioAnalysisResponse` during retrieval.
- Relational start/end dates must match the validated snapshot. Negative
  drawdowns, signed risk contributions, intentional nulls, numeric behavior,
  and collection ordering remain preserved.
- Saved reports are immutable application-level snapshots; later portfolio
  edits do not change an existing report.
- At this workstream's completion, `X-User-ID` remained a temporary trusted
  ownership selector. The later authentication workstream removed it from
  production authentication. Missing/wrong-owner portfolios return
  `Portfolio not found`, while missing/wrong-associated reports return
  `Report not found` without exposing ownership information.
- Repositories and services do not commit, roll back, or close sessions.
  Successful report creation commits at the request/API boundary, GET report
  operations are read-only, and failed analysis leaves no partial report.

### Live PostgreSQL verification

Live verification exercised the complete FastAPI → reporting service →
AnalysisService → market-data service → PostgreSQL market data → analytics →
AnalysisRepository → PostgreSQL snapshot flow. Coverage included real report
persistence, validated JSONB snapshots, fresh-session detail retrieval,
deterministic history ordering, ownership isolation, failed-analysis rollback,
saved-report immutability after portfolio edits, relational/snapshot date
consistency, ordering preservation, and read-only GET behavior.

### Final verification

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
- Manual analytics engine, Python compilation, dependency, and Git diff checks:
  passed
- Existing warning: 1 non-blocking Starlette/httpx TestClient deprecation
  warning

### Branch boundary at completion

Analysis reporting did not implement authentication/JWT/login, user
registration, historical/allocation/combined simulations, simulation history,
AI-agent behavior, PDF generation, report sharing, frontend work, automatic
market-data scheduling, or deployment.

## Backend Authentication

**Status:** Completed and merged into `develop`
**Source branch:** `feat/backend-authentication`

### Completed scope

- Extended the existing `User` persistence with canonical email and
  password-hash credentials while preserving credential-less legacy/internal
  users. PostgreSQL enforces unique canonical email and credential-pair
  integrity.
- Added a second reversible Alembic revision without rewriting the original
  database-foundation revision.
- Added Argon2 password hashing through `pwdlib`; plaintext passwords are never
  persisted, and generic/dummy verification avoids exposing unknown-account
  differences.
- Added Bearer JWT access tokens using the authenticated User UUID as `sub`,
  with required `sub`, `iat`, and `exp` claims, 30-minute expiry, and HS256.
  The signing secret is environment/configuration driven and no usable secret
  is committed.
- Added `POST /api/auth/register`, `POST /api/auth/login`, and
  `GET /api/auth/me`. Duplicate canonical email returns `409`; invalid
  credentials and invalid or missing Bearer authentication return generic
  `401` responses through the Bearer boundary. Public User responses never
  expose password hashes.
- Migrated all portfolio and analysis-reporting APIs from the former trusted
  `X-User-ID` header to Bearer authentication. Production `X-User-ID`
  authentication was removed.

### Ownership, transaction, and application boundaries

- The authenticated User UUID continues into the existing service ownership
  checks. Wrong-owner portfolios remain `404 Portfolio not found`; report
  privacy behavior remains unchanged, with no private-resource disclosure
  through `403`.
- Repositories do not commit, roll back, or close caller sessions, and services
  do not own commits or rollbacks. Successful writes commit at the API/request
  boundary; failure rollback and cleanup remain request-boundary-owned.
- Current-user authentication lookup is read-only. Lazy application/database
  initialization remains preserved, and `/api/health` remains public.

### Live PostgreSQL end-to-end coverage

Live verification covered registration, canonical credential persistence,
Argon2 password-hash persistence, login, JWT/Bearer authentication,
`/api/auth/me`, authenticated portfolio access, authenticated report
creation/retrieval, two-user ownership isolation, immutable report snapshots,
fresh-session persistence, and rejection of `X-User-ID` as authentication.

### Final verification

- Live PostgreSQL integration tests: 27 passed
- Complete API tests: 94 passed
- Schema tests: 386 passed
- Analytics tests: 820 passed
- Full backend tests: 1,588 passed, 0 failed
- Manual analytics engine, Python compilation, dependency consistency,
  application import smoke, public health, and Git integrity/diff checks:
  passed
- Existing warning: 1 non-blocking Starlette/httpx TestClient deprecation
  warning; it is not an authentication defect

### Branch boundary at completion

Authentication did not implement email verification, password reset, refresh
tokens, logout/token revocation, OAuth/social login, MFA, RBAC/admin
authorization, frontend/mobile authentication integration, historical
simulations, AI-agent functionality, full backend integration, or deployment.

## Backend Historical Scenario Simulator

**Status:** Completed and merged into `develop`
**Source branch:** `feat/backend-historical-scenario-simulator`

### Completed responsibility

The Historical Scenario Simulator now answers:

> **How would the user's current saved portfolio have behaved during a selected
> predefined historical market event?**

It applies the saved/current portfolio allocation unchanged. The workflow is
educational and deterministic: it does not forecast future prices, use
buy-and-hold share-count semantics, or provide buy/sell recommendations.

### Initial predefined scenarios

- **COVID-19 Market Shock**
  - ID: `covid-19-shock-2020`
  - Requested period: `2020-02-01` through `2020-04-30`
- **2022 Inflation and Rate Shock**
  - ID: `inflation-rate-shock-2022`
  - Requested period: `2022-01-01` through `2022-12-31`

At this workstream's completion, this two-scenario catalogue was immutable,
deterministic, code-owned, and not stored in PostgreSQL. The completed
Historical Scenario Catalogue workstream documented below later appended
three events without changing these original definitions.

### Contracts and calculation behavior

- Historical simulation uses strict Pydantic contracts imported directly from
  `backend.app.schemas.simulation`; the established 21-name package-level
  schema export contract was not expanded.
- Unknown fields are rejected, public numerical values must remain finite, and
  intentionally undefined Sharpe ratios serialize as JSON `null`.
- The pure simulator reuses Aura's periodically rebalanced fixed-weight
  portfolio-return semantics and keeps the saved allocation unchanged.
- At least three aligned price observations are required. Alignment uses the
  exact common-date intersection across every requested holding without
  forward-fill, backfill, interpolation, synthesized prices, silently dropped
  holdings, or special removal of zero-weight holdings.
- Normalized portfolio value starts at exactly `1.0`. Results include a
  deterministic normalized trajectory, cumulative return, annualized
  volatility, Sharpe ratio using existing analytics behavior, and signed
  maximum drawdown with existing peak/trough semantics.
- Requested scenario dates and effective aligned dates remain separate.
  Recovery-time calculations remain deferred.

### Production integration and service boundaries

```text
authenticated User
        ↓
owned Portfolio
        ↓
ordered Holdings
        ↓
predefined Historical Scenario
        ↓
MarketDataService → PostgreSQL
        ↓
exact common-date alignment
        ↓
pure historical simulator
        ↓
validated simulation response
```

Production simulation retrieves historical prices through Aura's existing
PostgreSQL-backed market-data and service infrastructure. It does not read CSV
files or call Yahoo Finance directly, and it required no new external API key.

Portfolio ownership uses the existing boundary, holding order is preserved,
and missing and wrong-owner portfolios remain indistinguishable as
`404 Portfolio not found`. The service is caller-session based and read-only:
it does not commit, roll back, close the caller-owned session, or persist a
result. It intentionally reuses AnalysisService's existing private exact-date
alignment seam instead of duplicating that algorithm. This accepted internal
coupling is protected by regression tests and is not a public API.

### HTTP API

- `GET /api/simulations/historical-scenarios` is a public, deterministic
  catalogue endpoint. Listing definitions requires neither authentication nor
  database access.
- `POST /api/portfolios/{portfolio_id}/simulations/historical-scenarios` is
  Bearer authenticated and runs the selected scenario against the authenticated
  user's owned saved portfolio. At this workstream's completion, it was
  computation-only and did not save simulation history; successful results are
  now persisted by the completed Simulation History workstream below.
- Missing/wrong-owner portfolios return `404 Portfolio not found`; unknown
  scenarios return `404 Historical scenario not found`; expected missing or
  insufficient historical data returns `422`; invalid or missing Bearer
  authentication returns the existing `401`; and unexpected internal failures
  return `500 Unable to run historical scenario`.
- `X-User-ID` is not accepted as authentication.

### Persistence and dependency boundary

This workstream added no Simulation ORM model, Simulation repository, Alembic
migration, database schema change, JSONB simulation snapshot,
simulation-history persistence, or dependency change. At this workstream's
completion, Simulation History was a separate later workstream; it has since
been completed as documented below.

The completed `feat/backend-market-data-historical-backfill` workstream later
extended verified historical coverage toward year 2000 where provider and
asset history permit. The completed
`feat/backend-historical-scenario-catalog` workstream then expanded the
educational event catalogue to five scenarios. Neither follow-on workstream
changed this completed simulator's calculations.

### Final verification

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

## Backend Allocation Simulator

**Status:** Completed and merged into `develop`
**Source branch:** `feat/backend-allocation-simulator`

### Completed responsibility

Allocation Simulation is Aura's Allocation Change mode. It answers:

> **How would different weights for the same saved portfolio assets have
> changed the portfolio's historical behavior over an arbitrary historical
> period?**

It is separate from the completed Historical Scenario and Combined Simulation
modes.

### Contracts and ordering behavior

- Added strict allocation request, result, comparison, and response contracts
  imported directly from `backend.app.schemas.simulation`; the stable
  package-level schema export contract was not expanded.
- The request changes weights only over an arbitrary start/end period and does
  not accept a predefined historical scenario ID.
- The modified allocation must contain exactly the saved portfolio's complete
  normalized symbol set. Request order may differ, but original and modified
  results are canonicalized to saved holding order.
- Existing symbol normalization, duplicate rejection, `[0, 1]` weight bounds,
  total-weight tolerance, zero-weight behavior, strict unknown-field rejection,
  finite-number behavior, and caller-input non-mutation are preserved.

### Calculation and historical-data behavior

Allocation comparison does not duplicate financial formulas. It uses one
already-aligned historical price frame and runs the existing historical
simulator once with the saved weights and once with the modified weights. Both
results therefore share the same prices, effective dates, fixed-weight /
periodically rebalanced semantics, and existing analytics behavior.

Comparison deltas are `modified - original` for normalized ending value,
cumulative return, annualized volatility, Sharpe ratio when both values exist,
and maximum drawdown. If either Sharpe ratio is undefined, the Sharpe delta is
JSON `null`. Existing signed negative maximum-drawdown behavior is preserved.

Historical prices come through the PostgreSQL-backed `MarketDataService`.
Alignment uses the exact common-date intersection across every saved holding,
with no forward fill, backfill, interpolation, synthesized prices, or silently
dropped holdings. Zero-weight holdings still require data and participate in
alignment. Requested dates remain separate from effective aligned dates.

### Production flow and service boundaries

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

`AllocationSimulationService` reuses the existing portfolio-ownership,
market-data, and exact-date alignment infrastructure. It is caller-session
based and read-only: it does not commit, roll back, close the caller-owned
session, persist a simulation, or persist an Analysis snapshot.

### HTTP API and ownership privacy

- `POST /api/portfolios/{portfolio_id}/simulations/allocations` uses existing
  Bearer authentication and returns `200` for a successful simulation.
- Missing or invalid Bearer authentication returns the existing `401`;
  `X-User-ID` is not accepted as authentication.
- Missing and wrong-owner portfolios remain client-indistinguishable as
  `404 Portfolio not found`; wrong ownership is not exposed as `403`.
- Expected allocation or historical-data failures return `422`.
- Unexpected failures return the stable
  `500 Unable to run allocation simulation` response without exposing internal
  exception details.
- At this workstream's completion, the POST was computation-only and created no
  simulation history; successful results are now persisted by the completed
  Simulation History workstream below.

### Persistence, dependencies, and deferred boundaries

This workstream added no Simulation ORM model, Simulation repository, Alembic
migration, simulation snapshot/history persistence, or dependency change.
Combined Simulation, Simulation History, and Historical Market-Data Backfill
were completed later as separate workstreams. Historical Scenario Catalogue
expansion was also completed later and was not a prerequisite for Allocation
Simulation.

### Final verification

- Dedicated real-PostgreSQL coverage verified authenticated success,
  saved-order canonicalization, reordered modified input, zero-weight behavior,
  ownership privacy, authentication, expected data failures, and fresh-session
  read-only persistence.
- Live PostgreSQL integration suite: 29 passed
- Full backend suite: 1,828 passed, 0 failed, 0 errors, 0 skipped
- Manual analytics engine, Python compilation, import/application smoke,
  public health, dependency consistency, schema export compatibility, and Git
  diff/whitespace checks: passed
- Existing warning: one non-blocking Starlette TestClient/httpx deprecation
  warning; it is not an Allocation Simulator defect

## Backend Combined Simulator

**Status:** Completed and merged into `develop`
**Source branch:** `feat/backend-combined-simulator`

### Completed responsibility

Combined Simulation answers:

> **How would the user's original saved portfolio allocation and a modified
> allocation compare during the same predefined historical event?**

It completes Aura's three core Historical What-If Simulator modes by composing
the existing immutable Historical Scenario catalogue with the completed
Allocation Simulation workflow. It introduces no new financial formulas.

### Composition and historical-data behavior

- The request selects one existing predefined scenario and supplies a complete
  modified allocation. The selected scenario provides the requested start and
  end dates; clients do not supply a separate arbitrary period.
- `CombinedSimulationService` resolves the scenario and delegates one
  `AllocationSimulationRequest` to the existing `AllocationSimulationService`.
- The workflow therefore uses one PostgreSQL historical-data retrieval and one
  exact common-date alignment for both original and modified allocations.
- Saved holding order is preserved even when modified holdings arrive in a
  different order. Zero-weight modified holdings remain present and still
  require historical data.
- Requested scenario dates remain separate from effective aligned dates.

The delegated workflow preserves the existing fixed-weight / periodically
rebalanced semantics, normalized starting value, cumulative return, annualized
volatility, Sharpe ratio, signed maximum drawdown, peak/trough behavior, and
`modified - original` comparison deltas. Nullable Sharpe ratios and nullable
Sharpe deltas remain JSON `null` when either side is undefined.

### Production flow

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

### HTTP API and security

`POST /api/portfolios/{portfolio_id}/simulations/combined` uses the existing
Bearer authentication boundary and returns:

- `200` for a successful Combined Simulation.
- The existing `401` for missing or invalid Bearer authentication;
  `X-User-ID` alone is not accepted.
- `404 Portfolio not found` for missing and wrong-owner portfolios, never
  ownership-revealing `403`.
- `404 Historical scenario not found` for an unknown scenario.
- The established `422` for expected allocation, historical-data, or
  simulation failures.
- Sanitized `500 Unable to run combined simulation` for unexpected failures.

### Read-only persistence and dependency boundary

At this workstream's completion, Combined Simulation was computation-only and
added no Simulation ORM model, Simulation repository, Alembic migration,
database schema change, simulation-history persistence, Analysis snapshot
persistence, or new dependency. Its calculation service still does not commit,
roll back, or close the caller-owned session. Successful results are now
persisted by the completed Simulation History workstream below.

### Final verification

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
- Stable package-level schema export surface: exactly 21 approved names
- Existing warning: one non-blocking Starlette TestClient/httpx deprecation
  warning; it is not a Combined Simulation defect

## Backend Simulation History

**Status:** Completed and merged into `develop`
**Source branch:** `feat/backend-simulation-history`

### Completed purpose and persistence behavior

Simulation History saves and retrieves immutable results from Aura's three
completed simulation modes: Historical Scenario, Allocation Simulation, and
Combined Simulation.

- Successful Historical Scenario simulations are persisted.
- Successful Allocation simulations are persisted.
- Successful Combined simulations are persisted.
- Every successful run creates an independent history record; repeated
  identical simulations are not deduplicated.
- Results are stored as versioned JSONB snapshots and revalidated through the
  correct existing simulation response schema when retrieved.
- Added Simulation ORM persistence, one reversible Alembic migration,
  `SimulationRepository`, and `SimulationHistoryService`.
- History belongs to its portfolio through `portfolio_id`, and portfolio
  deletion cascades its associated Simulation records.
- History is immutable and ordered deterministically newest-first by
  `created_at DESC`, then `id ASC`.

### Completed HTTP surface

- `GET /api/portfolios/{portfolio_id}/simulations` returns the authenticated
  owner's ordered history summaries.
- `GET /api/portfolios/{portfolio_id}/simulations/{simulation_id}` returns one
  authenticated, owner-scoped, schema-revalidated saved result.
- The existing Historical Scenario, Allocation Simulation, and Combined
  Simulation POSTs now persist successful results without changing their
  calculation contracts or validated HTTP response structures.

### Transaction, authentication, and privacy boundaries

- A successful simulation POST saves history and commits exactly once at the
  API/request boundary. Repositories and services do not commit, roll back, or
  close caller-owned sessions.
- History GET endpoints remain read-only. Failed simulations create no
  committed history, and request-session rollback and cleanup remain owned by
  the existing database dependency.
- Bearer authentication remains required; `X-User-ID` is not authentication.
- Missing and wrong-owner portfolios return `404 Portfolio not found`.
  Missing or wrong-associated simulations return `404 Simulation not found`;
  private ownership is not exposed through `403`.

### Final verification

- Full backend suite: 2,029 passed, 0 failed, 0 errors, 0 skipped
- Live PostgreSQL and migration verification: passed
- Historical Scenario, Allocation, and Combined persistence flows: verified
- API, privacy, transaction, and analytics regression verification: passed
- Manual analytics engine, Python compilation, application/import, public
  health, OpenAPI, dependency consistency, and Git diff/whitespace/scope
  checks: passed
- Existing warning: one non-blocking Starlette/httpx TestClient deprecation
  warning

## Historical Market-Data Backfill

**Status:** Completed and merged into `develop`
**Source branch:** `feat/backend-market-data-historical-backfill`

### Completed scope and production behavior

- Added a pure historical-coverage audit helper with deterministic per-symbol
  coverage reporting and complete requested-symbol accounting.
- Added `MarketDataBackfillService` and a dedicated manual PostgreSQL
  historical-backfill CLI.
- Enforced the strict production sequence: fetch, clean, validate, complete
  historical coverage audit, then PostgreSQL persistence. Unresolved requested
  symbols block all persistence instead of producing silent partial success.
- Reused the existing `MarketDataService`, 1,000-row batching, and
  `(symbol, date)` PostgreSQL upsert identity.
- Preserved caller-owned service and repository transactions. The manual CLI
  commits exactly once after a successful complete workflow.
- Verified safe reruns without duplicate identities and preservation of
  existing or newer market-data rows.
- Kept the backfill independent from canonical raw and processed CSV
  replacement.

### Historical-data integrity boundary

The completed backfill reports observed provider coverage without fabricating
prices, forward-filling, backward-filling, interpolating missing history,
synthesizing pre-history, silently removing unresolved assets, or treating an
observed first provider date as a guaranteed asset inception date. Symbols may
legitimately have different available historical ranges.

### Real Yahoo Finance verification

A controlled run for `2000-01-01` through `2026-08-21` requested all 17 Aura
symbols and resolved all 17. It processed and upserted 95,488 rows representing
95,488 unique requested-range `(symbol, date)` identities, with 0 duplicate
identity groups, 0 unresolved symbols, and 25,884 observations earlier than
2010.

An identical rerun retained the same identity count, and an existing newer
AAPL sentinel row survived. The canonical raw and processed CSV files remained
unchanged. Observed first provider dates varied by symbol; these boundaries are
evidence from that run only and may change with Yahoo Finance availability and
coverage.

### Final verification

- Full backend suite: 2,079 passed, 0 failed, 0 errors, 0 skipped
- Historical-backfill helper, service, CLI, and data-pipeline regressions:
  passed
- Complete live PostgreSQL, simulation, and analytics regressions: passed
- Manual analytics engine, Python compilation, dependency consistency,
  application/import, and Git diff/whitespace/scope checks: passed
- Existing warning: one non-blocking Starlette/httpx TestClient deprecation
  warning

## Historical Scenario Catalogue

**Status:** Completed and merged into `develop`
**Source branch:** `feat/backend-historical-scenario-catalog`

### Completed catalogue and reference

Aura's immutable, deterministic, code-owned catalogue now contains exactly
five scenarios in this order:

1. `covid-19-shock-2020` — COVID-19 Market Shock,
   `2020-02-01` through `2020-04-30`
2. `inflation-rate-shock-2022` — 2022 Inflation and Rate Shock,
   `2022-01-01` through `2022-12-31`
3. `dot-com-bust-2000-2002` — Dot-Com Bust,
   `2000-03-10` through `2002-10-09`
4. `global-financial-crisis-2007-2009` — Global Financial Crisis,
   `2007-10-09` through `2009-03-09`
5. `q4-market-selloff-2018` — Q4 2018 Market Selloff,
   `2018-10-01` through `2018-12-31`

The original first two definitions remain unchanged; the three new events
were appended in the approved order. Listing and exact-ID resolution remain
database-independent and network-independent.

The workstream added `docs/historical_events.md` as an educational reference
for historical context, rationale, requested-versus-effective date semantics,
and observed coverage limitations. Category, extended rationale, context, and
coverage notes remain documentation-only metadata and were not added to
production schemas or public API responses.

### Compatibility and historical-data boundaries

The catalogue expansion did not change simulator or analytics formulas,
fixed-weight periodically rebalanced semantics, normalized starting value,
cumulative-return, annualized-volatility, Sharpe, signed maximum-drawdown, or
peak/trough behavior; exact common-date alignment; requested/effective date
separation; minimum observations; missing-data behavior; validation behavior
or order; result structures; production schemas; authentication;
ownership/privacy; HTTP contracts; service/repository transaction ownership;
Simulation History persistence; database models; repositories; migrations; or
dependencies.

Older events intentionally may fail for portfolios containing later-starting
assets. Aura retains the established historical-data failure behavior without
dropping holdings, altering allocations, shortening scenarios, or fabricating,
forward-filling, backfilling, interpolating, or synthesizing prices.

### Controlled live PostgreSQL verification

The guarded `aura_test` database was restored to migration head and populated
through the completed historical-backfill workflow. The observed dataset had
95,488 rows across all 17 canonical symbols, 25,884 observations before 2010,
and 0 duplicate `(symbol, date)` groups. Observed coverage included AAPL and
MSFT from `2000-01-03` through `2026-08-21`, while ETH-USD began on
`2017-11-09`; provider coverage is not a permanent guarantee.

Dedicated live tests verified Dot-Com and Global Financial Crisis success
with AAPL plus MSFT, the existing `422` and no committed history for an old
ETH-USD scenario, COVID requested/effective date separation, successful
Simulation History persistence and fresh-session retrieval, and unchanged
historical `market_data` after cleanup.

### Final verification

- Catalogue definitions: 13 passed
- Historical Scenario service: 22 passed
- Simulation API: 57 passed
- Scenario suite: 59 passed
- Simulation History: 109 passed
- Dedicated catalogue live PostgreSQL: 4 passed
- Analytics: 820 passed
- Broadest safe backend suite: 2,027 passed
- Application, health, OpenAPI, and schema-export checks: 9 passed
- Manual analytics engine, Python compilation, dependency consistency, and
  Git diff/whitespace/scope checks: passed
- Earlier pre-live compatibility verification: full backend suite 2,084 passed
- Eight destructive PostgreSQL modules were intentionally omitted from the
  preserved-data run because their fixtures truncate `market_data` and/or
  downgrade Alembic; this is not a catalogue defect

## Backend Market-Data Scheduler

**Status:** Completed and merged into `develop`
**Source branch:** `feat/backend-market-data-scheduler`

### Completed scope and production flow

- Added one reusable service-layer market-data update and PostgreSQL
  persistence workflow. It completes the existing pipeline before creating
  database resources, reuses the canonical validated DataFrame,
  `MarketDataService`, `MarketDataRepository`, 1,000-row batching, and the
  `(symbol, date)` upsert identity, and commits once at the outer workflow
  boundary while preserving rollback, session-close, and engine-disposal
  behavior.
- Migrated `backend/scripts/update_market_data.py --persist-database` to the
  reusable helper and removed duplicate database orchestration from the CLI.
  CSV-only behavior, existing arguments, output/error behavior,
  partial-provider reporting, and stored-row reporting remain compatible.
- Added APScheduler `3.11.3` with a standalone UTC `BlockingScheduler`, a
  strict `MARKET_DATA_UPDATE_TIME_UTC` setting defaulting to `02:00`, and one
  daily `CronTrigger` configured with `coalesce=True`, `max_instances=1`, and
  `misfire_grace_time=None`.
- Added the production scheduled-job wrapper, explicit standard-library INFO
  console logging, and the side-effect-free standalone runner:

```text
python -m backend.scripts.run_market_data_scheduler
```

The scheduler does not run the job at startup, add a custom retry loop, use a
persistent scheduler job store, or perform downtime catch-up after restart. It
is not integrated into FastAPI startup or lifespan. Job failures are logged
and re-raised to APScheduler while the scheduler process remains available for
future executions.

### Guarded PostgreSQL and compatibility verification

Dedicated deterministic live tests verified the real scheduled job through
the reusable helper, service, repository, and PostgreSQL, including successful
persistence, fresh-session retrieval, repeat-safe upsert, partial-provider
persistence, transaction rollback, exact synthetic-record cleanup, and
preservation of unrelated `market_data`. The live scheduler tests replaced the
pipeline handoff with synthetic canonical data and did not call Yahoo Finance.

The workstream did not change analytics or simulation formulas, historical
scenario definitions, authentication, portfolio/report APIs, schemas/result
structures, database models, Alembic migrations, provider or historical
backfill behavior, FastAPI startup/router behavior, AI behavior, or
frontend/mobile/admin behavior.

Final verification passed 33 targeted scheduler tests, 4 guarded PostgreSQL
scheduler tests, 85 market-data regression tests, 405 non-destructive
simulation regression tests, 820 analytics tests, the broad safe backend suite
with 2,048 passed and 52 skipped, and 1 Health API test. Python compilation,
`pip check`, APScheduler `3.11.3`, runner import safety, application/OpenAPI
compatibility, the bounded standalone-runner smoke, and final readiness and
17-file branch-scope checks also passed.

The existing Starlette/httpx TestClient deprecation warning remains unrelated
and non-blocking. Yahoo Finance production execution was outside the
deterministic live integration test. Deployment and long-running process
supervision remain later work; production deployment must run one scheduler
process replica because `max_instances=1` prevents overlap only within one
process.

## Customer React Web Backend Integration

**Status:** Completed and merged into `develop`
**Source branch:** `feat/react-web-backend-integration`

### Completed scope

The completed workstream connected Aura's existing non-AI customer/investor
React application to the stable FastAPI and PostgreSQL backend capabilities.
It did not integrate the separate Admin frontend or add an Admin-specific API.

- Added a centralized fetch-based API client with structured API errors, an
  environment-driven API origin, Bearer authentication, and frontend
  TypeScript contracts derived from the existing backend contracts.
- Added an explicit environment-driven FastAPI CORS allowlist for browser
  communication without changing financial calculations or existing API
  contracts.
- Integrated real registration, login, `/api/auth/me` session restoration,
  `sessionStorage` JWT persistence, protected routes, frontend logout, and
  401-only session invalidation.
- Integrated real portfolio list, creation, detail, rename, complete ordered
  symbol/weight replacement, duplication, and deletion through the existing
  authenticated Portfolio API and PostgreSQL persistence.
- Connected Analyze Portfolio to
  `POST /api/portfolios/{portfolio_id}/reports`, with real backend analytics,
  report history, and immutable report detail rendering.
- Integrated all three completed simulation modes: Historical Scenario,
  Allocation Change, and Combined Simulation, including the backend scenario
  catalogue, automatic Simulation History persistence, and immutable history
  detail rendering.
- Composed the Dashboard from real portfolio detail and latest saved report
  data, including backend risk, return, drawdown, and risk-driver values. It
  uses holdings count instead of an unsupported dollar valuation and does not
  fabricate financial series or values.
- Removed production fallback-to-mock behavior and browser-local authority for
  domain records. Watchlist, Search, Notifications, profile editing, and other
  deferred capabilities remain truthful and unavailable. AI integration was
  completed later through the dedicated backend and React AI workstreams.

Backend analytics and simulation calculations remain the financial source of
truth. The approved Phase 9 Dashboard adjustment only rounds the
backend-returned risk score for display.

### Live end-to-end and final verification

Phase 9 exercised real React → FastAPI → PostgreSQL behavior for registration,
login, session restoration, protected routes, portfolio persistence, report
creation/history/detail, immutable report snapshots, Dashboard composition,
all three simulation modes, Simulation History/detail, logout/re-login
persistence, and expected authentication and error behavior.

The preserved historical dataset contained 95,488 `market_data` rows across
17 symbols. One clearly synthetic account remains in the test database because
there is no safe user-deletion endpoint:
`phase9-e2e-20260830-001@example.com`. This is test-environment residue, not a
production feature defect.

Final verification confirmed:

- exactly 20 Aura HTTP operations;
- a passing React production build;
- passing focused API and targeted reporting/simulation regressions;
- 820 passing analytics tests;
- a broad safe backend result of 2,058 passed and 52 skipped;
- passing Python compilation, FastAPI import, public health, CORS preflight,
  `npm ls`, `pip check`, and Git diff checks;
- no dependency drift, committed credentials/secrets, or unexpected backend
  financial, schema, model, or migration changes; and
- successful final manual checks for the portfolio rename dialog,
  duplicate/delete dialogs, and Analytics custom date inputs.

### Current boundaries and future capabilities

The customer web application is integrated for authentication, portfolios,
holdings, analysis, reports and report detail, Historical Scenario, Allocation
Change, Combined Simulation, Simulation History and detail, the Dashboard, and
the grounded AI Assistant. The Backend AI Agent and React web AI integration
are complete and merged into `develop`. Mobile AI integration is complete and
pushed on `feat/mobile-web-parity`.

Future or optional gaps include Watchlist persistence, customer quote/live
market-data APIs, asset search/catalogue support, shares and invested amounts,
live portfolio valuation, editable profiles, password management, global
Search, Notifications, support/contact APIs, report export/share/delete
actions, and user-level report/simulation history optimization.

Aura's Admin frontend remains a separate future workstream. No completed
Admin role/authorization system, Admin-specific backend API, or Admin
web/backend integration exists.

## Backend AI Agent

**Status:** Completed and merged into `develop`

**Source branch:** `feat/backend-ai-agent`

The completed backend AI workstream added the authenticated, read-only
`POST /api/agent/explain` endpoint. It grounds explanations in backend-owned
portfolio, saved-report, and saved-simulation context without replacing the
deterministic analytics or simulation engines.

- Supports configured OpenAI and GroqCloud providers behind one provider
  boundary.
- Preserves authenticated ownership and the existing private `404` behavior
  for portfolio, report, and simulation context.
- Returns explanation text together with source references and limitations.
- Applies educational-scope guardrails and blocks personalized portfolio or
  investment recommendations.
- Does not create a second source of financial calculations or make trading
  decisions.

## Customer React Web AI Integration

**Status:** Completed and merged into `develop`

**Source branch:** `feat/react-web-ai-integration`

The customer React Assistant uses real saved portfolios and the authenticated
`POST /api/agent/explain` endpoint. It presents backend-returned explanations,
source references, limitations, loading states, and truthful retryable errors
without duplicating financial calculations or exposing provider credentials.
Controlled web verification is complete, and the current React production
build passes.

## Customer Mobile Backend and AI Integration

**Status:** Completed, including mobile AI, and pushed; not yet merged into
`develop`

**Source branch:** `feat/mobile-web-parity`

The mobile client now uses the shared FastAPI/PostgreSQL backend as production
authority for all currently supported customer workflows:

- centralized environment-aware API communication and structured errors;
- registration, login, secure token storage, `/api/auth/me` restoration,
  retryable temporary verification failures, logout, and centralized `401`
  invalidation;
- portfolio CRUD, real ordered holdings, and authenticated ownership;
- real analysis creation, immutable reports, report history, and report
  detail;
- Historical Scenario, Allocation Change, Combined Simulation, and immutable
  Simulation History/detail;
- a real Dashboard composed from portfolios, holdings, and the newest saved
  backend report without fabricated financial authority;
- an authenticated, stateless AI Assistant grounded by the backend in the
  selected real portfolio and newest saved report when available, with
  backend-returned source references and limitations; and
- Expo SDK 57 compatibility, consistent Android Aura colors, and dynamic
  local FastAPI host discovery during Expo development.

Production mobile financial and domain state no longer depends on mock records
for these integrated workflows. The mobile Assistant calls only the shared
FastAPI AI endpoint, keeps provider secrets in the backend, preserves central
authentication behavior, rejects malformed success bodies, and does not create
authoritative local chat history or financial calculations. Mobile verification
passed TypeScript checking and all 11 production-authority tests; the focused
backend AI regression passed 187 tests.

## Customer Mobile Real-Holdings Integration

**Status:** Priority 0 contracts, Priority 1 core screens, the shared mobile
error-state contract, and Priority 2 source-level UX hardening are implemented;
runtime device verification remains

**Source branch:** `feat/mobile-real-holdings-integration`

- Mobile portfolio CRUD now records complete ordered real holding facts and no
  longer exposes or submits manual portfolio weights.
- Portfolio Detail and Dashboard request backend-owned USD/THB valuation and
  keep current values separate from persisted facts and saved analysis.
- Analysis creation supports USD/THB, while V1 reports remain readable and V2
  reports display their immutable valuation and per-asset composition.
- Allocation and Combined simulation editors keep hypothetical percentages but
  initialize real portfolios from the backend-resolved current USD allocation.
- Saved Simulation Detail supports V1 and all V2 variants, displaying the
  frozen real-holding baseline without revaluation.
- Mobile API failures now retain their original status through presentation:
  expired authenticated sessions route to a visible 401 sign-in state; missing
  detail resources use blocking 404 states; 422 responses remain inside forms
  with field messages when the backend supplies locations; and 500/network
  failures use distinct retryable states. Previously loaded data remains visible
  behind inline stale-data notices when the page can still serve its purpose.
- Priority 2 accessibility and compact-phone hardening now gives every direct
  mobile `Pressable` an explicit role, every direct `TextInput` an accessible
  label, selection controls selected/disabled state, and the audited compact
  controls at least a 44-point target. Dense holding, date, action, metric,
  valuation, report, and simulation layouts wrap rather than clipping on narrow
  screens or with enlarged text. Keyboard-aware form scrolling remains shared
  across holding, analysis, simulation, search, and Assistant workflows.
- A missing `sessionExpired` auth-context binding in `RootNavigator` was repaired
  after the Priority 2 typecheck exposed it, restoring the intended expired-
  session route and a clean TypeScript build.
- Create Portfolio and Edit Holdings now share an accessible native purchase-
  date picker with a calendar affordance. It permits any valid past date through
  the backend-approved current date, blocks future selection, and preserves the
  public `YYYY-MM-DD` request format. Expo's compatible
  `@react-native-community/datetimepicker` module and config plugin were added
  specifically for this native control.
- Report Detail now offers a truthful Assistant handoff that preselects the
  report's portfolio while stating that backend AI grounding uses the newest
  saved report. My Portfolios loads report history and shows `View Latest
  Report` only on portfolio cards with a confirmed saved analysis; loading,
  stale-history failure, and retry states remain explicit.
- Mobile TypeScript checking passes, and the production-authority suite passes
  21 tests, including regression guards for interactive accessibility semantics,
  compact-layout wrapping, purchase-date limits, and report/Assistant entry
  points. Expo web preview is
  unavailable because the optional web runtime is not installed, and no Android
  SDK/emulator is present;
  no dependency was added solely for preview. No backend, database, or financial-
  formula change was made by this mobile work.

## Backend API Integration and Feature Expansion

**Status:** Baseline integration completed; additional feature work in progress

**Workstream:** `feat/backend-api-integration`

The original integration goal is complete across authentication, portfolios,
holdings, analytics, reports, simulations, the Backend AI Agent, and the
completed React web and mobile client connections. The workstream is now
continuing as an active expansion stage for newly approved features. Those new
features must be documented and verified individually before they are treated
as completed. This ongoing expansion does not make deployment complete.

## Real Holdings and Dynamic Allocation Backend

**Status:** Complete and verified; final documentation/readiness phase complete

**Source branch:** `feat/backend-real-holdings-dynamic-allocation`

### Final capability

- Real holdings persist symbol, invested amount/currency, shares, purchase
  date, and backend-controlled order while keeping persisted weight `NULL`.
- Weight-only legacy holdings remain temporarily compatible; normal holdings
  replacement is the explicit legacy-to-real conversion and duplication
  preserves mode.
- Current valuation is canonical USD with optional THB display, persisted
  market observations no more than four calendar days old, and dynamic current
  allocation.
- The 17 user assets remain distinct from the internal `THB=X` USD/THB
  instrument included in default and scheduled market-data updates.
- Real analysis uses current allocation against the selected historical period
  without replaying shares or changing financial formulas.
- Reports retain V1 and add immutable
  `portfolio-analysis-response-v2` snapshots.
- Historical, Allocation, and Combined simulations retain V1 and add immutable
  V2 history with frozen current baselines.
- AI grounding is mode/version aware for live legacy, live real, saved Report
  V2, and saved Simulation V2 context.
- Alembic head is `d4a6f8c2e1b7`.

### Guarded PostgreSQL 18.4 verification

Phase 12 used only the approved local test target at `127.0.0.1:5433`, database
`aura_test`, role `aura`. It upgraded from `7c1e2f4a6b90` to
`d4a6f8c2e1b7` and preserved baseline legacy rows.

The guarded end-to-end flow passed real CRUD, USD and THB valuation, Report V2
and all three Simulation V2 JSONB round-trips, immutability after current
market-data changes, stale-data behavior, THB-failure independence, privacy,
transaction rollback, and AI integration with a mock provider. Cleanup
restored business and market-data counts to baseline. The test database remains
at the final head intentionally.

### Phase 13 readiness verification

- Database-free unit suite: 2,255 passed
- Database-free API suite: 253 passed
- Service suite: 363 passed
- Analytics suite: 820 passed
- Retained guarded PostgreSQL end-to-end test: 1 passed
- Python compilation, application import, health, and dependency checks:
  passed
- Generated OpenAPI: exactly 18 paths and 23 operations
- Production assumption audit: no new backend defect found
- Git whitespace/scope and Markdown local-link checks: passed
- Tracked-change/history secret audit: no tracked secret found
- Documentation now covers architecture, public API changes, legacy
  compatibility, currency/instrument behavior, report/simulation versions,
  AI grounding, transaction ownership, fresh-Supabase readiness, and the
  frontend/mobile integration backlog.

### Remaining boundaries

The React and mobile clients still require a later branch to adopt real
holding entry, current valuation, dynamic allocation, Report V2, and Simulation
V2. Production deployment requires a fresh Supabase project and has not been run.
Frontend/mobile production code was not changed, Supabase was not accessed,
Docker lifecycle was untouched, and no financial formula changed.

## Known Issues and Technical Debt

### Starlette/httpx warning

The backend test suite still produces one existing non-blocking
Starlette/httpx deprecation warning.

This warning is unrelated to the analytics calculations and does not
cause test failures.

## Current Project Priorities

### Recommended next integration work

- Review and merge `feat/backend-real-holdings-dynamic-allocation` into
  `develop` after the final commit/push/PR workflow is explicitly authorized.
- Follow with dedicated React and mobile integration work for the completed
  real-holding, valuation, and V2 history contracts.
- Deploy only afterward to a fresh Supabase project using the documented
  fresh-project checklist.

```text
✅ feat/backend-real-holdings-dynamic-allocation
        ↓
React real-holding/V2 integration
        ↓
Mobile real-holding/V2 integration
        ↓
Fresh Supabase deployment
```

### Approved follow-on development order

1. Complete the branch commit/push/PR workflow when authorized.
2. Update the React client to real holding CRUD, current valuation, and V2
   report/simulation contracts.
3. Update the mobile client to the same shared contracts.
4. Run client and cross-feature regression verification.
5. Provision and migrate a fresh Supabase project using the documented
   checklist; then run deployment smoke verification.

The backend real-holding branch is complete. Customer real-holding parity,
fresh Supabase deployment, optional product gaps, and Admin integration remain
incomplete.
