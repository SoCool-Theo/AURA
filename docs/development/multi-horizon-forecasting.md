# Multi-horizon forecasting — manual rollout

Date: 2026-10-07

## Current checkpoint: trained package reviewed; backend runtime prepared

The new offline workflow constructs true 7-, 14-, and 21-calendar-day return
and non-annualized realized-volatility labels. It reuses V1 features, baseline/
model families, chronological folds, minimum training history and selection
policy. The original 30-day target builder, deployment workflow, inference,
endpoints, frozen `forecast-v1-20260917` package and customer clients are unchanged.
Weekly buttons remain disabled. Selection, calibration and final testing are
completed and reviewed. The user trained the separate experimental weekly bundle
and its 102 model/metadata pairs were reviewed read-only. Additive weekly runtime
and API code is now prepared; its new regressions and real runtime smoke checks
remain user-run, not a claim of verified deployment readiness.

Training/evaluation, tests and builds are user-run only for this task. The user
completed the selection run on the verified original snapshot; Codex reviewed
the local JSON without rerunning evaluation or accessing the database/provider.
The user ran 627 targeted tests successfully and created the frozen manifest.
Its canonical checksum and provenance were verified read-only. The user then ran
661 targeted tests and completed all 102 calibrations, followed by 721 passing
tests and the one-run final evaluation. A later run reported 791 passed and one
test false positive caused by `30d` inside a valid checksum; that assertion was
corrected. The user completed training afterwards, but an updated passing test
count has not been supplied. No agent-run test result is claimed.

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
- `backend/app/forecasting/horizon_calibration.py`: calibration-only horizon
  orchestration, reused empirical residual quantiles, strict endpoint purges and
  final-period exclusion before feature/label construction.
- `backend/scripts/calibrate_forecasting_horizons.py`: pinned manifest/source
  reconciliation before DB access, read-only original-snapshot verification,
  selected-candidate calibration and new-file evidence output only.
- `backend/tests/unit/forecasting/test_horizon_calibration.py`: synthetic/mocked
  residual calculations, clipping, boundary isolation, frozen identity, warning
  retention, no fallback, cache reuse, source binding and database/output guards.
- `backend/app/forecasting/horizon_final_test.py`: strict pinned calibration
  reader, frozen-candidate final-fold scoring, inclusive empirical asset interval
  coverage, explicit empty-interval misses and checksum-bound evidence.
- `backend/scripts/evaluate_forecasting_horizon_final_test.py`: manual, pinned
  selection/calibration/provenance gates, one-run markers and final scoring only.
- `backend/tests/unit/forecasting/test_horizon_final_test.py`: synthetic coverage,
  frozen ranges, clipping, boundary isolation, bad evidence, poor finite results,
  source preservation, database lifecycle and consumed-run/retry protection.
- `backend/app/forecasting/horizon_artifacts.py`: pinned final-evidence validation,
  actual-horizon serialized wrappers, frozen-candidate deployment fitting and
  new-only experimental packages with reload checks, hashes and quality evidence.
- `backend/scripts/train_forecasting_horizons.py`: explicit experimental-quality
  acknowledgement, existing final-run completion checks, verified read-only
  snapshot access, revision/source-byte recording and fixed weekly output only.
- `backend/tests/unit/forecasting/test_horizon_artifacts.py`: synthetic/mocked
  evidence gates, true-horizon completed labels, frozen families/parameters,
  wrapper identity, 102-model packaging, partial/reload failures and DB/CLI guards.
- `backend/app/forecasting/weekly_registry.py`: externally pinned, read-only
  deployment loader with full-package integrity and actual-horizon identity gates.
- `backend/app/forecasting/weekly_inference.py` and `weekly_portfolio.py`:
  past-only current asset estimates and same-horizon authoritative composition.
- `backend/app/schemas/weekly_forecasting.py`,
  `backend/app/services/weekly_forecasting_response_mapper.py`, and
  `backend/app/api/routes/weekly_forecasting.py`: additive neutral-field weekly
  contracts and authenticated, owner-safe read-only endpoints. The existing
  API router registers the new routes alongside unchanged 30-day routes.
