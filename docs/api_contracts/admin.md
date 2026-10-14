# Administration backend contracts

The backend supplies the access boundary, Audit Log storage/query API, Dashboard
statistics, a Users directory with account suspension/reactivation, a global
portfolio directory/details API, Market Data inventory/status/history,
System Health checks, and content-free AI Monitoring for Aura's separate admin
website. Its frontend integration is implemented in `Admin/`.
Account deletion remains subsequent work. Customer account creation is implemented below. Administrator role management
is available through the guarded account-role endpoint below. Manual
Market Data refresh requests use the existing separate worker and tracked pipeline.

## Manual market-data refresh and run history

Migration `c1d3e5f7a9b2` adds `market_data_refresh_runs`, leaving observations,
accounts, financial calculations and saved snapshots unchanged. History begins
with this migration; earlier runs are not reconstructed.

- `POST /api/admin/market-data/refresh` takes exactly `{ "request_id": "<UUID>" }`.
  Returns HTTP 202 and the persisted run. This confirms acceptance, not successful
  data acquisition. A replay of the same ID by the same administrator returns its
  current outcome without another run or audit event, including while execution
  is in progress or the worker is offline. Use the same ID after an uncertain
  response. Request IDs belonging to another actor or trigger return 409.
- `GET /api/admin/market-data/refresh-runs?limit=25&offset=0` returns `items`,
  `total`, `limit` and `offset`. Limit is 1–100 and offset is 0–10000. Order is
  requested UTC time descending, then UUID descending. All administrators can
  read this safe operational directory; customer access is forbidden.
- Run fields: `id`, `trigger` (`ADMIN`, `SCHEDULED`, `CATCH_UP`, `OPERATOR`),
  `requested_by` (administrator UUID or null), `status` (`queued`, `running`,
  `success`, `partial`, `failed`), UTC `requested_at`, nullable `started_at` and
  `finished_at`, `attempt_count`, `stored_count`, `updated_symbols`,
  `failed_symbols`, and allowlisted nullable `error_code`. No provider exception,
  credentials, database URL or arbitrary error text is exposed.

Request acceptance rechecks persisted administrator role, credentials, suspension
and authenticated session generation under the existing users transaction lock.
It requires a running worker heartbeat within 180 seconds and rejects future
heartbeats. A transaction advisory lock uses the same key as the existing session
refresh lease: scheduled/CLI execution causes immediate 409, and parallel admin
requests serialize. One queued admin request is accepted at a time. Offline or
stale workers return 409 without creating a request. Request and typed
`MARKET_REFRESH_REQUESTED` audit event commit together; failures roll back both
and return sanitized 503. The audit target is `MARKET_REFRESH`, target UUID is the
request UUID, and details contain exactly `{ "mode": "daily" }`.

The existing worker polls every 10 seconds, consumes one queued request under
the shared refresh lease, rechecks the requesting account's active administrator
permission, and uses the same full-universe daily fetch/clean/validate/retry/upsert
pipeline. HTTP callers cannot choose provider, dates, symbols, paths or database.
The daily UTC schedule remains unchanged. API startup never starts the worker or
contacts a provider. Queued requests survive restart. Lost permissions produce
`authorization_changed` without fetching. A running history row found while
holding a newly acquired refresh lease is recorded as failed with `lock_lost`,
and singleton status is repaired. Interrupted execution is not automatically
reported as successful or retried as a new manual request.

Observation writes, singleton outcome and history outcome commit together.
Partial retry history remains running until the final outcome. Valid partial
data preserves old observations for failed symbols. Failed writes roll back;
safe failure bookkeeping is committed separately, as in the existing pipeline.
Run history is retained independently of account records. Authorization errors
remain 401/403; malformed/extra request fields return 422; request/history storage
or response validation failures return sanitized 503.

The Market Data page provides a themed confirmation, queued feedback, run history
and visible-page polling every 10 seconds. It disables repeat/offline requests,
preserves the request UUID on uncertain responses, and cancels transport on
unmount without cancelling an accepted server job. The Dashboard update button
opens Market Data for confirmation and progress. This refreshes completed daily
observations through yesterday UTC; it does not provide streaming quotes.

## Persisted roles

