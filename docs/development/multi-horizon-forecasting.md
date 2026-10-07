# Multi-horizon forecasting — manual rollout

Date: 2026-10-07

## Current checkpoint: reviewed selection and manual freeze

The new offline workflow constructs true 7-, 14-, and 21-calendar-day return
and non-annualized realized-volatility labels. It reuses V1 features, baseline/
model families, chronological folds, minimum training history and selection
policy. The original 30-day target builder, deployment workflow, inference,
APIs, frozen `forecast-v1-20260917` package and customer clients are unchanged.
Weekly buttons remain disabled. This checkpoint does not claim trained weekly
artifacts, calibrated ranges, final-test performance or runtime readiness.

Training/evaluation, tests and builds are user-run only for this task. The user
completed the selection run on the verified original snapshot; Codex reviewed
the local JSON without rerunning evaluation or accessing the database/provider.
The new freezer and regression tests are prepared. Their execution, including
creation of the frozen manifest, awaits the user's terminal commands.

## Files and responsibilities

- `backend/app/forecasting/multi_horizon.py`: immutable horizon-aware labels,
  feature/label joins, an isolated compatibility bridge to existing candidate
  algorithms, and selection-only orchestration.
- `backend/scripts/evaluate_forecasting_horizons.py`: explicit local database
  selection, read-only transaction, required fingerprint/row-count gate,
  new-file output guards and strict horizon-aware JSON evidence.
- `backend/tests/unit/forecasting/test_multi_horizon.py`: synthetic/mocked
  checks for calendar/slippage rules, no scaling/filling, volatility windows,
  30-day formula parity, joins, mixed horizons, endpoint purging, report labels,
  provenance mismatch, database lifecycle, safe errors and frozen-file protection.
- `backend/app/forecasting/horizon_selection_manifest.py`: validates all 102
  groups, recomputes the established selection policy and freezes deterministic
  horizon-aware records with provenance, versions and selected-model warnings.
- `backend/scripts/freeze_forecasting_horizons.py`: verifies the reviewed report's
  exact byte checksum before parsing, rejects duplicate JSON keys/non-finite
  values, and writes only a new ignored evidence manifest. No fitting or DB access.
- `backend/tests/unit/forecasting/test_horizon_selection_manifest.py`: synthetic
  report/manifest validation, policy and warning consistency, checksum changes,
  full coverage, strict JSON, source preservation and protected-output checks.
- `CURRENT_STATUS.md` and this guide: checkpoint and manual next steps.

No dependency, architecture-file move, migration, server task, commit or push
is included. Unrelated report files are preserved.

## Label and evaluation rules

For horizon H, use the first persisted price on or after origin + H calendar
days, with at most four days of slippage. Missing endpoints are omitted, not
backfilled. Return is endpoint price / origin price - 1. Realized volatility
uses the square root of the sum of squared consecutive future-window log returns;
it is not annualized. Neither value is a fraction of the 30-day forecast.

Past-only V1 features are identical across horizons at a common origin, but
each horizon has distinct labels and its own candidate comparisons. Feature
lookbacks still count observed rows, not calendar days. The new target-set
identities are `forecast-targets-7d-v1`, `forecast-targets-14d-v1`, and
`forecast-targets-21d-v1`. The original V1 identity remains unchanged.

The private candidate bridge puts these freshly computed values into V1's
legacy internal slots so algorithms need not be rewritten. It does not load,
repurpose or publish the trained 30-day artifacts. Serialized evidence uses
`return_7d` / `realized_volatility_7d` and analogous names for each actual horizon;
it cannot be passed to the original V1 selection freezer as a deployable package.

Selection uses the existing five chronological folds only. Training labels
must finish strictly before each fold starts. Scored evaluation labels must
finish strictly before that fold ends, so selection cannot score outcomes from
the reserved calibration/final-test periods. This stricter scoring boundary is
isolated from V1; do not compare its selection metrics as an identical rerun of
the original V1 protocol. The original 5% complex-model improvement and 1%
practical-tie rules remain unchanged. Unavailable candidate/fold results are
reported explicitly; the command does not fabricate a winner or deploy fallback.

## Manual commands

