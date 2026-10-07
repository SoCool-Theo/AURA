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

Future or optional gaps include customer quote/live market-data APIs, global
asset search/catalogue support, shares and invested amounts,
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
- Current analysis uses fixed owned shares at each historical price date for
  portfolio-level return/risk metrics; current allocation remains authoritative
  for concentration, diversification, and risk contribution.
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

## Planned Portfolio Expansion

**Status:** Step 6 mode-aware planned AI grounding complete

### Approved product target contract

- Customer-facing portfolio types are `CURRENT` and `PLANNED`; `LEGACY` is
  internal compatibility state and cannot be selected for new portfolios.
- Current holdings keep actual ownership facts. Planned holdings persist only
  positive proposed amounts under one USD/THB plan currency.
- Planned target weights are backend-derived from proposed amounts. Estimated
  shares are optional display context and never analytics authority.
- The shared baseline resolver now produces one provenance-aware canonical
  allocation for `CURRENT`, `PLANNED`, and `LEGACY` analysis preparation.

### Completed database foundation

- Added explicit `portfolios.portfolio_type`, nullable `plan_currency`, and
  optional self-referencing `source_plan_id` with database constraints.
- Added nullable positive `holdings.proposed_amount` and extended the complete
  holding-shape constraint for mutually exclusive legacy, current, and planned
  rows.
- Added additive Alembic revision `e5b7c9d2a4f1`. It classifies existing real
  and empty portfolios as `CURRENT`, saved-weight portfolios as `LEGACY`, and
  refuses mixed/incomplete source state before mutation.
- Downgrade refuses to discard planned holdings or source-plan provenance. A
  safe downgrade restores the prior real/legacy schema without rewriting
  holding facts or fabricating weights.

### Step 2 verification

- Database unit suite: 142 passed.
- Complete backend unit suite: 2,261 passed.
- Credential-safe preflight confirmed the approved local PostgreSQL 18.4 test
  database at starting revision `d4a6f8c2e1b7`.
- Guarded live upgrade, backfill, constraints, downgrade refusal, cleanup, and
  restoration: 2 passed.
- The preserved local database was restored to `d4a6f8c2e1b7`; repository
  Alembic head is `e5b7c9d2a4f1`.

### Completed Step 3 runtime foundation

- Portfolio create and response contracts are type-aware. New clients can
  create `CURRENT` or `PLANNED` portfolios; omitted type still defaults to
  `CURRENT`, and clients cannot create `LEGACY` portfolios.
- Planned portfolios require one normalized `USD` or `THB` plan currency and
  accept only ordered, unique symbols with positive proposed amounts.
- The shared holdings replacement route dispatches complete current facts or
  planned amounts by request shape and returns a sanitized `409` when the body
  conflicts with the saved portfolio type. The existing explicit
  `LEGACY`-to-`CURRENT` compatibility replacement remains supported.
- Portfolio duplication preserves the source portfolio type and copies the
  corresponding complete holding shape. Planned copies retain proposed amounts
  and plan currency without inventing shares.
- `GET /api/portfolios/{portfolio_id}/planned-allocation` returns the
  backend-derived total and canonical target allocations at 18-decimal
  precision. It is read-only and independent of current market prices and FX.
- Full portfolio responses expose `portfolio_type`, `plan_currency`, and
  optional `source_plan_id`; list summaries expose the type and plan currency.

### Step 3 verification

- Focused schema, repository, service, allocation, and portfolio API suite:
  282 passed.
- Complete backend unit suite: 2,288 passed.
- Non-PostgreSQL API integration suite: 265 passed. Live PostgreSQL modules were
  intentionally excluded because this step made no schema change and the
  preserved database remains at the pre-Step-2 revision by design.
- Python compile verification completed for `backend/app` and `backend/tests`.
- Ruff was not available in the existing environment; no dependency was added.

### Completed Step 4 preview and analysis integration

- `GET /api/portfolios/{portfolio_id}/planned-preview` returns canonical target
  allocations plus optional current-price estimated shares. Estimate status is
  explicit per holding, and missing price or THB FX data does not prevent the
  successful allocation response.
- Estimated shares retain full calculation precision, include their price/FX
  provenance when available, remain read-only, and never become saved ownership
  facts or analytics inputs.
- `PortfolioBaselineResolutionService` is now the common baseline source:
  `CURRENT` uses current valuation weights, `PLANNED` uses proposed-amount target
  weights, and `LEGACY` uses saved weights.
- Analysis preparation and composition accept the planned baseline and enrich
  per-asset output with proposed amount and holding position without requiring
  current prices. Historical-data sufficiency rules remain unchanged.
- Planned report snapshots, simulations, and AI grounding remain deliberately
  guarded with sanitized compatibility errors until their dedicated steps. No
  later-stage persistence contract was activated early.

### Step 4 verification

- Focused preview, schema, baseline, composition, reporting/simulation guard,
  AI guard, and API suite: 362 passed.
- Complete backend unit suite: 2,310 passed.
- Non-PostgreSQL API integration suite: 270 passed. Live PostgreSQL modules were
  intentionally excluded because Step 4 makes no schema change.
- Python compile verification completed for `backend/app` and `backend/tests`.
- No database, Docker, external LLM, branch, commit, or dependency operation was
  performed.

### Completed Step 5 immutable planned history

- Planned analysis now uses its canonical proposed-amount target allocation and
  persists `portfolio-analysis-response-v3`. The snapshot freezes the plan
  currency, ordered proposed amounts, exact backend target weights, complete
  analytics, and an explicit hypothetical/non-forecast notice.
- Historical Scenario, Allocation, and Combined simulations now accept planned
  baselines. Their immutable history uses the exact V3 versions
  `historical-scenario-simulation-response-v3`,
  `allocation-simulation-response-v3`, and
  `combined-simulation-response-v3`.
- Allocation and Combined V3 snapshots verify that the result's original
  allocation matches the frozen plan baseline. Snapshot validation also
  verifies proposed totals, exact amount-derived weights, unique holdings, and
  saved ordering.
- V1 legacy and V2 current report/simulation readers remain unchanged and
  readable. V3 history retrieval revalidates only the stored JSONB snapshot and
  never requests current market data, FX, valuation, or recomputation.
- Estimated shares are intentionally excluded from V3 snapshots because they
  are optional display context and do not control planned analytics.
- Existing AI tools continue to reject V3 context with a sanitized compatibility
  error until the dedicated mode-aware grounding step.
- No migration was needed because the existing report and simulation tables
  already persist an explicit schema version and JSONB payload.

### Step 5 verification

- Focused report, simulation, snapshot, AI guard, and API suite: 399 passed.
- Complete backend unit suite: 2,332 passed.
- Non-PostgreSQL API integration suite: 273 passed with 50 existing short JWT
  test-key warnings. The three explicitly live PostgreSQL API modules were
  excluded; an accidentally broad collection that reached those modules was
  stopped during setup before any test body or database mutation.
- Python compile verification completed for `backend/app` and `backend/tests`.
- No database, Docker, external LLM, branch, commit, or dependency operation was
  performed.

### Completed Step 6 mode-aware AI grounding

- Live AI context now identifies `CURRENT`, `PLANNED`, and `LEGACY` portfolio
  types and their authoritative baseline source. Planned context contains only
  plan currency, proposed amounts, exact target weights, order, and the explicit
  hypothetical notice; it never includes estimated shares or internal holding
  IDs.
- Saved Report V3 and all Simulation V3 variants are projected from their frozen
  snapshots. Their schema version, portfolio type, baseline source, proposed
  amounts, target weights, results, and historical period/scenario are preserved
  without live price, FX, valuation, or recomputation calls.
- Saved-context portfolio projection exposes identity and portfolio type while
  omitting mutable live planned/current facts, so a later portfolio edit cannot
  conflict with the selected immutable snapshot.
- System instructions require mode-aware wording: actual/current terminology
  for `CURRENT`, planned/proposed/hypothetical terminology for `PLANNED`, and
  saved-allocation terminology for `LEGACY`.
- Planned explanations receive a deterministic hypothetical/non-forecast/
  non-order limitation. A planned response that claims the user currently owns
  the proposed assets is rejected before it reaches the API response.
- Existing advice refusal, prompt-injection resistance, signed/null/zero value
  preservation, source attribution, ownership privacy, and output-safety rules
  remain in force.

### Step 6 verification

- Focused AI tool, prompt, guardrail, orchestration, API, Report V3, and
  Simulation V3 regression suite: 422 passed with 54 existing short JWT test-key
  warnings.
- Complete backend unit suite: 2,339 passed.
- Isolated non-PostgreSQL API integration suite: 275 passed with 54 existing
  short JWT test-key warnings. The three explicitly live PostgreSQL API modules
  were not run.
- Python compile verification completed for `backend/app` and `backend/tests`.
- No database, Docker, external LLM, migration, dependency, branch, commit, or
  push operation was performed.

### Completed Step 7A mobile planned-portfolio integration

- Mobile portfolio contracts and API clients now distinguish `CURRENT`,
  `PLANNED`, and `LEGACY`, submit planned proposed amounts, and consume the
  backend planned-allocation and planned-preview endpoints.
- Create Portfolio offers explicit current/planned choices. Planned entry uses
  one USD/THB plan currency plus symbol and proposed amount only; current entry
  retains actual shares, invested amount/currency, and purchase date. Edit
  Holdings preserves the saved type and cannot mix the two holding shapes.
- Portfolio list/detail and Dashboard identify hypothetical plans, display the
  backend-derived total and target allocation, and show estimated shares only
  as optional, non-authoritative preview information.
- Mobile analytics and saved reports render immutable Report V3 planned
  baselines and the hypothetical notice. Report V1/V2 behavior remains intact.
- Allocation and Combined simulation editors initialize planned portfolios
  from `planned-allocation`, never from on-device amount division. Saved
  simulation detail renders all planned V3 baseline variants without current
  price or FX requests.
- The Assistant keeps its unchanged authenticated request shape while the UI
  identifies planned context; wording and limitations remain backend-owned.

### Step 7A verification

- Mobile TypeScript compilation completed with no errors.
- Mobile production-authority suite: 23 passed, including planned amount
  validation, exact API payload/path checks, backend target-weight consumption,
  display-only estimate guards, and V3 report/simulation presentation checks.
- No web client, backend, database, Docker, external LLM, dependency, branch,
  commit, or push operation was performed.

### Remaining planned-portfolio work

The atomic plan-to-new-current conversion capability and its client flow, plus
final guarded deployment verification, remain pending. Conversion is not
exposed in either client because the required backend operation does not exist
yet.

### Completed Step 8M mobile readiness verification

- The committed mobile planned-portfolio integration was verified on branch
  `feat/mobile-real-holdings-integration`; the worktree was clean before this
  documentation update and no web files were changed.
- Mobile TypeScript compilation completed successfully and the complete mobile
  production-authority/regression suite passed 23 tests.
- The installed dependency tree resolved successfully with no missing package.
- Expo/Metro resolved 1,153 modules and produced a release Android Hermes
  bundle plus its assets and metadata. The temporary export directory was
  removed after verification.
- The production mobile source audit found no embedded LLM keys, database URLs,
  PostgreSQL credentials, or Supabase service-role configuration. Backend-only
  financial authority remains enforced: current valuation, planned target
  allocation, planned share previews, reports, simulations, and AI context are
  consumed from authenticated API responses.
- `CURRENT`, `PLANNED`, and `LEGACY` presentation remains distinct. Planned
  estimates remain display-only, planned V3 history remains immutable, and
  error presentation continues to distinguish authentication, not-found,
  validation, server, and network failures.
- No database, migration, rollback, Docker, external LLM, dependency install,
  branch change, commit, or push operation was performed during this step.

### Mobile-only readiness boundary

