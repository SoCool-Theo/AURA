# Planned Portfolio Domain Contract

**Status:** Approved target contract. The additive database/model foundation is
implemented at Alembic revision `e5b7c9d2a4f1`; type-aware CRUD and runtime
integration begin in later steps. The current public API still exposes the
completed legacy/real-holding contract documented in `public_api.md`.

## Purpose

Aura supports two user-facing questions without becoming a trading or
prediction product:

- **CURRENT:** What historical risk characteristics does my current allocation
  show?
- **PLANNED:** How would this proposed allocation have behaved under historical
  market conditions?

Both workflows remain educational and deterministic. They do not forecast
future returns, recommend a purchase, or represent an executable brokerage
order.

## Portfolio types

| Type | User-created | Authoritative input | Canonical baseline |
| --- | --- | --- | --- |
| `CURRENT` | Yes | Shares, invested amount/currency, and purchase date | Current USD values derived from shares and fresh persisted prices |
| `PLANNED` | Yes | Proposed investment amount per asset and one plan currency | Proposed amounts normalized into target weights |
| `LEGACY` | No | Previously persisted weights | Saved weights |

`CURRENT` is the public successor name for the existing `REAL` implementation.
Existing V1/V2 snapshots and internal compatibility readers retain their exact
stored discriminators. They are never rewritten merely to adopt the new public
name.

`LEGACY` is an internal compatibility state. It must not appear as a selectable
create option in customer clients.

## Persisted portfolio discriminator

The target `Portfolio` record has an explicit `portfolio_type` because an empty
portfolio cannot infer its type from holdings. It also has an optional
`plan_currency` and optional `source_plan_id`.

| Portfolio type | `plan_currency` | `source_plan_id` |
| --- | --- | --- |
| `CURRENT` | `NULL` | Optional; present only when created from a plan |
| `PLANNED` | `USD` or `THB` | `NULL` |
| `LEGACY` | `NULL` | `NULL` |

Migration mapping is additive:

- a non-empty portfolio with complete real holdings becomes `CURRENT`;
- a non-empty portfolio with complete saved-weight holdings becomes `LEGACY`;
- an existing empty draft becomes `CURRENT` because it contains no legacy
  allocation to preserve;
- mixed or incomplete existing state aborts migration rather than being
  guessed or repaired silently.

New create requests select `CURRENT` or `PLANNED`. During client rollout, an
omitted type may default to `CURRENT` for backward compatibility. New clients
must send the intended type explicitly.

## Mutually exclusive holding shapes

Every holding uses exactly one complete shape:

```text
CURRENT
symbol + invested_amount + invested_currency + shares + purchase_date
weight = NULL
proposed_amount = NULL

PLANNED
symbol + proposed_amount
weight = NULL
invested_amount = NULL
invested_currency = NULL
shares = NULL
purchase_date = NULL

LEGACY
symbol + weight
proposed_amount = NULL
invested_amount = NULL
invested_currency = NULL
shares = NULL
purchase_date = NULL
```

Amounts and shares are positive finite decimals. Symbols are unique within a
portfolio, and request order remains the backend-controlled holding position.
Portfolio replacement is transactional and rejects mixed shapes or a shape
that does not match the parent portfolio type.

The existing explicit `LEGACY`-to-`CURRENT` replacement remains a compatibility
path. Ordinary replacement never changes `CURRENT` to `PLANNED` or `PLANNED`
to `CURRENT`.

## Planned allocation calculation

A planned portfolio has one currency, so its target weights do not require
asset prices or FX:

```text
total_proposed_amount = sum(proposed_amount)

target_weight_i = proposed_amount_i / total_proposed_amount
```

The backend owns decimal normalization and canonical output order. Clients
display returned target allocations and do not reproduce the calculation as
financial authority.

Saving a valid plan and resolving its target allocation must succeed when
current asset prices or FX are unavailable. Historical analysis can still
fail when the requested historical series lacks sufficient aligned coverage;
Aura retains its existing no-fabrication policy.

## Estimated shares

Estimated shares are optional, derived display information:

```text
USD plan:
estimated_shares = proposed_amount / current_asset_price_usd

THB plan:
estimated_shares =
    proposed_amount_thb / usd_thb_rate / current_asset_price_usd
```

They must never:

- be stored as ownership facts;
- determine target weights;
- drive analytics or simulations;
- be treated as an executable order; or
- be copied into a current portfolio as actual shares.

When available, the preview includes price, price date, quote currency, and FX
rate/date where applicable. Calculation retains full decimal precision;
rounding is presentation-only. Missing or stale price/FX context makes only the
affected estimate unavailable and does not block saving or analyzing the plan.

