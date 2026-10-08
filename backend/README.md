# AURA Backend

## Overview

Aura's FastAPI backend is the authority for authentication, portfolio
persistence, current valuation, historical analytics, immutable reports,
historical/allocation/combined simulations, market-data updates, and grounded
educational AI explanations.

The current database migration head is `d4a6f8c2e1b7`. Customer web/mobile
real-holding integration and production deployment remain separate future
work.

## Requirements

- Python 3.13
- PostgreSQL
- pip
- Git

## Local setup

Create and activate a virtual environment from the repository root, then
install the pinned backend dependencies:

```powershell
py -3.13 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements.txt
```

`backend/.env.example` is the committed configuration template.
`backend/.env` is ignored. Copy the template locally, supply deployment/runtime
settings through an approved secret store, and never commit credentials.

```powershell
Copy-Item backend/.env.example backend/.env
```

From the repository root, start the API with:

```text
python -m uvicorn app.main:app --reload --app-dir backend
```

The default local URL is <http://127.0.0.1:8000>. Interactive documentation is
available at `/docs` and `/redoc` while the server is running.

## Current architecture

Real portfolio holdings persist user-entered symbol, invested amount/currency,
shares, and purchase date, plus backend-controlled order. They do not persist
manual weight or current market values. Current USD values and allocations are
derived from recent persisted observations; THB is an optional display using
the internal `THB=X` USD/THB series.

Weight-only legacy portfolios remain temporarily supported for CRUD,
reporting, simulations, and AI. They cannot be currently valued. A normal
holdings replacement converts a portfolio to the real model.

Analytics apply a resolved allocation to historical prices; they do not replay
share ownership through time. Reports and simulation history use versioned,
immutable JSONB snapshots. Opening a saved V2 resource does not revalue or
rerun it.

Repositories and services do not commit. Successful write requests commit at
the API boundary; valuation is read-only, and failed workflows do not commit
partial snapshots.

See:

- [System architecture](../docs/architecture/System_Architecture.md)
- [Public API contract](../docs/api_contracts/public_api.md)
- [Fresh Supabase readiness](../docs/development/supabase-fresh-project-readiness.md)
- [Frontend/mobile integration backlog](../docs/frontend_mobile_integration_backlog.md)

## Public API

The generated OpenAPI surface contains 18 paths and 23 operations covering:

- health;
- registration, login, and current-user identity;
- portfolio CRUD, holding replacement, duplication, and valuation;
- report creation/history/detail/deletion;
- scenario catalogue and three simulation modes with immutable history;
- grounded AI explanation.

The exact inventory and error/version contracts are documented in
[Aura Public Backend API](../docs/api_contracts/public_api.md).

## Market data and scheduler

Aura has 17 user-selectable, USD-quoted asset symbols. `THB=X` is a separate
internal FX instrument and must never appear as a user holding. Default and
scheduled updates include all required user assets and the internal FX series.
Current valuation requires observations no more than four calendar days old.

The scheduler is a standalone process:

```text
python -m backend.scripts.run_market_data_scheduler
```

Production process supervision and deployment configuration remain platform
responsibilities. Run only one scheduler process replica unless the scheduler
architecture is changed deliberately.

## Tests

From the repository root:

```text
python -m pytest backend/tests/unit -q
python -m pytest backend/tests/integration/api -q
```

Live PostgreSQL suites require an explicitly isolated test database and their
documented guard. Do not point tests at a runtime or production database. The
retained Phase 12 test reads only the ignored `.env.test-database` setting,
validates the approved local target before mutation, restores its baseline
records, and must not be replaced with destructive legacy fixtures.

For the Docker-based disposable test setup, see
[test-database-setup.md](../docs/development/test-database-setup.md). Docker is
not required or authorized merely by reading this README.

## Product boundaries

Aura is educational and non-advisory. It does not provide a transaction
ledger, tax lots or tax calculations, brokerage integration, historical
purchase/FX reconstruction, price prediction, or buy/sell advice.
