# Real-Holding Frontend and Mobile Integration Backlog

The backend contracts are complete. The mobile client now supports current,
planned, and legacy portfolio modes and has passed its mobile-only readiness
verification. The equivalent customer React integration is intentionally
skipped by current product direction. Plan-to-current conversion remains
unavailable until its atomic backend operation exists.

## Required real-holding integration

### Portfolio create and edit

- Replace portfolio allocation-percentage fields with `symbol`,
  `invested_amount`, `invested_currency`, `shares`, and `purchase_date`.
- Remove the portfolio CRUD requirement that entered values total 100%.
- Preserve the user's holding order in the replacement request.
- Default invested currency to USD and offer THB as the other supported value.
- Treat backend `position` as authoritative ordering metadata.

The clients must stop treating saved allocation as user-authored authority. A
normal real holdings replacement can convert a legacy portfolio; the UX should
make that explicit and should not construct mixed holding state.

### Portfolio detail and dashboard

- Display persisted holding facts separately from current valuation.
- Request `GET /api/portfolios/{portfolio_id}/valuation` separately, defaulting
  to USD and optionally requesting THB.
- Show backend-returned prices, values, price dates, totals, FX context, and
  dynamic current allocation.
- Handle `409` holding-state conflicts and `503` stale/missing current data
  without fabricating values.
- Build dashboard allocation from current valuation or a saved report snapshot,
  never from `holding.weight` for a real portfolio.
- Do not calculate official allocation in the client.

### Analytics, reports, and simulations

- Continue to render V1 legacy reports.
- Add the `portfolio-analysis-response-v2` envelope and frozen valuation/
  per-asset composition without revaluing old reports.
- Add optional USD/THB report creation and display.
- Keep simulation POST shapes unchanged.
- Seed Allocation/Combined hypothetical editors from the backend-resolved real
  baseline instead of a nullable saved weight.
- Add all three V2 history detail variants and render the frozen baseline.

### AI

The web and mobile Assistants already use the unchanged authenticated public AI
request/response contract. They must not calculate allocation. Backend
grounding now chooses saved legacy weights, current real valuation, or a frozen
V2 report/simulation snapshot as appropriate.

## Audited deferred and hardcoded inventory

| Feature | Current client behavior | Missing backend capability/API | Priority | Recommended future action |
| --- | --- | --- | --- | --- |
| Current/planned holding CRUD | Web and mobile submit real ownership facts or planned proposed amounts without manual CRUD weights; legacy weights remain readable for compatibility | Atomic plan-to-new-current conversion | Core integration complete | Add conversion only after its backend contract is approved |
| Current valuation / planned allocation | Both clients consume valuation for current holdings and planned allocation/preview for plans; estimated shares remain display-only | None | Core integration complete | Run environment-specific authenticated acceptance checks before deployment |
| Report V2/V3 | Both clients render legacy V1, current V2, and planned V3. Current/planned metric cards can show response-derived currency equivalents for cumulative return, annualized return, and exact maximum drawdown | None | Core integration complete | Preserve versioned immutable rendering |
| Simulation History V2/V3 | Both clients render current V2 and planned V3 history and initialize editors from the appropriate backend baseline | None | Core integration complete | Preserve frozen history and backend-owned baselines |
| Assistant | Both clients call the real authenticated AI endpoint and show sources/limitations | No core gap for current stateless explanations | Optional | Preserve the contract; add conversation persistence only if separately approved |
| Watchlist | Web and mobile use authenticated shared CRUD, reuse the supported-asset catalogue, and render persisted latest/daily/YTD market context with complete loading, empty, and error states | None for V1 | Core integration complete | Preserve backend authority; add alerts, forecasts, or live quotes only through separately approved contracts |
| Daily market-data status | Both clients show scoped freshness and worker/update warnings on Watchlist and current values; foreground/five-minute active reads, web Refresh and mobile pull-to-refresh reload saved data only | Deployment-ready status/worker implemented | Client integration complete; runtime activation pending | Apply migration d6e8f0a2b4c6 and choose/start the supervised worker later; no client-triggered provider updates or live quotes |
| Search | Web global search is disabled; local portfolio/report/simulation/Learn filtering exists | No global search API or asset-catalogue search endpoint | Optional | Define searchable resources and ownership/pagination contracts first |
| Notifications | Web bell and mobile More inbox show account-owned analysis/simulation updates; Settings controls master/category preferences | None for in-app V1; optional push/email remain deferred | In-app V1 complete | Apply migration c3d5e7f9a2b4 and verify browser/device acceptance; no external delivery is enabled |
| Hide portfolio values | Web and mobile enable account-specific, device-local privacy toggles; personal amounts and share quantities are masked across portfolio/result displays, monetary inputs are hidden while enabled, and AI chat is shielded with a privacy notice | None for local V1; cross-device synchronization would need a separate preference API | Local V1 complete | Verify authenticated browser/device behavior; keep percentages, public prices, and backend calculations unchanged |
| Profile update/edit | Web account profile is read-only; web preferences are browser-local; mobile display name is explicitly device-local | None for backend Profile V1; authenticated profile/email/password APIs are implemented | Backend complete, client integration pending | Replace local/read-only profile state with the authenticated backend contract in the next frontend task |
| Export/share/download | Report screens explicitly say these actions are unavailable | Secure render/export, download authorization, and share/revocation APIs | Optional | Define privacy, format, expiry, and audit requirements first |
| Mock/static market data | Obsolete Watchlist mocks and client-side Watchlist movement summaries are removed; production portfolio, analytics, simulation, and Watchlist flows use backend APIs. Learn content remains code-owned educational content | None for current integrated domains | Complete | Keep future demos isolated from production import graphs |
| Saved-weight assumptions | Removed from web and mobile current/planned production flows; legacy display remains compatible | None | Core integration complete | Retain legacy readers until a separate migration policy is approved |
| Percentage-entry assumptions | Web and mobile CRUD no longer accept weights; Allocation/Combined simulation percentages correctly remain user-controlled hypotheses | None | Core integration complete | Preserve the distinction between saved holdings and simulation hypotheses |

## Explicit product boundaries

The following remain out of scope unless a later approved proposal changes the
boundary: tax lots, transaction ledger, brokerage integration, tax
calculations, historical purchase-price inference, historical FX
reconstruction, and buy/sell advice. Forecasting or ML prediction is also a
future feature; Aura does not currently claim to predict prices or train a
market model.
