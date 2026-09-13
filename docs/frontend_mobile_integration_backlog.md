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
| Current/planned holding CRUD | Mobile submits real ownership facts or planned proposed amounts without manual CRUD weights; web planned integration remains pending | None for CRUD | Core | Implement the same discriminated flow in web |
| Current valuation / planned allocation | Mobile dashboard/detail consume valuation for current holdings and planned allocation/preview for plans; web planned views remain pending | None | Core | Integrate planned allocation and preview in web without client-side official calculations |
| Report V2/V3 | Mobile renders legacy V1, current V2, and planned V3. Current/planned metric cards can show response-derived currency equivalents for cumulative return, annualized return, and exact maximum drawdown; web planned V3 remains pending | None | Core | Add discriminated V3 planned baseline and monetary-detail rendering in web only if web integration is resumed |
| Simulation History V2/V3 | Mobile renders current V2 and planned V3 history and initializes editors from the correct backend baseline; web V3 remains pending | None | Core | Add planned baseline initialization and V3 history rendering in web |
| Assistant | Both clients call the real authenticated AI endpoint and show sources/limitations | No core gap for current stateless explanations | Optional | Preserve the contract; add conversation persistence only if separately approved |
| Watchlist | Web and mobile truthfully show unavailable/deferred UI; mock files/components remain for isolated prototype/test use | Persistent watchlist CRUD and customer quote/market summary endpoints | Optional | Add a separate backend product proposal before client activation |
| Search | Web global search is disabled; local portfolio/report/simulation/Learn filtering exists | No global search API or asset-catalogue search endpoint | Optional | Define searchable resources and ownership/pagination contracts first |
| Notifications | Web control is disabled; mobile labels delivery unavailable | Notification preferences, event model, delivery service, and API | Optional | Separate notifications design/implementation branch |
| Profile update/edit | Web account profile is read-only; web preferences are browser-local; mobile display name is explicitly device-local | Authenticated profile update/password-management API | Optional | Add backend account/profile contract before syncing edits |
| Export/share/download | Report screens explicitly say these actions are unavailable | Secure render/export, download authorization, and share/revocation APIs | Optional | Define privacy, format, expiry, and audit requirements first |
| Mock/static market data | Watchlist/prototype mock assets and demo calculations remain, while production portfolio/analytics/simulation flows use backend APIs; Learn content is code-owned educational content | Customer quote/watchlist APIs for live market UI | Optional | Keep mocks test/demo-only; remove or isolate stale demo modules during client integration |
| Saved-weight assumptions | Removed from mobile current/planned production flows; legacy display remains compatible. Web planned migration remains pending | None | Core | Complete the web migration while retaining legacy readers |
| Percentage-entry assumptions | Mobile CRUD no longer accepts weights; Allocation/Combined simulation percentages correctly remain user-controlled hypotheses. Web planned CRUD remains pending | None | Core | Preserve this boundary during web integration |

## Explicit product boundaries

The following remain out of scope unless a later approved proposal changes the
boundary: tax lots, transaction ledger, brokerage integration, tax
calculations, historical purchase-price inference, historical FX
reconstruction, and buy/sell advice. Forecasting or ML prediction is also a
future feature; Aura does not currently claim to predict prices or train a
market model.