Run from the repository root in PowerShell. Every command is a single line.
Run tests first; stop and share any failure before freezing. The selection command
below is retained for provenance/reference: the approved run already completed.
Do not rerun it or overwrite its evidence for this checkpoint.

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests/unit/forecasting backend/tests/unit/schemas/test_forecasting.py backend/tests/unit/schemas/test_portfolio_forecasting.py backend/tests/integration/api/test_forecasting_api.py backend/tests/integration/api/test_portfolio_forecasting_api.py -q -p no:cacheprovider
```

After tests pass, the following command deliberately selects the separately
restored `aura_forecast_training_20260917` local snapshot: 69,928 rows, 17 assets,
and the original V1 fingerprint, verified by the user's manual run. It does not
silently switch to current application data, another
database URL key, or a new cutoff. The environment file is read without variable
interpolation. Only a PostgreSQL loopback connection on port 5433 is accepted;
remote URLs and connection-query overrides are rejected. No credentials appear
in evidence or expected error messages. `--database-name` changes only the
database component of that explicit local URL in memory; credentials, host,
port and allowed options are preserved. Overrides require a lowercase
`aura_forecast_training_` name and cannot select `aura_test` or a remote server.
Omitting this option preserves the previous command's URL behavior.

```powershell
.\.venv\Scripts\python.exe -m backend.scripts.evaluate_forecasting_horizons --env-file .\.env.test-database --database-url-key TEST_DATABASE_URL --database-name aura_forecast_training_20260917 --evaluation-cutoff 2026-09-17 --horizons 7 14 21 --expected-market-data-fingerprint dd8cfbe6963ffad4cb3f64034e834d324c7981426704193c00256c9add504e99 --expected-row-count 69928 --output .\forecasting-evidence\forecast-multihorizon-selection-20260917\selection.json
```

The command may take a substantial amount of time: it compares five candidates
over five selection folds, two targets, three horizons and 17 assets. It prints
progress per symbol/target/horizon. It performs offline selection fitting only,
not deployment-artifact training. All database resources close before fitting.

### Original-snapshot recovery checkpoint

The user's first targeted test run passed 526 checks. Initial evaluation stopped
before fitting because the ordinary Docker database contained 95,488 rows ending
on 2026-08-21. The current Supabase slice had the original counts/date ranges but
a different canonical fingerprint; neither was approved as the frozen V1 input.

The user selected the original backup and manually created a separate database
and matching market-data table, then restored the data-only archive using an
all-or-nothing transaction. The user reported 69,928 rows and the exact original
fingerprint `dd8cfbe6963ffad4cb3f64034e834d324c7981426704193c00256c9add504e99`
from `aura_forecast_training_20260917`. Application databases, environment files
and frozen models were not replaced by these commands.

The small database-selector addition has regression tests for explicit routing,
credential/endpoint preservation, unchanged environment files, safe failures,
invalid names and remote rejection. Those new tests await the user's manual run;
the earlier 526-pass result does not verify this subsequent addition. Selection
fitting is now completed and reviewed, but calibration, final testing and artifact
generation remain pending. Keep the training database separate from
the application's daily updater for the remainder of this run.

If the snapshot fingerprint differs, stop; do not replace the expected hash
simply to bypass the guard. Confirm the intended dataset and cutoff first.
If choosing updated data instead, fingerprint and approve that snapshot through
the existing provenance workflow, then supply its matching cutoff/hash/count.
Reusing the V1 snapshot does not create a wholly untouched project-level holdout.
A later fresh-period assessment is needed for that stronger claim.

The script creates a separate ignored evidence folder and refuses to overwrite
an existing JSON file or write inside frozen V1 evidence. A rerun needs a new
filename, not deletion of earlier evidence. A failure produces no successful
report and does not modify the frozen package or activate weekly UI controls.

## Completed selection evidence review

The local report `forecasting-evidence/forecast-multihorizon-selection-20260917/selection.json`
was reviewed read-only. Its byte SHA-256 is
`9579936f543c20a9b7adf117bba982375cb518ea22378b9f831c9379d60fea06`.

- Schema/stage, approved cutoff, 69,928 rows, 17 symbols and original V1 data
  fingerprint match. All 102 groups and 2,550 candidate/fold results are present
  and available. Minimum training count is 1,501, exceeding the required 756.
- Independently recomputed means and policy leaders match the report. Returns
  select historical averages except MSFT at 14 days (moving average).
- There are 57 available ARIMA convergence warnings. One belongs to a selected
  model: QQQ 21-day volatility on selection fold 05. Its mean MAE improves over
  the best baseline by about 16.11%. Existing policy allows this available warned
  fit; preserve the warning without silently changing the winner. This selection
  is not evidence of calibrated intervals or final-test acceptance.

## Next manual command: freeze reviewed selections

Run the test command above first. After it passes, run this single line:

```powershell
.\.venv\Scripts\python.exe -m backend.scripts.freeze_forecasting_horizons --selection-report .\forecasting-evidence\forecast-multihorizon-selection-20260917\selection.json --expected-selection-report-sha256 9579936f543c20a9b7adf117bba982375cb518ea22378b9f831c9379d60fea06 --expected-market-data-fingerprint dd8cfbe6963ffad4cb3f64034e834d324c7981426704193c00256c9add504e99 --expected-row-count 69928 --output .\forecasting-evidence\forecast-multihorizon-selection-20260917\selection-manifest.json
```

The command checks exact source bytes before parsing and revalidates the full
five-fold policy, versions, fold dates, coverage, counts and selected warnings.
The original report is never changed. The output refuses an existing filename,
frozen V1 evidence, artifact folders or any path outside `forecasting-evidence/`.
It never opens a database, fits estimators, calibrates intervals or writes models.

The manifest schema is `forecast-horizon-selection-manifest-v1`, release identity
`forecast-weekly-v1-20260917`, and stage `frozen_selection_not_deployable`. Records
use actual 7/14/21-day target names and include the reviewed source hash and data
provenance. All 102 records and one selected-model warning should be retained.
The manifest reader validates the complete contract, ordering and digest. A
self-contained digest is an integrity check, not proof of an approved decision:
later training must pin the reviewed manifest hash and verify its source binding.

Share the command's summary and manifest before calibration. No frozen weekly
manifest has been produced by the agent; final-test results, trained models,
runtime APIs and client activation are not claimed by this checkpoint.

## Subsequent checkpoints, not yet implemented or activated

1. Run tests and the prepared freezer, then review its manifest and checksum.
   Keep the weekly evidence separate and do not overwrite V1.
2. Implement/run horizon-specific calibration, a guarded final test and
   deployment-artifact training. Preserve separate test evidence and interval
   coverage per horizon; do not reuse the 30-day residual ranges.
3. Validate/load the new package through horizon-aware runtime contracts while
   preserving the original 30-day endpoints and package behavior. Portfolio
   composition must use component forecasts for the same selected horizon.
4. Integrate backend-supported horizons on both clients, enabling only verified
   horizons. Plot actual horizon estimates and asset ranges; connecting lines
   are visual guides, not a predicted daily price trajectory. Do not invent
   portfolio prediction intervals or forecast AI grounding.

Suggested checkpoint commit: `feat(forecasting): freeze validated weekly model selections`
