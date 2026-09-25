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
