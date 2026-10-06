# Web forecasting V1 integration report

Date: 2026-10-07

## Delivered scope

A dedicated authenticated Forecasting page presents portfolio and standalone
asset outlooks using the existing read-only backend APIs. It retains Aura's
navy/teal theme, responsive cards, selectors, loading/error presentation, and
historical-analysis navigation. No backend, mobile, model, or artifact changes
are included.

Entry points:

- Analytics: Historical Analysis / 30-Day Outlook navigation; Analytics remains
  active in the existing six-item top navigation.
- Portfolio details: View 30-Day Outlook with that portfolio selected.
- Dashboard Core Workflows: View 30-Day Outlook for the selected portfolio.
- Watchlist list/grid: View Outlook for the selected asset.

Routes:

- `#/forecasting`
- `#/forecasting/portfolio/{portfolio_id}`
- `#/forecasting/asset/{symbol}`

## Results and chart behavior

Portfolio outlooks show expected 30-day return, non-annualized forecast volatility,
backend-resolved allocation, signed risk contributions, per-asset forecasts and
origins, model IDs, artifact version, correlation context, and backend limitations.
CURRENT, PLANNED, and LEGACY share one screen; planned allocations are explicitly
hypothetical. No saved analysis is substituted for the forecast baseline.

Asset outlooks show both estimates and their nominal 80% prediction ranges,
origin/data date and age, model IDs, artifact version, and limitations. Asset
access does not require creating or owning a portfolio.

The horizon controls show 7, 14, 21, and 30 calendar days; only 30 days is enabled.
The current API has no other horizons or daily forecast trajectory. Accordingly,
the chart plots one actual 30-day marker, with asset interval bars when available.
There is no fabricated future line, rescaled weekly estimate, or portfolio interval.
Its Expected Return / Volatility switch keeps those metrics on separate axes.
The chart component supports explicit multiple points later, using a dashed
visual guide, but this does not enable any additional production horizon.

The signed contributor chart uses a zero reference with negative and positive
bars rather than discarding offsets or turning them into a pie. Forecast risk
levels, forecast prices, monetary outcomes, and investment recommendations are
not invented.

## Implementation files and purpose

- `web-prototype-react/src/types/forecasting.ts` and
  `src/api/forecastingApi.ts`: typed existing asset/portfolio GET contracts.
- `src/pages/forecasting/useForecasting.ts`: manual refresh, account/selection
  scoping, cancellation, timeout, and suppression of late or malformed responses.
- `src/pages/forecasting/forecastingUi.ts`: percentage formatting, safe error
  wording, supported horizons, response checks, and direct chart-point mapping.
- `src/pages/forecasting/ForecastingPage.tsx`, `components/ForecastingResults.tsx`,
  `components/OutlookChart.tsx`, and `Forecasting.module.css`: selectors, cards,
  chart geometry, signed contributors, metadata, limitations, and responsive UI.
- App/TopNavigation, AnalyticsPage, PortfolioDetailView, PortfolioAnalysisCard,
  and WatchlistTable: protected routing, active navigation, and contextual links.
- `tests/forecasting.test.cjs`, existing App test fixtures, and `package.json`:
  forecasting interaction/authority regressions in the standard test runner.
- `CURRENT_STATUS.md` and this report: completed scope and verification record.

Only presentation/geometry is calculated in the client. Forecast returns,
volatility, allocations, intervals, and contributions remain backend-owned.

## Verification

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
2. Sign in to web, open Analytics, then 30-Day Outlook.
3. Review CURRENT/PLANNED/LEGACY portfolios, their baseline labels, breakdowns,
   and contributor bars. Drill into an asset.
4. Open an asset from Watchlist and switch Return / Volatility.
5. Verify disabled weekly controls, the single 30-day point, asset range bars,
   and no portfolio prediction range.
6. Test a narrow browser window, selectors/search, keyboard access, and refresh.
7. Review missing/stale-data and unusable-portfolio errors without creating
   reports, simulations, holdings, or new forecast records.

Refresh re-requests an outlook; it does not fetch provider data or retrain a model.
Frozen baseline models may return the same estimate after a refresh. Enabling
weekly horizons requires separately validated backend models and contracts.

Suggested commit: `feat(web): add forecasting v1 outlook preview`

No commit, push, migration, training, deployment, provider update, or saved-result
mutation was performed. Unrelated report files/status edits were preserved.
