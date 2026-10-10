# Administration backend contracts

The backend supplies the access boundary, Audit Log storage/query API, Dashboard
statistics, a read-only Users directory, and Market Data inventory/status/history
for Aura's separate admin website. User mutations, Market Data refresh requests,
AI Monitoring, System Health
aggregation, and admin web integration remain subsequent work.

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

## Dashboard statistics

`GET /api/admin/dashboard` requires the persisted admin role and has no query
parameters. It counts retained database rows and returns a fixed 30-day UTC
calendar trend. No new migration or dependency is introduced for this endpoint.

| Field | Meaning |
| --- | --- |
| `generated_at` | UTC request-generation timestamp |
| `timezone` | Always `UTC` |
| `window_start`, `window_end` | Inclusive calendar dates, today minus 29 days through today |
| `users` | `total`, `customers`, `admins`, `registered`, `legacy`, `new_last_7_days` |
| `portfolios` | `total`, `current`, `planned`, `legacy`, `new_last_7_days` |
| `saved_reports`, `saved_simulations` | Each has `total`, `today`, `yesterday`, `last_7_days` |
| `daily` | Exactly 30 ascending date rows, each with `date`, `new_users`, `new_portfolios`, `saved_reports`, `saved_simulations` |

User totals include admin accounts and legacy owners without credentials.
`REGISTERED` accounts have a non-null email (the existing database constraint
requires a matching password hash); `LEGACY` account rows have no credentials.
Account classification is distinct from a portfolio's holding mode.

Each saved `analyses` row represents one report, not every analysis request.
Each saved `simulations` row represents one simulation history entry. All
portfolio modes and saved result versions are counted without reading their
holdings or snapshots. Deleted rows disappear from these counts; these metrics
are not durable lifetime activity counters. No analysis or forecast is run.

Today/yesterday use UTC midnight bounds: start is inclusive, next midnight is
exclusive. Seven-day metrics cover today plus six preceding calendar days.
Thirty-day trends include today plus 29 preceding days and zero-fill missing
dates. The current day is in progress. PostgreSQL date buckets explicitly use
UTC regardless of the database session timezone. Aggregate each resource table
independently before joining, so multiple reports or simulations do not
multiply account/portfolio counts. Totals and trends share one SQL statement
snapshot. `generated_at` is a request clock value, not a historical as-of filter.

There is no invented active-user count, suspension state, AI request count,
health verdict, growth percentage, most-analyzed-assets ranking, or customer
risk/portfolio detail. These require separate tracking/contracts before UI
integration. Existing market status and audit history endpoints remain separate.

Missing/invalid credentials return `401`; customers return `403` before the
overview service is called. Database/response-validation failures return
sanitized `503`, `{"detail":"Admin dashboard unavailable"}`, without a fake
healthy or zero-count fallback. The endpoint performs no writes or commits.

## Read-only user directory

`GET /api/admin/users` requires the persisted admin role and returns global
directory metadata rather than granting access to account-owned resources.

| Query | Meaning |
| --- | --- |
| `limit` | 1–100, default 25 |
| `offset` | 0–10000, default 0 |
| `q` | Up to 100 characters; trimmed, case-insensitive literal substring of email or display name; blank means no search |
| `role` | Optional `CUSTOMER` or `ADMIN` |
| `account_type` | Optional `REGISTERED` or `LEGACY` |

Filters combine with AND. `%`, `_`, backslash, and SQL-like text in `q` are
literal search input, not wildcard/SQL expressions. Default results include
customers, admins, and legacy owners. Order is newest `created_at` first, then
UUID descending for deterministic ties. Portfolio counts include all holding
modes owned by each displayed account, without returning any portfolio contents.
The page, matching total, and portfolio counts use one SQL statement with no
per-user queries. An offset beyond the matches returns an empty `items` list
and the matching `total`.

```json
{
  "items": [
    {
      "id": "62a1279e-bc8d-4c89-876d-a09250b50395",
      "email": "user@example.com",
      "display_name": "Aura User",
      "role": "CUSTOMER",
      "account_type": "REGISTERED",
      "created_at": "2026-10-10T00:00:00Z",
      "updated_at": "2026-10-10T00:00:00Z",
      "portfolio_count": 2
    }
  ],
  "total": 1,
  "limit": 25,
  "offset": 0
}
```

Legacy account emails and display names may be null. Timestamps are UTC. No
password hashes, tokens, phone numbers, preferences, holdings, result snapshots,
or fabricated active/suspended status are selected/returned by the directory
query. There are no account-create/edit/delete, suspend, or role-change methods
on this endpoint; existing customer self-service APIs retain their ownership
checks.

Authentication errors return `401`/`403`, invalid filters return `422`, and
database/response-validation failures return sanitized `503`,
`{"detail":"Admin user directory unavailable"}`. Reads do not write audit
events, change accounts, or commit. Browser integration and live PostgreSQL
acceptance remain pending; automated endpoint acceptance uses synthetic SQLite
with real Bearer authentication, plus PostgreSQL SQL compilation checks.

## Read-only Market Data administration

