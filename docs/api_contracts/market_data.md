# Prepared historical market data

These provider-independent contracts describe requests for, and exchange of,
prepared daily historical market data. They do not fetch, clean, or store data.

## `HistoricalMarketDataRequest`

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `symbols` | `list[AssetSymbol]` | Yes | One or more ordered, normalized, unique symbols. |
| `start_date` | `date` | Yes | Inclusive requested start date. |
| `end_date` | `date` | Yes | Inclusive requested end date. |

## `HistoricalPricePoint`

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `date` | `date` | Yes | Observation date. |
| `adjusted_close` | `float` | Yes | Positive finite adjusted-close value. |
| `volume` | `int \| null` | No | Non-negative integer volume; defaults to `null`. |

## `AssetPriceSeries`

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `symbol` | `AssetSymbol` | Yes | Normalized asset symbol. |
| `source` | `str` | Yes | Non-empty trimmed source description; not a closed provider enum. |
| `points` | `list[HistoricalPricePoint]` | Yes | One or more observations in strictly increasing date order. |

Point dates must be unique. Schemas preserve supplied order and reject, rather
than sort or repair, malformed series. Consecutive calendar or business dates
are not required.

## `HistoricalMarketDataResponse`

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `series` | `list[AssetPriceSeries]` | Yes | One or more ordered series with unique normalized symbols. |
| `start_date` | `date` | Yes | Inclusive response-period start. |
| `end_date` | `date` | Yes | Inclusive response-period end. |

Every point must fall inside the declared period. Assets may have different
trading dates and different point counts. Unknown fields are rejected.

Canonical examples:

- [`backend/examples/market_data_request.json`](../../backend/examples/market_data_request.json)
- [`backend/examples/market_data_response.json`](../../backend/examples/market_data_response.json)

## Runtime instrument boundary

The production pipeline, PostgreSQL persistence, historical retrieval, and
scheduled update workflow are implemented outside these transport schemas.
Aura separates:

- 17 user assets, all quoted in USD; and
- the internal `THB=X` USD/THB instrument (THB per USD).

Default and scheduled updates include the internal FX series. Explicit user
asset selection remains the 17-symbol set, so `THB=X` must not be exposed as a
holding choice. Current valuation accepts a required asset or FX observation
only when it is no more than four calendar days old.

## Daily refresh status

`GET /api/market-data/status` is authenticated and read-only. It requires
migration `d6e8f0a2b4c6` after `c3d5e7f9a2b4`. The singleton operational table
is separate from prices, user data, reports, simulations, and model artifacts.

Response fields:

- `mode`: `daily`, never live/streaming.
- `checked_at`, `update_time_utc`, `next_scheduled_at`: UTC timestamps and the
  configured HH:MM schedule. The next time is nominal; an offline worker cannot
  execute it. The default 02:00 UTC is 09:00 Asia/Bangkok.
- `worker_status`: `unknown` before any heartbeat, `online` while marked running
  with a heartbeat no more than 180 seconds old, otherwise `offline`.
  `worker_last_seen_at` is independent of successful data updates.
- `last_run_status`: `never`, `running`, `success`, `partial`, or `failed` from
  the last persisted attempt. A crash can leave `running` until recovery; this
  field alone is not proof of an active process.
- `last_attempt_at`, `last_finished_at`, `last_complete_at`: nullable UTC times.
  Only a complete, current, full-universe daily refresh advances last-complete.
  Subset updates, historical backfills, failures, and partial runs do not erase
  or advance the prior complete marker.
- `attempt_count`, `stored_count`, `updated_symbols`, `failed_symbols`: latest
  run details; stored count is for the last committed attempt, not net new rows.
- `error_code`: null or a safe classification: `provider_unavailable`,
  `database_unavailable`, `validation_failed`, `update_failed`, `lock_lost`, or
  `incomplete_coverage`. No provider exception, SQL, credentials, or URL is exposed.
- `data_status`: `missing` if any required instrument has no observation,
  otherwise `current` only if all satisfy the status freshness checks, else `stale`.
- `observations`: the 17 assets then internal `THB=X`, each with `symbol`,
  `kind` (`asset`/`fx`), nullable `latest_price_date`/`age_days`, and `is_current`.
  Missing/future dates are not current; invalid future ages are null.

Daily status expects completed dates before today UTC. Crypto must have
yesterday's observation; stocks/ETFs/FX retain the four-calendar-day tolerance.
This is a freshness tolerance, not an exchange-holiday calendar or proof that
the latest trading session is present. Existing valuation/forecasting freshness
checks are unchanged. A successful fetch and current observations are distinct.
Market observation dates are not the timestamps when Aura downloaded data.

Missing authentication returns `401`; status retrieval failures return safe
`503`. There is no customer POST/refresh endpoint and no application-startup
scheduler.

## Web and mobile integration

Both clients read status on Watchlist and current-portfolio dashboard/detail
screens. Freshness labels use only the displayed symbols (including internal
USD/THB when THB valuation is selected), not the entire market universe.
Worker connectivity and partial/failed attempts remain separate from price
freshness. A persisted running flag is not described as proof of an active update.

Existing loaders read prices on entry; foreground return and five-minute active
polling reload persisted Watchlist/current valuation data. Web offers a compact
Refresh button, while mobile uses pull-to-refresh. Hidden browser tabs,
background apps, and blurred mobile screens do not poll. Status reads have a
20-second timeout, abort on inactivity/cleanup, and ignore late account responses.
Status failures show an unavailable label without blocking existing price APIs.
These are GET reads, never provider downloads or automatic report creation.
Planned allocations, saved reports, and saved simulations are not revalued.

Apply the migration before using status. Automatic provider updates still
require separately starting/supervising the backend worker; client refresh
alone does not make the updater run.
