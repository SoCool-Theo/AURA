# Mobile forecasting V1 integration report

Date: 2026-10-07

## Delivered scope

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

The horizon controls show one, two, three weeks and 30 calendar days. Only 30 days
is enabled because V1 has no validated weekly estimates or daily trajectory.
The chart plots a single actual 30-day marker with asset interval whiskers;
portfolio prediction ranges are not invented. Return and Volatility have separate
chart views, labeled axes, and an accessible spoken estimate/range description.
Multiple-point chart support remains a visual guide for future backend horizons,
not an enabled feature or interpolated forecast.

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

## Verification

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
3. Switch Expected Return / Volatility; check axes, one actual 30-day point,
   asset-only ranges, disabled weekly controls and contribution offsets.
4. Search/select assets, expand model details, and refresh or pull to refresh.
   Refresh does not fetch provider data, retrain models or save reports.
5. Verify Back from Watchlist, Analytics, portfolio details and Dashboard;
   component drill-down returns to the portfolio outlook. Bottom tabs go to roots.
6. Check a narrow phone, both appearance themes, large text and screen-reader
   controls. Review stale-data, missing-artifact and unusable-portfolio errors.

Suggested commit: `feat(mobile): add forecasting v1 outlook preview`