The checked mobile source is ready for device/API acceptance testing, but this
is not a claim that the entire product is deployment-ready. A signed native
binary, physical-device or emulator E2E run against a deployed backend,
plan-to-current conversion, and the broader database/deployment verification
are outside this mobile-only Step 8M.

### Completed mobile report monetary metric details

- Current V2 and planned V3 report responses include deterministic
  `monetary_metrics` derived only from the saved report snapshot. New current
  reports use the fixed-share historical starting value and exact ending-minus-
  starting change; planned reports use the proposed reference amount. Maximum
  drawdown remains tied to the saved historical path rather than today's
  portfolio value.
- The monetary context is response-only and does not modify persisted report
  JSONB, require a migration, fetch fresh prices, or revalue historical reports.
  V1 legacy reports remain percentage-only because they have no trustworthy
  currency reference amount.
- On mobile, cumulative return, annualized return, and maximum drawdown cards
  show a chevron and tap hint when monetary context is available. Tapping opens
  an accessible bottom sheet with the percentage, signed USD/THB equivalent,
  saved reference amount, time basis, and explicit educational/non-forecast
  wording.
- The mobile client does not calculate these financial amounts. It formats the
  decimal strings supplied by the authenticated report response and remains
  compatible with older responses that omit `monetary_metrics`.
- Report Detail opened through More now has an explicit accessible back arrow
  that returns to the Reports list; the existing Home action remains available.

### Monetary metric verification

- Focused report schema, mapper, service, and API suite: 124 passed.
- Complete backend unit suite: 2,341 passed.
- Mobile TypeScript compilation completed with no errors.
- Mobile production-authority suite: 24 passed, including signed currency
  formatting and guards against client-side reference-amount multiplication.
- No database, migration, Docker, external LLM, dependency, branch, commit, or
  push operation was performed.

### Completed Step 8W web readiness verification

- The React web client now supports `CURRENT`, `PLANNED`, and `LEGACY`
  portfolio presentation and workflows without replacing the established web
  design system.
- Current CRUD records real ownership facts; planned CRUD records proposed
  amounts and one plan currency. Neither workflow accepts manual saved weights.
- Current valuation uses backend-returned market values and allocation. Planned
  detail uses backend target allocation and optional display-only estimated
  shares; missing estimates do not become analytics authority.
- Dashboard, Analytics, Reports, all simulation modes and V1/V2/V3 history,
  monetary metric details, portfolio report shortcuts, and mode-aware Ask Aura
  context are integrated. Saved report and simulation assistant links preserve
  their exact immutable context identifiers.
- Shared web error presentation distinguishes authentication, not-found,
  validation, server, temporary-data, configuration, and network failures.
  Blocking failures use page-level states and recoverable actions remain inline;
  unexpected server details are not shown to users.
- A final routing correction prevents an invalid Ask Aura portfolio deep link
  from silently falling back to another owned portfolio.
- Web TypeScript compilation, the 7-test production-authority suite, dependency
  resolution, production Vite build, source secret/authority audit, and Git
  whitespace checks pass.
- Local browser smoke verification passed login rendering, sign-up navigation,
  protected-route redirection, and console-error inspection. Authenticated live
  browser E2E was not run because no test-user credentials were supplied.
- No backend, database, migration, Docker, external LLM, dependency install,
  branch, commit, push, merge, or PR operation was performed during Step 8W.

### Web readiness boundary

The checked React source is ready for authenticated API acceptance testing.
This is not a production-deployment claim: fresh Supabase deployment,
environment-specific authenticated browser E2E, and plan-to-current conversion
remain separate follow-on work.

### Completed backend per-asset risk and historical-series contract

- Each analyzed asset now receives a deterministic educational risk score and
  `Low`/`Moderate`/`High`/`Very High` level derived equally from Aura's existing
  annualized-volatility and maximum-drawdown point thresholds. Portfolio-only
  concentration and diversification components are deliberately excluded.
- `PortfolioAnalysisResponse` now exposes ordered dated return observations for
  every asset. Symbols and dates are validated against `asset_metrics` and the
  portfolio return series, so clients can render directly comparable graphs.
- New V2 current and V3 planned report snapshots automatically freeze the
  per-asset classifications and return series through the existing immutable
  analysis payload. Older V1/V2/V3 snapshots without these additive fields
  remain readable without market-data queries or recomputation.
- No database migration or dependency change was required.

### Per-asset backend verification

- Focused analytics, schema, mapping, and service suite: 365 passed.
- Focused reporting, example, and composition suite: 115 passed.
- Complete backend unit suite: 2,356 passed.
- Reporting and agent API integration suite: 70 passed with 54 existing short
  JWT test-key warnings.
- Python compilation completed successfully for `backend/app` and
  `backend/tests`.
- Web and mobile now expose report-backed asset-risk detail pages from every
  per-asset analysis card. Each page shows the saved backend risk
  classification, historical asset return graph with 1M/3M/6M/1Y/ALL views,
  portfolio-impact contribution, saved holding or planned-position context,
  and the existing educational limitation.
- Direct web report/asset routes and both mobile navigation stacks preserve the
  originating immutable report. Older reports remain readable and clearly
  explain when their snapshots predate asset risk or return-series fields.
- Neither client recalculates risk, volatility, drawdown, or historical return
  data; both format the additive backend report contract only.

### Per-asset client verification

- Web production TypeScript/Vite build completed successfully.
- Mobile TypeScript compilation completed with no errors.
- Web production-authority suite: 18 passed, including a regression guard for
  asset navigation and backend-only risk authority.
- Mobile production-authority suite: 30 passed, including the equivalent
  report-backed asset-detail guard in both navigation stacks.
- Git whitespace validation completed with no errors.

### Completed backend per-asset monetary metrics

- V2 current and V3 planned report detail responses now include ordered
  `asset_monetary_metrics` derived only from the immutable saved report.
- Each asset exposes its saved currency/reference amount plus cumulative-return,
  annualized-return, and exact peak-to-trough maximum-drawdown amounts. V2 uses
  saved current value; V3 uses proposed amount.
- Exact drawdown money is reconstructed from the saved dated asset return path
  and verified against the saved asset drawdown percentage. Older snapshots
  without a verifiable path return `null` for non-zero drawdown money rather
  than using misleading percentage multiplication.
- The field is response-only: no snapshot mutation, live market-data request,
  database migration, or dependency change was required. Client presentation
  remains a separate follow-on step.

### Per-asset monetary backend verification

- Focused reporting schema, mapper, service, and API suite: 129 passed.
- Complete backend unit suite: 2,360 passed.
- Reporting and agent API integration suite: 70 passed with 54 existing short
  JWT test-key warnings.
- Python compilation completed successfully for `backend/app` and
  `backend/tests`; Git whitespace validation completed with no errors.

### Completed per-asset monetary metric details in both clients

- The web and mobile asset-risk detail pages now make cumulative return,
  annualized return, and maximum drawdown selectable when the immutable report
  includes the corresponding per-asset monetary context.
- Web opens the existing accessible metric dialog; mobile opens the existing
  accessible bottom sheet. Both show the saved percentage, signed USD/THB
  amount, saved asset reference amount, and whether that basis is a current
  saved value or a planned proposed amount.
- Exact maximum-drawdown money is shown only when the backend supplies it.
  Older reports and unverifiable non-zero drawdowns stay percentage-only rather
  than displaying a locally estimated or misleading amount.
- Both clients treat `asset_monetary_metrics` as an additive optional report
  field and only format backend decimal strings; neither client multiplies a
  reference amount by a return or drawdown percentage.

### Per-asset monetary client verification

- Web production TypeScript/Vite build completed successfully.
- Mobile TypeScript compilation completed with no errors.
- Web production-authority suite: 19 passed, including guards for optional
  legacy compatibility and backend-only per-asset monetary authority.
- Mobile production-authority suite: 30 passed with the equivalent asset-detail
  monetary interaction and no-client-calculation guards.
- Git whitespace validation completed with no errors.

### Completed dashboard risk-driver asset links

- Every displayed Top Risk Drivers entry on the web and mobile home pages is
  now an accessible control that opens that asset's risk-detail page.
- Navigation carries the exact portfolio ID, immutable latest report ID, and
  asset symbol shown on the dashboard, so the detail page remains grounded in
  the same saved analysis rather than loading unrelated or live data.
- Web risk-driver asset rows align directly beneath their section header rather
  than being vertically centered inside a taller dashboard card.
- Web and mobile production-authority suites remain green at 19 and 30 tests;
  both TypeScript checks and the web production Vite build pass.

### Completed dashboard AI explanation action

- The web home-page AI Explanation card now includes a prominent Ask Aura
  button and a compact context panel instead of leaving most of the card empty.
- When a latest report exists, the action grounds Aura in that exact immutable
  report. Otherwise it opens the selected portfolio context without inventing
  saved analysis results.

### Completed planned estimated ending value

- Planned V3 report responses now include a backend-derived
  `estimated_ending_value`, calculated from the immutable proposed total and
  saved historical cumulative-return amount. It does not use current prices,
  estimated shares, or client-side financial calculations.
- Web and mobile planned report results show the beginner-facing label
  **Estimated Value at End of Period** as a clickable metric. Its detail view
  explains the saved proposed amount, historical change, selected period, and
  the non-forecast limitation.
- The field is response-only and backward-compatible; no report snapshot,
  database migration, or dependency change was required.
- Reporting regression suite: 131 passed. Web production-authority suite: 19
  passed. Mobile production-authority suite: 30 passed. Mobile TypeScript and
  the web production build completed successfully.

### Completed fixed-share current portfolio history

- Current portfolio analysis now values the same owned share quantities at
  every aligned historical price date. Cumulative return, annualized return,
  annualized volatility, Sharpe ratio, and maximum drawdown all come from that
  historical portfolio-value series.
- Current valuation weights remain authoritative for concentration,
  diversification, and risk contribution against historical covariance.
- New V2 snapshots freeze the historical USD starting and ending values.
  Report mapping uses the exact ending-minus-starting change and no longer
  multiplies today's saved portfolio value by historical return. Older V2
  snapshots remain readable and omit unverifiable portfolio money context.
- Web and mobile label the result **Historical Portfolio Return**, show the
  fixed-share historical start/end values when available, and explicitly state
  that the result is not the user's actual profit or loss.
- Fixed-share focused backend suite: 445 passed. Complete backend unit suite:
  2,386 passed. Reporting schema/API regression suite: 83 passed. Web
  production-authority suite: 19 passed and production build completed. Mobile
  production-authority suite: 30 passed and TypeScript compilation completed.

### Completed portfolio input warning navigation

- Web and mobile create/edit portfolio forms now show a warning popup when
  local validation or a backend `422` response identifies invalid input.
- Validation returns the exact first invalid holding row and field. The same
  message is shown inline, the field receives its error styling, and the form
  moves focus to that input. Web scrolls the field into view; mobile reuses the
  keyboard-aware form scroll behavior after focusing it.
- Empty holding lists direct the user to the holdings area. On mobile, Aura
  restores one blank row and focuses its symbol field so the user can correct
  the problem immediately.
- Web production-authority suite: 20 passed and the production build completed.
  Mobile production-authority suite: 31 passed and TypeScript compilation
  completed.

### Completed planned report USD/THB display switch

- New planned V3 reports capture a best-effort USD/THB observation with its
  requested date and observation date. Missing or stale FX does not block
  planned analysis or saving the report.
- Report detail derives complete backend-owned USD and THB views for the saved
  proposed total, holding amounts, estimated ending value, and other monetary
  metric explanations. Percentage, allocation, and risk results do not change.
- Web and mobile show an accessible USD/THB selector on the saved planned
  allocation card when the snapshot contains frozen FX. Older reports without
  FX remain readable in their original plan currency.
