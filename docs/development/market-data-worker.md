# Deployment-ready daily market-data worker

This prepares backend execution only. It does not choose a hosting platform,
deploy anything, install a Windows scheduled task, or start a local worker.
Aura fetches daily historical observations, not streaming quotes.

## Deploy when a host has been selected

1. Install the existing `backend/requirements.txt`; no new dependency is needed.
2. Configure secrets through the host's secret store. Set `DATABASE_URL`, the
   existing API authentication settings, and the market-data settings below.
3. Apply Alembic `upgrade head`, including `d6e8f0a2b4c6`. This new revision adds
   only `market_data_refresh_state`; it does not edit financial records.
4. Start FastAPI as its normal process.
5. Configure one **separate supervised worker**, from the repository root:

   ```shell
   python -m backend.scripts.run_market_data_scheduler
   ```

6. Enable automatic startup/restart on the chosen host. Send console logs to
   its log service and monitor `/api/market-data/status` with authentication.
   API `/api/health` remains application health, not worker/price freshness.

Supabase stores observations but does not run this Python process. Frontend-only
hosting cannot run it either. Hosting, restart policy, and external alert delivery
are not configured by this change. Windows Task Scheduler remains a later task.
The worker needs writable `data/raw/` and `data/processed/` output directories;
provide writable mounts if the deployed application filesystem is read-only.
These generated CSVs are operational outputs, not authoritative deployment state.

## Configuration

| Setting | Default | Meaning |
| --- | --- | --- |
| `MARKET_DATA_UPDATE_TIME_UTC` | `02:00` | Daily UTC HH:MM, 09:00 in Thailand by default |
| `MARKET_DATA_REFRESH_MAX_ATTEMPTS` | `3` | Bounded 1–5 attempts per invocation, including partial fetch retries |
| `MARKET_DATA_REFRESH_RETRY_SECONDS` | `10` | Initial delay, 1–60 seconds; exponential backoff capped at 60 seconds |
| `MARKET_DATA_WORKER_DATABASE_URL` | Falls back to `DATABASE_URL` | Optional direct/session-pooled connection to the **same database** |

Session advisory locks require a direct PostgreSQL connection or session pooling.
Do not use transaction pooling for the worker or persisting updater. Known
Supabase transaction-pool URLs on port 6543 are rejected; other poolers must be
configured correctly by the operator. The API can retain its ordinary runtime
connection. Worker connections are dedicated/non-pooled, with a 10-second connect
timeout and 30-second statement timeout. Provider requests retain their existing
20-second per-request timeout. These are not a hard whole-job deadline.

Connection requirements follow [PostgreSQL session advisory-lock semantics](https://www.postgresql.org/docs/current/explicit-locking.html#ADVISORY-LOCKS)
and [Supabase direct/session/transaction connection guidance](https://supabase.com/docs/guides/database/connecting-to-postgres).

## Execution and recovery

- A PostgreSQL worker-leader lock prevents two scheduler replicas. A distinct
  update lock covers the entire fetch/retry/write sequence for scheduled jobs,
  catch-up, and `update_market_data --persist-database`.
- The worker sends a heartbeat every 60 seconds. Loss of its heartbeat/lease
  stops it with a nonzero exit for the supervisor to restart. An update error
  does not stop a healthy scheduler.
- At startup and hourly, catch-up checks the latest due UTC slot and persisted
  coverage under the update lock. One refresh covers missed days; missed slots
  are not replayed individually. No persistent APScheduler job store is needed.
- Full/current successful coverage skips redundant catch-up. Partial/stale runs
  are retried on later checks. Each invocation has its own bounded attempts.
- The pipeline still uses its existing full historical range (2010 onward by
  default), cleaning, validation, `(symbol,date)` upserts, and batching. This
  intentionally avoids introducing incremental adjusted-price reconciliation.
- Default refresh coverage ends yesterday UTC; explicit historical CLI end dates
  are capped at that boundary. No unfinished current-day daily bar is requested.
- Valid partial data commits without deleting old observations for failed
  symbols. Observation writes and their final status commit together; a failed
  transaction rolls back both. Attempt/heartbeat bookkeeping commits separately.
- Transient provider/network/database errors retry only while the original lock
  remains valid. Invalid data does not retry. A lost physical lock connection
  aborts without silently reconnecting to write prices. Closing it releases locks.
  Initial connection/lease failures exit safely; restart/backoff at that stage
  belongs to the deployment supervisor, not an unlocked updater loop.
- `SIGTERM`/terminal interruption requests graceful shutdown. Allow time for a
  running request to finish. A force-killed worker can leave the last run marked
  running; expired heartbeat and next-worker catch-up support recovery.

The existing one-shot command now shares tracking/locking and requires the
migration before use:

```shell
python -m backend.scripts.update_market_data --persist-database
```

CSV-only and historical seed/backfill tooling remain unchanged. Coordinate those
operator-only workflows while the worker is stopped: they do not acquire this
worker lock and may replace the shared generated CSVs. CSV and PostgreSQL remain
separate transactions; generated files are not proof of a committed DB update.

## Verification and boundaries

Unit/API tests use mocked providers/databases. Guarded live acceptance uses only
an explicitly selected **local** `aura_test`/`aura_test_*` database and temporary
UUID-named schemas, synthetic canonical observations, and fixture-only cleanup.
It verifies real locks, migration DDL, commit/rollback, partial preservation,
heartbeat, and recovery after terminating its own lock connection. It never
migrates public, changes application rows, or contacts Yahoo Finance.

Before release, perform an explicitly authorized real-provider smoke on the
chosen deployment database and verify required assets plus `THB=X`, per-symbol
dates, logs, restart recovery, and status. This has not been run by the code change.
No web/mobile changes, host configuration, deployment, production migration,
financial-formula change, forecast retraining, or artifact regeneration is included.
