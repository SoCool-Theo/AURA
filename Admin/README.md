# Aura Admin Panel

Independent React + TypeScript administration frontend for Aura. Keep this folder beside the investor web and mobile apps:

```text
AURA/
├── Admin/                  # this project — administrators only
├── backend/                # shared FastAPI backend
├── web-prototype-react/    # investor/customer web
├── mobile/                 # investor/customer mobile
├── data/
└── docs/
```

## Admin source structure

```text
Admin/
├── app/
│   ├── globals.css         # Aura theme and responsive styles
│   ├── layout.tsx          # metadata and root layout
│   └── page.tsx            # admin application entry
├── components/
│   ├── admin/
│   │   ├── AdminApp.tsx
│   │   ├── AdminSidebar.tsx
│   │   ├── AdminTopbar.tsx
│   │   ├── SectionCard.tsx
│   │   ├── mockData.ts
│   │   ├── types.ts
│   │   └── pages/
│   │       ├── DashboardPage.tsx
│   │       ├── UsersPage.tsx
│   │       ├── OtherPages.tsx
│   │       └── SettingsPage.tsx
│   └── ui/                 # reusable accessible UI controls
├── public/
├── package.json
├── package-lock.json
├── tsconfig.json
└── vite.config.ts
```

## Included pages

- Dashboard
- Users
- Portfolios
- Market Data
- Reports
- System Health
- AI Monitoring
- Activity Logs
- Settings

Dashboard, Users, Market Data, System Health, AI Monitoring, and Activity Logs now
read the existing FastAPI admin endpoints. Portfolios and Reports show supported
aggregate counts; global directories, deletion, report downloads, account creation,
role changes, manual market refresh, notifications, and system/security mutations
remain unavailable. These controls never simulate a successful server operation.

Users supports Active/Suspended status filtering and suspend/reactivate actions.
The existing themed confirmation explains the access change and preserves user
records. Pending requests disable repeat submissions; errors remain visible and
the directory reloads from the API. Your own suspension is disabled; backend
checks also protect the last active administrator. Activity Logs displays both
status transitions with the actual actor and target UUIDs. Reactivated users
must sign in again because previous sessions remain invalid.

Settings shows the verified read-only identity. Only appearance and compact
sidebar are saved locally, separately for each administrator on this device.
The production application does not import `mockData.ts`.

## Run locally

Requirements: Node.js 22.13 or later.

```bash
cd Admin
npm install
npm run dev
```

The npm development, build, lint, test and typecheck commands also run directly
in Windows PowerShell without Bash:

```powershell
cd Admin
if (-not (Test-Path .env.local)) { Copy-Item .env.example .env.local }
npm run dev
```

For the approved Docker test database, open a separate terminal at the repository
root and use the ignored local backend override created during setup:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --env-file backend/.env.local --reload --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:5190`. The dedicated local test administrator's credentials
are in ignored `.local-secrets/admin-dev-credentials.json`. Keep this account and
file for local development only; there are no committed/default passwords.
`backend/.env.local` selects `127.0.0.1:5433/aura_test` and a local JWT key,
without changing the saved `backend/.env` configuration. The local override
disables AI-provider credentials; starting FastAPI does not start a market worker.
Start in a fresh terminal without conflicting exported database variables.
General backend startup is documented in
[`running-local-servers.md`](../docs/development/running-local-servers.md).
The default backend origin is `http://127.0.0.1:8000`; change
`VITE_API_BASE_URL` in ignored `.env.local` and restart Vite if needed. Configure
an HTTP(S) origin only, without `/api`, credentials, query strings, or fragments.
During development, requests to `/api` use Vite's reverse proxy, so the admin
port does not require a new backend CORS entry.

For production, set `VITE_API_BASE_URL` before building to a reachable backend
origin and allow the admin website's exact origin in the backend CORS settings.
Alternatively leave it empty and provide a same-origin `/api` reverse proxy in
your hosting setup. Vite's development proxy is not a production proxy. No
deployment configuration or remote database migration is performed by this change.

## Sign-in and data behavior