- Focused reporting backend suite: 96 passed; reporting API integration suite:
  39 passed; complete backend unit suite: 2,389 passed. Web
  production-authority suite: 20 passed and production build completed. Mobile
  TypeScript compilation completed.

### Completed portfolio input warning presentation and validation

- Web asset-symbol controls keep the picker button aligned to the input when an
  inline validation warning is shown; the warning no longer stretches the
  button below the input.
- Web and mobile current-share inputs now use `10.50` guidance and enforce a
  maximum of two decimal places in local validation before submission.
- Current and planned holding forms validate typed symbols against Aura's exact
  17-asset catalog before starting portfolio creation or replacement. Unsupported
  entries such as `ASDF` are identified as symbol-field errors.
- Web browser alerts and mobile native alerts were replaced with centered,
  theme-aware Aura warning dialogs. Choosing **Show input** closes the dialog,
  preserves the inline warning, and reveals/focuses the exact invalid field.
- Web production-authority suite: 20 passed and production build completed.
  Mobile production-authority suite: 31 passed and TypeScript compilation
  completed.

### Completed Watchlist Backend V1

- Added authenticated observation-only Watchlist CRUD at `GET/POST
  /api/watchlist` and `DELETE /api/watchlist/{symbol}`. Ownership always comes
  from the Bearer-authenticated user; request bodies cannot supply `user_id`.
- Added reversible migration `a8d3f1c6b2e7` and the `watchlist_items` model with
  UUID identity, user cascade ownership, deterministic creation ordering, and
  database-enforced `UNIQUE(user_id, symbol)`.
- Reused Aura's canonical 17-symbol user-asset registry. Symbols are normalized
  before service validation; duplicate normalized entries return a sanitized
  conflict and non-owned or missing deletes share one private not-found result.
- Watchlist responses derive latest available price, previous-available daily
  change, and first-available-observation YTD change from persisted PostgreSQL
  `adjusted_close` rows. One focused query returns at most the three required
  observations per symbol; no provider call, fill, fabricated price, or market
  data mutation occurs.
- Watchlist storage contains no holdings, quantities, invested amounts,
  allocations, prices, returns, or risk metrics and has no portfolio-analysis,
  simulation, reporting, or AI-agent effect.
- Complete focused Watchlist suite: 45 passed, including 2 guarded live
  PostgreSQL tests covering authenticated CRUD, enrichment, ownership
  isolation, uniqueness, user cascade, fresh-session persistence, cleanup,
  and preservation of the existing 95,488 market-data rows. Backend database
  regression suite: 196 passed. Complete unit and non-live API integration
  suite: 2,892 passed. Python compilation, dependency consistency, and Git
  whitespace checks pass.
- The populated local test database was upgraded additively from
  `d4a6f8c2e1b7` through the current `a8d3f1c6b2e7` head without changing
  existing row counts. A live Watchlist-only downgrade to `f2c8e9a1b3d4` and
  upgrade back to head also passed while preserving all existing market data.
- Web and mobile Watchlist integration was completed in the following frontend
  task without changing the backend contract.

### Completed Watchlist Frontend Integration V1

- Added typed web and mobile clients for authenticated `GET/POST
  /api/watchlist` and `DELETE /api/watchlist/{symbol}` through each platform's
  shared API client and centralized Bearer-session handling.
- Replaced both deferred Watchlist screens with real loading, empty, populated,
  retryable error, add, duplicate/unsupported, and remove states. Null market
  values render as an em dash, and the UI labels prices as latest saved data
  rather than live quotes.
- Reused each client's canonical 17-asset catalogue for local picker/search
  labels and exclusion of already-added assets. The clients do not calculate
  daily or YTD returns, call market-data providers, or persist a second local
  Watchlist authority.
- Preserved the existing web protected route and the mobile `More` stack route;
  no additional bottom tab or navigation architecture was introduced.
- Removed obsolete Watchlist mock datasets and the unused web summary component
  that derived client-side aggregate movement values.
- Web production-authority suite: 23 passed; TypeScript/Vite production build
  passed. Mobile production-authority suite: 35 passed; TypeScript checking and
  Expo public-config validation passed.

### Completed latest-analysis simulation references

- Web and mobile historical-scenario results now use the selected portfolio's
  newest saved analysis as the visible reference instead of a synthetic flat
  no-movement baseline.
- Web and mobile allocation-change results also show the newest saved analysis,
  its period, backend metrics, and exact report-detail action as additional
  context. The authoritative original-versus-modified calculation remains the
  backend comparison over one common requested period.
- New combined-simulation results directly compare the newest saved portfolio
  analysis with the modified portfolio under the selected historical scenario
  in a metric table and a selectable two-line normalized chart on both clients.
  The backend's period-matched original-versus-modified scenario comparison is
  still shown separately and remains authoritative for simulation deltas.
- The comparison identifies the saved report time and analysis period, exposes
  an exact report-detail action, and handles loading, missing-report, and
  retrieval-error states without invalidating the scenario result.
- Reference metrics come directly from the immutable saved analysis. Its chart
  path is a display-only normalized reconstruction of the saved backend return
  observations; scenario metrics and trajectory remain backend-owned.
- Trajectory charts on both clients show each selected line with its own date
  and normalized-value labels. The all-lines view omits x-axis dates when the
  compared periods may differ and retains shared normalized-value labels.
- Web production-authority suite: 29 passed and the production build completed.
  Mobile production-authority suite: 38 passed and TypeScript compilation
  completed.

### Completed mobile saved-simulation AI grounding

- Mobile saved-simulation detail now exposes an **Open AI Assistant** action
  that carries both the owning portfolio ID and the exact saved simulation ID.
- The Assistant preserves that immutable simulation context across the chat,
  sends `simulation_id` with every explanation request, shows simulation-
  specific starter questions, and clearly labels the selected snapshot.
- Users can explicitly switch back to live portfolio context. Changing the
  selected portfolio also clears the saved-simulation context and starts a
  fresh conversation.
- Mobile production-authority suite: 39 passed. TypeScript compilation
  completed successfully.

### Completed Backend Account Profile V1

- Extended the authenticated `GET /api/auth/me` response with nullable display
  name and phone number plus persisted language and timezone preferences.
- Added authenticated `PATCH /api/auth/me` for partial profile updates. Email
  changes require the current password, normalized duplicate emails return a
  sanitized conflict, and ownership always comes from the Bearer session.
- Added authenticated `PUT /api/auth/me/password` for current-password-verified
  password replacement. Passwords remain one-way hashed and are never returned.
- Added reversible migration `b9e4d2f7c1a6` with additive profile columns,
  safe defaults for existing users, and database constraints matching the V1
  language, timezone, and field-length contract.
- Kept transaction ownership at the API boundary: repositories flush but do
  not commit, while each successful mutation commits exactly once.
- Profile photos, notification delivery/preferences, session revocation, and
  password-reset email flows remain outside Backend Profile V1.
- Focused profile/auth suite: 74 passed. Expanded auth, migration, model, and
  API-contract regression suite: 101 passed. Isolated live PostgreSQL migration
  and authentication lifecycle suite: 2 passed, including persistence and
  downgrade cleanup. Python compilation passed.

### Completed Account Profile Frontend Integration V1

- Web and mobile Settings now read display name, email, optional phone number,
  preferred language, and timezone from the authenticated backend user instead
  of treating browser or device storage as profile authority.
- Both clients submit typed partial updates through `PATCH /api/auth/me`, only
  send changed fields, require the current password when the email changes, and
  immediately synchronize the returned user into shared authentication state.
- Both clients provide a separate current-password-verified password form using
  `PUT /api/auth/me/password`, including minimum-length, difference, and
  confirmation checks before submission.
- Backend validation, incorrect-password, duplicate-email, network, and server
  failures have themed inline presentation without exposing credentials or
  backend internals. Successful changes receive visible confirmation.
- Profile photos and notification controls remain visibly unavailable because
  Backend Profile V1 does not provide storage or delivery contracts for them.
- Web production-authority suite: 30 passed and the production build completed.
  Mobile production-authority suite: 40 passed and TypeScript compilation
  completed successfully.

### Completed internal frozen-artifact asset forecasting

- Internal forecasting loads the configured artifact version from trusted,
  read-only deployment storage. The registry validates all 34 symbol/target
  records and model/metadata checksums before deserialization and caches loaded
  models without caching forecast results.
- Inference uses the caller's current application database session and existing
  MarketDataService. The latest stored observation supplies the forecast origin;
  existing forecast-features-v1 construction and a four-calendar-day freshness
  limit remain authoritative.
- Frozen baselines use their serialized constants; fitted Linear Regression and
  Random Forest models consume the latest feature vector. ARIMA uses the approved
  deployment anchor: the first stored observation on or after the artifact cutoff
  is step one, and each subsequent stored observation advances one step. Missing
  dates and the purged training-label gap add no steps.
- The internal typed asset outlook applies frozen q10/q90 residual prediction
  intervals at nominal 80% coverage and preserves volatility non-negativity.
  There is no runtime fitting, state update, selection, calibration, or fallback.
- Validation uses synthetic artifacts and mocked market data. No generated
  artifacts, real databases, public forecast APIs, portfolio composition,
  forecast persistence, AI integration, or clients were changed.

### Completed authenticated current asset outlook API

- Added `GET /api/forecasting/assets/{symbol}/outlook` using Aura's existing
  Bearer authentication and application database session. Symbols follow the
  canonical 17-asset normalization and support rules; no portfolio context or
  historical/as-of input is exposed.
- Public Pydantic response contracts expose finite numeric predictions, nested
  nominal 80% prediction intervals, fixed 30-day horizon, current market-data
  provenance, selected model IDs, artifact version, and deterministic educational
  limitations. The pure mapper copies inference-owned values without rounding,
  clamping, or recalculating them.
- Unsupported symbols return safe 404 responses; stale data, insufficient
  history, artifact failures, and invalid predictions return safe 503 responses.
  Internal paths, residuals, evaluation metrics, credentials, and exception
  details are not exposed.
- Tests use mocked inference and sessions. Frozen model artifacts, internal
  prediction semantics, portfolio composition, persistence, migrations,
  scheduler/updater behavior, AI integration, and client code are unchanged.

### Completed authenticated portfolio forecast composition

- Added owner-scoped `GET /api/forecasting/portfolios/{portfolio_id}/outlook`
  with existing Bearer authentication, application sessions, and ownership-safe
  `404` behavior. No caller weight, horizon, scenario, or as-of override is
  supported; the endpoint is read-only and persists no forecast.
- Reused the authoritative baseline resolver: current USD valuation weights
  for CURRENT, saved weights for LEGACY, and existing proposed-amount target
  weights for PLANNED. The response identifies the baseline kind. Only sum
  drift within absolute `1e-10` is normalized; invalid/empty/unsupported
  allocations fail with a sanitized `409` rather than dropping components.
- Every component reuses frozen asset inference with one server-selected UTC
  reference date and the four-calendar-day freshness rule. Portfolio expected
  return is an arithmetic weighted sum, without compounding or annualization.
- Forecasting-local correlation computes log returns on each asset's stored
  calendar, intersects return dates, and uses the latest 60–252 common returns
  on or before the earliest component origin. A single batch historical query
  supplies correlation data; there is no provider call, filling, external
  calendar, or change to deterministic historical correlation.
- Portfolio forecast volatility uses `D @ R @ D` covariance and
  `sqrt(w.T @ Sigma @ w)`. Signed Euler contributions and shares are preserved;
  both are zero at zero portfolio volatility. Matrix tolerance is `1e-12` and
  negative variance roundoff is floored only within `1e-14` squared volatility
  units. Invalid/non-finite matrices or results fail with a safe `503`.
