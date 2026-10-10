# Mobile forecasting V1 integration report

Date: 2026-10-07; weekly mobile integration checkpoint: 2026-10-08;
portfolio monetary integration checkpoint: 2026-10-09

## Original 30-day delivered scope

Added an authenticated mobile 30-Day Outlook screen using the existing read-only
forecasting endpoints. The screen retains Aura's navy/teal cards, themed stack
headers, accessible controls, and five-item bottom navigation. No backend,
model, artifact, database, provider, or web production changes were needed.

Entry points:

- More: Forecasting, with the active portfolio selected when available.
- Analytics and portfolio details: View 30-Day Outlook for the selected portfolio.
- Home: View 30-Day Outlook; its header back action returns to Dashboard.
- Watchlist: View Outlook for each asset, returning to Watchlist with Back.
- Portfolio outlook components: open an asset outlook on the same stack;
  Back returns to the portfolio outlook.

Forecasting is registered in the existing Portfolio and More stacks. Historical
Analysis and View Portfolio links remain available. Bottom-tab root behavior is
unchanged. Standalone asset outlooks do not require creating a portfolio.

## Results and chart behavior

Portfolio outlooks show backend expected return, non-annualized volatility,
resolved allocation, signed risk contributions, asset breakdowns and origins,
artifact/model identifiers, correlation dates/observations, and limitations.
CURRENT, PLANNED and LEGACY share the same screen with accurate baseline labels;
planned allocations are explicitly hypothetical. Forecasts are independent of
saved historical analyses and simulation reports.

Asset outlooks show both estimates and nominal 80% prediction ranges, model
identifiers, origin/data date and age, and limitations. Search filters the
supported asset catalog without replacing the selected asset when no match exists.

At the original checkpoint, the horizon controls showed one, two, three weeks
and 30 calendar days. Only 30 days was enabled pending weekly backend models.
The chart plots a single actual 30-day marker with asset interval whiskers;
portfolio prediction ranges are not invented. Return and Volatility have separate
chart views, labeled axes, and an accessible spoken estimate/range description.
Multiple-point chart support was a visual guide for future backend horizons,
not an enabled feature or interpolated forecast. The weekly checkpoint below
supersedes these original horizon-control and chart limitations.

Signed contribution bars retain negative offsets and shares above 100%. Only
chart geometry and percentage display are calculated locally; model estimates,
allocations, intervals and financial contributions remain backend-owned.
No forecast risk levels, prices, monetary outcomes or AI forecast grounding are
fabricated. Educational wording distinguishes estimates from guarantees.

## Files changed and purpose

- `mobile/src/types/forecasting.ts`, `src/api/forecastingApi.ts`: typed asset and
  portfolio GET contracts using the existing authenticated API client.
- `src/forecasting/forecastingUi.ts`, `useForecasting.ts`, `forecastingStyles.ts`:
  formatting, response checks, safe errors, themed styling, and scoped loading.
  Requests cancel on blur, account/selection changes or unmount; timeouts and
  refresh clear stale results. Returning to the screen reloads saved backend data.
- `src/screens/forecasting/ForecastingScreen.tsx`: portfolio/asset selectors,
  asset search, fixed horizons, pull-to-refresh, empty/loading/error states and
  historical/portfolio navigation. Portfolio lists are account-scoped and
  cancellable; list errors do not prevent standalone asset access.
- `src/components/forecasting/ForecastingResults.tsx`, `OutlookChart.tsx`:
  native result cards, responsive SVG chart, signed bars, breakdowns and expandable
  model details/limitations, using the existing SVG dependency.
- Navigation types/MainTabNavigator and More, Dashboard, PortfolioDetail,
  PortfolioAnalysis and Watchlist screens: contextual links and themed back actions.
- `mobile/tests/forecasting.test.cjs`, `mobile/package.json`: 15 new forecasting
  regressions and a standard `npm test` command for mobile's Node-only checks.
- `web-prototype-react/tests/marketData.test.cjs`: pass navigation into existing
  mobile Watchlist test mounts after its contextual outlook action was added.
  No web production code changed.
- `CURRENT_STATUS.md` and this report: delivery and verification record.

## Original 30-day verification (predates weekly integration)

- Mobile TypeScript: passed (`npm run typecheck`).
- Mobile forecasting and existing authority tests: 84 passed (15 new, 69 existing).
- Shared market-data/notification checks and web forecasting regressions:
  56 passed. Existing Watchlist and notification behavior remains covered.