Migration `e7f9a1b3c5d8`, following `d6e8f0a2b4c6`, adds `users.role` with a
non-null `CUSTOMER` default. Existing accounts, including legacy owners without
credentials, remain customers. Only `CUSTOMER` and `ADMIN` are valid values;
an administrator must have both email and password hash.

Public registration explicitly creates customers. Registration and profile
requests reject `role` as an unknown field. Existing customer identity and
token response shapes are unchanged. There is no public role mutation API.

Admin requests use the existing signed Bearer token and resolve the persisted
User on every request, rejects suspended accounts and checks the signed session
version against the persisted account version. `get_current_admin` requires the exact `ADMIN` role and
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

The original bootstrap phase does not provision additional administrators.
Additional role changes now use the authorized account-role API below; more
granular permissions remain future work. Suspended accounts cannot be bootstrapped. Downgrading
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

The allowlist contains `ADMIN_BOOTSTRAPPED`, target type `USER`, with
only `previous_role: CUSTOMER` and `new_role: ADMIN` details, plus
`USER_SUSPENDED` (`previous_status: ACTIVE`, `new_status: SUSPENDED`) and
`USER_REACTIVATED` (the reverse transition). Status events require an `ADMIN`
actor with a non-null UUID; provisioning requires an `OPERATOR` with no actor UUID.
`USER_ROLE_CHANGED` requires an `ADMIN` actor, a `USER` target, and exactly
`previous_role`/`new_role` describing either CUSTOMER → ADMIN or ADMIN → CUSTOMER.
An unchanged role is not a transition. Bootstrap retains its original direction
and operator-only actor rule. `MARKET_REFRESH_REQUESTED` uses the separate
`MARKET_REFRESH` target and daily-mode details described above.
Unknown actions,
extra keys, free text, and arbitrary payloads are rejected before persistence.
Future admin mutations must deliberately extend the typed event/detail catalog
and record their action in the same transaction as the mutation.

Successful first-admin provisioning records an `OPERATOR` actor with null
`actor_user_id`, because the CLI has no authenticated account actor. Its target
is the promoted account. Recording failure rolls back the promotion; repeating
bootstrap for the same sole admin does not duplicate the event. Existing roles
are not backfilled, and rejected/failed attempts, sign-ins, and history reads
are not currently recorded. Successful status transitions record authenticated
`ADMIN` actors in the same transaction; idempotent retries add no event.

### Read endpoint

`GET /api/admin/audit-logs` requires Bearer authentication and the persisted
admin role. It reads global administrative history rather than account-owned
customer data. It never writes events or commits.

| Query | Values |
| --- | --- |
| `limit` | 1–100; default 25 |
| `offset` | 0–10000; default 0 |
| `action` | Optional `ADMIN_BOOTSTRAPPED`, `USER_SUSPENDED`, `USER_REACTIVATED`, `USER_ROLE_CHANGED`, `USER_CREATED`, or `MARKET_REFRESH_REQUESTED` |
| `actor_kind` | Optional `OPERATOR` or `ADMIN` |
| `actor_user_id` | Optional account UUID; operator events have no account actor |
| `target_type` | Optional `USER` or `MARKET_REFRESH` |
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

There is no invented active-user count, AI request count,
health verdict, growth percentage, most-analyzed-assets ranking, or customer
risk/portfolio detail. These require separate tracking/contracts before UI
integration. Existing market status and audit history endpoints remain separate.

Missing/invalid credentials return `401`; customers return `403` before the
overview service is called. Database/response-validation failures return
sanitized `503`, `{"detail":"Admin dashboard unavailable"}`, without a fake
healthy or zero-count fallback. The endpoint performs no writes or commits.

## User directory

`GET /api/admin/users` requires the persisted admin role and returns global
directory metadata rather than granting access to account-owned resources.

| Query | Meaning |
| --- | --- |
| `limit` | 1–100, default 25 |
| `offset` | 0–10000, default 0 |
| `q` | Up to 100 characters; trimmed, case-insensitive literal substring of email or display name; blank means no search |
| `role` | Optional `CUSTOMER` or `ADMIN` |
| `account_type` | Optional `REGISTERED` or `LEGACY` |
| `status` | Optional `ACTIVE` or `SUSPENDED` |

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
      "status": "ACTIVE",
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
or session versions are selected/returned by the directory
query. The directory endpoint stays GET-only; account access changes use the
dedicated endpoint below. Existing customer self-service APIs retain their ownership
checks.