- Ordered components preserve their own origins, individual calibrated
  intervals, model IDs, artifact version, and market-data age. Portfolio
  market-data-as-of is the oldest component date. No portfolio prediction
  interval is created; deterministic wording explains correlation uncertainty
  and the educational/non-advisory scope.
- Added synthetic composition, response-schema, and authenticated API tests.
  Updated only the global OpenAPI inventory assertions in existing asset and
  reporting API tests; reporting behavior and contracts remain unchanged.
  The public API documentation now records the new endpoint and methodology.
- Validation: 106 targeted tests and 3,140 tests across the complete backend
  unit suite plus relevant database-free auth, portfolio, reporting,
  simulation/history, forecasting, Watchlist, health, and CORS API suites pass.
  Compilation, import/OpenAPI checks (25 paths/32 operations), `pip check`,
  and Git whitespace checks pass. All 68 frozen model/metadata files match
  their manifest checksums.
- No real database, real model evaluation/training, artifact writes, migrations,
  updater changes, AI/client changes, new dependency, commit, push, merge,
  PR, or branch change occurred. Live acceptance and the separate stale-market-
  data operational task remain outstanding; no subsequent phase was started.

### Completed offline selection dataset provenance support

- Both manual return/volatility selection commands now require an explicit
  environment file and accept `--database-url-key` (default `DATABASE_URL`).
  They reuse the fingerprint workflow's loader, read only the requested file
  key without interpolation/fallback, and never serialize connection details.
- Added a shared offline helper for canonical market-data fingerprinting and
  paired expected fingerprint/row-count verification. The loaded records are
  fingerprinted before history adaptation or any candidate evaluation; exactly
  those records supply the unchanged evaluator. Mismatch/invalid expectations
  stop without writing a selection report, and existing output is preserved.
- Reports now include additive actual cutoff, symbol count, row count, hash,
  and `provenance_verified` metadata. Developer runs without both expectations
  explicitly remain unverified. The selection-report parser/freezer already
  tolerates additive metadata and required no production change.
- Added mocked/synthetic tests for explicit key selection, missing-key and
  no-fallback behavior, credential-safe failures, gate ordering, mismatches,
  deterministic report metadata, unchanged numerical/selection results, and
  freezer compatibility. Targeted suite: 67 passed. Complete forecasting unit
  suite: 345 passed. Broader forecasting/schema/API suite: 474 passed.
  Compilation, import/parser checks, `pip check`, whitespace, and scope checks
  pass; both candidate evaluator functions are unchanged from HEAD.
- Documented exact user-controlled remediation commands with new report paths
  that preserve old selection evidence. No real evaluation, database access,
  fitting, manifest replacement, artifact generation, production inference,
  API, analytics, client, dependency, migration, or Git history change occurred.
- The original selection provenance remains insufficient: supporting future
  verified runs does not retroactively establish the original reports' dataset.
  Merge readiness remains blocked pending manual verified reports, comparison
  of their selections, and a separate decision on any versioned artifact work.

### Completed verified selection reconciliation and final readiness audit

- The user manually reproduced selection decisions on the authoritative frozen
  69,928-row, 17-symbol dataset at cutoff `2026-09-17`, fingerprint
  `dd8cfbe6963ffad4cb3f64034e834d324c7981426704193c00256c9add504e99`.
  Both supplied reports record verified provenance. Their byte SHA-256 values
  and the deterministic symbol-sorted reconciliation are recorded in
  `docs/development/forecasting-selection-provenance.md`.
- All 17 return and 17 volatility candidate IDs match both frozen manifests:
  34/34 matches. This resolves the prior selection-reproduction readiness gate.
  The original Phase 4/5 run dataset provenance was not independently recorded
  and is NOT newly proven. The original package `forecast-v1-20260917` remains
  frozen: it was NOT regenerated; calibration and final-test reports were NOT
  rerun. Verified reports supplement, rather than replace, the original evidence.
- Read-only artifact validation passes: 17 symbols, two targets, 34 unique
  artifacts, all 68 model/metadata checksums, completed final-test marker,
  feature/target versions, 0.80 interval coverage, authoritative fingerprint,
  canonical selection manifest hash, and embedded/source evidence consistency.
- Runtime review and synthetic regressions confirm application-session persisted
  data plus immutable model prediction only, approved ARIMA stored-calendar step
  alignment, no runtime training/provider/offline database calls, existing Bearer
  authentication, ownership isolation, and sanitized failure behavior. Shared
  modules contain offline helper definitions but request paths never call them.
- Portfolio composition retains authoritative weights, arithmetic weighted
  expected return, `D @ R @ D` covariance, square-root quadratic-form volatility,
  60–252 common-date log returns at the earliest origin, signed contributions,
  no filling/fallback/dropped assets, and no calibrated portfolio-level interval.
  API documentation now explicitly distinguishes deterministic historical
  analytics from 30-calendar-day non-annualized probabilistic forecasting,
  empirical asset intervals, and offline/versioned retraining. The existing
  `backend/.env.example` artifact version matches the frozen package unchanged.
- All 345 forecasting unit tests also pass in a dedicated run. All 3,219 backend
  unit and non-live API tests pass, including auth, portfolio,
  valuation, schemas, analytics, reporting, simulation, forecasting, and AI Agent
  regressions. Compilation, import/OpenAPI (25 paths/32 operations), `pip check`,
  whitespace, and scope checks pass. The 54 warnings are from the existing short
  JWT secret in AI test fixtures. Live/PostgreSQL integration tests were excluded.
- Added narrow root-output ignore rules for forecasting JSON evidence, the
  Supabase snapshot dump, and artifact backup ZIP. These files and frozen
  artifacts remain untracked/ignored; no user file was deleted or rewritten.
- Readiness decision: READY TO MERGE under the requested gates. Stale-data `503`
  is expected and does not block this decision; production updater restoration
  and fresh-data live acceptance remain separate operational follow-ups. Trusted
  immutable artifact deployment remains required; hashes are not authenticity
  proofs. Changes await user review and explicit commit authorization.
- No real database connection, ML training/evaluation, calibration/final testing,
  artifact generation, production code/contract change, dependency addition,
  commit, push, merge, PR, history rewrite, or branch switch occurred in this audit.

### Completed public web welcome page (2026-10-01)

- Added a long, responsive welcome page in Aura's existing navy/teal theme:
  product introduction, current/planned sample preview, workflow, risk analytics,
  selectable simulation chart lines, AI explanation example, expandable lessons,
  web/mobile illustrations, methodology, FAQ, and account calls to action.
- The root URL now opens Welcome for signed-out visitors. Session restoration
  keeps the focused loading screen, authenticated visitors continue to Dashboard,
  and existing saved-report/simulation deep links remain protected. Login and
  signup include a return link to Welcome.
- Product examples are clearly labelled illustrative, use no live account data,
  and do not calculate portfolio results. No backend, mobile app, dependencies,
  financial engine, or authentication contracts changed.
- Browser checks verified desktop and 390/320-pixel layouts, current/planned
  switching, single-line chart selection, lesson/FAQ disclosure, mobile menu and
  Escape handling, and Welcome/Login/Signup navigation. Fixed compact metric
  overflow and a missing accessible section label during visual review.
- Validation: production build and 34 web authority tests passed, including new
  runtime public-entry/session/protected-deep-link regressions. Changes remain
  uncommitted pending user review and explicit authorization.

### Completed mobile bottom-tab root navigation (2026-10-02)

- Bottom-bar taps now return Portfolio to Portfolios, Simulate to Simulations,
  and More to More instead of reopening the last detail screen. Each tap resets
  only the selected child stack, including direct-entry screens with no root in
  their existing history. Home and AI retain their native single-screen behavior.
- In-page report, simulation, and Ask Aura links retain their exact context;
  other tabs, shared portfolio state, and AI conversations are not reset.
- Added a navigation listener and small scoped action helper. Regression checks
  use the installed tab/stack routers for focused/unfocused tabs, normal history,
  cold deep links, empty root back history, and unchanged other-tab state.
- Validation: mobile TypeScript check and all 43 mobile authority tests passed.
  Physical-device interaction was not verified. No backend, web, API, dependency,
  financial calculation, commit, or push changes were made.

### Completed saved-simulation deletion (2026-10-02)

- Added Bearer-authenticated, owner-scoped `DELETE
  /api/portfolios/{portfolio_id}/simulations/{simulation_id}` returning empty
  `204`. Missing/unowned parents and missing/wrong-associated snapshots retain
  safe `404` responses. Failures roll back through the request dependency and
  expose no internal details; successful requests commit exactly once.
- Repository/service deletion removes only the selected snapshot without
  restoring its payload, recalculating results, or changing portfolios, reports,
  market data, or other simulations. All modes and V1/V2/V3 remain supported;
  no migration, dependency, or financial calculation change was required.
- Web Simulation History and Saved Simulation, plus mobile Recent Simulations,
  Simulation History, and Saved Simulation, now offer red delete actions with
  the existing Aura-themed confirmation dialogs. Cancel performs no mutation;
  failures remain visible for retry and duplicate submissions are blocked.
- Successful deletion removes the history row and returns detail views to
  history. Mobile shared history filters deleted IDs from in-flight refreshes,
  preventing stale responses from restoring deleted rows. Web ignores aborted
  history responses and removes confirmed deletions from its displayed list.
- Updated the public API contract and added authentication, privacy, transaction,
  transport/empty-response, confirmation/cancel/retry, duplicate-submission,
  and stale-history regressions. Verification: 3,237 backend unit/non-live API
  tests, 37 web authority tests, 46 mobile authority tests, both TypeScript
  checks, and the web production build passed.
- Live PostgreSQL and physical-device/browser acceptance were not performed.
  No user data was deleted, no database migration was run, and no commit or
  push was made; changes await user review and explicit commit authorization.

### Completed self-service account deletion (2026-10-02)

- Added Bearer-authenticated `DELETE /api/auth/me` with a required current
  password and empty `204` success. The service verifies the secret before
  deleting only the authenticated user; the API commits once, and failures
  roll back through the request dependency with sanitized error responses.
- Existing database cascades delete owned CURRENT/PLANNED/LEGACY portfolios,
  holdings, saved analyses/reports, all simulation modes, and watchlist entries.
  Shared market data and other users remain intact. Deleted-account tokens
  subsequently fail the persisted-user lookup. No migration is required.
- Added red Delete Account sections below Data & Support in web Settings and
  directly above Sign Out in mobile Settings. Both use red-themed confirmation
  dialogs with password input, permanent-deletion warnings, cancel/error/retry
  handling, and duplicate-submission guards. Existing web privacy/support
  previews remain inactive as requested.
- Both clients clear their sessions after success. Web also clears authenticated
  UI if token-storage removal fails; mobile retains its existing secure-storage
  cleanup error/retry flow. A cleanup failure never retries an already completed
  server deletion. Local Learn progress/preferences and exported files remain.
- Added API/service/transport/confirmation regressions and synthetic in-memory
  FK-cascade tests covering both portfolio types, every simulation mode, other
  users, market data, and rollback. Public API documentation was updated.
- Validation: backend unit/non-live API suites, both client authority suites,
  TypeScript checks, and web production build. Live PostgreSQL and physical
  device/browser account-deletion acceptance were not performed; no actual
  user accounts/data were deleted and no migrations, commits, or pushes were run.

### Completed sign-out confirmation dialogs (2026-10-02)

- Web profile-menu Sign Out and mobile Settings Sign Out now open the shared
  Aura red-themed confirmation dialogs before clearing the signed-in session.
  Mobile's saved-session recovery Sign Out also requires confirmation.
- Dialogs use sign-out icons, identify the account/device, and clearly state
  that account and saved portfolio/report/simulation data are not deleted.
  Cancel/Close perform no sign-out; confirmed actions retain the existing
  authentication and navigation flows, guarded against duplicate submissions.