- `backend/tests/unit/forecasting/test_weekly_registry.py`,
  `test_weekly_inference.py`, and
  `backend/tests/integration/api/test_weekly_forecasting_api.py`: synthetic
  loading, composition, contracts and access-control regressions. The existing
  forecasting OpenAPI inventory assertion also includes the two additive paths.
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
Run the current runtime verification command near the end of this guide.
Selection, freeze, calibration, final-test and training commands below are
retained for reference: approved runs already completed. Do not rerun them or
overwrite their evidence.

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
invalid names and remote rejection. The later 627-pass run verifies selection
and freeze regressions; the 661-pass run also verifies calibration and the later
721-pass run includes final-test regressions. Selection, calibration and final
testing were completed and reviewed before the later user-run artifact fitting.
Keep the training database separate from the application's daily updater.

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

## Completed manual selection freeze (reference command)

The user successfully ran the following single line; do not overwrite its output:

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

The completed manifest has 102 records and one selected-model warning. Its
verified canonical SHA-256 is
`829b5f9616643c3969cbd1cf220ce25b113d1b494b88c0693e376d5c43292a5c`.
The source report is unchanged. Neither the manifest nor the 627-pass test run
constitutes calibration, final-test evidence or weekly deployment readiness.

## Completed manual calibration (reference command)

The user successfully ran this command after 661 targeted tests passed:

```powershell
.\.venv\Scripts\python.exe -m backend.scripts.calibrate_forecasting_horizons --env-file .\.env.test-database --database-url-key TEST_DATABASE_URL --database-name aura_forecast_training_20260917 --selection-manifest .\forecasting-evidence\forecast-multihorizon-selection-20260917\selection-manifest.json --selection-report .\forecasting-evidence\forecast-multihorizon-selection-20260917\selection.json --expected-manifest-sha256 829b5f9616643c3969cbd1cf220ce25b113d1b494b88c0693e376d5c43292a5c --output .\forecasting-evidence\forecast-multihorizon-selection-20260917\calibration.json
```

The manifest's canonical hash is pinned, its source bytes are checked, and all
frozen records are reproduced from that reviewed source before reading the
environment file or opening a database. The command requires an explicit isolated
training-database name. Dataset hash, row count and cutoff come from the pinned
manifest: there is no separate flag that can silently override that provenance.
The full snapshot is read once in a read-only transaction and verified, then
database resources close before any selected estimator is fitted.

Calibration uses `calibration-01`: origins from 2025-03-18 through 2025-09-17
(exclusive end 2025-09-18). Prices on/after that end are removed before feature
and label construction. Training endpoints must precede 2025-03-18, and scored
endpoints must precede 2025-09-18. Origins near the end whose targets complete in
the final-test period are excluded. The 756 training-origin requirement remains
unchanged, and at least 60 usable calibration observations are required per
asset/horizon/target. Insufficient data or an unavailable frozen candidate stops
the run; there is no fallback or winner change.

Only the 102 frozen candidates are fitted for calibration, not all competing
models. Each horizon gets its own actual-minus-prediction residual quantiles
(q10/q90, linear interpolation) using the existing V1 calculation. Volatility
point predictions are clipped to zero before calculating residuals, and remain
non-annualized. These are nominal 80% empirical asset intervals: overlapping
labels mean residuals are not independent, and coverage is not guaranteed.
No portfolio intervals or daily predicted path are fabricated.

The new report schema is `forecast-horizon-calibration-v1`, stage
`calibration_only_not_deployable`. It records 102 horizon-aware results, the
manifest/source hashes, approved and verified dataset provenance, metrics,
residual quantiles, training/evaluation counts and endpoint boundaries. The
original selection warning and any new calibration fit warning are separate.
Its canonical `calibration_sha256` binds the evidence for the next checkpoint.
Pure history-based calls explicitly retain unverified persisted provenance;
only the successfully verified database orchestration sets it to true.

Read-only review confirmed all 102 unique records, the original provenance,
selection/warning matches, finite ordered quantiles and strict endpoint boundaries.
Minimum calibration count is 113; minimum training count is 2,413. One selection
warning is retained, with zero new calibration fit warnings. The verified
canonical calibration SHA-256 is
`0f42993972269884b160ff9983555abad865ddd07483c574205b37f15a9a2ab1`.
No final testing or deployment-artifact training occurred in that command.

## Completed guarded final scoring (reference command only)

The user successfully ran this command once after 721 tests passed. Do not
rerun it, change its evidence or remove/reset its guard markers:

```powershell
.\.venv\Scripts\python.exe -m backend.scripts.evaluate_forecasting_horizon_final_test --env-file .\.env.test-database --database-url-key TEST_DATABASE_URL --database-name aura_forecast_training_20260917 --selection-manifest .\forecasting-evidence\forecast-multihorizon-selection-20260917\selection-manifest.json --selection-report .\forecasting-evidence\forecast-multihorizon-selection-20260917\selection.json --expected-manifest-sha256 829b5f9616643c3969cbd1cf220ce25b113d1b494b88c0693e376d5c43292a5c --calibration .\forecasting-evidence\forecast-multihorizon-selection-20260917\calibration.json --expected-calibration-sha256 0f42993972269884b160ff9983555abad865ddd07483c574205b37f15a9a2ab1 --output .\forecasting-evidence\forecast-multihorizon-selection-20260917\final-test.json
```

The manifest/source reconciliation remains unchanged. Calibration's canonical
checksum, full 102-record contract, provenance, versions, frozen winners and
warnings, observation counts, clipping and date boundaries are checked before
database access. No calibration or selection fitting is repeated. The full
snapshot is read-only, verified, and closed before final scoring.

Final-test origins lie in `final-test-01`, from 2025-09-18 through 2026-09-17
(exclusive end 2026-09-18). Selected candidates fit only labels completed before
2025-09-18, including eligible calibration-period history. The family/parameters
remain frozen; calibration q10/q90 are carried over unchanged. Features at each
test origin are past-only; outcomes are read for scoring after prediction. Labels
whose endpoints reach the exclusive end are omitted. Only the frozen candidates
are evaluated, with no competitor tournament, fallback or retuning.

Each of the 102 records reports MAE/RMSE, return direction accuracy where
applicable, clipping, observation/training counts, endpoint bounds, frozen
quantiles, and empirical interval coverage. Coverage includes observations on
either interval boundary. Counts distinguish covered observations, misses below/
above, and empty intervals. Some calibrated volatility upper residual quantiles
are negative. When the existing zero-lower-bound rule gives lower > upper, that
interval is empty: count a miss, retain an explicit warning, and exclude it only
from the mean *valid* interval width. Do not widen frozen ranges, clip the upper
bound to disguise the issue, or claim 80% achieved coverage without evidence.

The fixed one-run guard folder is
`forecasting-evidence/forecast-weekly-v1-20260917/`. It is not selected by the
output filename. `final-test-started.json` is created exclusively after all input
and DB provenance gates pass, before constructing or scoring test targets. A
failure after that point keeps the run consumed; different output filenames
cannot rerun it. On success, the new report is written exclusively and
`final-test-completed.json` binds its hash to the original run marker. Never
delete/reset either marker to retry or tune this release. Share any failure for
review. Failures before the run starts (for example wrong input hashes or data
provenance) do not consume it. No reset/force/retry flag is provided.

The output schema is `forecast-horizon-final-test-v1`, stage
`final_test_only_not_deployable`. Its canonical `final_test_sha256` binds the
scoring evidence and run identity to the pinned inputs. Pure history-based
calls retain unverified persisted-data provenance; only the DB orchestration
sets it verified. Finite poor errors/coverage and all warning stages are retained,
not silently rejected or replaced. Successful completion is not predictive-
quality acceptance. Review the results before creating a separate weekly model
package or enabling clients. No deployment models, provider downloads, API
changes, portfolio intervals, or UI activation occur in this command.

## Final-test evidence review

Read-only review independently recomputed canonical final-test SHA-256:
`e2aeb387fa10376f2f925d74138f194c4ce102494a64bafb0e6703fbc22d7193`.
All 102 unique records match frozen candidates, warnings, ranges and recorded
endpoint boundaries. Provenance remains the original 69,928-row, 17-asset
snapshot. Minimum final observation count is 237 and minimum training count
is 2,597. No new calibration/final fit warnings or empty intervals were recorded;
the QQQ 21-day volatility selection warning remains preserved.

| Horizon | Pooled return coverage | Pooled volatility coverage | Pooled return direction accuracy |
| --- | ---: | ---: | ---: |
| 7 calendar days | 79.03% | 77.30% | 51.18% |
| 14 calendar days | 70.15% | 77.95% | 51.29% |
| 21 calendar days | 72.33% | 81.73% | 51.40% |