Authentication errors return `401`/`403`, invalid filters return `422`, and
database/response-validation failures return sanitized `503`,
`{"detail":"Admin user directory unavailable"}`. Reads do not write audit
events, change accounts, or commit. Endpoint checks use synthetic SQLite and
the approved Docker PostgreSQL database, with real Bearer authentication.

## Suspend/reactivate account access

Migration `b0c2d4e6f8a1`, after `a9b1c3d5e7f0`, adds non-null
`users.is_suspended` (false) and `users.auth_version` (zero, nonnegative).
Existing accounts remain active with unchanged roles and records. Apply it
explicitly to the selected database before starting the updated backend;
application startup never migrates storage. Downgrade removes this state and
the session-revocation history; use only as an explicit operator operation.

`PATCH /api/admin/users/{user_id}/status` requires persisted active ADMIN
permission and accepts exactly:

```json
{"status":"SUSPENDED","expected_status":"ACTIVE"}
```

Both fields use `ACTIVE`/`SUSPENDED`. Reactivation reverses them. The successful
response contains only `id`, `status`, and UTC `updated_at`. Status is separate
from role and REGISTERED/LEGACY classification; either account type can be
suspended. No passwords, profile changes, role changes or free-text reasons are
accepted. Portfolios, holdings, saved results and account identity are preserved.

The transaction takes the same PostgreSQL `SHARE ROW EXCLUSIVE` users-table lock
as bootstrap, then refreshes and rechecks the acting administrator and session
generation. This serializes status decisions and prevents mutually competing
administrators from suspending each other. Self-suspension and suspension of
the last credential-bearing active administrator return `409`. A missing target
returns `404`; stale expected state returns `409`; malformed/extra fields return
`422`. A target already in the requested state is an idempotent success with
no duplicate event or version increment. Status transitions record the allowlisted
ADMIN audit event before the route commits once. Persistence, audit or commit
failure rolls back and returns sanitized `503`; authorization remains `401`/`403`.

Suspension increments `auth_version`. New signed access tokens carry `ver`;
tokens issued before this migration use version zero. Every shared protected
request checks both persisted status and version, so customer and admin access
are blocked on the next request (already-running requests are not cancelled).
Login for a suspended account returns the same generic `401` as invalid
credentials. Reactivation allows fresh login; pre-suspension tokens never become
valid again. Public registration/profile contracts still reject status/version
fields, and customer web/mobile response shapes are unchanged.

The Users page displays real status, filters on the server and uses themed
confirmations, pending/error feedback and verified response-driven refresh.
Self-suspension is disabled in the UI and enforced by the API. Activity Logs
displays/filter both status events and provisioning events. Account deletion remains separate work. Account creation, role changes and manual refresh are
implemented by their dedicated endpoints; they do not widen this status request.

Verification covers rollback, idempotency, invalid inputs, actor revalidation,
shared token enforcement, fresh-login reactivation and safe event details;
Docker checks exercise real migration defaults and concurrent status locking in
a disposable schema with fingerprints of all existing public data before/after.

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

## System Health

`GET /api/admin/system-health` requires Bearer authentication and the persisted
admin role. This is a read-only observation endpoint, separate from public
`GET /api/health`, which still reports application liveness without a database
dependency. No new migration, dependency, startup task, or external probe is added.

The response contains `checked_at` (UTC request-start clock), `status`,
`coverage: partial`, `checks`, and nullable `market_data`. Each check contains a
stable `component` identifier, `status`, an allowlisted `reason`, and nullable
`latency_ms`. No exception text, SQL, database URL, secret, account identity,
host paths, or invented timings are returned.