- Mobile cleanup failures retain themed error/retry handling. Automatic session
  rejection and successful account-deletion cleanup do not prompt again. No
  backend API, database, dependency, preference, or financial changes were made.
- Added confirmation/cancel/stale-handler/error/retry/duplicate-tap regressions.
  Validation: 45 web authority tests, 51 mobile authority tests, both TypeScript
  checks, and the web production build passed. Browser/device acceptance was
  not performed; no commit or push was made.

### Completed themed About Aura settings popups (2026-10-02)

- Enabled only About Aura in web Data & Support; the other four web privacy,
  alerts, reset, and help previews remain disabled. Replaced mobile's native
  About alert with an Aura navy/teal themed modal opened from the existing row.
- Both clients show matching current/planned portfolio-risk, what-if simulation,
  AI Assistant, Watchlist, and Learn overviews. Copy distinguishes saved market
  observations from live quotes and explains Aura's educational,
  non-advisory purpose without promising future investment performance.
- Added themed Close/Done controls, bounded scrollable content, backdrop
  dismissal, mobile hardware-back dismissal, and web Escape/focus trapping,
  scroll locking, and focus restoration. No API call, data reset, or new
  dependency is required; unrelated settings behavior remains unchanged.
- Added interaction/content-parity/theme/accessibility regressions. Validation:
  46 web authority tests, 52 mobile authority tests, both TypeScript checks,
  and the web production build passed. Physical-device/browser visual acceptance
  was not performed. No backend, migration, commit, or push changes were made.

### Completed About Aura full-row interaction and product wording (2026-10-03)

- Web About Aura is now one full-width native button: icon, title, description,
  whitespace, and side arrow all open the existing popup. Keyboard activation,
  teal focus/hover styling, and side-arrow placement at narrow widths are retained.
  Mobile already uses a whole-row Pressable; regression coverage now verifies
  that the arrow is inside that same control.
- Removed academic-project branding from both About popups, the welcome footer,
  repository guidance, and the earlier status note. Aura is described as a
  portfolio risk education platform, with professional wording required for
  future features in AGENTS.md. No remaining wording matches were found in the
  repository source/documentation scan.
- Added full-row and branding regressions. Validation: 47 web authority tests,
  52 mobile authority tests, both TypeScript checks, and web production build
  passed. Browser/device visual acceptance was not performed. No backend,
  dependency, migration, commit, or push changes were made.

### Removed About Aura row background highlight (2026-10-03)

- Removed the web About Aura hover background while preserving the full-row
  click target, popup behavior, pointer cursor, and keyboard-only focus outline.
- Added a styling regression. Validation: 47 web authority tests and the web
  production build (including TypeScript) passed. No mobile/backend changes,
  dependencies, commits, or pushes were made; browser visual acceptance was
  not performed.

### Completed account-specific local portfolio privacy (2026-10-03)

- Enabled Hide portfolio values in web/mobile Settings with Aura-themed,
  accessible switches. Separate account-ID keys in browser localStorage and
  mobile AsyncStorage remember both On and Off across logout/login. New
  accounts and other devices/browsers default Off; logout never clears the
  choice. The old unused device-global mobile privacy field was removed.
- Added privacy providers inside each authentication provider and presentation
  helpers across Dashboard, current/planned portfolio details and holdings,
  analysis, asset risk, saved reports, simulations, and money-equivalent popups.
  Personal amounts, owned/estimated share quantities, and reference amounts
  render as masked text, not raw values hidden with CSS. Existing percentage/
  normalized charts, allocations, risk scores, public prices, FX rates, and
  Learn examples remain visible. Backend data and calculations are unchanged.
- Monetary/share editor fields show blank masked placeholders while privacy
  is On, with instructions to turn it Off before editing; underlying form
  values and payloads are preserved. AI questions, answers, grounding details,
  and the composer are shielded by a themed privacy notice while On, rather
  than relying on unreliable redaction of free-form prose. No new chat request
  can be submitted from the hidden UI.
- Mobile starts hidden until preference restoration completes, ignores stale
  account loads, and serializes rapid-toggle writes. Unreadable/malformed
  preferences fail closed; save failures explain that the choice is temporary
  and can be retried. This is local screen privacy, not encryption or account
  security; there is no backend preference, synchronization, or migration.
- Added account isolation, On/Off persistence, logout, new-device defaults,
  restoration, malformed/blocked storage, retry, ordered-write, masking,
  immutable-data, input, switch, and result-surface coverage. Validation:
  52 web authority tests, 57 mobile authority tests, both TypeScript checks,
  and web production build passed. Browser/physical-device acceptance was not
  performed. No dependencies, commits, or pushes were added.
### Local data reset and Learn completion — 2026-10-03

- Enabled Reset local data in web and replaced mobile's native reset alert with
  Aura-themed confirmation. Cancel and duplicate-submit guards, retryable
  partial-failure messages, and success notices are included. The warning
  explicitly says Hide portfolio values turns Off. Reset clears only the
  current account's local Learn progress/privacy choice; mobile also restores
  device appearance/notification preferences and removes obsolete demo keys.
  Server-owned account/profile, portfolios, holdings, reports, simulations,
  watchlist, authentication tokens, and signed-in sessions stay unchanged.
- Added account-scoped browser Learn progress and account-scoped mobile progress
  using local storage only. Opening lessons or YouTube does not complete them:
  users explicitly mark lessons completed and can undo completion. Counts,
  lesson badges, progress bars, and web learning-path groups reflect saved
  completion; storage failures are explained without claiming a successful
  save. Logout/login retains each account's choices on the same device/browser.
  Existing unscoped mobile Learn progress is not assigned to an account because
  its ownership is unknown; its legacy key is removed only on explicit reset.
- Strict privacy reset persists Off before revealing values. Mobile preferences
  serialize reset after earlier writes, and Learn ignores stale pre-reset reads.
  Other accounts' Learn progress and privacy choices are not cleared. No bulk
  storage clear, backend change, migration, or dependency was added.
- Validation: 57 web and 63 mobile authority regression tests (120 total), both
  TypeScript checks, web production build, and git diff whitespace checks passed.
  Browser/physical-device acceptance was not performed. No commit or push.
### Completed Help & Support guides — 2026-10-03

- Enabled the full Help & Support row in web Settings and replaced mobile's
  placeholder native alert with a dedicated Aura-themed guide. Web's protected
  help route uses the existing app shell; mobile's HelpSupport screen lives in
  the existing More stack. Both have explicit Back to Settings navigation,
  and the mobile More tab still returns to its root from Help.
- Added 20 matching code-owned help articles across Getting started, Portfolio
  types, Analysis & simulations, AI Assistant, Privacy & local data,
  Troubleshooting, and Support & safety. Guidance explains current shares
  versus proposed amounts, latest-analysis reference versus simulation baseline,
  saved snapshots, exact simulation AI context, local Learn/privacy persistence,
  reset versus deletion, and safe troubleshooting without investment advice.
- Search matches section titles, questions, and answer text, with result counts,
  no-match feedback, and Clear search. Web uses native keyboard-accessible
  details/summary accordions; mobile uses full-row expandable Pressables with
  expanded-state accessibility. Existing navy/teal styles, responsive web
  layout, and mobile theme colors are retained.
- Support is self-service only. No invented contact details, ticket form, live
  chat, password recovery, or notification delivery is enabled. Help does not
  call APIs, alter saved data, reset preferences, or change backend authority.
  No backend change, migration, dependency, commit, or push was made.
- Validation: 59 web and 65 mobile authority regression tests (124 total),
  both TypeScript checks, web production build, and diff whitespace checks
  passed. The web build reports a non-blocking minified chunk-size warning
  (507 kB main JS, about 146 kB gzip); code splitting was not changed in this
  task. Browser/physical-device visual acceptance was not performed.

### AI help capability audit and answer table rendering — 2026-10-03

- Checked the existing agent prompt, orchestration, request schema, and public
  contract. Aura receives portfolio, selected/latest report, and optional exact
  saved simulation context; it does not receive the Help & Support articles.
  The API still requires a portfolio ID. General risk concepts overlap, but
  local reset/privacy/support workflows are not grounded in the approved guide.
  This was a capability check only: no backend, prompt, contract, or Help
  knowledge integration was changed.
- Extended matching code-owned answer parsers on web/mobile to recognize
  Markdown tables with headers and valid delimiter rows, optional outer pipes,
  alignment markers, bold text, escaped pipes, and code-span pipes. Fenced
  examples and incomplete/malformed table rows remain literal text rather than
  losing or shifting values. Existing headings, paragraphs, and bullets remain.
- Web answers now render semantic tables with column headers and a themed,
  keyboard-focusable horizontal scroll region. Mobile answers use themed,
  horizontally swipeable tables with selectable text, header accessibility,
  and per-cell column/value labels. HTML is rendered as text; no HTML injection
  or WebView was added. Answers, request/history payloads, backend financial
  calculations, AI safety boundaries, and local privacy behavior are unchanged.
- Validation: 61 web and 67 mobile authority regression tests (128 total),
  25 existing backend agent/prompt tests, both TypeScript checks, web production
  build, and diff whitespace checks passed. Existing non-blocking main-bundle
  size warning remains (about 509 kB minified / 147 kB gzip). Browser/device
  visual acceptance and live-provider checks were not performed. No dependency,
  migration, commit, or push was added.

### Account-owned in-app notifications V1 — 2026-10-03

- Added notification/preferences ORM models, a scoped repository/service,
  strict schemas, and five authenticated notification operations using the
  existing shared FastAPI/PostgreSQL architecture. Account-owned master,
  analysis, and simulation preferences default On and survive logout/login.
  Off suppresses future events without deleting old messages; re-enabling
  does not backfill existing history. Local reset does not change these settings.
- New report and all three simulation API saves record generic notifications
  before the same single commit. Errors roll back the save and notification;
  unique target keys deduplicate repeated recording of the same result. Exact
  portfolio/resource ownership is checked without reading financial snapshots.
  Messages contain no portfolio names, balances, holdings, or financial advice.
  Result/portfolio/account deletion cascades related notifications, and account
  deletion also removes notification preferences.
- Added migration `c3d5e7f9a2b4` after `b9e4d2f7c1a6`. The migration has been
  checked against ORM metadata and generated PostgreSQL upgrade/downgrade SQL
  without applying it to a deployed database. Apply it before using notification
  APIs or creating new reports/simulations with the updated backend.
- Web navigation now has a working unread-count bell and protected, themed
  inbox/preferences routes. Mobile More has an unread-count Notifications entry,
  and Settings opens matching account preference controls. Both clients show
  newest-first paginated updates, exact saved-result links, mark-one/all-read,
  loading/empty/error/retry states, and guarded writes. Background/hidden polling
  stops; foreground refresh uses 30-second intervals. Read/settings mutations
  refresh badges, and stale account/unmounted responses cannot restore old UI.
- Added matching typed API adapters, state/foreground hooks, web CSS, mobile
  navigation/screens, persistence/API/interaction tests, and updated public
  API/backlog/Help guidance. Removed the obsolete unused mobile device-global
  notification preference so local reset cannot imply resetting account settings.
- Validation: 3,290 backend unit/non-live API tests; 76 web/shared-client tests
  and 67 mobile authority tests (143 client tests total); both TypeScript checks;
  web production build; migration SQL/model parity. Existing short-JWT-fixture
  warnings and the non-blocking web bundle warning remain.
- Live PostgreSQL notification acceptance and browser/physical-device visual
  acceptance are pending. No phone/browser push, email delivery, OS permission
  prompt, device tokens, price alerts, new dependencies, deployed migration,
  commit, push, or financial calculation changes were made.

### Unread notification dots and clear inbox actions — 2026-10-03

- Web TopNavigation and mobile More Notifications icons now show a small red
  top-corner dot only when the account has unread notifications. Accessible
  labels retain the unread count; zero/unknown counts do not show a dot.