Coverage pools covered observations / all observations across assets, not an
independence claim or evidence that every asset achieves the nominal 80%.
BTC-USD 14-day volatility coverage is 15.38%; SLV 21-day return coverage is
29.96%. Quality is mixed. This review supports an experimental educational
training checkpoint, not predictive-quality approval or production activation.
The reused original snapshot is not a new untouched project-level holdout.
Do not retune this release from final outcomes or rescore the consumed holdout.

## Completed manual experimental weekly artifact training (reference only)

The user completed the command below. Preserve its output; do not rerun fitting,
final testing, or overwrite this package to verify the new runtime code:

```powershell
.\.venv\Scripts\python.exe -m backend.scripts.train_forecasting_horizons --env-file .\.env.test-database --database-url-key TEST_DATABASE_URL --database-name aura_forecast_training_20260917 --selection-manifest .\forecasting-evidence\forecast-multihorizon-selection-20260917\selection-manifest.json --selection-report .\forecasting-evidence\forecast-multihorizon-selection-20260917\selection.json --expected-manifest-sha256 829b5f9616643c3969cbd1cf220ce25b113d1b494b88c0693e376d5c43292a5c --calibration .\forecasting-evidence\forecast-multihorizon-selection-20260917\calibration.json --expected-calibration-sha256 0f42993972269884b160ff9983555abad865ddd07483c574205b37f15a9a2ab1 --final-test .\forecasting-evidence\forecast-multihorizon-selection-20260917\final-test.json --expected-final-test-sha256 e2aeb387fa10376f2f925d74138f194c4ce102494a64bafb0e6703fbc22d7193 --accept-experimental-quality
```

The flag explicitly acknowledges the reviewed limitations; it does not approve
predictive quality, suppress warnings or enable inference. All three evidence
hashes, the source selection report and completed fixed final-run markers are
validated before environment/DB access. Only the isolated loopback PostgreSQL
snapshot is read, in a read-only transaction, and resources close before fitting.
No candidate competition, calibration, final scoring or provider calls occur.

Each selected candidate fits actual horizon labels whose endpoints complete on
or before 2026-09-17, including completed final-period labels after evaluation
is frozen. This is deployment fitting, not new out-of-sample scoring. Historical
averages use all eligible labels; moving averages keep their frozen 90-calendar-
day completed-label window. Other families/parameters/random seeds are unchanged.
Frozen per-horizon calibration q10/q90 and all final quality evidence are copied,
not recomputed. The unchanged V1 fitter is used privately as an algorithm bridge;
the new serialized outer wrapper always carries the actual horizon/target.

The fixed ignored destination is
`backend/artifacts/forecasting/forecast-weekly-v1-20260917/`. It is never the
original `forecast-v1-20260917` folder and has no CLI output override. Layout:
`<7d|14d|21d>/<SYMBOL>/<actual_target>/model.joblib` with adjacent `metadata.json`.
All 102 models are reload/prediction-checked. Metadata records actual versions,
training counts/dates, parameters, clipping, warning stages, frozen quantiles,
full per-record final coverage and hashes. Below-nominal coverage remains an
explicit advisory warning, not an excuse for fallback or interval widening.

Selection/calibration/final evidence copies, source bytes and a training-start
record remain inside the new bundle. The checksum-bound root `manifest.json` is
written last after model/metadata hashes are rechecked. A valid complete manifest
plus all matching checksums is required for later readiness review. Partial output
is preserved and existing folders refuse overwrite or automatic retry. If fitting
fails, share the error; do not delete the folder or reset final-test markers.

This experimental build records Git HEAD, actual forecasting source-file byte
hashes, tracked-worktree cleanliness and runtime-library versions. It permits a
dirty working tree without claiming a clean official release; prefer committing
reviewed source first. Unlike official 30-day artifact generation, this does not
require committing unrelated concurrent document work. Credentials/environment
files are excluded. No dependency or .gitignore change is needed. Joblib loading
is restricted to newly written trusted local output; checksums are not signatures
and do not make externally supplied pickle/joblib files safe.