| Component | Evidence and status |
| --- | --- |
| `api` | `healthy`, `request_received`: this request reached the authorized handler; not uptime or fleet health |
| `authentication` | `healthy`, `admin_authorized`: this request passed signed-token and persisted-role authorization; not a probe of registration/password login |
| `database` | Executes `SELECT 1` on the request's already authorized connection; `healthy`/`database_query_succeeded` or `unavailable`/`database_query_failed` |
| `market_data_worker` | Shared heartbeat rules map `online` to `healthy`/`worker_online`, `offline` to `degraded`/`worker_offline`, and no heartbeat to `unknown`/`worker_unknown` |
| `market_data` | Shared required-instrument freshness maps current observations to `healthy`/`observations_current`, stale or missing observations to `degraded`/`observations_stale` or `observations_missing` |
| `market_data_refresh` | Latest stored attempt: success is `healthy`/`refresh_success`; partial/failed is `degraded`/`refresh_partial` or `refresh_failed`; never/running is `unknown`/`refresh_never_run` or `refresh_running` |
| `market_data_provider` | Always `not_checked`/`probe_not_run`; no provider connectivity request or download is made |
| `analytics` | Always `not_checked`/`probe_not_run`; no calculation, forecast, model loading/training/evaluation, or artifact operation is run |

`checks` are returned in the order above. Only the database check has a measured
`latency_ms`, using a monotonic clock around timeout setup and `SELECT 1`;
it is server-side probe duration, not end-to-end request or remote service
latency. Other checks have null latency. A reachable database does not prove
schema/migration completeness, write permissions, or connectivity from another
worker/host.

The PostgreSQL probe sets `SET LOCAL statement_timeout = '2000ms'` for this
request transaction before querying. Subsequent shared market-status reads
use the same per-statement bound. No persistent database setting is changed:
the request owner closes its uncommitted session, rolling back transaction-local
settings. This is not a hard HTTP deadline or an authentication/connection
timeout; token/account authorization happens first. The SQLite test fixture
skips PostgreSQL timeout SQL. No tables, market rows, users, or audit events are
written, and the health service never commits, rolls back, or closes the caller's
session itself.

When the ping fails after authorization, `database` is unavailable and the three
market checks become `unknown`/`database_unavailable`; no further SQL reads are
attempted in a potentially failed transaction and `market_data` is null. If the
ping succeeds but shared status has a database/validation failure, all three
market checks become `unavailable`/`market_status_unavailable` and `market_data`
is null. The successful ping evidence remains visible. Known probe failures do
not turn into successful empty or healthy fallbacks.

