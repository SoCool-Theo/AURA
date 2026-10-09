# Web forecasting V1 integration report

Date: 2026-10-07; weekly web integration checkpoint: 2026-10-08;
portfolio monetary integration checkpoint: 2026-10-09

## Delivered scope

A dedicated authenticated Forecasting page presents portfolio and standalone
asset outlooks using the existing read-only backend APIs. It retains Aura's
navy/teal theme, responsive cards, selectors, loading/error presentation, and
historical-analysis navigation. No backend, mobile, model, or artifact changes
are included.

Entry points:

- Analytics: Historical Analysis / Forecast Outlook navigation; Analytics remains
  active in the existing six-item top navigation.
- Portfolio details: View Forecast Outlook with that portfolio selected.
- Dashboard Core Workflows: View Forecast Outlook for the selected portfolio.
- Watchlist list/grid: View Outlook for the selected asset.

Routes:

- `#/forecasting`
- `#/forecasting/portfolio/{portfolio_id}`
- `#/forecasting/asset/{symbol}`

## Results and chart behavior

Portfolio outlooks show expected selected-horizon return, non-annualized forecast volatility,
backend-resolved allocation, signed risk contributions, per-asset forecasts and
origins, model IDs, artifact version, correlation context, and backend limitations.
CURRENT, PLANNED, and LEGACY share one screen; planned allocations are explicitly
hypothetical. No saved analysis is substituted for the forecast baseline.

Asset outlooks show both estimates and their nominal 80% prediction ranges,
origin/data date and age, model IDs, artifact version, and limitations. Asset
access does not require creating or owning a portfolio.

The horizon controls enable 7, 14, 21, and 30 calendar days; 30 remains the
default. Weekly requests use the verified additive `/horizons/{days}/outlook`
routes and neutral numeric fields, while 30 days retains the original routes
and `_30d` contracts. No weekly value is scaled from 30-day output.

The selected-horizon view plots one actual estimate and asset range bars.
The optional Compare all horizons checkbox requests all four horizons with
independent cancellation, timeout and failure handling. It plots only successful
responses and shows dates, return, volatility and status in an accessible table.
Dashed visual guides connect only adjacent supported horizons with matching
market-data dates; missing horizons or different dates break the line. These
guides are not daily predictions or price paths. Portfolio intervals are never
invented. Expected Return / Volatility remain separate chart views.

Weekly responses must retain experimental/not-predictive-quality-approved
flags, calendar-day units and per-target warnings, including in every portfolio
component. The UI displays an experimental notice and friendly, asset/target/
horizon-specific warning messages. Comparison warnings remain available even
when viewing the original 30-day result. Amber markers identify weekly points;
teal identifies 30 days. Each outlook's full backend limitations remain intact.

The signed contributor chart uses a zero reference with negative and positive
bars rather than discarding offsets or turning them into a pie. Forecast risk
levels, forecast prices, monetary outcomes, and investment recommendations are
not invented.

## Implementation files and purpose

- `web-prototype-react/src/types/forecasting.ts` and
  `src/api/forecastingApi.ts`: separate typed weekly and original asset/portfolio
  GET contracts, sharing the existing authenticated transport.
- `src/pages/forecasting/useForecasting.ts`: manual refresh, account/selection
  and horizon scoping, independent comparison loading/failures, cancellation,
  timeout, and suppression of late or malformed responses.
- `src/pages/forecasting/forecastingUi.ts`: percentage formatting, safe error
  wording, supported horizons, response checks, and direct chart-point mapping.
- `src/pages/forecasting/ForecastingPage.tsx`, `components/ForecastingResults.tsx`,
  `components/OutlookChart.tsx`, and `Forecasting.module.css`: selectors, cards,
  chart geometry, signed contributors, metadata, limitations, and responsive UI.
- `components/ForecastHorizonComparison.tsx`: actual-horizon comparison chart,
  data-date/status table and retained model-quality warnings.
- App/TopNavigation, AnalyticsPage, PortfolioDetailView, PortfolioAnalysisCard,
  and WatchlistTable: protected routing, active navigation, and contextual links.
- `tests/forecasting.test.cjs`, existing App test fixtures, and `package.json`:
  forecasting interaction/authority regressions in the standard test runner.
- `CURRENT_STATUS.md` and this report: completed scope and verification record.

Only presentation/geometry is calculated in the client. Forecast returns,
volatility, allocations, intervals, and contributions remain backend-owned.

## Verification

The following original-preview results predate weekly client activation:

- 13 forecasting regressions passed: GET transport, fixed horizons, actual
  chart values/intervals, malformed response rejection, safe errors,
  account/selection races, refresh, cancellation, timeouts, all baseline modes,
  signed contributions, standalone asset access, search, and protected routing.
- Full web/shared-client runner: 121 passed, one pre-existing failure.
  The existing product-branding test flags an unrelated report-outline entry
  in CURRENT_STATUS.md. That other task's content was retained unchanged.
- TypeScript and production build passed. The existing bundle-size warning
  remains; no dependency was added.
- Browser check confirmed the protected local route redirects to sign-in.
  No authenticated session was available, so real-data result rendering,
  responsive visual acceptance, and real-model/provider acceptance are pending.

## User acceptance checklist

1. Start the existing backend, ensure the frozen configured artifact package is
   available, and use sufficiently fresh persisted market data.
