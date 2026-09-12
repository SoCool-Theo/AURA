# Real-Holding Frontend and Mobile Integration Backlog

The backend branch is complete, but the current customer React and mobile
clients were built against the earlier authoritative-weight model. This file
records the required later integration work; Phase 13 does not implement it.

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
| Real holding CRUD | Web and mobile forms still enter weights and require 100%; their TypeScript holding responses require `weight` | None; the backend real holding contract is complete | Core | Dedicated React/mobile real-holding integration branch |
| Current valuation | Dashboard/detail read saved weights and do not call the valuation route | None; USD/THB valuation exists | Core | Add shared valuation types/API clients and explicit loading, 409, and 503 states |
| Report V2 | Both clients type and render only the V1 `analysis` envelope | None; report create/detail are V1/V2-aware | Core | Add discriminated V1/V2 response handling and frozen valuation UI |
| Simulation History V2 | Both clients type history detail as V1-only and initialize hypothetical inputs from saved weights | None; all three V2 formats exist | Core | Add V2 unions, frozen baseline views, and real-baseline editor initialization |
| Assistant | Both clients call the real authenticated AI endpoint and show sources/limitations | No core gap for current stateless explanations | Optional | Preserve the contract; add conversation persistence only if separately approved |
| Watchlist | Web and mobile truthfully show unavailable/deferred UI; mock files/components remain for isolated prototype/test use | Persistent watchlist CRUD and customer quote/market summary endpoints | Optional | Add a separate backend product proposal before client activation |
| Search | Web global search is disabled; local portfolio/report/simulation/Learn filtering exists | No global search API or asset-catalogue search endpoint | Optional | Define searchable resources and ownership/pagination contracts first |
| Notifications | Web control is disabled; mobile labels delivery unavailable | Notification preferences, event model, delivery service, and API | Optional | Separate notifications design/implementation branch |
| Profile update/edit | Web account profile is read-only; web preferences are browser-local; mobile display name is explicitly device-local | Authenticated profile update/password-management API | Optional | Add backend account/profile contract before syncing edits |
| Export/share/download | Report screens explicitly say these actions are unavailable | Secure render/export, download authorization, and share/revocation APIs | Optional | Define privacy, format, expiry, and audit requirements first |
| Mock/static market data | Watchlist/prototype mock assets and demo calculations remain, while production portfolio/analytics/simulation flows use backend APIs; Learn content is code-owned educational content | Customer quote/watchlist APIs for live market UI | Optional | Keep mocks test/demo-only; remove or isolate stale demo modules during client integration |
| Saved-weight assumptions | Portfolio cards, detail, dashboard allocation, and simulation editor code dereference `holding.weight` | None for backend; client migration is pending | Core | Replace CRUD assumptions with real fields and valuation-derived allocations |
| Percentage-entry assumptions | Portfolio create/edit requires 0–100 inputs summing to 100%; simulation modified allocation correctly remains percentage-based | None for portfolio CRUD; simulation percentages remain the intended contract | Core | Remove percentages only from CRUD; retain them for Allocation/Combined hypotheses |

## Explicit product boundaries

The following remain out of scope unless a later approved proposal changes the
boundary: tax lots, transaction ledger, brokerage integration, tax
calculations, historical purchase-price inference, historical FX
reconstruction, and buy/sell advice. Forecasting or ML prediction is also a
future feature; Aura does not currently claim to predict prices or train a
market model.