Otherwise `market_data` contains exactly the existing
[daily refresh status](market_data.md#daily-refresh-status), evaluated with the
same `checked_at` clock. Its heartbeat, observation freshness, last-attempt
metadata, and prior last-complete marker remain independent. A recorded
`running` flag alone cannot prove an active updater, so its refresh check is
unknown. A failed/partial attempt lowers the summary even with current prices
and a recent worker heartbeat. A successful historical attempt alone cannot
make stale prices or an offline worker healthy. The singleton is latest state,
not a durable history or fleet-wide measurement.

### Summary semantics and HTTP errors

- `unavailable`: database ping failed after successful authorization.
- `degraded`: database ping succeeded, but an observed worker/freshness/refresh
  check is degraded or unavailable. This takes precedence over unknown checks.
- `unknown`: no observed degradation, but worker/refresh evidence is unknown.
- `healthy`: all observed API/auth/database/worker/freshness/refresh checks are
  healthy. Provider and analytics remain unprobed, so `coverage` stays `partial`;
  this must not be displayed as proof that all services are operational.

Known probe failures still return `200` with structured component/summary
statuses: HTTP success means the authorized health observation was produced,
not that the system is healthy. Clients must inspect the payload. Missing,
invalid, expired, or deleted-account credentials return `401`, and customers
or demoted admins return `403` before probes run. If authorization cannot query
the database, this protected report cannot be reached; it never bypasses the
role check or falls back to anonymous diagnostics. Unexpected database or
response-validation failures outside the component probes return sanitized
`503`, `{"detail":"Admin system health unavailable"}`. No HTTP mutations are
exposed.

Automated verification covers real FastAPI/Bearer/role/SQLite reads, truthful
missing/current data and unknown-worker reporting, fixed query counts/no
writes or refresh, failure/unknown precedence, safe failures, actual timed-ping
mapping, and mocked PostgreSQL transaction-local timeout SQL/order. This does
not establish live PostgreSQL cancellation/reset behavior, real-provider
connectivity, analytics execution, deployment health, or browser integration.

## AI Monitoring

Migration `a9b1c3d5e7f0`, after `f8a0b2c4d6e9`, adds `ai_request_logs`.
It introduces no new dependency or provider behavior. Apply the migration to
the explicitly selected deployment database before using the monitoring APIs;
this implementation does not migrate an application/remote database or contact
a real provider. Missing storage causes admin reads to return sanitized 503;
customer explanations retain their existing behavior when telemetry cannot be
stored. There is no startup migration, historical backfill, retention cleanup,
or model training/evaluation.

### What is recorded

Each authorized, schema-valid `POST /api/agent/explain` invocation that reaches
the handler attempts one event with:

| Fields | Meaning |
| --- | --- |
| `id` | Random log UUID; not a user/resource identifier |
| `started_at`, `duration_ms` | UTC handler start and actual monotonic-clock processing duration, rounded to milliseconds with three decimal places; includes provider resolution/context work, excludes authentication, telemetry commit, transport, and client time |
| `created_at` | Database creation timestamp; PostgreSQL `now()` reflects the recording transaction's start, which may precede handler start when the existing read transaction is reused |
| `outcome`, `http_status` | `COMPLETED`, `REFUSED`, or `ERROR` and the selected response status; not proof of client delivery |
| `provider_kind`, `provider_called` | Actual adapter kind (`openai`, `groq`, `custom`), or selected configured kind/null when resolution fails; whether the adapter's `generate` was invoked, including failed attempts |
| `refusal_stage`, `guardrail_reason` | Observed input/output refusal stage and allowlisted deterministic guardrail reason; unsafe-output errors also carry their reason |
| `error_code` | Allowlisted failure classification, never exception text |
| `has_portfolio_source`, `has_report_source`, `has_simulation_source`, `limitation_count` | Returned source categories and limitation count for completed explanations; refusals/errors have false flags and zero count |

No prompt, message, answer, conversation history, system instruction, raw
provider payload, account/email/phone/user ID, portfolio/report/simulation ID,
holdings, balance, financial snapshot, model string, credential, URL, arbitrary
JSON, or free-text error is stored. Only anonymous operational metadata is
retained. There are no foreign keys to accounts/resources, so their deletion
does not change aggregate history. No API exposes update/delete or guardrail/
logging-disable controls. Application recording is insert-only; it is not a
database tamper-evident archive or a retention-policy implementation.

The actual agent observes input guardrail refusals before any tool lookup or
provider call, output advice refusals after a provider call, and unsafe output
rejections without returning the unsafe text. Both advice refusals retain their
existing successful HTTP 200 response; monitoring distinguishes them from
completed explanations without inspecting answer strings. The existing public
request/response bodies and domain ownership rules are unchanged. Provider
resolution now happens after authentication and schema validation inside the
handler, so configuration failures are observable; malformed bodies receive 422
before provider construction. Authentication failures, validation failures,
requests that never reach/finish the handler, crashes, and failed telemetry
commits are not counted. Internal service/agent calls outside this HTTP boundary
do not persist events.

Error codes are `CONTEXT_UNAVAILABLE`, `REPORT_UNAVAILABLE`,
`SIMULATION_UNAVAILABLE`, `MARKET_DATA_UNAVAILABLE`, `HOLDING_STATE_INVALID`,
`PROVIDER_UNAVAILABLE`, `PROVIDER_TIMEOUT`, `INVALID_PROVIDER_RESPONSE`,
`UNSAFE_PROVIDER_OUTPUT`, and `INTERNAL_ERROR`. Guardrail reasons use the
existing catalog: `empty_message`, `investment_advice`, `invalid_output`,
`output_too_long`, `system_leakage`, `planned_ownership_claim`. Empty input is
normally rejected by public schema validation before orchestration. No
guardrail policy is disabled or changed.

Recording uses a typed, revalidated event and database constraints for outcomes,
safe enums, provider-call/refusal consistency, and count/source semantics. The
API owns the event commit. Agent tools/services remain domain-read-only; SQL
context failures reset their failed read transaction before attempting telemetry.
Insert/validation/commit failure rolls back the event, emits only the constant
warning `AI monitoring metadata could not be stored`, and preserves the primary
answer or established error status/detail. No raw exception is logged. This is
best-effort monitoring: persisted counts are not complete lifetime traffic,
unique users, billing, token consumption, or proof of remote-provider receipt.
The provider contract exposes only text, so token usage/cost is not invented.

### Summary and configuration

`GET /api/admin/ai-monitoring` requires the persisted admin role. Optional
timezone-aware `created_from`/`created_to` bound database creation timestamps
inclusively and normalize to UTC. Reversed or naive ranges return 422.
One SQL statement returns `total`, `completed`, `refused`, `errors`,
`provider_calls`, `input_refusals`, `output_refusals`, `average_duration_ms`,
`first_recorded_at`, and `last_recorded_at` for the selected retained rows.
The average covers all selected outcomes. Empty storage returns zero counts
and null average/first/last timestamps. `checked_at` is the UTC generation clock;
no provider/analytics operation runs to produce these metrics.

`configuration` reports only the selected configured provider, whether a model
and the selected provider's key are present, and `ready` (all required settings
present). Model/key text is never returned. `connectivity` is always
`not_checked`, `telemetry_mode` is `best_effort_metadata`, and
`advice_guard_enabled` is true for the always-on current deterministic policy.
Configuration presence is not a network probe or proof of provider availability.
The provider per event is observed separately from current configuration.

