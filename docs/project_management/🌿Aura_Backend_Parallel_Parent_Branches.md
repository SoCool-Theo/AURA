# Aura Backend Parallel Parent Branches

The FastAPI foundation and `feat/backend-analytics-core` workstreams are completed and merged into `develop`.

The remaining backend work should continue through independent feature branches created from the latest `develop`.

Each branch should:

- Be created directly from the latest `develop`
- Own a clearly separated part of the backend
- Avoid depending on unfinished work from another branch
- Be reviewed and merged through a Pull Request **into `develop`**
- Avoid unnecessary changes to shared files such as `main.py`, `api/router.py`, and `CURRENT_STATUS.md`

Branch flow for every parent branch:

```text
develop
   ↓ create
feat/backend-...
   ↓ Pull Request
develop
```

Feature branches are never created directly from main. `main` never receives a PR from a `feat/*` branch — only `develop` gets promoted to `main` later, as a release.

---

## Backend Parent Workstream Status

| Branch | Status | Main Responsibility | Primary Files |
|---|---|---|---|
| `feat/backend-analytics-core` | Completed | Pure portfolio-risk calculations | `app/analytics/`, `tests/unit/analytics/` |
| `feat/backend-market-data-pipeline` | In progress | Fetch, clean, validate, and normalize market data | `app/data_pipeline/`, `tests/unit/data_pipeline/` |
| `feat/backend-database-foundation` | Planned | PostgreSQL connection, models, migrations, and repositories | `app/database/`, database integration tests |
| `feat/backend-schemas-contracts` | Planned | Pydantic schemas and API data contracts | `app/schemas/`, `docs/api_contracts/`, `examples/` |
| `feat/backend-quality-ci` | Optional | Testing and code-quality automation | GitHub Actions, pytest, linting, type checking |

---

# 1. `feat/backend-analytics-core` — Completed

## Completion Status

**Status:** Completed and merged into `develop`

The branch produced a deterministic portfolio analytics engine with:

- Return calculations
- Annualized volatility
- Maximum drawdown
- Sharpe ratio
- Correlation analysis
- Concentration analysis
- Diversification scoring
- Risk-driver analysis
- Overall risk classification
- Individual asset metrics
- Analytics-engine coordination
- Public analytics exports
- A deterministic manual engine-check script

Final verification:

- 704 analytics tests passed
- 705 full backend tests passed
- No failed tests
- No branch-boundary violations

## Purpose

Build the portfolio-risk calculation engine without connecting it to FastAPI, PostgreSQL, or external market-data APIs.

## Work Included

- Portfolio return calculation
- Annualized return
- Volatility
- Maximum drawdown
- Sharpe ratio
- Asset correlation
- Concentration analysis
- Diversification score
- Risk-driver identification
- Risk classification
- Analytics engine coordinator
- Unit tests with fixed sample data

## Main Files

```text
backend/app/analytics/
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
```

## Branch Boundary

This branch should accept prepared data such as a Pandas DataFrame and portfolio weights.

It should not:

- Download market data
- Read from PostgreSQL
- Create FastAPI routes
- Call the AI agent

---

# 2. `feat/backend-market-data-pipeline`

## Purpose

Develop the market-data collection and cleaning process.

## Work Included

- Market-data provider interface
- Initial financial-data provider
- Historical-price fetching
- Date validation
- Symbol validation
- Missing-value handling
- Duplicate removal
- Column normalization
- Data-quality validation
- Processed DataFrame or CSV output
- Unit tests with mocked provider responses

## Main Files

```text
backend/app/data_pipeline/
├── providers/
│   └── market_provider.py
├── fetcher.py
├── cleaner.py
├── validator.py
└── updater.py

backend/tests/unit/data_pipeline/
```

## Suggested Output Structure

```text
date
symbol
adjusted_close
volume
source
```

## Branch Boundary

This branch should produce clean market data, but it should not store it in PostgreSQL yet.

It should not:

- Calculate portfolio risk
- Use database repositories
- Create portfolio API routes
- Run historical simulations

---

# 3. `feat/backend-database-foundation`

## Purpose

Prepare the PostgreSQL storage system independently from the data pipeline and analytics engine.

## Work Included

- Database configuration
- SQLAlchemy connection
- Database session management
- PostgreSQL health check
- Alembic migration setup
- Base database model
- Initial database tables
- Repository methods
- Database integration tests

## Initial Models

```text
User
Portfolio
Holding
MarketData
Analysis
```

The AI conversation model can be added later during the AI-agent stage.

## Main Files

```text
backend/app/database/
├── connection.py
├── models/
│   ├── user.py
│   ├── portfolio.py
│   ├── holding.py
│   ├── market_data.py
│   └── analysis.py
└── repositories/
    ├── market_data_repository.py
    ├── portfolio_repository.py
    └── analysis_repository.py

backend/tests/integration/database/
```

## Branch Boundary

This branch should use generated test records for database testing.

It should not:

- Fetch live market data
- Calculate analytics
- Build portfolio routes
- Build the AI agent

---

# 4. `feat/backend-schemas-contracts`

## Purpose

Define the shared data formats used later by the frontend, API, analytics, and database integrations.

## Work Included

- Portfolio request schema
- Holding schema
- Market-data schema
- Analytics-result schema
- Simulation request schema
- Simulation response schema
- Validation rules
- Example request JSON
- Example response JSON
- API contract documentation

## Main Files

```text
backend/app/schemas/
├── portfolio.py
├── analytics.py
├── market_data.py
└── simulation.py

backend/examples/
├── portfolio_request.json
├── analysis_response.json
└── simulation_response.json

docs/api_contracts/
```