All three endpoints below require the persisted admin role. They read PostgreSQL
observations and existing refresh state, never CSV files or live provider prices.
No new migration or dependency is needed. Authentication is the same shared
Bearer login as the other admin modules; customers receive `403` before the
market service runs.

### Inventory

`GET /api/admin/market-data` returns `checked_at` in UTC and:

| Field | Meaning |
| --- | --- |
| `total_records` | All retained market observation rows, including internal FX and unexpected symbols |
| `stored_symbols` | Number of distinct symbols with stored rows |
| `required_symbols` | Current update universe: 17 user assets plus `THB=X` (18 total) |
| `present_required_symbols` | Required symbols with at least one stored observation |
| `current_required_symbols`, `stale_required_symbols`, `missing_required_symbols` | Partition of the required universe under the existing daily refresh freshness rule |
| `unexpected_symbols` | Stored symbols outside the required update universe |
| `instruments` | Required symbols in registry order, including missing ones, followed by unexpected symbols alphabetically |

Each instrument includes `symbol`, `required_for_refresh`, `kind` (`asset`, `fx`,
or `unknown`), `quote_currency`, `base_currency`, `total_records`,
`first_price_date`, `latest_price_date`, `latest_adjusted_close`, `latest_volume`,
`latest_source`, `age_days`, and `freshness`. Count/date ranges and the latest
observation's price/volume/source come from one SQL statement, without querying
each symbol separately. The `(symbol, date)` primary key prevents latest-row
joins from multiplying counts. Missing instruments have zero records and null
dates/latest-observation fields.

Prices are serialized as decimal strings without conversion to float. Assets
are quoted in USD; `THB=X` is THB per USD (`base_currency: USD`,
`quote_currency: THB`). FX remains internal infrastructure, never a customer
holding choice. Unsupported stored instruments retain their counts/prices but
have `kind: unknown`, null currency metadata, and `freshness: unknown`; no
supported-instrument freshness or currency is invented for them.

Freshness reuses the worker's rule: completed dates must precede today UTC;
crypto needs yesterday's observation, while stocks/ETFs/FX allow four calendar
days. Present required instruments outside that rule are `stale`, including
today/future dates. `age_days` is null for missing/future observations, zero for
today. It describes price-date age, not a download timestamp. The rule does not
prove gap-free trading-day history or model holidays. Missing required symbols
remain visible even in an entirely empty database. No live provider connectivity,
data-gap count, or completeness/coverage percentage is fabricated.

### Worker status

`GET /api/admin/market-data/status` reuses `MarketDataStatusService` and exactly
the [shared daily status contract](market_data.md#daily-refresh-status). It
reports the existing singleton's latest run, attempts, stored count, updated/
failed symbols, sanitized error code, worker heartbeat/liveness, schedule, and
required-instrument freshness. Worker liveness is distinct from observation
freshness and provider connectivity. Its `stored_count` belongs to the last run,
whereas inventory `total_records` counts all retained observations. This is the
latest operational state, not durable multi-run history. Inventory and status
are separate reads and can change between requests when the worker commits.

### Observation history

`GET /api/admin/market-data/observations` supports:

| Query | Meaning |
| --- | --- |
| `limit` | 1–100, default 25 |
| `offset` | 0–10000, default 0 |
| `symbol` | Optional 1–64 characters, trimmed and uppercased; literal exact match, including internal FX or unexpected stored symbols |
| `date_from`, `date_to` | Optional ISO calendar dates; inclusive observation-date bounds |

Filters combine with AND. Blank symbols, invalid dates, and reversed bounds
return `422`. Unknown symbols without stored matches return an empty page;
wildcards and SQL-like text are literal input. Results sort by date descending,
then symbol ascending for deterministic ties. A single SQL statement supplies
the page and matching `total`; an offset beyond the last match retains that
total. Missing trading dates are not interpolated or invented. Observations
retain actual stored dates, including today/future anomalies, for admin review.

```json
{
  "items": [{
    "symbol": "THB=X",
    "date": "2026-10-09",
    "adjusted_close": "35.250000000000",
    "volume": null,
    "source": "Synthetic FX example"
  }],
  "total": 1,
  "limit": 25,
  "offset": 0
}
```

Database or persisted-response validation failures return sanitized `503` with
`Admin market-data inventory unavailable`, `Admin market-data status unavailable`,
or `Admin market-data observations unavailable`, respectively. No successful
empty/healthy fallback is used. Reads never write audit events, flush/commit,
start a worker, download prices, or run analytics/models. No HTTP mutations are
exposed. The prototype's manual update control requires a separate authenticated,
audited request flow to the locked worker before integration; it is not connected
by this phase. Historical refresh-run storage, gap-calendar analysis, provider
probes, and frontend wiring remain subsequent work.

Automated acceptance uses synthetic SQLite storage with real FastAPI/Bearer
authorization, shared status/freshness checks, fixed query-count/read-only checks,
and offline PostgreSQL SQL compilation. Decimal mapping also verifies full
`Numeric(28,12)` precision with a synthetic Decimal fixture, because SQLite's
numeric storage does not establish PostgreSQL numeric precision. Live PostgreSQL,
real-provider, worker-deployment, and browser acceptance remain pending.
