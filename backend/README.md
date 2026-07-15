# AURA Backend

## Overview

The AURA backend uses FastAPI and will eventually provide portfolio-risk
analytics, historical simulations, market-data services, database access, and
AI-generated explanations. The current implementation is only the initial
FastAPI foundation.

## Requirements

- Python 3.13
- pip
- Git

## Create the virtual environment

Run these commands from the AURA project root.

Windows PowerShell:

```powershell
py -3.13 -m venv .venv
.venv\Scripts\Activate.ps1
```

Git Bash:

```bash
py -3.13 -m venv .venv
source .venv/Scripts/activate
```

## Install dependencies

From the project root, run:

```text
python -m pip install -r backend/requirements.txt
```

## Configure environment variables

`backend/.env.example` is the committed environment-variable template.
`backend/.env` is the local configuration file and is ignored by Git. Copy the
template locally, then adjust only the local file when configuration values
need to change.

PowerShell:

```powershell
Copy-Item backend/.env.example backend/.env
```

Git Bash:

```bash
cp backend/.env.example backend/.env
```

Do not commit secrets or the local `backend/.env` file.

## Run the development server

From the project root, run:

```text
python -m uvicorn app.main:app --reload --app-dir backend
```

The base development URL is <http://127.0.0.1:8000>.

## Current endpoint

The current backend exposes:

```text
GET /api/health
```

Example response:

```json
{
  "status": "healthy",
  "app_name": "AURA",
  "environment": "development"
}
```

The application name and environment values come from the application
settings.

## API documentation

While the development server is running, FastAPI provides interactive API
documentation at:

- <http://127.0.0.1:8000/docs>
- <http://127.0.0.1:8000/redoc>

## Run tests

Run the normal test command from the backend directory:

```text
cd backend
python -m pytest tests -v
```

Alternatively, run the tests from the project root:

```text
python -m pytest backend/tests -v
```

The current health endpoint integration test passes. The current dependency
stack may display a non-blocking Starlette TestClient deprecation warning.

## Current implemented foundation

- FastAPI application entry point
- Environment-based settings
- Central API router
- `GET /api/health`
- Health endpoint integration test

## Not implemented yet

- Portfolio input schemas
- Portfolio analytics engine
- Market-data pipeline
- Database integration
- Historical simulator
- AI agent

## Current backend structure

```text
backend/
|-- .env.example
|-- requirements.txt
|-- app/
|   |-- main.py
|   |-- core/
|   |   `-- config.py
|   `-- api/
|       |-- router.py
|       `-- routes/
|           `-- health.py
`-- tests/
    `-- integration/
        `-- api/
            `-- test_health_api.py
```