`GET /api/portfolios/{portfolio_id}/planned-preview` uses one server-selected
UTC request date and returns the canonical allocation even when estimates are
unavailable. Each holding reports `AVAILABLE`, `PRICE_UNAVAILABLE`, or
`FX_UNAVAILABLE`. The endpoint is owner-scoped and read-only; it never persists
prices, FX, estimated shares, or derived weights.

## Shared baseline allocation resolver

The existing `PortfolioBaselineResolutionService` remains the single entry
point and is extended rather than duplicated:

```text
CURRENT -> current valuation -> dynamic weights
PLANNED -> proposed amounts -> target weights
LEGACY  -> saved weights
                         |
                         v
               canonical baseline
                         |
                         v
      analytics / reports / simulations / AI
```

The resolved baseline contains semantic provenance, not weights alone:

```text
portfolio_type
baseline_source
resolved_weights
baseline_as_of, when applicable
plan_currency, when applicable
valuation context, when applicable
```

Downstream services must consume this resolution and must not independently
infer portfolio type or calculate official weights.

## Reports and simulations

Existing immutable V1 and V2 snapshots remain byte-for-byte readable. Planned
portfolio support receives new discriminated snapshot versions rather than
overloading real-holding V2 semantics.

A planned snapshot freezes at least:

- `portfolio_type = PLANNED`;
- plan currency;
- ordered proposed amounts;
- backend-derived target weights;
- selected historical period or scenario;
- complete analytics or simulation results; and
- an explicit hypothetical/non-forecasting limitation.

Estimated-share context is optional. If a saved result displays it, the exact
price and FX context used must be frozen in that snapshot. Opening history never
recalculates weights, estimates, or analytics.

For every simulation mode, the original baseline is resolved consistently:

- `CURRENT`: current dynamic allocation at execution;
- `PLANNED`: target allocation at execution;
- `LEGACY`: saved weights.

User-entered modified allocation percentages remain hypothetical simulation
inputs and are separate from portfolio CRUD.

## AI grounding

AI context includes portfolio type, baseline source, snapshot version, resolved
weights, and the relevant period. It uses mode-aware language:

- `CURRENT`: "your current portfolio" or "your current allocation";
- `PLANNED`: "your planned portfolio" or "your proposed allocation";
- `LEGACY`: "your saved allocation."

AI must not call proposed assets owned holdings, treat estimated shares as
actual, recommend executing a plan, predict future behavior, or replace
deterministic backend calculations.

## Create-current-from-plan conversion

Conversion creates a separate `CURRENT` portfolio and leaves the original
`PLANNED` portfolio and all of its saved history unchanged:

```text
PLANNED portfolio
       |
       v
user supplies actual shares, invested amount/currency, and purchase date
       |
       v
new CURRENT portfolio with optional source_plan_id
```

The operation does not infer execution facts from estimated shares. It creates
the new portfolio and all current holdings atomically, or creates nothing.

## Error and privacy requirements

Existing ownership privacy is preserved: missing and wrong-owner resources are
both `404`. The target behavior also distinguishes:

- `401`: missing or invalid authentication;
- `409`: portfolio/holding type conflict or unsupported operation for the type;
- `422`: invalid request or insufficient historical analysis input;
- `503`: required current market context unavailable for a current-only
  operation;
- `500`: sanitized unexpected failure.

Planned estimate unavailability is represented in a successful plan preview;
it is not a portfolio-wide `503` because estimates are non-authoritative.

## Delivery sequence

Steps 1 through 6 and the mobile portion of Step 7 are implemented. Web
integration, conversion, and Step 8 remain pending.

1. Freeze the planned-portfolio product, data, API, and provenance contract.
2. Add and verify the database discriminator, planned fields, constraints, and
   compatibility backfill.
3. Add type-aware portfolio CRUD and price-independent target allocation.
4. Add optional estimated-share preview, then extend the shared baseline
   resolver and analysis composition.
5. Add immutable planned report and simulation snapshot variants. Implemented
   as Report V3 and three Simulation V3 formats; V3 freezes only authoritative
   planned inputs and results and never recalculates on retrieval.
6. Add mode-aware AI grounding. Implemented for live planned portfolios and
   frozen Report/Simulation V3 context with planned-language instructions,
   explicit hypothetical limitations, and ownership-claim output rejection.
7. Integrate customer mobile and web workflows. Mobile now supports typed
   create/edit/detail/dashboard, Report V3, Simulation V3, planned simulation
   baselines, and mode-aware Assistant context. Web integration and the
   conversion workflow remain pending.
8. Run migration, rollback, privacy, immutability, and full regression
   verification before deployment readiness is claimed.
