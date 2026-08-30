# Local Environment Setup

Aura uses local environment files for backend configuration, frontend API
configuration, and the Docker test database. These files contain local secrets
and are ignored by Git.

## Generated files

The setup workflow creates:

```text
.env.test-database
.local-secrets/aura-test-db-password
backend/.env
web-prototype-react/.env
```

The tracked `aura-local-env-setup.yml` Compose file generates a 128-character
JWT secret and a 64-character PostgreSQL password from the container's secure
random source. It does not include those values in its image configuration or
print them to the terminal. The one-shot container runs without network access
and with Docker's `no-new-privileges` security option.

The PostgreSQL password is stored in the ignored local secret file and is also
included in `backend/.env` because Aura's current backend accepts its database
connection as a `DATABASE_URL`. Anyone who can read that local file can read
the password, so keep access to the project directory restricted to trusted
local users.

## Cross-platform Docker commands

Requirements:

- Docker Desktop or Docker Engine with the Compose plugin is installed and
  running.
- Commands are run from the Aura project root.
- None of the four generated targets listed above already exists.

The same `aura-local-env-setup.yml` service is used on every platform. Run
exactly one of the platform-specific commands below. Bash supplies the host
user and group so files created through a bind mount remain owned by the local
developer on native Linux.

The generator intentionally stops before writing anything if any target
already exists. It never silently overwrites a JWT secret, database password,
or local configuration.

Expected non-sensitive output:

```text
Created backend/.env.
Created web-prototype-react/.env.
Created .env.test-database.
Created the ignored local database secret.
Generated secrets were not printed.
```

## Windows PowerShell

Generate the environment:

```powershell
docker compose -f aura-local-env-setup.yml run --rm env-setup
```

Confirm that all four generated targets exist without displaying their
contents:

```powershell
Test-Path -LiteralPath backend/.env
Test-Path -LiteralPath web-prototype-react/.env
Test-Path -LiteralPath .env.test-database
Test-Path -LiteralPath .local-secrets/aura-test-db-password
```

Each command should return `True`.

## macOS/Linux Bash

Generate the environment while preserving host file ownership:

```bash
docker compose -f aura-local-env-setup.yml run --rm \
  --user "$(id -u):$(id -g)" env-setup
```

Confirm that all four generated targets exist without displaying their
contents:

```bash
test -f backend/.env && echo 'backend/.env exists'
test -f web-prototype-react/.env && echo 'frontend .env exists'
test -f .env.test-database && echo 'database environment exists'
test -s .local-secrets/aura-test-db-password && echo 'database secret exists'
```

## Generated backend configuration

`backend/.env` receives the following settings, with real generated values in
place of the two placeholders shown here:

```dotenv
APP_NAME=AURA
APP_ENV=development
DEBUG=true
API_PREFIX=/api
DATABASE_URL=postgresql+psycopg://aura:GENERATED_DATABASE_PASSWORD@127.0.0.1:5433/aura_test
JWT_SECRET_KEY=GENERATED_JWT_SECRET
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
MARKET_DATA_UPDATE_TIME_UTC=02:00
CORS_ALLOWED_ORIGINS=["http://localhost:5173","http://127.0.0.1:5173"]
```

The generated database password uses hexadecimal characters, so it is already
safe inside the URL and does not require percent-encoding.

## Generated frontend configuration

`web-prototype-react/.env` receives:

```dotenv
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Vite reads this file when the frontend development server starts. Restart Vite
after changing the file.

## Generated database configuration

`.env.test-database` contains only non-secret Compose values:

```dotenv
POSTGRES_USER=aura
POSTGRES_DB=aura_test
POSTGRES_PORT=5433
```

The database Compose file reads the password through the ignored local secret
file instead of placing it in container environment variables.

## Confirm Git protection

Run:

```shell
git status --short --ignored
```

The generated environment files and `.local-secrets/` must appear as ignored,
not as tracked or untracked files intended for a commit.

Never paste the real JWT secret or database password into documentation,
issues, commits, or chat messages.

## Regenerating the environment

Regeneration changes both the JWT signing secret and database password. Old
tokens stop working, and an existing PostgreSQL volume retains its old
password. Regeneration therefore requires an explicit clean reset.

> **Warning:** The following procedure deletes the Docker test database and
> every record stored in its named volume.

1. Stop and remove the test database volume as documented in
   `test-database-setup.md`.
2. Back up anything needed from the existing local environment files.
3. Delete only the four generated targets listed at the top of this document.
4. Run the generator again.
5. Start the new database and apply Alembic migrations.

The generator does not perform these destructive steps automatically.