- Both notification inboxes now offer Clear notification and Clear all
  notifications with existing red-themed danger confirmations. Clear-all
  covers every page. Cancel revokes authorization; duplicate confirmations,
  failed writes/retries, stale accounts, and unmounts are guarded. Already-cleared
  single entries refresh safely; an emptied late page returns to page one.
  Successful clears refresh inbox totals and the unread indicator.
- Updated notification repository/service/routes with authenticated,
  account-scoped DELETE operations, and both client API adapters/state hooks.
  Only notification messages are removed; saved reports, simulations,
  portfolios, and account notification preferences remain unchanged.
  No extra migration is required beyond notification V1's c3d5e7f9a2b4.
- Updated public API documentation (30 paths / 41 operations) and added
  persistence/API/interaction regressions for ownership, rollback, sanitization,
  confirmation, cancellation, retry, pagination, counts, and red-dot rendering.
- Validation: 3,301 backend unit/non-live API tests; 86 web/shared-client tests
  and 67 mobile authority tests (153 client tests total); both TypeScript checks;
  web production build and whitespace checks passed. Existing short-JWT fixture
  warnings and the non-blocking web main-bundle warning (about 520 kB) remain.
  Live PostgreSQL and browser/physical-device visual acceptance were not run.
  No dependencies, deployed migrations, commits, pushes, push delivery, or
  financial calculation changes were added.

### Compact notification actions — 2026-10-03

- Updated web NotificationsPage and mobile NotificationsScreen to label each
  single-notification removal action "Delete", including its confirmation
  button; the dialog still identifies the notification being deleted.
- Web notification CSS now gives Clear all notifications a dark-red box,
  red border, rounded corners, hover/focus styling, and disabled state.
  Mobile retains its existing boxed danger Button for that action.
- Updated shared notification UI regression tests to verify labels, boxed
  styling, and unchanged confirmation behavior on both clients. Backend,
  account isolation, saved resources, and deletion behavior are unchanged.
- Validation: 86 web/shared-client tests, mobile TypeScript check, web
  TypeScript/production build, and whitespace checks passed. Existing web
  bundle-size warning remains; browser/device visual acceptance was not run.
  No dependencies, migrations, commits, or pushes were added.

### Smaller web notification cards and controls — 2026-10-03

- Reduced NotificationsPage card padding, icon size, heading/body sizes,
  button padding/type size, and list/pagination gaps in its scoped CSS.
  Actions now share a compact horizontal row instead of a tall stack.
- Actions wrap below the content on narrower screens, with 44px minimum
  button heights for touch layouts. Red delete/clear-all styling, unread state,
  confirmations, and all notification behavior are unchanged. Mobile and
  backend code were not modified.
- Updated the page icon and added a scoped-layout regression. Validation:
  87 web/shared-client tests, TypeScript/production build, and whitespace checks
  passed. Existing bundle-size warning remains. Browser visual acceptance was
  not run; no dependencies, migration, commit, or push was added.

### Matching risk label and score colors — 2026-10-04

- Web AssetAnalysisCard now colors the combined score/label by its saved
  classification rather than fixed teal. Low uses green, Moderate amber,
  and High/Very High red. Analytics summaries, asset-risk detail headings/
  score cards, dashboard risk KPI values/labels, and gauge numbers match.
  Added a presentation-only riskColor helper in the existing analyticsUi file.
- Mobile AnalysisResults, AssetRiskDetailScreen, and DashboardScreen now color
  scores consistently with their existing RiskBadge/riskTone palette, including
  current, planned, and legacy asset rows. WebKpiCard accepts an optional value
  color only used for risk scores; other metric values keep their styling.
  Missing/legacy classifications remain absent or neutral, never invented.
- Added client regressions for all four saved levels, label/score consistency,
  neutral missing data, unchanged unrelated KPIs, and backwards-compatible
  gauge callers. The same test number is used with different saved labels to
  ensure the UI does not calculate or override backend classifications.
- Validation: 89 web/shared-client tests and 68 mobile authority tests (157
  total), both TypeScript checks, web production build, and whitespace checks
  passed. Existing web bundle warning remains. Browser/device visual acceptance
  was not run; backend calculations, dependencies, migrations, commits, and
  pushes are unchanged.

### Dashboard View analysis jumps to Risk Drivers — 2026-10-04

- Web dashboard RiskDrivers now opens the exact saved report used by the
  dashboard with a risk-drivers section target instead of the analysis setup
  page. Loading disables the action; without a report it retains setup navigation.
- Added the section anchor to AnalysisResults and a matching App/ReportDetailPage
  focus flag. Scrolling waits until the report is loaded and rendered, preserves
  the existing per-asset section jump, and does not create a new analysis.
- Mobile DashboardScreen's corresponding action now says View analysis and
  opens that saved report with a typed focusRiskDrivers flag. AnalysisResults
  reports section layout; ReportDetailScreen waits for both offsets and guards
  scheduled scrolls after blur/unmount. Normal report opening remains unchanged.
- Updated client regression tests for exact-report navigation, no-report
  fallback, loading guards, deferred section scrolling, existing asset jumps,
  and mobile layout/unmount behavior. Validation: 91 web/shared-client tests
  plus 69 mobile authority tests (160 total), both TypeScript checks, web
  production build, and whitespace checks passed. Existing bundle warning
  remains. Browser/device visual acceptance was not run; no backend changes,
  dependencies, migrations, commits, or pushes were added.

### Keep report section headings visible after jumps — 2026-10-04

- Fixed web ReportDetailPage section jumps hiding Risk Drivers under the sticky
  top bar. Before scrolling, the target's scroll margin now includes the measured
  navigation height plus 18px of spacing, instead of only the original 18px.
  This also protects the existing per-asset jump and adapts to wrapped navigation
  on narrow browser layouts without changing the report or page structure.
- Extended the report-jump regression to cover desktop, wrapped/fractional-height,
  and absent navigation, alongside loading guards and untargeted report opening.
  Validation: 91 web/shared-client tests, TypeScript/production build, and
  whitespace checks passed. Existing bundle warning remains; browser visual
  acceptance was not run. Mobile, backend, dependencies, migrations, commits,
  and pushes were unchanged.

### Portfolio return table date sorting — 2026-10-05

- Web AnalysisResults now defaults the saved portfolio-return table to newest
  dates first. The Date header toggles ascending/descending order with a visible
  arrow and Newest first/Oldest first label, keyboard focus, and aria-sort.
  Changing order scrolls the table to the top; opening another report resets
  to newest first. The existing stylesheet supplies compact themed styling.
- Sorting uses a copy of saved observations, preserving date/return pairs,
  negative-value formatting, and the chronological graph. Mobile has a graph
  but no equivalent observations table, so mobile and backend are unchanged.
- Added a regression for both orders, report changes, scroll reset, immutable
  saved data, unchanged chart points, and empty/single-observation reports.
  Validation: 92 web/shared-client tests, TypeScript/production build, and
  whitespace checks passed. Existing bundle warning remains; browser visual
  acceptance was not run. No dependencies, migrations, commits, or pushes.

### AURA Senior Project 1 report outline — 2026-10-06

- Added `docs/report/AURA_Senior_Project_1_Report_Outline.md` with the supplied
  VMES template's front matter and six-chapter structure, References, and
  supporting appendices, using one-sentence content placeholders.
- Reviewed the supplied AU Document Wallet and Libby-bot reports, AURA proposal,
  current implementation records, contracts, and relevant source code to define
  the report scope around AURA's delivered portfolio risk education workflows.
- Included 30-day asset and portfolio forecasting in the report's implemented
  feature scope at the user's request. The backend is implemented; the user is
  completing its frontend, and final UI screenshots and integration evidence
  will be incorporated when the complete report is drafted.
- The outline separates recorded verification from pending user, device, live
  database, and deployment acceptance, without inventing results or feedback.
- Documentation structure and placeholder checks passed. No application code,
  dependencies, migrations, commits, or pushes were changed by this report task.

### Deployment-ready backend market-data refresh — 2026-10-06

- Added tracked refresh orchestration around the existing fetch/clean/validate
  pipeline and MarketDataService. Scheduled, startup/hourly catch-up, and the
  persisting manual CLI share a dedicated PostgreSQL session advisory lock.
  Bounded transient/partial retries use capped backoff; invalid data does not
  retry. Lost locks abort before price writes without silent reconnection.
  Explicit unlock and non-pooled connection closure protect session cleanup.
- Automatic/default coverage ends yesterday UTC. Unexpected symbols or dates
  are rejected. Valid partial results preserve existing observations for failed
  symbols; prices and final run state commit together, with rollback on failure.
  Complete daily markers survive failures/subset backfills. Missed schedules
  recover in one refresh instead of replaying each missed day.
- Added a separate worker-leader lease, 60-second heartbeat, immediate/hourly
  catch-up, graceful interruption, and nonzero exit after heartbeat loss for
  future supervisor restart. The daily default remains 02:00 UTC (09:00 Thailand).
  Imports and FastAPI startup never launch the worker. Runtime hosting/restart
  configuration and Windows Task Scheduler installation are not included.
- Added MarketDataRefreshState, repository, strict status schemas/service, and
  authenticated read-only GET /api/market-data/status. Liveness, fetch outcome,
  and observation freshness are independent; no customer update trigger exists.
  Status uses completed-date checks, daily crypto coverage, and the existing
  four-day tolerance elsewhere without changing valuation/forecasting rules.
  Runtime/API/configuration errors hide credential-bearing details.
- Added migration d6e8f0a2b4c6 after c3d5e7f9a2b4, example settings, public
  contract updates (31 paths / 42 operations), and the deployment worker guide.
  Apply the migration before using status or the tracked worker/manual updater;
  it has not been applied to the application/Supabase database.
- Validation: 3,359 unit/non-live API tests passed; 9 environment-dependent
  tests skipped. Six guarded PostgreSQL acceptance tests passed in temporary
  UUID-named local schemas, validating migration DDL, real locks, transaction
  rollback, partial preservation, heartbeat, and killed-session recovery.
  All fixture schemas were cleaned up; existing application tables/data were
  unchanged. Migration/model parity and whitespace checks passed. Existing
  short-JWT-fixture warnings remain unrelated.
- No real-provider download, production migration, worker activation, Windows
  task, deployment, frontend change, analytics-formula change, production model training,
  artifact regeneration, dependency, commit, or push was performed. Real-provider
  and chosen-host acceptance remain deployment prerequisites. Unrelated report
  outline/documentation edits in the shared workspace were preserved.

### Web/mobile daily market-data integration — 2026-10-06

- Added matching typed GET-only marketDataApi adapters, foreground refresh hooks,
  scoped freshness presentation, and compact themed MarketDataStatus components
  in both clients. Watchlist and current-portfolio dashboard/detail screens show
  saved daily price freshness, last-check time, worker connectivity, and partial/
  failed update warnings. Only displayed instruments affect the freshness label;
  THB valuation includes the internal FX observation. A persisted running flag
  is not presented as proof of an active provider download.
- Existing page loaders read prices on entry. Return-to-foreground and five-minute
  active polling reload persisted Watchlist/current values. Web has a compact
  Refresh button; mobile keeps/adds pull-to-refresh. Polling stops in hidden tabs,
  background apps, or blurred mobile screens. Status reads abort/timeout and guard
  late account/unmounted responses; status failure does not block price APIs.
- Watchlist refreshes preserve rows after failed reads and abort pre-mutation
  reads so they cannot restore deleted assets. Current-value refresh remains
  independent from saved analysis; planned allocations and immutable report/
  simulation history are unchanged. No client financial calculations were added.
