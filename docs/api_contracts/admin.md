# Administrator access foundation

The backend establishes the access boundary and Audit Log storage/query API for
Aura's separate admin website. Dashboard statistics, Users management, Market
Data administration, AI Monitoring, and System Health aggregation require
subsequent backend work before web integration.

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
New provisioning also requires audit migration `f8a0b2c4d6e9` after the role
migration, so its role change and event can commit atomically.

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

Provisioning additional admins, role-management UI, account
suspension, and more granular permissions are outside this phase. Downgrading
the migration removes the role column and all stored role assignments.

## Audit history

Migration `f8a0b2c4d6e9`, following `e7f9a1b3c5d8`, adds `audit_logs` with
application-generated UUIDs, database-generated timestamps, actor kind and
optional actor account UUID, action, target type/UUID, and JSONB details.
Time, actor/time, and target/time indexes support history queries. Actor and
target UUIDs are historical references without cascading foreign keys; deleting
an account preserves its event history. Email addresses and display names are
not copied into events.

`AuditLogService.record(AuditEventCreate(...))` is the reusable internal recording
entry point. The request/operator owns the transaction: recording adds and
flushes, never commits, rolls back, or closes the session. There is no HTTP event
creation, update, or deletion endpoint. Application recording is insert-only;
this phase does not add database triggers or a tamper-evident archive.

The current allowlist contains `ADMIN_BOOTSTRAPPED`, target type `USER`, with
only `previous_role: CUSTOMER` and `new_role: ADMIN` details. Unknown actions,
extra keys, free text, and arbitrary payloads are rejected before persistence.
Future admin mutations must deliberately extend the typed event/detail catalog
and record their action in the same transaction as the mutation.

Successful first-admin provisioning records an `OPERATOR` actor with null
`actor_user_id`, because the CLI has no authenticated account actor. Its target
is the promoted account. Recording failure rolls back the promotion; repeating
bootstrap for the same sole admin does not duplicate the event. Existing roles
are not backfilled, and rejected/failed attempts, sign-ins, and history reads
are not currently recorded. `ADMIN` actor storage is reserved for future
authenticated admin mutations, which are not implemented in this phase.

### Read endpoint

`GET /api/admin/audit-logs` requires Bearer authentication and the persisted
admin role. It reads global administrative history rather than account-owned
customer data. It never writes events or commits.

| Query | Values |
| --- | --- |
| `limit` | 1–100; default 25 |
| `offset` | 0–10000; default 0 |
| `action` | Optional `ADMIN_BOOTSTRAPPED` |
| `actor_kind` | Optional `OPERATOR` or `ADMIN` |
| `actor_user_id` | Optional account UUID; operator events have no account actor |
| `target_type` | Optional `USER` |
| `target_id` | Optional target UUID |
| `created_from`, `created_to` | Optional timezone-aware ISO timestamps, inclusive bounds |

Filters combine with AND. Timestamps normalize to UTC; reversed time ranges and
invalid values return `422`. Items sort newest first by `created_at`, then UUID
descending for deterministic ties. `total` counts all matching events before
pagination. Page and count use one SQL statement so concurrent inserts cannot
produce a mismatched count/page snapshot. An offset beyond the matching count
returns an empty page with the matching total.

```json
{
  "items": [
    {
      "id": "62a1279e-bc8d-4c89-876d-a09250b50395",
      "actor_kind": "OPERATOR",
      "actor_user_id": null,
      "action": "ADMIN_BOOTSTRAPPED",
      "target_type": "USER",
      "target_id": "72a1279e-bc8d-4c89-876d-a09250b50395",
      "details": {"previous_role": "CUSTOMER", "new_role": "ADMIN"},
      "created_at": "2026-10-10T00:00:00Z"
    }
  ],
  "total": 1,
  "limit": 25,
  "offset": 0
}
```

Missing/invalid authentication returns `401`; customers return `403` before
history is queried. Audit-query database failures or invalid persisted event
shapes return sanitized `503`, `{"detail":"Audit history unavailable"}`;
they never return a successful empty-history fallback or leak invalid details.
Downgrading the audit migration drops only its indexes/table and loses its
stored event history.

## Verification boundary

Automated coverage uses real token validation through FastAPI TestClient with
synthetic SQLite storage for audit history and mock database sessions for some
identity/authentication checks. SQLite verifies role/event commit and rollback,
idempotency, filters/pagination, UTC mapping, constraints, and history retention
after account deletion. PostgreSQL upgrade/downgrade SQL generation is offline;
the bootstrap SQL lock is mocked. These checks do not establish live PostgreSQL
migration or concurrent-lock acceptance. No real account was promoted and no
application database was migrated; web/browser integration remains pending.