## Example Portfolio Request

```json
{
  "name": "Technology Portfolio",
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

## Branch Boundary

This branch defines input and output formats only.

It should not implement:

- Database operations
- Analytics formulas
- Market-data downloading
- API route business logic

---

# 5. Optional: `feat/backend-quality-ci`

## Purpose

Set up automated testing and code-quality checks without changing feature logic.

## Work Included

- GitHub Actions test workflow
- Automatic `pytest`
- Ruff or another Python linter
- Type checking
- Test coverage configuration
- Pull-request checks

This branch is useful, but the first four branches have higher project value.

---

# Branches That Should Not Start Yet

These are child or integration branches because they depend on one or more parent branches. They will also be created from `develop`, once their dependencies have merged into `develop`.

## Integration Branch Readiness

| Later Branch | Dependencies | Current Readiness |
|---|---|---|
| `feat/backend-analysis-service` | Analytics + database + schemas | Analytics ready; waiting for database and schemas |
| `feat/backend-portfolio-api` | Schemas + database + analytics | Analytics ready; waiting for database and schemas |
| `feat/backend-historical-simulator` | Analytics + historical data + schemas | Analytics ready; waiting for historical data and schemas |
| `feat/backend-risk-reporting` | Analytics + database + schemas | Analytics ready; waiting for database and schemas |
| `feat/backend-ai-agent` | Stable analytics + reports + database | Analytics ready; reports and database still required |
| `feat/backend-api-integration` | Routes + services + schemas + database | Not ready yet |
| `feat/backend-market-data-storage` | Data pipeline + database | Waiting on data pipeline and database |
| `feat/backend-market-data-scheduler` | Data pipeline + database | Waiting on data pipeline and database |
| `feat/backend-deployment` | Completed backend integration | Not ready yet |

The historical simulator should wait until core analytics and historical market data are stable.

The AI agent should wait until the system produces reliable analytics results and reports.

---

## Recommended Current Parallel Work

```text
Developer 1 → feat/backend-market-data-pipeline
Developer 2 → feat/backend-database-foundation
Developer 3 → feat/backend-schemas-contracts
```

Optional separate cleanup:

```text
refactor/analytics-validation
```

The validation refactor is not a parent feature workstream and is not required before other independent parent branches continue.

The `feat/backend-schemas-contracts` branch can be handled by:

- The backend lead
- The person who finishes first
- A fourth contributor

The schemas branch requires coordination because all later backend components will use its formats.

---

# Correct Git Branch Structure

All parent branches should start from the latest `develop`, not `main`.

```text
develop
├── feat/backend-analytics-core
├── feat/backend-market-data-pipeline
├── feat/backend-database-foundation
└── feat/backend-schemas-contracts
```

Do not create one shared backend parent feature branch like this:

```text
develop
└── feat/backend-parent
    ├── analytics
    ├── database
    └── data-pipeline
```

They are parent workstreams in the project plan, but each Git branch should still be created directly from `develop`.

## Frontend branches follow the same structure

The same pattern applies to frontend work — every frontend branch is also created directly from `develop`, not from a separate frontend base branch:

```text
develop
├── feat/frontend-dashboard
├── feat/frontend-portfolio-management
├── feat/frontend-risk-report
└── feat/frontend-simulation
```

You do not need separate permanent `frontend` and `backend` branches — `develop` is the single shared integration branch for both.

---

# Commands Before Creating a Branch

Update local `develop` first:

```bash
git switch develop
git pull origin develop
```

Create the analytics branch:

```bash
git switch -c feat/backend-analytics-core
```

Create the market-data branch:

```bash
git switch -c feat/backend-market-data-pipeline
```

Create the database branch:

```bash
git switch -c feat/backend-database-foundation
```

Create the schemas branch:

```bash
git switch -c feat/backend-schemas-contracts
```

Push a new branch to GitHub:

```bash
git push -u origin branch-name
```

---

# Shared-File Rule

To reduce merge conflicts, contributors should avoid editing the same shared files in parallel.

Avoid changing these files unless the branch specifically owns the integration work:

```text
backend/app/main.py
backend/app/api/router.py
backend/app/services/
CURRENT_STATUS.md
```

Each parent branch should mainly modify its own folder and tests.

After a branch is merged, update `CURRENT_STATUS.md` on `develop` (or in a small documentation branch merged into `develop`) — not on `main` directly.

---

# Recommended Development Order

## Parallel Parent Stage

```text
✅ feat/backend-analytics-core
⬜ feat/backend-market-data-pipeline
⬜ feat/backend-database-foundation
⬜ feat/backend-schemas-contracts
```

## First Integration Stage

```text
feat/backend-market-data-storage
feat/backend-analysis-service
feat/backend-portfolio-api
```

## Second Feature Stage

```text
feat/backend-historical-simulator
feat/backend-risk-reporting
feat/backend-market-data-scheduler
```

## Later AI Stage

```text
feat/backend-ai-agent
feat/backend-api-integration
```

## Final Stage

```text
feat/backend-deployment
final integration tests
```

Once `develop` has absorbed and stabilized all of the above, it is promoted to `main` through its own Pull Request, following the team's `develop → main` release process.

---

# Final Recommendation

The strongest independent branches to begin immediately are:

1. `feat/backend-analytics-core`
2. `feat/backend-market-data-pipeline`
3. `feat/backend-database-foundation`
4. `feat/backend-schemas-contracts`

These branches are separate enough for different contributors to work at the same time with minimal dependency and fewer merge conflicts.

---
## P.S

- All branches above already use the **feat/** prefix and branch from `develop`, in line with the team's updated `main → develop → feat/*` workflow.