### Request metadata directory

`GET /api/admin/ai-monitoring/requests` is admin-only and read-only.

| Query | Meaning |
| --- | --- |
| `limit` | 1–100, default 25 |
| `offset` | 0–10000, default 0 |
| `outcome` | Optional `COMPLETED`, `REFUSED`, `ERROR` |
| `provider_kind` | Optional `openai`, `groq`, `custom` |
| `refusal_stage` | Optional `INPUT`, `OUTPUT` |
| `error_code` | Optional allowlisted code above |
| `created_from`, `created_to` | Optional timezone-aware inclusive creation bounds |

Filters combine with AND. Items sort newest database timestamp/UUID first for
deterministic ties. One SQL statement supplies the bounded page and matching
total, including offsets beyond the last match. Each item exposes only the
fields above. Summary and list are independent reads and can observe different
commits. Customers/demoted accounts receive 403 before monitoring queries;
missing/invalid credentials receive 401. Invalid filters receive 422. Database
or persisted-metadata validation failures return sanitized 503 with
`AI monitoring summary unavailable` or `AI monitoring requests unavailable`.
Reads never create events, commit, resolve providers, contact providers, or run
models. Frontend integration is implemented; live PostgreSQL/provider verification
remains pending. Automated coverage uses real synthetic SQLite/FastAPI/Bearer recording,
fake providers/tools, constraint/rollback checks, and offline PostgreSQL migration
and SQL compilation.

## Admin website integration

The separate admin frontend shares `/api/auth/login` with the customer clients
and verifies `/api/admin/me` before exposing the workspace. Its tab-local token
uses a distinct `aura.admin.accessToken` session-storage key. Tokens and passwords
are not transferred via URLs; decoded token claims never grant admin access.
The backend still resolves the persisted role for every protected request.
401/403 remove the current frontend session; transient failures allow retry.

The dashboard, account directory, market inventory/status/observations, system
health, AI metadata, and audit log pages use the endpoints above. Lists use
bounded server pagination and supported filters, rather than filtering only a
loaded page. DTOs are runtime validated; malformed payloads show an error, never
prototype data. Decimal prices remain strings. Date labels and filters use UTC.
AI summary counts cover all retained events; request filters apply to the list.

Portfolios supports the global read directory and saved details documented below.
Reports still shows dashboard aggregate counts; global report browsing/downloads
and portfolio deletion are subsequent features. No customer ownership endpoint
is used to simulate global access. Users supports the status and role
actions and audit events described above. Market Data supports manual refresh
and run history. Users also create customer accounts. User deletion, account editing, security/session
administration, notifications,
and platform-setting mutations are unavailable. Only theme/compact-sidebar
preferences are persisted locally. Existing colors and component styles remain.

Development uses a Vite `/api` proxy to the configured backend origin. Production
requires a configured backend origin plus exact-origin CORS, or a separately
provided same-origin reverse proxy. See `Admin/README.md` for setup and the
synthetic acceptance harness. Account status adds only the dedicated route and
additive migration above, without new dependencies, model execution or remote-data changes.