- Full web/shared-client runner: 121 passed, one pre-existing branding failure
  on an unrelated report entry in CURRENT_STATUS.md. That content was preserved.
- Android production Hermes export: passed, 1,171 modules, using installed Expo
  and dependencies. The sandbox initially blocked Hermes execution; the approved
  retry succeeded. Output remains ignored under `mobile/.expo/forecasting-v1-export/`.
- Git whitespace checks: passed. No dependencies, secrets, backend changes,
  model training, migrations, commits, pushes or deployments were added.

These Node tests are minimal hook/tree orchestration checks, not React Native
rendering or device E2E. Android export verifies bundling, not authenticated
real-data operation. Physical-device visual acceptance remains pending; no phone
session was available. Unrelated report work was left unchanged.

## Phone acceptance checklist

1. Run the backend with configured frozen artifacts and sufficiently fresh saved
   market data. Start the existing Expo app and sign in from your phone.
2. Open More > Forecasting. Try current and planned portfolios, then an asset
   without a portfolio. Confirm contextual entry selection from other pages.
3. Switch 7/14/21/30 calendar days (30 is default), then Expected Return /
   Volatility. Check actual horizon-specific values, asset-only ranges,
   weekly experimental notices/warnings and signed contribution offsets.
   Enable Compare all horizons and review all four data dates/statuses. Missing
   horizons and different data dates must break the dashed visual guide.
4. Search/select assets, expand model details, and refresh or pull to refresh.
   Refresh does not fetch provider data, retrain models or save reports.
5. Verify Back from Watchlist, Analytics, portfolio details and Dashboard;
   component drill-down returns to the portfolio outlook. Bottom tabs go to roots.
6. Check a narrow phone, both appearance themes, large text and screen-reader
   controls. Review stale-data, missing-artifact and unusable-portfolio errors.

Suggested commit: `feat(mobile): add forecasting v1 outlook preview`

## Experimental weekly integration — 2026-10-08

Enabled the verified additive weekly GET endpoints for both standalone assets
and CURRENT/PLANNED/LEGACY portfolios. Original 30-day endpoints and `_30d`
contracts remain unchanged and the default; weekly responses use neutral fields.
No weekly output is scaled from a 30-day result. Entry points now say Forecast
Outlook and More describes the 7–30-day offering.

The existing screen now has accessible 7/14/21/30-day radio controls and a
Compare all horizons checkbox. Optional comparison requests have independent
60-second timeouts/errors. Successful horizons remain visible even if the
selected horizon fails. Refresh, account/selection/horizon changes, leaving the
screen and unmount cancel relevant requests and suppress late responses;
returning to the screen reloads the current selection. Changing the selected
horizon during comparison uses its already loaded response without a refetch.

ForecastHorizonComparison adds compact native date/return/volatility/status
cards rather than a wide desktop table. Its Return / Volatility chart plots only
real response points. Amber marks weekly models; teal marks 30 days. Dashed
guides join only adjacent supported horizons with matching market-data dates;
missing horizons or different dates break them. Asset range whiskers are kept,
but portfolio ranges and daily trajectories are never invented. The comparison
chart replaces the single-point chart while comparison is enabled.

Weekly validation requires matching calendar-day horizons, package identity,
experimental/not-predictive-quality-approved flags and target warning arrays,
including every portfolio component. Model-quality warnings are shown with
their symbol/target/horizon; unknown warnings get safe generic wording. Model
identifiers, component origins and the full returned limitations remain available
for each successful comparison, not only the selected horizon. Planned baselines
remain hypothetical and signed contributions stay backend-owned.

Changed existing types/API adapters, focus-aware loader/UI helpers, result/chart
components, styles, screen controls and contextual entry labels. Added one native
comparison component and expanded the existing forecasting tests for transport,
validation, neutral values, races, independent failures/timeouts, focus/account
cancellation, line gaps/date separation, warnings, controls and metadata.

Verification: source review and Git whitespace checks completed. No new passing
test count, TypeScript/export success or physical-device acceptance is claimed.
Run these commands manually from the repository root:

```powershell
npm --prefix .\mobile test
npm --prefix .\mobile run typecheck
```

Optional Android bundling check using installed tooling (no new dependencies):

```powershell
Set-Location .\mobile; npx --no-install expo export --platform android --output-dir .expo/forecast-weekly-v1-export; Set-Location ..
```