- Added shared market-data tests to the web authority runner and updated the
  market-data contract/integration backlog. Validation: 17 new shared regressions,
  91 existing web/shared regressions, and 69 mobile regressions passed (177 total).
  One pre-existing branding regression fails on the unrelated report-outline entry
  in this file, preserved unchanged. Both TypeScript checks, web production build,
  and whitespace checks passed; the existing bundle-size warning remains.
- Browser/device and authenticated runtime acceptance remain pending. No backend
  code, migration application, worker activation, deployment, Windows task,
  provider download, forecasting artifact, dependency, commit, or push was added.
  Migration d6e8f0a2b4c6 and separately supervised worker activation are still
  runtime prerequisites; client Refresh reads saved data only. Unrelated
  docs/report files were preserved.

### Academic report first draft — 2026-10-07

- Created `docs/report/AURA_Senior_Project_1_Report_V1.docx`, a 41-page report
  using the supplied university template and the user's revised chapter scope.
- Updated the companion outline to place the overview first, combine the
  existing-system review/comparison, shorten methodology, remove the requested
  standalone design and feedback sections, and retain two supporting appendices.
- Included recorded implementation and verification evidence, verified external
  references, illustrative calculation examples, and the complete forecasting
  selection table without inventing final-test performance or feedback results.
- Preserved 15 labeled visual placeholders and student, advisor, committee, and
  academic-detail placeholders. Refreshed the contents and figure/table indexes.
- Verified all 41 rendered pages, native equations, structure, pagination, table
  layout, and preservation of the original template geometry and opaque parts.
- No application code, dependencies, database records, commits, or pushes changed.

### Web forecasting V1 outlook preview — 2026-10-07

- Added an authenticated Forecasting page under Analytics, with portfolio and
  standalone asset views using the existing GET-only forecasting endpoints.
  Portfolio details, dashboard Core Workflows, and Watchlist list/grid now have
  contextual outlook links. The existing top-bar structure remains unchanged.
- Added typed transport, scoped/cancellable/timeout-aware loading, response
  checks, and sanitized errors. Account/selection changes suppress old estimates;
  no saved reports, forecasts, simulations, or financial mutations are created.
- Added themed return/volatility cards, asset nominal 80% ranges, actual model/
  origin metadata, backend limitations, portfolio component tables, and signed
  contribution bars. Current/planned/legacy use one screen with truthful baseline
  labels. No client forecast calculations, monetary estimates, or risk levels.
- The 7/14/21/30-day horizon layout is present, but only 30 days is enabled.
  V1 supplies a single chart marker and asset range bars, not a daily trajectory
  or a four-horizon line. Explicit multi-point chart support uses a dashed visual
  guide for a later backend integration; no weekly estimates or portfolio ranges
  are interpolated or fabricated. Return/volatility have separate chart views.
- Added 13 forecasting regressions and the web integration/acceptance report at
  docs/development/web-forecasting-v1.md. Full web/shared-client runner: 121 passed,
  one pre-existing branding failure on unrelated report-outline wording retained
  unchanged. TypeScript, production build, and whitespace checks passed; the
  existing bundle-size warning remains. Browser confirmed the protected route
  redirects to login; authenticated real-data/responsive visual acceptance is
  pending because no signed-in session was available.
- Mobile, backend, frozen artifacts, dependencies, migrations, model training,
  provider downloads, commits, pushes, and deployments are unchanged. Unrelated
  report files and concurrent report status entries were preserved. Weekly model
  support and forecast-specific AI/persistence remain separate follow-on work.

### Mobile forecasting V1 outlook preview — 2026-10-07

- Added authenticated portfolio and standalone asset outlooks in the existing
  Portfolio/More stacks, with entry points from More, Analytics, portfolio
  details, Home and Watchlist. The five bottom tabs and root behavior remain
  unchanged; contextual header Back and component drill-down are covered.
- Added typed GET transport, account/selection-scoped loading, focus cancellation,
  response checks, timeouts, manual/pull refresh and sanitized errors. Portfolio
  list failures do not block standalone assets; no report or forecast is saved.
- Added themed return/volatility cards, asset nominal 80% ranges, native SVG axes
  and actual 30-day markers, signed contributor bars, component allocations,
  model metadata and limitations. Current/planned/legacy labels remain accurate.
  Weekly controls stay disabled; no weekly estimates, price paths, portfolio
  intervals, risk classifications or client financial forecasts are invented.
- Mobile TypeScript and 84 regressions passed (15 new forecasting checks).
  Shared market-data/notifications and web forecasting: 56 passed. Full web
  runner: 121 passed with the same unrelated report-wording branding failure
  preserved. Android Hermes export passed after approved compiler execution;
  ignored build output stays under mobile/.expo/. Whitespace checks passed.
- Added docs/development/mobile-forecasting-v1.md with file purposes, verification
  and phone acceptance steps. Device visual/authenticated real-model acceptance
  is pending; Node orchestration tests and export are not device E2E checks.
- Backend, frozen artifacts, models, migrations, web production code, dependencies,
  provider data, commits, pushes and deployments remain unchanged. Concurrent
  report content was preserved. Weekly model support remains follow-on work.

### Multi-horizon forecasting offline selection foundation — 2026-10-07

- Added isolated, horizon-aware 7/14/21-day label construction and feature joins,
  reusing V1 feature/model families through an explicit private candidate bridge.
  Returns and non-annualized volatility use actual horizon observations, not
  scaled 30-day estimates. Calendar endpoints retain the four-day slippage cap.
- Added a manual selection-only evaluator with explicit local snapshot/URL-key
  selection, required fingerprint/row-count verification, read-only database
  transactions, safe errors, strict correctly labeled JSON and new-output guards.
  Database resources close before estimator fitting. Evidence cannot overwrite
  frozen V1 files or be treated as deployable weekly artifacts.
- Selection preserves V1 policy and chronological training purges, adding an
  isolated scoring-endpoint boundary so labels do not cross into later folds or
  reserved calibration/final-test periods. Missing fold/model availability is
  reported, not silently replaced. The original V1 evaluation is unchanged.
- Added synthetic/mocked regressions and a manual rollout guide at
  docs/development/multi-horizon-forecasting.md. Tests, builds and all real-data
  evaluation/training were deliberately not run, per the user's manual-terminal
  instruction. Verification and selection results await the user's commands.
- This is the first rollout checkpoint only. Selection freeze, separate horizon
  calibration/final testing/artifact training, runtime APIs, portfolio composition
  and client horizon activation remain pending. Weekly controls stay disabled.
- Frozen 30-day artifacts, original forecasting source/tests/APIs, database data,
  provider data, frontend code, dependencies, architecture files, commits and
  pushes remain unchanged. Unrelated report work is preserved. The recorded
  frozen snapshot is reusable for comparisons, not a new untouched project-level
  final holdout; fresh-period acceptance must be distinguished from that reuse.

### Verified isolated V1 training snapshot and explicit selector — 2026-10-07

- The user ran the targeted suite: 526 passed. The initial real selection attempt
  correctly stopped at provenance validation before fitting; the ordinary Docker
  snapshot had 95,488 rows, while current Supabase matched the original counts but
  not its canonical fingerprint.
- At the user's explicit choice, manual commands created the isolated local
  `aura_forecast_training_20260917` database and market-data table and restored
  the original data-only backup in a single transaction. The user then reported
  69,928 rows and the exact original V1 SHA-256, confirming the intended dataset.
- Added an optional, narrowly validated `--database-name` to the new horizon
  evaluator. It reuses the explicit local connection's credentials/host/port and
  selects only an `aura_forecast_training_` database in memory, without editing
  environment files or relaxing the fingerprint gate. Default behavior remains
  unchanged. Added selector regressions and updated the manual command guide.
- This subsequent selector change awaits user-run tests. No agent-run tests,
  training, provider requests or database operations occurred. New-horizon model
  fitting, selection review, calibration, final testing, deployment artifacts
  and client activation remain pending. Original V1 models and application
  databases were not replaced; unrelated report status/content was preserved.

### Report Version 2 review and wording — 2026-10-07

- Created `docs/report/AURA_Senior_Project_1_Report_V2.docx` from the saved
  report and its two reviewer comments; Version 1 remains unchanged.
- Removed the abstract's final paragraph and all of Appendix B.2, including
  its table. Rewrote the main prose with shorter sentences, simpler wording,
  and necessary technical terms, while preserving formulas and evidence limits.
- Updated forecasting descriptions to include the implemented web and mobile
  outlook screens, their recorded checks, the active 30-day horizon, and pending
  authenticated runtime and device acceptance. No weekly runtime capability
  or user feedback results are claimed.
- Updated the companion outline to match revised headings and appendix scope.
  Retained 15 visual placeholders and student, advisor, and committee fields.
- Refreshed the contents and figure/table indexes in Word and visually checked
  all 40 rendered pages. Structure, equations, template fidelity, comment removal,
  source preservation, text bounds, and document field checks passed.
- No application code, dependencies, database data, commits, or pushes changed.

### Reviewed weekly selection and prepared offline freeze — 2026-10-07

- Reviewed the user's completed 7/14/21-day selection report read-only: verified
  original V1 dataset provenance (69,928 rows, 17 assets), all 102 groups and
  2,550 available candidate/fold results, and independently recomputed leaders.
  Source report SHA-256:
  `9579936f543c20a9b7adf117bba982375cb518ea22378b9f831c9379d60fea06`.
- The evidence contains 57 ARIMA convergence warnings, including one on selected
  QQQ 21-day volatility in selection fold 05. The existing available-fit policy
  is preserved; selected warnings remain explicit, with no silent reselection.
- Added a separate horizon-aware selection manifest validator/freezer and manual
  CLI. They pin the source checksum and approved dataset, recheck five-fold
  coverage/policy/versions/counts, preserve selected warnings, validate output
  round trips and refuse overwrites or writes into frozen V1/artifact folders.
  Output remains selection-only evidence, not deployable weekly models.
- Added synthetic regressions and updated the manual rollout guide. Tests and
  freeze execution await the user's terminal run; no manifest, calibration,
  final-test evidence or model artifact was generated by the agent.
- Original 30-day source/package, runtime APIs, clients, environment files,
  databases and dependencies remain unchanged. Weekly controls stay disabled.
  Unrelated report work was preserved; no commit, push or deployment occurred.

### Verified weekly freeze and prepared manual calibration — 2026-10-07

- The user ran the targeted forecasting/schema/API suite: 627 passed. The
  weekly freezer completed 102 selections and retained the QQQ 21-day volatility
  convergence warning. Read-only inspection verified original-data provenance,
  unchanged source evidence and canonical manifest SHA-256:
  `829b5f9616643c3969cbd1cf220ce25b113d1b494b88c0693e376d5c43292a5c`.
- Added isolated weekly calibration orchestration and a manual command. The
  pinned manifest is reconciled against its original source report before DB
  access; the explicit local training snapshot is verified in a read-only
  transaction and closed before selected-candidate fitting.
- Calibration removes final-test prices before feature/label construction,
  purges training/scored endpoints at both calibration boundaries and requires
  756 training origins plus 60 residual observations. It reuses actual-minus-
  prediction q10/q90 calculations and volatility clipping, without rescaling
  30-day ranges, changing winners, fallback, or creating portfolio intervals.
- Separate, checksum-bound calibration evidence records all 102 target/horizon
  identities, source/provenance, quantiles, metrics, counts and boundaries.
  Selection warnings and new fit warnings remain distinct. Existing output,
  frozen V1 evidence and model-artifact folders are protected from writes.
- Added synthetic/mocked regressions and updated the manual guide. The 627-pass
  result predates these additions; new tests and calibration execution await the
  user's commands. No agent-run calibration, final test, deployment fitting,
  database operation or provider request occurred in this checkpoint.
- Original V1 source/models, APIs, clients, dependencies and environment files
  remain unchanged. Final testing, artifacts, runtime support and weekly client
  activation remain pending. No commit or push; unrelated report work preserved.

