# Docker Test Database Setup

Aura's `aura-test-database.yml` starts only a local PostgreSQL test database.
The FastAPI backend and React frontend continue to run directly on the host.

## Configuration

The database uses:

| Setting | Value |
|---|---|
| PostgreSQL image | `postgres:18` |
| Host | `127.0.0.1` |
| Host port | `5433` |
| Container port | `5432` |
| User | `aura` |
| Database | `aura_test` |
| Storage | Docker named volume |

Create the local files first by following `local-environment-setup.md`.

## Cross-platform Docker commands

The Docker commands in this section work in Windows PowerShell, macOS Bash,
and Linux Bash.

### Validate the Compose definition

This command renders the configuration without starting PostgreSQL:

```shell
docker compose --env-file .env.test-database -f aura-test-database.yml config --quiet
```

### Start PostgreSQL

```shell
docker compose --env-file .env.test-database -f aura-test-database.yml up -d
```

Check status:

```shell
docker compose --env-file .env.test-database -f aura-test-database.yml ps
```

The service should become `healthy`. View logs without revealing the password:

```shell
docker compose --env-file .env.test-database -f aura-test-database.yml logs postgres-test
```

### Stop while preserving data

```shell
docker compose --env-file .env.test-database -f aura-test-database.yml down
```

The named volume remains available for the next startup.

## Windows PowerShell

### Apply Alembic migrations

From the project root:

```powershell
.venv\Scripts\python.exe -m alembic -c backend/alembic.ini upgrade head
```

Check the current revision:

```powershell
.venv\Scripts\python.exe -m alembic -c backend/alembic.ini current
```

### Configure live PostgreSQL tests

Aura's guarded live tests require `AURA_TEST_DATABASE_URL` and reject database
names outside `aura_test` or `aura_test_*`. The backend `.env` already contains
the correct URL under `DATABASE_URL`; the following PowerShell commands copy it
into the current terminal session without printing it:

```powershell
$databaseUrlLine = Get-Content -LiteralPath backend/.env |
    Where-Object { $_.StartsWith('DATABASE_URL=') } |
    Select-Object -First 1

if (-not $databaseUrlLine) {
    throw 'DATABASE_URL was not found in backend/.env'
}

$env:AURA_TEST_DATABASE_URL = $databaseUrlLine.Substring('DATABASE_URL='.Length)
```

Run a guarded live database test, for example:

```powershell
.venv\Scripts\python.exe -m pytest backend/tests/integration/database/test_database.py -q
```

Remove the session variable afterward:

```powershell
Remove-Item Env:AURA_TEST_DATABASE_URL
```

## macOS/Linux Bash

### Apply Alembic migrations

From the project root:

```bash
.venv/bin/python -m alembic -c backend/alembic.ini upgrade head
```

Check the current revision:

```bash
.venv/bin/python -m alembic -c backend/alembic.ini current
```

### Configure live PostgreSQL tests

Copy `DATABASE_URL` from `backend/.env` into the current shell without printing
it:

```bash
export AURA_TEST_DATABASE_URL="$(grep '^DATABASE_URL=' backend/.env | cut -d= -f2-)"
test -n "$AURA_TEST_DATABASE_URL" || {
  echo 'DATABASE_URL was not found in backend/.env' >&2
  exit 1
}
```

Run a guarded live database test:

```bash
.venv/bin/python -m pytest backend/tests/integration/database/test_database.py -q
```

Remove the session variable afterward:

```bash
unset AURA_TEST_DATABASE_URL
```

## Reset the database

> **Destructive action:** The following command permanently deletes the Aura
> test database volume and all portfolios, users, reports, simulations, market
> data, and other records stored in it. It does not delete source files.

```shell
docker compose --env-file .env.test-database -f aura-test-database.yml down -v
```

Start PostgreSQL again and reapply Alembic migrations after a reset.

## Password changes and existing volumes

The official PostgreSQL image applies its initialization password only when
the data directory is empty. If the generated password changes while the named
volume remains, the backend and database credentials no longer match. Either
keep the original generated files or perform the documented destructive reset
before starting with regenerated credentials.

## Troubleshooting

### Docker cannot read its configuration

Confirm Docker Desktop or the Docker Engine is running and that the current
user can access Docker and the user's Docker configuration directory.

### Port 5433 is occupied

Choose an unused host port in `.env.test-database`, then update the port in
`backend/.env` to match. Do not change the container port `5432`.

### PostgreSQL remains unhealthy

Inspect the service logs. Confirm that the generated password file exists and
is non-empty, but do not print its contents.

Windows PowerShell:

```powershell
Test-Path -LiteralPath .local-secrets/aura-test-db-password
docker compose --env-file .env.test-database -f aura-test-database.yml logs postgres-test
```

macOS/Linux Bash:

```bash
test -s .local-secrets/aura-test-db-password && echo 'database secret exists'
docker compose --env-file .env.test-database -f aura-test-database.yml logs postgres-test
```