No model package was generated by Codex. Read-only review confirmed the user-run
package's 102 distinct models, all 204 model/metadata file hashes, five evidence
file hashes, frozen source bindings and training provenance. The root canonical
SHA-256 is `5b604af0c7e965cfcebdc0ae38a9570b64464ffc2c8d8adee230a19b2aaf95fe`.
There are zero deployment-fit warnings, 48 below-nominal final-coverage warning
records, and the preserved QQQ 21-day volatility selection convergence warning.
The original 30-day package's 34 model pairs remain unchanged.

## Prepared backend runtime: manual verification required

Two additive routes support only 7/14/21 calendar days:

- `GET /api/forecasting/assets/{symbol}/horizons/{horizon_days}/outlook`
- `GET /api/forecasting/portfolios/{portfolio_id}/horizons/{horizon_days}/outlook`

Continue to use the original `/outlook` routes for 30 days. Their response names,
configured registry, behavior and customer clients are unchanged. Weekly fields
are `expected_return` and `forecast_realized_volatility`, never misleading `_30d`
names. The response identifies its horizon, experimental quality, lack of
predictive-quality approval, nominal intervals and retained per-target warning
codes. It exposes no artifact path, private residual or final-test metrics.

The weekly registry has an external code-owned approval pin for this reviewed
root manifest. Recomputing the package's self-digest cannot approve another
bundle. Before any joblib load it verifies all 102 unique symbol/horizon/target
pairs, all model/metadata bytes, evidence hashes, strict JSON, exact relative
paths, versions, candidate identities and frozen quantile bindings. Selected
bytes are rechecked before their first deserialization. The serialized wrapper
must carry the actual requested horizon/target and frozen candidate family.
Models, not predictions, are cached. Storage remains trusted immutable local
deployment input; checksums do not make externally supplied pickle files safe.
Constructor pin/path overrides are only explicit trusted test/deployment wiring,
not request inputs or automatically accepted package settings.

Importing the serialized wrapper loads its existing module definitions but does
not invoke offline fitting/evaluation/calibration functions or any CLI. Runtime
uses the existing application session and latest persisted prices, V1 past-only
features and four-day freshness gate. ARIMA counts stored observations from the
training cutoff rather than calendar-day gaps. There is no provider fetch,
training, recalibration, horizon scaling, fallback or database write.

Portfolio weights still come from the existing CURRENT/PLANNED/LEGACY baseline
resolver. All components use the requested horizon and correct target version;
one unavailable component fails the entire outlook. Weighted returns and D R D
volatility reuse the original numerical helpers, with non-annualized same-horizon
volatilities and past common-date correlations capped at the earliest component
origin. Signed contributions remain intact. No portfolio interval is fabricated.

The package's `runtime_activated=false` field remains immutable historical build
evidence. Runtime preparation does not change that field or mark predictive
quality approved. Web/mobile weekly controls and AI grounding remain unchanged.

Run this single line manually; share any failure before client integration:

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests/unit/forecasting backend/tests/unit/schemas/test_forecasting.py backend/tests/unit/schemas/test_portfolio_forecasting.py backend/tests/integration/api/test_forecasting_api.py backend/tests/integration/api/test_portfolio_forecasting_api.py backend/tests/integration/api/test_weekly_forecasting_api.py -q -p no:cacheprovider
```

After tests pass, validate package integrity without deserialization, fitting,
provider calls or DB access (must run from the repository root):

```powershell
.\.venv\Scripts\python.exe -c "import sys; sys.path.insert(0, 'backend'); from app.forecasting.weekly_registry import WeeklyArtifactRegistry; r = WeeklyArtifactRegistry(); r._validate(); print('Weekly runtime integrity verified:', len(r._records), 'model pairs')"
```

Restart the backend after verification, then manually request a weekly asset
and owned portfolio route using the existing authenticated API interface. A
successful forecast additionally requires fresh current application market data,
sufficient features and portfolio correlation history; snapshot training dates
do not bypass freshness. No migration or retraining is needed for this step.

## Remaining checkpoints

1. User-run new regressions and read-only runtime integrity check, then manual
   authenticated asset/portfolio smoke checks on fresh application data.
2. Integrate backend-supported horizons on both clients, enabling only verified
   horizons. Plot actual horizon estimates and asset ranges; connecting lines
   are visual guides, not a predicted daily price trajectory. Do not invent
   portfolio prediction intervals or forecast AI grounding.

Suggested checkpoint commit: `feat(forecasting): serve experimental weekly asset and portfolio outlooks`
