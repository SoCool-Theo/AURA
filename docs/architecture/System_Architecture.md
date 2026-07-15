# Aura System Architecture

## Project Structure

```text
AURA/
│
├── .venv/                         ← Virtual Environment
├── AGENTS.md                      ← Tells Codex how to work on Aura
├── PROJECT_CONTEXT.md             ← What Aura is and why it is being built
├── CURRENT_STATUS.md              ← Tells Codex what has actually been completed
├── backend/                       ← Analytics engine, database, AI agent
├── web/                           ← Website frontend
├── mobile/                        ← Mobile app later
├── data/                          ← Shared market data
├── docs/                          ← Team documentation
├── .gitignore
└── README.md
```

## Main Decisions Reflected Here

- Website first, mobile later.
- FastAPI backend.
- Clean historical data is used directly for calculations.
- Automatic market-data updates.
- Database support.
- Analytics engine first.
- Historical simulator after core analytics.
- AI agent later.
- No ML training folder yet.

---

## Detailed Backend Folder Structure

```text
AURA/
│
├── .venv/
├── AGENTS.md
├── PROJECT_CONTEXT.md
├── CURRENT_STATUS.md
│
├── backend/
│   │
│   ├── app/
│   │   │
│   │   ├── __init__.py
│   │   ├── main.py
│   │   │
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   ├── constants.py
│   │   │   └── logging.py
│   │   │
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── router.py
│   │   │   │
│   │   │   └── routes/
│   │   │       ├── __init__.py
│   │   │       ├── health.py
│   │   │       ├── portfolio.py
│   │   │       ├── simulation.py
│   │   │       └── agent.py                  ← Later
│   │   │
│   │   ├── analytics/
│   │   │   ├── __init__.py
│   │   │   ├── returns.py
│   │   │   ├── volatility.py
│   │   │   ├── drawdown.py
│   │   │   ├── sharpe.py
│   │   │   ├── correlation.py
│   │   │   ├── concentration.py
│   │   │   ├── diversification.py
│   │   │   ├── risk_driver.py
│   │   │   ├── risk_classifier.py
│   │   │   └── engine.py
│   │   │
│   │   ├── scenarios/
│   │   │   ├── __init__.py
│   │   │   ├── definitions.py
│   │   │   └── simulator.py
│   │   │
│   │   ├── data_pipeline/
│   │   │   ├── __init__.py
│   │   │   ├── providers/
│   │   │   │   ├── __init__.py
│   │   │   │   └── market_provider.py
│   │   │   ├── fetcher.py
│   │   │   ├── cleaner.py
│   │   │   ├── validator.py
│   │   │   └── updater.py
│   │   │
│   │   ├── database/
│   │   │   ├── __init__.py
│   │   │   ├── connection.py
│   │   │   │
│   │   │   ├── models/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── user.py
│   │   │   │   ├── portfolio.py
│   │   │   │   ├── holding.py
│   │   │   │   ├── market_data.py
│   │   │   │   ├── analysis.py
│   │   │   │   └── conversation.py          ← Later
│   │   │   │
│   │   │   └── repositories/
│   │   │       ├── __init__.py
│   │   │       ├── market_data_repository.py
│   │   │       ├── portfolio_repository.py
│   │   │       └── analysis_repository.py
│   │   │
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── portfolio.py
│   │   │   ├── analytics.py
│   │   │   ├── market_data.py
│   │   │   ├── simulation.py
│   │   │   └── agent.py                     ← Later
│   │   │
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── market_data_service.py
│   │   │   ├── portfolio_service.py
│   │   │   └── analysis_service.py
│   │   │
│   │   ├── agents/                           ← Later
│   │   │   ├── __init__.py
│   │   │   ├── agent.py
│   │   │   ├── tools.py
│   │   │   └── prompts.py
│   │   │
│   │   └── utils/
│   │       ├── __init__.py
│   │       └── date_utils.py
│   │
│   ├── tests/
│   │   │
│   │   ├── __init__.py
│   │   │
│   │   ├── unit/
│   │   │   │
│   │   │   ├── analytics/
│   │   │   │   ├── test_returns.py
│   │   │   │   ├── test_volatility.py
│   │   │   │   ├── test_drawdown.py
│   │   │   │   ├── test_sharpe.py
│   │   │   │   ├── test_correlation.py
│   │   │   │   └── test_engine.py
│   │   │   │
│   │   │   └── data_pipeline/
│   │   │       ├── test_cleaner.py
│   │   │       └── test_validator.py
│   │   │
│   │   └── integration/
│   │       ├── __init__.py
│   │       │
│   │       ├── api/
│   │       │   ├── __init__.py
│   │       │   ├── test_health_api.py
│   │       │   ├── test_portfolio_api.py
│   │       │   └── test_simulation_api.py
│   │       │
│   │       └── database/
│   │           └── test_database.py
│   │
│   ├── scripts/
│   │   ├── seed_historical_data.py
│   │   ├── update_market_data.py
│   │   └── run_engine_check.py
│   │
│   ├── examples/
│   │   ├── portfolio_request.json
│   │   ├── analysis_response.json
│   │   └── simulation_response.json
│   │
│   ├── .env.example
│   ├── requirements.txt
│   └── README.md
│
├── web/
│
├── mobile/
│
├── data/
│   ├── raw/
│   ├── processed/
│   └── README.md
│
├── docs/
│   ├── api_contracts/
│   ├── architecture/
│   └── data_dictionary/
│
├── .gitignore
└── README.md
```

---

## Backend Folder Definitions

| Folder | Simple Meaning |
|---|---|
| `api/` | Receives frontend requests |
| `analytics/` | Calculates portfolio risk |
| `scenarios/` | Runs historical What-If simulations |
| `data_pipeline/` | Automatically updates market data |
| `database/` | Reads and saves stored data |
| `schemas/` | Defines data input/output format |
| `services/` | Coordinates the whole process |
| `agents/` | AI explanation later |
| `core/` | Global settings and constants |
| `utils/` | Small reusable helper functions |

---

## Important File and Folder Roles

### Root Files

- `AGENTS.md` — tells Codex how to work on Aura.
- `PROJECT_CONTEXT.md` — explains what Aura is, why it exists, and the main project direction.
- `CURRENT_STATUS.md` — tracks what is completed, what is currently being worked on, and what comes next.
- `.gitignore` — prevents local, generated, private, and unnecessary files from being uploaded to GitHub.
- `README.md` — gives the main project overview and setup instructions.

### Backend

- `core/` — application settings, constants, and logging.
- `api/` — FastAPI routes and request handling.
- `analytics/` — portfolio risk calculations.
- `scenarios/` — historical What-If simulation logic.
- `data_pipeline/` — market-data fetching, cleaning, validation, and updating.
- `database/` — database connection, models, and repository actions.
- `schemas/` — expected data structures for input and output.
- `services/` — coordinates workflows between different backend parts.
- `agents/` — AI explanation layer to be developed later.
- `utils/` — small reusable helper functions.

### Tests

- `tests/unit/` — tests individual functions and modules.
- `tests/integration/` — tests how multiple components work together.
- `test_health_api.py` — verifies the implemented health endpoint.

### Scripts

- `seed_historical_data.py` — manually loads initial historical market data.
- `update_market_data.py` — manually triggers a market-data update.
- `run_engine_check.py` — reserved for manually checking the analytics engine.

### Shared Data

- `data/raw/` — original market-data files.
- `data/processed/` — cleaned and prepared market-data files.

### Documentation

- `docs/api_contracts/` — API request and response documentation.
- `docs/architecture/` — system architecture documents.
- `docs/data_dictionary/` — definitions of stored data fields.
