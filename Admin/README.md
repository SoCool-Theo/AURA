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
aggregate counts; global directories, deletion, report downloads, account creation/
suspension, manual market refresh, notifications, and system/security mutations
remain unavailable. These controls never simulate a successful server operation.

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

On Windows PowerShell, use the existing binaries directly:

```powershell
cd Admin
Copy-Item .env.example .env.local
node node_modules/vite/bin/vite.js --host 127.0.0.1 --port 5190
```

Start the FastAPI backend as documented in
[`running-local-server.md`](../docs/development/running-local-server.md).
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
node --test tests/admin-api.test.mjs
node node_modules/vinext/dist/cli.js build
node --test tests/*.test.mjs
node node_modules/typescript/bin/tsc --noEmit --incremental false
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

Known baseline checks: TypeScript has three missing Cloudflare worker type
diagnostics. The full Node suite retains two existing failures for development
preview metadata and the catalog's thin-scrollbar utility.