The admin form uses the same `/api/auth/login` endpoint and account credentials
as the customer clients. It verifies `/api/admin/me` before storing a token or
showing the workspace. A customer account cannot enter the admin dashboard.
The previously prepared migrations and deliberate first-admin provisioning must
already be applied to the intended database; see the
[admin contract](../docs/api_contracts/admin.md#first-admin-provisioning).
There are no default administrator credentials.
Account status requires migration `b0c2d4e6f8a1`. The approved persistent local
Docker test database is upgraded during this feature's local acceptance; remote
databases require a separately authorized migration before using this version.

The token is stored only in this tab's session storage under
`aura.admin.accessToken`. Passwords are not retained, and tokens are not copied
between websites or passed in URLs. Restored sessions are reverified. Protected
401/403 responses clear the current session; service failures retain it for retry.
Signing out clears the local token and unmounts the data pages; this does not
revoke other clients' tokens. Responses are runtime validated with the already
installed Zod package. Loading, empty, failed, and malformed responses never
fall back to prototype statistics. Filter changes/navigation cancel old requests.

Counts describe retained records, dates use UTC, market prices preserve the
backend's decimal strings, and health has partial coverage. Provider configuration
presence is not a connectivity probe. AI monitoring retains metadata only;
summary counts cover all retained events while request filters apply to the list.
Financial calculations and permanent data changes remain in FastAPI.

## Verification

```powershell
cd Admin
npm run typecheck
npm run lint
npm test
```

For repeatable local acceptance using real routers with synthetic in-memory
SQLite data, start these in separate terminals after building:

```powershell
# Repository root: no PostgreSQL access, provider calls, or real-data mutations.
.\.venv\Scripts\python.exe Admin/tests/serve-backend-fixture.py
# From Admin:
node tests/serve-admin-preview.mjs
node tests/admin-backend-acceptance.mjs
```

To check Vite's development proxy too, run Vite on port 5191 with
`VITE_API_BASE_URL=http://127.0.0.1:8019`, then run
`node tests/admin-backend-acceptance.mjs http://127.0.0.1:5191`.

Open `http://127.0.0.1:5192`. The fixture generates fresh synthetic credentials
in ignored `.wrangler/admin-fixture-credentials.json`; use those only with this
local acceptance server. Stop both servers when finished. The preview harness
serves the built worker and assets with a localhost-only API proxy; it is not a
hosting/deployment setup. Automated client tests and synthetic browser checks do
not establish live PostgreSQL, real-provider, or Cloudflare deployment readiness.

`npm run build` uses a cross-platform Node launcher with a three-minute limit.
The existing large-chunk warning remains informational. Runtime worker types
are generated by the already installed Wrangler and committed in
`worker-configuration.d.ts`; regenerate with `npm run types:generate` when
`worker-types.jsonc` or the installed runtime changes. This type-only config
does not add deployment bindings or connect Aura to D1.

The HTML test checks production metadata and the administrator access guard.
Shared scrolling utilities are emitted for the existing catalog components.
SSR tests use isolated ignored caches and disable HMR/WebSocket listeners, so
they can run alongside the development server without sharing its optimizer
cache or opening competing HMR ports. Native Cloudflare runtime startup may
require running outside a restricted process sandbox.

Normal Windows development startup, login, page reads, hot reload and session
restoration/logout were verified against the persistent Docker test database.
Vinext logged a renderer warning following hot reload without blocking those
checks. The test market inventory remains stale with one missing instrument and
no active worker heartbeat, so a degraded health status is expected.

### Docker PostgreSQL acceptance

Use the approved Docker test database at `127.0.0.1:5433/aura_test`. The harness
reads `TEST_DATABASE_URL` from ignored `.env.test-database` and validates the
host, port, database, role and PostgreSQL version before writing. From the
repository root:

```powershell
.\.venv\Scripts\python.exe Admin/tests/serve-postgres-fixture.py --check-only
```

It creates a unique temporary schema with a search path that excludes `public`,
runs the actual Alembic migration chain, checks preservation of a pre-existing
customer, provisions the synthetic first administrator using the real service,
and checks all ten admin routes, permissions, aggregates, audit persistence,
decimal observations and concurrent reads. Cleanup removes only the schema it
created. Fingerprints of all existing public tables are compared before/after.
No provider calls, worker startup or model execution occur.

For client/browser acceptance, omit `--check-only`, then start the existing built
preview and client check in separate terminals from `Admin`:

```powershell
node tests/serve-admin-preview.mjs
node tests/admin-backend-acceptance.mjs
```

The PostgreSQL harness uses the same port `8019`, synthetic account shape and
ignored credentials file as the SQLite harness; run only one backend harness at
a time. Open `http://127.0.0.1:5192` for the browser check. Stop the preview and
gracefully stop the Python server with Ctrl+C so its `finally` cleanup runs.
A forced process termination can leave the temporary schema behind; never
remove public tables or reset the Docker volume to clean up a fixture.
Testing migrations in this disposable schema does not upgrade the persistent
public application schema or provision a real administrator.
