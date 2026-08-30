# Running the Aura Frontend and Backend Locally

This guide runs the real React frontend against the real FastAPI backend and
local PostgreSQL test database. Run commands from the Aura project root unless
a section says otherwise.

## Prerequisites

- Docker Desktop or Docker Engine with the Compose plugin
- Python 3.13 and the Aura `.venv`
- Backend dependencies from `backend/requirements.txt`
- Node.js and npm
- Frontend dependencies installed under `web-prototype-react/`
- Local environment files created according to `local-environment-setup.md`

## Cross-platform Docker commands

The Docker commands in this section work in Windows PowerShell, macOS Bash,
and Linux Bash.

### 1. Start the test database

```shell
docker compose --env-file .env.test-database -f aura-test-database.yml up -d
```

Wait until the service reports `healthy`:

```shell
docker compose --env-file .env.test-database -f aura-test-database.yml ps
```

### Stop the database while preserving data

```shell
docker compose --env-file .env.test-database -f aura-test-database.yml down
```

Do not add `-v` unless the test database should be permanently erased.

## Windows PowerShell

### 2. Apply backend migrations

```powershell
.venv\Scripts\python.exe -m alembic -c backend/alembic.ini upgrade head
```

### 3. Start the FastAPI backend

Open a PowerShell terminal in the project root and run:

```powershell
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --app-dir backend
```

Verify:

- Health: <http://127.0.0.1:8000/api/health>
- OpenAPI: <http://127.0.0.1:8000/docs>
- ReDoc: <http://127.0.0.1:8000/redoc>

Keep this terminal running, then open a second PowerShell terminal.

### 4. Start the React frontend

```powershell
Set-Location web-prototype-react
npm run dev
```

## macOS/Linux Bash

### 2. Apply backend migrations

```bash
.venv/bin/python -m alembic -c backend/alembic.ini upgrade head
```

### 3. Start the FastAPI backend

Open a terminal in the project root and run:

```bash
.venv/bin/python -m uvicorn app.main:app --reload --app-dir backend
```

Keep this terminal running, then open a second terminal.

### 4. Start the React frontend

```bash
cd web-prototype-react
npm run dev
```

Alembic reads `DATABASE_URL` from `backend/.env`. Run migrations before the
first backend startup and whenever new migrations are added.

Open <http://127.0.0.1:5173>.

The frontend reads `VITE_API_BASE_URL=http://127.0.0.1:8000` from
`web-prototype-react/.env`. The backend allows both `localhost:5173` and
`127.0.0.1:5173` through its configured CORS origins.

## Startup order

Use this order after restarting the computer:

1. Start Docker Desktop or the Docker Engine.
2. Start `aura-test-database.yml`.
3. Confirm PostgreSQL is healthy.
4. Apply any pending Alembic migrations.
5. Start FastAPI.
6. Start Vite.

## Stop the application servers

Stop Vite and FastAPI with `Ctrl+C` in their terminals.
Then use the cross-platform Docker shutdown command above to stop PostgreSQL.

## Common problems

### Frontend reports a network error

- Confirm FastAPI is running on port `8000`.
- Confirm `web-prototype-react/.env` uses `http://127.0.0.1:8000`.
- Restart Vite after changing its environment file.
- Open the health endpoint directly.

### Backend cannot connect to PostgreSQL

- Confirm the database is healthy.
- Confirm `backend/.env` targets port `5433` and database `aura_test`.
- Confirm `.local-secrets/aura-test-db-password` was generated with the same
  setup run as `backend/.env`.
- If the password was regenerated, reset the old Docker volume before starting
  PostgreSQL with the new password.

### Port already in use

Stop the program using port `5433`, `8000`, or `5173`. Changing the PostgreSQL
host port also requires updating `POSTGRES_PORT` and the port inside the
backend `DATABASE_URL` so they remain consistent.
