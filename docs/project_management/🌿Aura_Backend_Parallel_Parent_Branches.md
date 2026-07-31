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
| `feat/backend-market-data-pipeline` | Parent feature | Planned / parallel | Fetch, clean, validate, and normalize market data |
| `feat/backend-database-foundation` | Parent feature | Planned / parallel | PostgreSQL connection, models, migrations, and repositories |
| `feat/backend-quality-ci` | Optional support | Optional | Automated testing and code-quality checks |

> Update the status of the market-data and database workstreams when their
> assigned contributors confirm progress.

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

# Remaining Independent Parent Workstreams

## 3. `feat/backend-market-data-pipeline`

**Status:** Planned / parallel workstream

### Purpose

Fetch, clean, validate, and normalize historical market data for use by the
analytics engine and later historical simulations.

### Planned Work

- Market-data provider interface
- Initial financial-data provider
- Historical-price fetching
- Symbol validation
- Date-range validation
- Provider-response validation
- Missing-value handling
- Duplicate removal
- Column normalization
- Data-quality checks
- Processed Pandas output
- Unit tests with mocked provider responses
- Manual data-pipeline check where useful

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

The actual internal shape should be finalized by the pipeline implementation
and coordinated with the schemas and database branches.

### Branch Boundary

This branch should produce validated market data.

It should not:

- Calculate portfolio risk
- Store production records in PostgreSQL
- Create portfolio API routes
- Run complete historical simulations
- Call the AI agent

Database persistence should be handled later by a storage integration branch.

---

## 4. `feat/backend-database-foundation`

**Status:** Planned / parallel workstream

### Purpose

Prepare PostgreSQL storage independently from the data-pipeline and analytics
implementations.

### Planned Work

- Database configuration
- SQLAlchemy connection
- Session management
- PostgreSQL health check
- Alembic migration setup
- Base model
- Initial database tables
- Repository interfaces and methods
- Database integration tests

### Initial Models

```text
User
Portfolio
Holding
MarketData
Analysis
```

Simulation-history and AI-conversation models can be added when their feature
requirements become stable.

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

### Branch Boundary

This branch should use generated test records and isolated database tests.

It should not:

- Fetch live market data
- Calculate portfolio analytics
- Build portfolio API routes
- Run historical simulations
- Build the AI agent

---

## 5. Optional: `feat/backend-quality-ci`

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
| `feat/backend-analysis-service` | Coordinate validated input, market data, and analytics | Analytics + schemas + data access | Schemas complete; waiting for market data and data access |
| `feat/backend-portfolio-api` | Portfolio and holding CRUD endpoints | Schemas + database | Schemas complete; waiting for database foundation |
| `feat/backend-market-data-storage` | Save and retrieve processed historical data | Data pipeline + database | Waiting for pipeline and database |
| `feat/backend-historical-scenario-simulator` | Test the current portfolio during a selected past event | Analytics + historical data + simulation schemas | Simulation schemas deferred; waiting for historical data and finalized simulation requirements |
| `feat/backend-allocation-simulator` | Compare original and modified allocations over the same period | Analytics + historical data + simulation schemas | Simulation schemas deferred; waiting for historical data and finalized simulation requirements |
| `feat/backend-combined-simulator` | Compare original and modified allocations during one event | Historical scenario + allocation simulator | Not ready |
| `feat/backend-analysis-reporting` | Save and retrieve analysis reports | Analytics + schemas + database | Schemas complete; waiting for database and report persistence |
| `feat/backend-simulation-history` | Save and retrieve simulation results | Simulators + schemas + database | Not ready |
| `feat/backend-market-data-scheduler` | Automate market-data updates | Data pipeline + database/storage | Not ready |
| `feat/backend-ai-agent` | Explain stable analysis and simulation results | Stable reports + schemas + database | Not ready |
| `feat/backend-api-integration` | Connect routes, services, schemas, repositories, and agent | Completed feature branches | Not ready |
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
feat/backend-schemas-contracts ─────────────┼── feat/backend-analysis-service
                                            │
feat/backend-market-data-pipeline ──────────┤
                                            │
feat/backend-database-foundation ───────────┘

feat/backend-market-data-pipeline
                +
feat/backend-database-foundation
                ↓
feat/backend-market-data-storage

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
integration. Its presence does not imply that those later implementations
exist.

---

# Recommended Current Work

## Remaining Independent Parent Workstreams

```text
feat/backend-market-data-pipeline
feat/backend-database-foundation
```

The exact team assignment should be confirmed by the team. The current
repository documentation does not show either workstream as actively assigned.

For the analytics/backend lead, `feat/backend-market-data-pipeline` is the
likely next technical workstream. `feat/backend-analysis-service` must wait
until its market-data and data-access dependencies are stable.

---

# Correct Git Branch Structure

All independent feature branches start from the latest `develop`.

```text
develop
├── feat/backend-analytics-core                # completed
├── refactor/analytics-validation              # completed support branch
├── feat/backend-schemas-contracts             # completed
├── feat/backend-market-data-pipeline          # planned / parallel
├── feat/backend-database-foundation            # planned / parallel
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

## Completed Foundation, Analytics, and Contracts Stage

```text
✅ feat/fastapi-foundation
✅ feat/backend-analytics-core
✅ refactor/analytics-validation
✅ feat/backend-schemas-contracts
```

## Remaining Parent Stage

```text
⬜ feat/backend-market-data-pipeline
⬜ feat/backend-database-foundation
```

## First Integration Stage

```text
feat/backend-market-data-storage
feat/backend-analysis-service
feat/backend-portfolio-api
```

## Simulation and Reporting Stage

```text
feat/backend-historical-scenario-simulator
feat/backend-allocation-simulator
feat/backend-combined-simulator
feat/backend-analysis-reporting
feat/backend-simulation-history
feat/backend-market-data-scheduler
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

After the schemas-contract branch and its documentation update are merged into
`develop`, continue or assign the remaining independent parent workstreams:

```text
feat/backend-market-data-pipeline
feat/backend-database-foundation
```

Later analysis-service, portfolio-API, storage, reporting, simulation, AI, and
integration branches should begin only when their listed dependencies are
stable. The exact team assignment should be confirmed by the team.
