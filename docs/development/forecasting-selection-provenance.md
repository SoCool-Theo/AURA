# Manual forecasting selection provenance

Return and volatility selection remain offline, user-triggered operations.
Production inference does not run these scripts or fit models per request.
Selection calculations, candidates, folds, and thresholds are unchanged.

Both manual evaluators now require `--env-file`. `--database-url-key` defaults
to `DATABASE_URL`, and only that requested key in that file is read, without
interpolation or fallback to process environment or other database keys.
Use `TEST_DATABASE_URL` explicitly for the existing Docker environment file.
URLs and credentials are never part of the report or connection-error message.

Supply `--expected-market-data-fingerprint` and `--expected-row-count` together.
The same loaded record collection is canonically fingerprinted and then used
for evaluation. The existing fingerprint implementation includes approved
symbols, cutoff, normalized adjusted-close prices, volume, source, and stored
dates. Either mismatch stops before any candidate fitting/evaluation and leaves
an existing output report untouched. Invalid or partial expectations also fail.

The additive `data_provenance` block records `provenance_verified`, the actual
cutoff, symbol count, row count, and SHA-256. Omitting both expected values is
allowed for non-official developer use but explicitly reports
`provenance_verified=false`, even though a persisted-data fingerprint is recorded.
Pure history-based internal calls lack canonical volume/source and therefore
serialize unverified provenance with null counts/hash. Old report readers and
the selection freezer tolerate the additive block without changing selection
validation. The freezer does not itself enforce verified provenance; official
readiness review must check the new reports before any further artifact work.

## User-controlled remediation run

After code review, run these from the repository root against the frozen local
database selected by the existing environment file. The expected values below
are supplied by the user, not hardcoded in general evaluation logic. A wrong
database or changed snapshot must fail the provenance gate.

```powershell
.\.venv\Scripts\python.exe -m backend.scripts.evaluate_forecasting_return_models --env-file .\.env.test-database --database-url-key TEST_DATABASE_URL --evaluation-cutoff 2026-09-17 --expected-market-data-fingerprint dd8cfbe6963ffad4cb3f64034e834d324c7981426704193c00256c9add504e99 --expected-row-count 69928 --output .\forecasting-return-model-selection-2026-09-17-provenance-verified.json

.\.venv\Scripts\python.exe -m backend.scripts.evaluate_forecasting_volatility_models --env-file .\.env.test-database --database-url-key TEST_DATABASE_URL --evaluation-cutoff 2026-09-17 --expected-market-data-fingerprint dd8cfbe6963ffad4cb3f64034e834d324c7981426704193c00256c9add504e99 --expected-row-count 69928 --output .\forecasting-volatility-model-selection-2026-09-17-provenance-verified.json
```

These output paths preserve the prior reports. Confirm both new reports have
verified provenance and compare their selections with the existing frozen
manifest. Do not overwrite or regenerate `forecast-v1-20260917`; subsequent
manifest/artifact decisions require a separate user decision. This code change
does not retroactively prove the provenance of the original selection reports.

## Verified selection reconciliation

The user manually performed the remediation reruns on the authoritative frozen
69,928-row, 17-symbol dataset with evaluation cutoff `2026-09-17`. Both supplied
reports record `provenance_verified=true`, that cutoff, `row_count=69928`,
`symbol_count=17`, and market-data fingerprint:

`dd8cfbe6963ffad4cb3f64034e834d324c7981426704193c00256c9add504e99`

Read-only reconciliation recorded the following report byte SHA-256 values:

| Verified report | SHA-256 |
| --- | --- |
| `forecasting-return-model-selection-2026-09-17-provenance-verified.json` | `e67ba08ec196d4527863afa9b205998557e4a36470df604bfb183b25ee7e4ad4` |
| `forecasting-volatility-model-selection-2026-09-17-provenance-verified.json` | `ef9f9fa2b7546724951d6df3aab4a96b90a163057b8f9989d324e68c9d79b132` |

Selection decisions were independently reproduced on the authoritative frozen
dataset. All 17 return and 17 volatility candidate IDs match both the frozen
selection manifest and the root artifact manifest: **34/34 matches**. The
following symbol-sorted table records the identical verified and frozen IDs.