2. Sign in to web, open Analytics, then Forecast Outlook (defaults to 30 days).
3. Review CURRENT/PLANNED/LEGACY portfolios, their baseline labels, breakdowns,
   and contributor bars. Drill into an asset.
4. Open an asset from Watchlist and switch Return / Volatility.
5. Switch through 7/14/21/30 days; check horizon-aware metrics, weekly warnings,
   asset range bars and no portfolio prediction range. Enable Compare all
   horizons and switch Return / Volatility. Check actual values, dates,
   experimental labels and missing-point gaps. No estimates should survive an
   account, selection or horizon change, refresh, timeout or failed request.
6. Test a narrow browser window, selectors/search, keyboard access, and refresh.
7. Review missing/stale-data and unusable-portfolio errors without creating
   reports, simulations, holdings, or new forecast records.

Refresh re-requests an outlook; it does not fetch provider data or retrain a model.
Frozen baseline models may return the same estimate after a refresh. Asset
drill-down preserves the asset but opens the default 30-day view; weekly horizons
can then be selected explicitly.

## Weekly integration verification checkpoint

Before activation, the user reported 954 passing backend forecasting/schema/API
tests and integrity validation of all 102 weekly model pairs. Authenticated
read-only localhost checks passed 25/25: AAPL and QQQ at all four horizons,
two CURRENT and two PLANNED portfolios at all four horizons, and unsupported
8-day rejection. QQQ's 21-day ARIMA warning was retained. These are runtime
checks, not new quality approval, training or holdout evaluation.

Added weekly transport, contract/quality validation, actual-value mapping,
selection/account races, no-fallback failures, independent comparison/timeout,
chart gaps/date separation, warnings and selector regressions. Terminal tests
and the production build are deliberately left for the user to run manually:

```powershell
npm --prefix .\web-prototype-react run test:authority
```

```powershell
npm --prefix .\web-prototype-react run build
```

No passing count is claimed for these new client tests until the user supplies
the results. Mobile weekly integration is the next separate checkpoint.

Signed-in browser checks confirmed the original default 30-day result, actual
7/14/21-day cards, four-horizon CURRENT and PLANNED comparison charts/tables,
return/volatility switching, immediate loaded-horizon selection and correct
hypothetical labels. QQQ's 21-day asset page displayed both nominal ranges and
the retained ARIMA convergence warning. Compact controls and chart styling
were visually inspected using the computer-use skill; no saved data changed.
Additional responsive breakpoints, induced network/error acceptance and mobile
device checks remain for user acceptance; browser rendering does not replace
the pending TypeScript/build and regression commands.
The session returned to sign-in during the final QQQ all-horizon comparison
check. Its completed rendering remains for user acceptance after signing in;
no login or authentication change was attempted.

Suggested checkpoint commit: `feat(web): integrate experimental weekly forecast horizons`

No commit, push, migration, training, deployment, provider update, or saved-result
mutation was performed. Unrelated report files/status edits were preserved.

## Portfolio monetary integration checkpoint

The 7/14/21/30-day portfolio views now consume the backend's overall and
per-component `monetary_projection` fields. Compact cards show the baseline,
expected gain/loss and estimated ending value. The asset breakdown shows each
holding's baseline, own forecast change and ending estimate, alongside the
existing percentages. No amount is derived from portfolio weights or overall
return in the browser.

CURRENT uses persisted USD prices times owned shares, with requested valuation
date and actual price-date provenance; it does not use purchase cost or saved
analysis. PLANNED uses entered USD/THB investment amounts and remains explicitly
hypothetical. THB assumes unchanged FX. LEGACY stays percentage-only, and
standalone Asset Outlook is unchanged and does not receive the user's amounts.

Selected and comparison charts offer Expected change in the returned currency,
in addition to Return and Volatility. Money guides require identical baseline
context, currency and market-data date and adjacent available horizons. No
daily forecast, monetary interval or volatility-as-loss estimate is introduced.
Display formatting rounds backend Decimal strings to cents without float
precision loss; numbers are used only for geometry. Compact money axes fit the
existing chart, while point/accessibility labels retain displayed cents.
Amounts outside the chart's safe numeric range stay in the cards/table and are
not scaled into substitute forecasts.

The existing Hide portfolio values preference masks all new amounts. A selected
money chart immediately falls back to percentages while hidden, without leaking
money into point properties, accessibility labels or baseline keys. Missing or
malformed required monetary context is rejected by the existing response guard.

Changed files: forecasting types, the new pure `forecastingMoney.ts` formatter
and context checks, `forecastingUi.ts`, results/comparison/chart components,
forecasting CSS and regression tests, plus this report and CURRENT_STATUS.md.
No dependencies, backend/mobile code, artifacts or APIs were changed.

Verification run by Codex (the user now permits direct test execution):

- Backend forecasting/schema/API suite: 1,061 passed in 52.28 seconds.
- Forecasting web regressions: 29 passed, including exact cents, all horizons,
  baseline modes, holding amounts, privacy, chart gaps and malformed responses.
- Full web/shared-client suite: 138 passed, one pre-existing product-branding
  failure caused by unrelated report-outline wording in CURRENT_STATUS.md,
  also present before these changes. That content remains unchanged.
- TypeScript and production build passed; the existing large-chunk warning
  remains. Signed-in visual acceptance of the new monetary views is pending.

Suggested commit: `feat(web): show portfolio forecast amounts and holding breakdowns`.
No staging, commit, push, migration, model training or data mutation was run.
