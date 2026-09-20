# Portfolio analysis request

These models define the normalized weight-based input consumed by Aura's
existing analytics and simulation engines. They are not the public portfolio
CRUD holding contract.

## `PortfolioHoldingInput`

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `symbol` | `AssetSymbol` | Yes | Asset symbol, trimmed and normalized to uppercase. |
| `weight` | `float` | Yes | Decimal portfolio weight from `0.0` through `1.0`. |

Empty symbols are rejected. Punctuation is preserved, while provider-specific
ticker validity remains deferred.

## `PortfolioAnalysisRequest`

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `portfolio_name` | `str` | Yes | Display name; surrounding whitespace is removed while internal text and casing are preserved. |
| `holdings` | `list[PortfolioHoldingInput]` | Yes | One or more holdings in caller-supplied order. |
| `start_date` | `date` | Yes | Inclusive analysis-period start. |
| `end_date` | `date` | Yes | Inclusive analysis-period end. |

Normalized holding symbols must be unique. Holding weights must total `1.0`;
validation uses `math.isclose` with `rel_tol=0.0` and `abs_tol=1e-9`.
Holdings are not sorted and weights are not normalized automatically.

Equal start and end dates are valid. A reversed range is rejected. Unknown
fields are rejected, and validation does not mutate caller-owned mappings,
lists, or nested holding objects.

Canonical example:
[`backend/examples/portfolio_request.json`](../../backend/examples/portfolio_request.json).

Real portfolio CRUD uses `PortfolioRealHoldingInput` through
`PUT /api/portfolios/{portfolio_id}/holdings`. Before analytics run, the backend
derives a real portfolio's current USD allocation and adapts it into this
weight-based engine contract. Legacy portfolios continue to supply their saved
weights during the temporary compatibility period.

## Saved-report monetary context

Current V2 and planned V3 report detail responses include an optional
`monetary_metrics` object. It is derived only from the stored report snapshot;
it does not fetch current prices, revalue a portfolio, or modify the persisted
JSONB payload. This keeps previously saved reports readable without a database
migration.

| Field | Type | Meaning |
| --- | --- | --- |
| `currency` | `USD` or `THB` | Currency of every amount in this object. |
| `basis` | `saved-current-valuation` or `planned-proposed-amount` | Identifies the saved reference amount. |
| `reference_amount` | Positive decimal string | Saved current valuation for V2 or total proposed amount for V3. |
| `cumulative_return_amount` | Signed decimal string | Historical cumulative return applied to the reference amount. |
| `annualized_return_amount` | Signed decimal string | Historical annualized rate expressed as a one-year equivalent on the reference amount. |
| `maximum_drawdown_amount` | Non-positive decimal string or `null` | Currency decline for the exact saved peak-to-trough drawdown episode. |

`maximum_drawdown_amount` is `null` when an older or malformed snapshot does
not contain enough internally consistent dated return information to reproduce
the saved drawdown episode. Clients must not substitute
`reference_amount × max_drawdown`, because the drawdown percentage is measured
from its historical peak rather than necessarily from the reference amount.

These amounts are historical educational equivalents, not actual realized
profit/loss, guarantees, or forecasts. V1 legacy reports remain
percentage-only because they do not contain a trustworthy currency reference
amount.

V2 and V3 report detail responses also include an ordered
`asset_monetary_metrics` list. It is response-only and derived from the same
immutable report snapshot; it is not written back to JSONB and does not fetch
current market data.

| Field | Type | Meaning |
| --- | --- | --- |
| `symbol` | Asset symbol | Asset whose saved metrics and return path were used. |
| `currency` | `USD` or `THB` | Currency of every amount in this item. |
| `basis` | `saved-current-value` or `planned-proposed-amount` | Identifies the asset's saved reference amount. |
| `reference_amount` | Positive decimal string | V2 saved holding value or V3 proposed amount. |
| `cumulative_return_amount` | Signed decimal string | Asset cumulative return applied to the saved asset reference amount. |
| `annualized_return_amount` | Signed decimal string | Asset annualized rate expressed as a one-year equivalent on the saved asset reference amount. |
| `maximum_drawdown_amount` | Non-positive decimal string or `null` | Currency decline for the asset's exact saved peak-to-trough return path. |

The list follows `analysis.asset_metrics` order and is complete for every V2
or V3 asset. For older snapshots without `asset_returns`, cumulative and
annualized amounts remain available from saved metrics, while a non-zero
`maximum_drawdown_amount` is `null`. Clients must not replace that `null` with
`reference_amount × max_drawdown`; maximum drawdown must use the reconstructed
historical peak and trough.