| Symbol | Return candidate | Volatility candidate |
| --- | --- | --- |
| AAPL | historical_average | volatility_linear_regression_v1 |
| AMZN | historical_average | volatility_linear_regression_v1 |
| BND | historical_average | moving_average_90_calendar_days |
| BTC-USD | historical_average | moving_average_90_calendar_days |
| DIA | random_forest_v1 | volatility_linear_regression_v1 |
| ETH-USD | historical_average | moving_average_90_calendar_days |
| GLD | historical_average | historical_average |
| GOOGL | historical_average | volatility_arima_1_0_1_v1 |
| META | historical_average | volatility_random_forest_v1 |
| MSFT | historical_average | moving_average_90_calendar_days |
| NVDA | historical_average | volatility_arima_1_0_1_v1 |
| QQQ | moving_average_90_calendar_days | volatility_arima_1_0_1_v1 |
| SLV | historical_average | historical_average |
| SPY | moving_average_90_calendar_days | volatility_linear_regression_v1 |
| TLT | historical_average | moving_average_90_calendar_days |
| TSLA | historical_average | historical_average |
| VTI | historical_average | volatility_random_forest_v1 |

The original Phase 4/5 run dataset provenance was not independently recorded.
These reruns reproduce the selection decisions; they do **not** establish which
dataset the original historical runs used, or reproduce calibration/final-test
metrics. The original package `forecast-v1-20260917` remains frozen and was NOT
regenerated. Calibration and final-test reports were NOT rerun. Original report
hashes in the frozen selection manifest remain unchanged; the verified reports
are additional audit evidence, not replacements for the original reports.

## Final readiness audit

Read-only inspection confirms 17 symbols, two targets, 34 unique artifacts,
`final_test_completed=true`, `forecast-features-v1`, `forecast-targets-v1`, and
nominal interval coverage `0.80`. All 68 model/metadata checksums match. Every
metadata record agrees with the root identity/version, candidate, model hash,
and authoritative training fingerprint. The canonical frozen selection manifest
hash is `fd2dedc4f3531a58278e450bce18f7471f4e8613c9f03bb8f22feb1596ada0e9`.
The embedded selection manifest and training verification also match their
original root-level source files byte-for-byte. No artifact was modified.

The production forecasting request path uses the current application's existing
database session, persisted market data, and frozen artifact prediction only.
Shared artifact/interval types import modules that also define offline training
helpers; importing those definitions does not execute or call them. Forecasting
routes/inference never invoke fitting, partial fitting, refitting, model-state
append/extend/update, selection, calibration, final testing, artifact generation,
provider retrieval, or offline database URL selection. No offline script or
`yfinance` library is loaded by the application import smoke check. Existing
updater/provider code is a separate operational workflow, not forecast inference.

Synthetic tests validate fixed 30-calendar-day, non-annualized forecasts;
nominal 80% empirical asset intervals; four-calendar-day freshness; approved
ARIMA stored-observation step alignment and repeated-origin determinism; Bearer
authentication; ownership-safe portfolio lookup; finite response values; safe
failure messages; and unchanged deterministic historical/report/simulation/AI
behavior. Portfolio composition uses authoritative backend weights, arithmetic
weighted return, `Sigma = D @ R @ D`, and `sqrt(w.T @ Sigma @ w)`. Correlations use
60–252 common-date daily log returns, no filling, and the earliest component
origin cutoff. Signed Euler contributions remain signed; shares sum to one when
defined, and zero volatility yields zero contributions/shares. One unavailable
component fails the whole outlook. No calibrated portfolio-level interval exists.

Validation passed: 345 forecasting unit tests in a dedicated run; 3,219 tests
across all backend unit tests and every non-live
API suite, including AI Agent regressions; Python compilation; import/OpenAPI
checks (25 paths, 32 operations); `pip check`; and Git whitespace/scope checks.
The 54 warnings are from the existing short JWT secret in the AI test fixture.
PostgreSQL-specific and live-database integration suites were excluded. No real
database access, model fitting/evaluation, calibration, final testing, artifact
generation, or live forecast acceptance was performed by Codex.

Readiness decision: **READY TO MERGE** under the requested reconciliation and
read-only integrity gates. Fresh-data live `200` acceptance is not required for
this decision: stale persisted data must safely return `503`. Restoring the
production updater is a separate operational follow-up. Deployment must preserve
the trusted immutable artifact package; checksums detect drift, not malicious
replacement of both manifests and serialized models.

Generated root-level forecasting JSON reports (old and verified), fingerprint
and verification JSON files, the Supabase snapshot dump, and artifact backup ZIP
are untracked and now narrowly ignored, as is the frozen artifact directory.
No user-generated evidence was deleted or rewritten; source and documentation
remain visible to Git. No commit, push, merge, PR, or branch change was performed.
