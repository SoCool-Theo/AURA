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
| `feat/backend-schemas-contracts` | Parent feature | Next planned | Pydantic schemas and stable backend data contracts |
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

# Completed Parent Workstream

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

## 2. `feat/backend-schemas-contracts`

**Status:** Next planned

### Purpose

Define stable Pydantic request and response structures shared by later API,
service, database, analytics, simulation, and frontend integration work.

This branch creates data contracts. It does not implement business workflows.

### Planned Work

- Common schema conventions
- Portfolio request and response schemas
- Holding input and output schemas
- Analysis-period schemas
- Market-data schemas
- Analytics result schemas
- Risk-driver schemas
- Individual asset-metric schemas
- Correlation and diversification schemas
- Historical-simulation request and response schemas
- Validation rules
- Example request JSON
- Example response JSON
- API contract documentation
- Direct schema tests

### Main Files

```text
backend/app/schemas/
├── __init__.py
├── portfolio.py
├── analytics.py
├── market_data.py
└── simulation.py

backend/examples/
├── portfolio_request.json
├── analysis_response.json
└── simulation_response.json

docs/api_contracts/
backend/tests/unit/schemas/
```

### Contract Goals

Schemas should:

- Use clear field names
- Define required and optional fields explicitly
- Produce frontend-friendly JSON
- Remain independent from SQLAlchemy models
- Avoid exposing Pandas or NumPy objects directly
- Match the completed analytics output structure where appropriate
- Support later service and API integration
- Reject invalid requests before business logic runs

### Example Portfolio Analysis Request

```json
{
  "portfolio_name": "Technology Portfolio",
  "holdings": [
    {
      "symbol": "AAPL",
      "weight": 0.4
    },
    {
      "symbol": "MSFT",
      "weight": 0.6
    }
  ],
  "start_date": "2021-01-01",
  "end_date": "2026-01-01"
}
```

The exact contract must be finalized during the schemas branch. This example is
illustrative and should not be treated as approved API behavior before that
branch is completed.

### Branch Boundary

This branch should define and test data formats only.

It should not:

- Create FastAPI route business logic
- Query PostgreSQL
- Define SQLAlchemy models
- Fetch market data
- Reimplement analytics formulas
- Run historical-simulation calculations
- Call the AI agent
- Add investment recommendations

---

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
| `feat/backend-analysis-service` | Coordinate validated input, market data, and analytics | Analytics + schemas + data access | Waiting for schemas and data access |
| `feat/backend-portfolio-api` | Portfolio and holding CRUD endpoints | Schemas + database | Waiting for schemas and database |
| `feat/backend-market-data-storage` | Save and retrieve processed historical data | Data pipeline + database | Waiting for pipeline and database |
| `feat/backend-historical-scenario-simulator` | Test the current portfolio during a selected past event | Analytics + historical data + simulation schemas | Waiting for data and schemas |
| `feat/backend-allocation-simulator` | Compare original and modified allocations over the same period | Analytics + historical data + simulation schemas | Waiting for data and schemas |
| `feat/backend-combined-simulator` | Compare original and modified allocations during one event | Historical scenario + allocation simulator | Not ready |
| `feat/backend-analysis-reporting` | Save and retrieve analysis reports | Analytics + schemas + database | Waiting for schemas and database |
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

---

# Recommended Current Work

## Next Branch for the Analytics/Backend Lead

```text
feat/backend-schemas-contracts
```

## Parallel Workstreams

```text
Contributor 1 → feat/backend-schemas-contracts
Contributor 2 → feat/backend-market-data-pipeline
Contributor 3 → feat/backend-database-foundation
```

Assignments may differ depending on team availability.

The schemas branch requires team review because later services, routes,
database mapping, frontend integration, and simulations will rely on its field
names and response structures.

---

# Correct Git Branch Structure

All independent feature branches start from the latest `develop`.

```text
develop
├── feat/backend-analytics-core                # completed
├── refactor/analytics-validation              # completed support branch
├── feat/backend-schemas-contracts             # next planned
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

Create the next schemas branch:

```bash
git switch -c feat/backend-schemas-contracts
git push -u origin feat/backend-schemas-contracts
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

## Completed Foundation and Analytics Stage

```text
✅ feat/fastapi-foundation
✅ feat/backend-analytics-core
✅ refactor/analytics-validation
```

## Remaining Parent Stage

```text
➡️ feat/backend-schemas-contracts
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

After the analytics-validation refactor and documentation updates are merged
into `develop`, begin:

```text
feat/backend-schemas-contracts
```

The schemas branch should be discussed and implemented in its own project chat
using the established phase-by-phase workflow.
