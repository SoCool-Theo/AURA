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