### Report Version 3 comments and scope — 2026-10-07

- Created `docs/report/AURA_Senior_Project_1_Report_V3.docx` from the six saved
  Version 2 comments, preserving the commented source document unchanged.
- Revised forecasting wording to explain its practical value, expanded the
  LEGACY definition with an allocation example, explained FR identifiers, and
  distinguished the 90-day historical averaging window from forecast horizons.
- Included the 7/14/21-day extension in methodology and scope while retaining
  the established 30-day results and separate verification boundaries. No
  weekly predictive-performance or authenticated-runtime results were invented.
- Added the user-confirmed admin scope: Dashboard, Users, Market Data, AI
  Monitoring, System Health, and Audit Log. Requirements, diagrams, UI, audit
  design, and acceptance placeholders reflect these modules. Forecasting
  Monitoring and analysis/simulation dashboard statistics remain recommendations.
- Updated the companion outline. Kept two appendices, 15 visual placeholders,
  editable equations, and student, advisor, and committee-name fields.
- Refreshed Word indexes and checked all 41 final rendered pages. Structure,
  comments, source preservation, template geometry and opaque parts, field
  references, tables, page breaks, and text bounds passed document verification.
- No application code, dependencies, database data, commits, or pushes changed
  in this report task; concurrent forecasting development was preserved.

### Verified weekly calibration and prepared guarded final test — 2026-10-07

- The user ran 661 targeted forecasting/schema/API tests and calibrated all
  102 frozen weekly selections. Read-only review verified provenance, selection
  matches, finite ordered ranges, endpoint boundaries and the canonical checksum:
  `0f42993972269884b160ff9983555abad865ddd07483c574205b37f15a9a2ab1`.
  Minimum residual count is 113; minimum training count is 2,413. One selection
  warning remains; no new calibration fit warnings were recorded.
- Added an isolated strict calibration reader and final-fold scoring workflow.
  Manifest/source and calibration hashes/contracts are pinned before DB access;
  the original snapshot is read-only and verified, then closed before fitting
  the frozen candidates on labels completed before the test fold starts.
- Final scoring preserves the existing winners and q10/q90, records errors,
  direction accuracy, clipping, inclusive empirical coverage, widths and date
  boundaries. Empty clipped volatility intervals are flagged and count as
  misses, without widening ranges or hiding finite poor performance.
- Added fixed, exclusive, ignored one-run start/completion markers per weekly
  release. Once scoring starts, failures remain consumed and changing report
  filenames cannot retry the final test. Bad pre-run inputs/provenance do not
  consume it. No automatic reset or force option is provided.
- Added synthetic/mocked regressions and updated the manual guide. The 661-pass
  result predates these additions; new tests and final evaluation await user
  commands. No final scoring, model fitting, DB/provider operation or run-marker
  creation was performed by the agent in this implementation checkpoint.
- No original 30-day source/models, APIs, clients, dependencies or environment
  files changed. Deployment-artifact fitting, acceptance review, runtime support
  and weekly UI activation remain pending. No commit or push; unrelated report
  content and concurrent status work preserved.

### Report visuals and source links — 2026-10-07

- Updated the existing V3 Word report in `docs/report/` in place. Added all
  15 numbered figures with 31 panels: project diagrams, authenticated web
  screenshots, and a graph of the recorded 30-day selection-fold MAE values.
- Added 13 underlined Source links. Ten point to verified external sources;
  three point to actual local project files. Student, advisor, and committee
  names remain placeholders. Admin visuals are labelled as design evidence,
  and final admin access verification remains pending.
- With user authorization, created `Report Example Current` (five AAPL shares
  and twenty BND shares) and `Report Example Planned` (USD 1,500 SPY and
  USD 1,000 BND). Saved one historical analysis and one Combined Simulation
  for the Current example, and captured real asset/portfolio 30-day outlooks
  and an actual grounded AI explanation. These examples remain in the account.
- Recorded the completed local web demonstration in the report. Weekly
  controls remain disabled in the captured runtime. No weekly performance
  results, admin statistics, or device-acceptance claims were invented.
- Refreshed Word indexes and reviewed all 62 rendered pages, including the
  changed pages after corrections. Verified image sources, 13 hyperlink
  targets, equations, table structure, name fields, template geometry and
  preserved parts. Updated the companion outline and retained visual sources
  and capture notes under `docs/report/assets/`.
- No application code, dependencies, forecasting artifacts, architecture,
  commits, or pushes changed. Concurrent forecasting work was preserved.

### Reviewed weekly final test and prepared experimental artifact training — 2026-10-07

- The user ran 721 targeted forecasting/schema/API tests and completed all
  102 weekly final-test selections once. Read-only review independently verified
  canonical SHA-256 `e2aeb387fa10376f2f925d74138f194c4ce102494a64bafb0e6703fbc22d7193`,
  original provenance, frozen ranges/identities and recorded date/count boundaries.
  Minimum final observation/training counts are 237/2,597. No new fit warnings
  or empty intervals; the original QQQ selection warning remains preserved.
- Pooled return coverage is 79.03%/70.15%/72.33% at 7/14/21 days, and volatility
  coverage is 77.30%/77.95%/81.73%. Return direction accuracy is about 51%.
  Individual quality can be weak (BTC-USD 14-day volatility coverage 15.38%; SLV
  21-day return coverage 29.96%). This is not predictive-quality approval or a
  new untouched project-level holdout. Final evidence and guard markers stay frozen.
- Added a separate manual weekly artifact-training workflow requiring explicit
  experimental-quality acknowledgement, pinned selection/calibration/final
  evidence and matching completed final-run markers before DB access. Original
  snapshot provenance is verified read-only; DB resources close before fitting.
- Frozen candidates/parameters fit actual 7/14/21-day completed labels through
  the approved cutoff, using the unchanged fitter privately. Actual-horizon
  serialized wrappers, per-record quality/warnings/ranges, source/revision/library
  provenance, reload checks and hashes form a new-only 102-model weekly package.
  A completion manifest is written last; partial output cannot overwrite or
  automatically retry. No final scoring, recalibration, reselection or activation.
- Added synthetic/mocked regressions and updated the manual rollout guide.
  The 721-pass result predates these additions; new tests and actual deployment
  fitting await the user's commands. No agent-run tests, DB/provider operations,
  model fitting, artifact creation, commits or pushes occurred in this checkpoint.
- Original 30-day V1 source/package, APIs, portfolio composition, web/mobile,
  dependencies, environment files and architecture remain unchanged. Weekly
  runtime validation and client activation remain pending. Unrelated report
  files/status were preserved; generated evidence/artifacts remain ignored.

### Report V3 formatting and exhibition feedback — 2026-10-07

- Updated the existing V3 document in place. Applied grayscale formatting to
  30 visual panels and kept Figure 5.7 in its original colors, following the
  new reviewer comment. Removed 15 figure source notes and placed all ten
  numbered table captions below their tables.
- Added 46 clickable citation numbers, including bibliography numbers, with
  targets matching the existing 13 Source links. References 1–10 use external
  source pages; references 11–13 use actual local project source files.
- Added Section 5.6 Student and Exhibition Feedback from the team's reported
  positive verbal comments. The section clearly identifies the feedback as
  informal. No survey, ratings, participant counts, or quotations were invented.
  Figure 5.8 remains a photograph placeholder. Renumbered Achievements and
  Limitations to 5.7 and refreshed the contents and figure/table indexes.
- Updated the companion outline and visual evidence notes. Verified source
  targets, table-caption order, picture effects, equations, template parts,
  and name placeholders. Reviewed all 62 rendered pages; after the final
  photograph-caption alignment adjustment, reviewed its page again and
  confirmed the other 61 page images were unchanged.
- No application code, architecture, dependencies, model artifacts, commits,
  or pushes changed. Concurrent forecasting work was preserved.

### Weekly artifact test checksum false-positive correction — 2026-10-07

- The user-run targeted suite reported 791 passed and one failure. The bundle
  test's blanket JSON substring check matched `30d` inside a valid model SHA-256,
  not an incorrect horizon or target declaration. No training output was supplied.
- Replaced that check with exact artifact schema, target/version, calendar-horizon
  and nested selection/calibration/final identity assertions. Added a deterministic
  synthetic checksum containing `30d` to retain regression coverage of this case.
- Only the test and this status entry changed. Training code, models, frozen
  evidence, APIs and clients remain unchanged. New verification awaits the user's
  manual test rerun; no agent-run test, training, DB access, commit or push occurred.

### Report V3 future work and limitation revision — 2026-10-07

- Edited the user's latest manually revised V3 document in place and applied
  reviewer comment 55. Updated Section 5.7 and Sections 6.2–6.5 to remove weekly
  runtime, admin access, and deployment from the concluding limitations and
  future-work priorities, without asserting that pending work was completed.
- Future Work now discusses custom stress testing, transaction-aware analysis,
  forecasting-model improvements, portfolio prediction intervals, and evaluation
  of user learning and AI explanation quality. Retained simple academic wording
  and updated the related outline placeholders.
- Preserved 325 other non-index paragraphs, all tables, pictures, equations,
  section geometry, external hyperlinks, styles, headers, and other package
  parts from the user's saved version. Refreshed only the Word index blocks
  through a working copy and kept the original navigation bookmarks.
- Verified the 62-page final render. Inspected all six changed page images;
  the other 56 images matched the previously inspected report exactly. The
  user's removals and formatting edits were preserved. A backup of the latest
  user-edited document and internal QA files are retained outside the report folder.
- No application code, models, architecture, dependencies, commits, or pushes
  changed. Concurrent forecasting work was preserved.

### Experimental weekly backend runtime preparation — 2026-10-07

- Reviewed the user-trained `forecast-weekly-v1-20260917` bundle read-only:
  102 models, all 204 model/metadata checksums, five evidence checksums and
  original 69,928-row snapshot bindings match. The approved root canonical hash
  is `5b604af0c7e965cfcebdc0ae38a9570b64464ffc2c8d8adee230a19b2aaf95fe`.
  Zero deployment-fit warnings, 48 below-nominal final-coverage warning records
  and the QQQ 21-day volatility selection convergence warning remain retained.
- Added a separately pinned weekly registry, strict JSON/path/identity gates,
  complete 102-pair validation before joblib loading and selected-byte rechecks.
  Only trusted immutable local deployment artifacts are accepted; request inputs
  cannot choose another package, path, checksum or model. Build evidence and
  experimental/not-predictive-quality-approved flags remain unchanged.
- Added current persisted-data weekly inference and portfolio composition for
  actual 7/14/21-calendar-day targets. Reused V1 features, observation-indexed
  ARIMA alignment, four-day freshness, authoritative CURRENT/PLANNED/LEGACY
  weights, common-date correlations and existing D R D/Euler risk formulas.
  Mixed horizons/provenance or any missing component fail the complete outlook;
  no scaled 30-day output, fallback, provider request, fitting or write occurs.
- Registered two additive authenticated `/horizons/{horizon_days}/outlook`
  asset/owner-scoped portfolio routes and neutral-field response schemas/mappers.
  Public responses retain per-target warnings and educational experimental
  caveats; no private residual/evidence metric, daily path or portfolio interval
  is exposed. Original 30-day source files, endpoints and packages are unchanged.
- Added synthetic/mocked registry, inference/composition/schema and API tests;
  extended the existing OpenAPI inventory assertion for the additive paths.
  Updated the public contract and manual rollout guide. New tests, the runtime
  integrity command and fresh-data authenticated smoke checks await the user.
  No updated passing test count or verified live runtime is claimed.
- No migrations, dependencies, training/evaluation reruns, environment changes,
  frontend activation, AI grounding, staging, commits or pushes were performed.
  Concurrent report work and pre-existing status edits were preserved.