On a signed-in phone, check AAPL and QQQ at every horizon, QQQ's retained 21-day
ARIMA warning, CURRENT/PLANNED/LEGACY baselines, comparison partial failure,
pull-to-refresh, account switching, back/blur return, both themes and large text.
Client tests and bundling do not replace device acceptance or predictive-quality
evaluation. Backend, models, evidence, database, provider refresh, AI grounding,
web production code, navigation architecture and dependencies are unchanged.
No training, migrations, staging, commit or push was performed.

Suggested weekly checkpoint commit: `feat(mobile): integrate experimental weekly forecast horizons`

## Portfolio monetary integration — 2026-10-09

Mobile portfolio Outlook now consumes the overall and holding-specific
`monetary_projection` fields for all four horizons. The existing native card
layout adds compact baseline, expected gain/loss and estimated ending-value
sections. Each asset card shows its own baseline, own forecast change and ending
estimate, alongside percentages. All amounts come directly from backend Decimal
strings; the app does not recalculate holdings, allocations or forecasts.

CURRENT shows USD market value from saved prices times owned shares, with the
requested valuation date, actual price-date range and each holding's price date.
Purchase cost and saved analyses are not substituted. PLANNED shows entered
USD/THB amounts, explicitly hypothetical; THB assumes unchanged exchange rates,
not an FX forecast. LEGACY remains percentage-only. Drilling into an asset still
opens the user-independent standalone 30-day Asset Outlook, with no user amount.

Selected and comparison charts add Expected change in the returned currency,
retaining separate Return and Volatility views. Monetary guides require adjacent
successful horizons, matching market-data dates, currency and identical baseline
context including holding amounts. A changed allocation/baseline breaks the
guide; mixed currencies disable the monetary comparison chart. Missing or
unplottable points are not replaced. No monetary range, daily trajectory or
volatility-as-loss calculation is introduced.

String-only rounding preserves exact cents, including large/scientific Decimal
strings, without an added native dependency or BigInt runtime requirement.
Only chart geometry/compact labels use numeric values. Narrow chart labels
abbreviate large amounts; native cards and spoken chart descriptions retain
full formatted amounts. Existing single-string calendar-day ticks remain intact.
Amounts outside the safe chart numeric range remain available in cards.

Hide portfolio values masks summary, holding and comparison amounts. A selected
money chart immediately falls back to percentages; money, currency-valued labels
and baseline keys are removed from its points/accessibility output. Masking also
applies on the initial hidden render while the privacy preference is loading.
Missing/malformed monetary context fails through the existing response guard,
without stale values, fallback amounts or additional valuation/API requests.
Model-quality warnings and full monetary/backend limitations remain available.

Changed files and purpose:

- `mobile/src/types/forecasting.ts`: overall and component monetary contracts.
- `src/forecasting/forecastingMoney.ts`: native exact display formatting and
  monetary context validation; `forecastingUi.ts`: safe amount-chart mapping.
- `src/components/forecasting/ForecastingResults.tsx`,
  `ForecastHorizonComparison.tsx`, `OutlookChart.tsx` and
  `src/forecasting/forecastingStyles.ts`: native amount cards, privacy-safe controls,
  currency charts, abbreviated labels and holding provenance.
- `mobile/tests/forecasting.test.cjs`: valid baseline-mode fixtures and eight new
  monetary regressions; CURRENT_STATUS.md and this report: verification record.

Verification run directly by Codex with user authorization:

- Mobile baseline before edits: 93 passed.
- Mobile suite after edits: 101 passed (32 forecasting and 69 existing authority).
- TypeScript: passed.
- Shared market-data/notification and web forecasting regressions: 72 passed.
- Android production Hermes export: passed, 1,173 modules. The sandbox initially
  denied writing temporary bytecode; the approved outside-sandbox retry passed.
  Output remains ignored under `mobile/.expo/forecast-money-v1-export/`.
- Git whitespace checks: passed.

These are orchestration/contract and bundling checks, not physical-device E2E.
On a signed-in phone, review CURRENT, PLANNED USD/THB and LEGACY at all horizons,
holding amounts versus standalone Asset Outlook, comparison failures/gaps,
privacy toggling/loading, both themes, large text and spoken amounts. Device
visual acceptance remains pending. No backend/web code, models, artifacts,
evidence, migration, dependency, provider update, training or saved data changed.

Suggested commit: `feat(mobile): show portfolio forecast amounts and holding breakdowns`.
No staging, commit or push was performed; unrelated report work is preserved.
