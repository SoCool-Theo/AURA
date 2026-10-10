# Administrator access foundation

This phase establishes the backend access boundary for Aura's separate admin
website. It does not yet supply Dashboard statistics, Users management, Market
Data administration, AI Monitoring, System Health aggregation, or Audit Log
storage. Those modules require subsequent backend work before web integration.

## Persisted roles

Migration `e7f9a1b3c5d8`, following `d6e8f0a2b4c6`, adds `users.role` with a
non-null `CUSTOMER` default. Existing accounts, including legacy owners without
credentials, remain customers. Only `CUSTOMER` and `ADMIN` are valid values;
an administrator must have both email and password hash.

Public registration explicitly creates customers. Registration and profile
requests reject `role` as an unknown field. Existing customer identity and
token response shapes are unchanged. There is no public role mutation API.

Admin requests use the existing signed Bearer token and resolve the persisted
User on every request. `get_current_admin` requires the exact `ADMIN` role and
credentials; a token role claim, client state, or `X-User-ID` cannot grant access.
A demoted account loses admin access on its next request even with an unexpired
token. Existing customer endpoints retain their ownership checks for admins.

## Admin identity endpoint

`GET /api/admin/me` is read-only and accepts the same Bearer token returned by
`POST /api/auth/login`. The admin router also applies `get_current_admin` to
all its routes, including future additions.

```json
{
  "id": "62a1279e-bc8d-4c89-876d-a09250b50395",
  "email": "admin@example.com",
  "display_name": "Administrator",
  "role": "ADMIN"
}
```

`display_name` may be null. Responses contain no password hashes or secrets.
Missing/invalid/expired credentials or a deleted account return `401` with
`WWW-Authenticate: Bearer`. An authenticated customer returns `403` with
`{"detail":"Administrator access required"}`. No writes or commit occur.

## First-admin provisioning

The operator command promotes an existing credential-bearing account by UUID.
It does not create accounts, accept passwords, or provide default credentials.
Use a deliberately selected `DATABASE_URL` and apply the migration to the
intended database before provisioning; normal account queries now need the
role column. Migration and provisioning are explicit operations, never app
startup actions.

From the repository root, after registering the intended account through the
existing authentication flow and obtaining its user ID:

```powershell
.\.venv\Scripts\python.exe -m backend.scripts.bootstrap_admin --help
# Run only when ready to change the selected account's persisted role:
.\.venv\Scripts\python.exe -m backend.scripts.bootstrap_admin --user-id <USER_UUID> --apply
```

Omitting `--apply`, using an invalid UUID, or requesting help exits without
opening a database connection. The command takes a PostgreSQL transaction-scoped
`SHARE ROW EXCLUSIVE` lock on `users` before checking for existing admins. This
serializes concurrent bootstrap attempts; user writes wait during the short
transaction. It refuses another account if an admin already exists. Repeating
the command for the same sole admin is idempotent. The caller commits once on
success and rolls back failures, closing the session and disposing the engine.
Database failures are sanitized in CLI output.

Provisioning additional admins, audit events, role-management UI, account
suspension, and more granular permissions are outside this phase. Downgrading
the migration removes the role column and all stored role assignments.

## Verification boundary

Automated coverage uses real token validation through FastAPI TestClient with
mock database sessions, SQLite role persistence/constraint checks, and offline
PostgreSQL migration SQL generation. The bootstrap transaction and SQL lock
are checked with mocks. These checks do not establish live PostgreSQL migration
or concurrent-lock acceptance. No real account was promoted and no application
database was migrated during implementation; web/browser integration remains
pending.