## Administrator role management

`PATCH /api/admin/users/{user_id}/role` is protected by the persisted ADMIN role,
active credentials and signed session generation. The body accepts exactly:

```json
{ "role": "ADMIN", "expected_role": "CUSTOMER" }
```

Both fields support only `CUSTOMER` or `ADMIN`; omitted, unsupported and extra
fields return 422. The safe 200 response contains `id`, `role` and UTC
`updated_at`. Unknown targets return 404. Missing/stale/suspended authentication
returns 401 with Bearer challenge; customers return 403.

The service uses the same PostgreSQL users transaction lock as account status
and first-admin bootstrap. It refreshes and rechecks the actor's identity,
credentials, role and original authenticated session generation under that lock.
It prevents self-demotion and removal of the last active credential-bearing
administrator. Only active registered accounts can receive ADMIN permission;
legacy owners and suspended customers cannot be promoted. Suspended administrators
may be demoted without reactivating the account. These safeguards return
allowlisted 409 details. A real transition requires the persisted role to match
`expected_role`; a stale confirmation returns 409. A retry whose desired role is
already persisted returns the current response without another event or version
increment, even when its original expected role is stale.

Every real transition increments `auth_version`. All previous customer/admin
sessions become invalid; the user must sign in again. Promotion never upgrades
an older customer token to administrator access. Demotion and later promotion
never revive an old administrator session. Role assignments and existing owned
records remain separate: portfolios, reports, simulations, account status,
profile and credentials are preserved. Public registration/profile still reject
role writes and create customers only. First-admin operator bootstrap retains
its existing contract. This API introduces no granular permission model.

Role, session-version change and typed `USER_ROLE_CHANGED` audit event commit in
one transaction. Audit/commit or response-validation failure rolls back all
changes and returns sanitized 503 `Account role update unavailable`. No secrets,
credentials, free text or arbitrary event details are recorded. Page reads do
not record mutation events. The existing role and audit migrations suffice;
this feature adds no database migration.

The Users page uses the existing themed confirmation for grant/remove admin
access, describes the effect and fresh sign-in requirement, prevents duplicate
pending submission and reloads verified server state after completion. Self,
legacy and suspended-customer grant actions are disabled with explanatory titles.
Failed/uncertain requests retain the confirmation and refresh the directory;
client feedback never simulates a permission change. Closing animation retains
the selected account wording. Focus returns to the action, or search when the
row leaves a role filter. Activity Logs filters/displays role transitions with
actual actor/target UUIDs and their previous/new roles.


## Customer account creation by administrators

`POST /api/admin/users` requires verified administrator permission and creates
one active, registered CUSTOMER account. Its request accepts canonical `email`,
`password` using the existing minimum-eight-character authentication rule, and
optional nullable `display_name` using the existing trimmed 1–100 character
profile rule. Extra fields are forbidden, including role, status, user ID,
password hash and session version. Password whitespace is significant and is
not trimmed. Omitted/null name leaves the account unnamed. Public registration
is unchanged and still creates customers only.

The 201 response uses the safe Users-directory item contract: UUID `id`,
canonical `email`, nullable `display_name`, CUSTOMER `role`, REGISTERED
`account_type`, ACTIVE `status`, UTC `created_at`/`updated_at`, and zero
`portfolio_count`. No password/hash, session token, private profile preferences
or administrator impersonation is returned. The creator's session is unchanged.
The account can use the existing shared login and change its password through
existing authenticated account settings. Administrator access requires the
separate role-management action and its confirmation/audit. There is no email
invitation, generated default password, forced first-login password change or
creation of a legacy/privileged/suspended account in this feature.

Creation rechecks the actor's persisted credentials, role, suspension and original
session generation under the same PostgreSQL users lock as status/role changes
and bootstrap. AuthService owns canonical email lookup, salted password hashing,
customer defaults and unique-email conflict classification. Optional name update,
account and typed USER_CREATED audit commit together. Audit/commit/hash/response
construction failure rolls back and returns sanitized 503 Account creation
unavailable. Missing/stale credentials return 401 with Bearer challenge;
authenticated customers return 403. Existing accounts and owned data are never
updated by this endpoint.

