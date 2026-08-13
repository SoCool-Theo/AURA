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

### Deferred work

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

### Deferred integration work

- Market-data pipeline-to-PostgreSQL integration
- Portfolio API routes
- Analysis and reporting services
- Historical simulations and simulation history
- Automatic market-data scheduling
- AI conversation persistence
- Full backend API integration

## Known Issues and Technical Debt

### Starlette/httpx warning

The backend test suite still produces one existing non-blocking
Starlette/httpx deprecation warning.

This warning is unrelated to the analytics calculations and does not
cause test failures.

## Current Backend Priorities

### Ready follow-on work

- `feat/backend-market-data-storage`: the market-data pipeline and database
  foundation are complete; the pipeline-to-PostgreSQL mapping and storage
  workflow remain to be implemented.
- `feat/backend-portfolio-api`: its schema and database prerequisites are now
  available; API and service orchestration remain unimplemented.
- `feat/backend-analysis-service` and `feat/backend-analysis-reporting`: their
  analytics, schema, and persistence foundations are available, while service
  mapping/orchestration and database-backed market-data access remain future
  integration work.

### Still deferred or dependency-blocked

- Market-data scheduling remains dependent on completed storage integration.
- Historical simulations still require finalized simulation contracts and
  implementation; simulation history remains dependent on those simulators.
- AI persistence, full backend API integration, and deployment remain later
  workstreams.