Canonical duplicate emails return 409 Email already registered and do not reset
credentials or emit another event. Concurrent duplicate requests create exactly
one account. If a successful response is lost, the same email's retry returns
409; inspect the directory instead of assuming another account was created.
The endpoint does not pretend that a duplicate request succeeded. Credential-
bearing validation errors, including malformed bodies, return sanitized 422
Invalid account details without input values or passwords. That error handling
is scoped to this POST route; other endpoint validation contracts are unchanged.

USER_CREATED audit events use an ADMIN actor, USER target UUID, and exactly
role: CUSTOMER / account_type: REGISTERED metadata. Email, name, plaintext,
hash, token and arbitrary free text are excluded. Account/event mutation is
atomic. No new database migration or dependency is required.

The existing Add New User button opens the themed form with optional name, email,
initial password and confirmation. It checks password length/matching, prevents
repeat submissions and closing while pending, clears password fields after each
request and clears all form state on cancel/close. Secret input is never written
to browser storage or displayed in success messages. Transport abort on unmount
does not cancel a committed server operation. Failure/uncertainty retains safe
feedback and refreshes the directory; success validates the server's customer
response, resets stale filters to display the new account and restores focus.
Activity Logs filters/displays the persisted creation event.

## Global portfolio directory and saved details

Both endpoints require the router's verified persisted administrator permission.
They read portfolios across all owners, including legacy and suspended owners.
Customer endpoints retain their existing ownership checks, even for administrators.

- GET /api/admin/portfolios returns items, total, limit and offset. Default limit
  is 25 (1–100); offset is 0 (0–10000). Optional portfolio_type accepts CURRENT,
  PLANNED or LEGACY. Optional owner_id is an account UUID; an absent owner matches
  zero records. Optional q is trimmed, at most 100 characters and searches portfolio
  name, owner email or owner display name case-insensitively. Percent, underscore
  and backslash are literal search characters. Filters combine with AND. Order is
  created_at descending, then UUID descending. Empty pages retain the matching
  total. Counts and rows share a single SQL statement snapshot.
- Directory items contain id, name, portfolio_type, plan_currency, UTC created_at
  and updated_at; owner (id, nullable email/display_name, REGISTERED/LEGACY
  account_type, ACTIVE/SUSPENDED status); holding_count, saved_report_count and
  saved_simulation_count. Holdings and immutable result snapshots are not loaded
  for directory pages. Independent aggregates avoid multiplying counts through
  holdings/results joins. Account type and portfolio type are distinct.
- GET /api/admin/portfolios/{portfolio_id} returns those fields plus nullable
  source_plan_id and holdings in stored position order. It reuses existing
  PortfolioResponse/PortfolioHoldingResponse validation and serialization:
  current shares plus optional investment provenance/date; planned proposed_amount
  in the portfolio's plan_currency; legacy saved weight. Holding IDs, symbols and
  positions are included. Amounts/shares are exact decimal strings; legacy weights
  retain the existing numeric response contract. Optional fields follow the
  existing mode-aware serializer. Empty portfolios return an empty holdings list.
  Header, owner, counts and holdings share one SQL snapshot without loading saved
  report/simulation payloads.

Missing/invalid/stale authorization returns 401 with Bearer challenge; authenticated
customers return 403, before reading portfolio data or revealing existence. A missing
portfolio returns 404 Portfolio not found. Invalid UUIDs/filters return 422.
Storage or invalid persisted response state returns sanitized 503 Admin portfolio
directory unavailable / Admin portfolio details unavailable. No fallback, repair,
valuation, analytics, provider call or synthetic risk/market value is produced.
Credentials, session generations, phone numbers, private preferences and saved
snapshot contents are excluded from both projections.

These are read-only endpoints: no commit, mutation audit, write API, portfolio
deletion or migration is added. The frontend retains aggregate totals and adds
server search/type/owner filters, pagination, explicit loading/error/empty states
and a themed details dialog with retry and focus restoration. It verifies the
detail UUID, decimal strings, mode, counts and ordered holding shape at runtime.
Proposed amounts are described as hypothetical; financial results are not
recalculated in the dialog. Report browsing/downloads remain a separate feature.
