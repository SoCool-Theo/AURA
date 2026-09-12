# Portfolio analytics response

`PortfolioAnalysisResponse` is the JSON-safe deterministic analytics contract
used by report creation and report snapshots. For real portfolios it is
composed with a frozen valuation and per-asset context in Report V2; legacy
reports retain the V1 envelope.

## Top-level fields

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `portfolio_name` | `str` | Yes | Trimmed display name. |
| `start_date` | `date` | Yes | Inclusive requested-period start. |
| `end_date` | `date` | Yes | Inclusive requested-period end. |
| `metadata` | `AnalysisMetadata` | Yes | Actual analysis dates and stable observation counts. |
| `portfolio_metrics` | `PortfolioMetrics` | Yes | Overall return, volatility, and Sharpe metrics. |
| `max_drawdown` | `MaximumDrawdownMetrics` | Yes | Signed maximum drawdown and peak/trough dates. |
| `concentration` | `ConcentrationMetrics` | Yes | Portfolio concentration measures. |
| `diversification` | `DiversificationMetrics` | Yes | Diversification measures, coverage, score, and level. |
| `risk_classification` | `RiskClassification` | Yes | Educational risk score, label, component points, metrics, and reasons. |
| `risk_drivers` | `RiskDriverAnalysis` | Yes | Portfolio volatility, top driver, and ordered signed contributions. |
| `asset_metrics` | `list[AssetMetrics]` | Yes | Ordered per-asset analytics; at least one entry. |
| `correlation_matrix` | `CorrelationMatrix` | Yes | Ordered square correlation matrix. |
| `correlation_pairs` | `list[CorrelationPair]` | Yes | Ordered unique pairs; may be empty for one asset. |
| `portfolio_returns` | `list[PortfolioReturnPoint]` | Yes | Ordered dated periodic portfolio returns. |

## Nested models

### `AnalysisMetadata`

| Field | Type | Meaning |
| --- | --- | --- |
| `analysis_start` | `date` | First price-observation date used by analytics. |
| `analysis_end` | `date` | Last price-observation date used by analytics. |
| `price_observation_count` | positive `int` | Number of price observations. |
| `return_observation_count` | positive `int` | Number of return observations; exactly one fewer than prices. |
| `asset_count` | positive `int` | Number of portfolio assets. |

### `PortfolioMetrics`

| Field | Type | Meaning |
| --- | --- | --- |
| `cumulative_return` | finite `float` | Compounded portfolio return as a decimal value. |
| `annualized_return` | finite `float` | Annualized portfolio return as a decimal value. |
| `annualized_volatility` | non-negative finite `float` | Annualized volatility as a decimal value. |
| `sharpe_ratio` | finite `float` | Current annualized Sharpe ratio. |

### `MaximumDrawdownMetrics`

| Field | Type | Meaning |
| --- | --- | --- |
| `max_drawdown` | `float` from `-1.0` through `0.0` | Most negative drawdown; losses remain negative. |
| `peak_date` | `date \| null` | Active peak date, or `null` when unavailable. |
| `trough_date` | `date \| null` | First trough date, or `null` when unavailable. |

### `ConcentrationMetrics`

| Field | Type | Meaning |
| --- | --- | --- |
| `largest_weight` | positive decimal `float` up to `1.0` | Largest asset weight. |
| `top_n_weight` | positive decimal `float` up to `1.0` | Sum of the largest `top_n` weights. |
| `hhi` | positive `float` up to `1.0` | Unscaled Herfindahl-Hirschman index. |
| `effective_number_of_assets` | positive finite `float` | Reciprocal of unrounded HHI. |
| `top_n` | positive `int` | Number of largest weights requested. |

### `DiversificationMetrics`

| Field | Type | Meaning |
| --- | --- | --- |
| `active_asset_count` | positive `int` | Assets with weight above zero. |
| `effective_number_of_assets` | positive finite `float` | Weight-implied effective asset count. |
| `weight_score` | `float` from `0.0` through `100.0` | Weight-diversification score. |
| `average_pairwise_correlation` | `float` from `-1.0` through `1.0`, or `null` | Average defined active-pair correlation. |
| `correlation_score` | `float` from `0.0` through `100.0`, or `null` | Correlation-diversification score. |
| `overall_score` | `float` from `0.0` through `100.0`, or `null` | Combined diversification score. |
| `level` | `Weak`, `Moderate`, `Strong`, or `Unavailable` | Current diversification label. |
| `defined_pair_count` | non-negative `int` | Active pairs with defined correlation. |
| `total_pair_count` | non-negative `int` | All active-asset pairs. |

An unavailable overall score remains `null` and uses the `Unavailable` level; it
is never converted to zero.

### `RiskClassification`

| Field | Type | Meaning |
| --- | --- | --- |
| `risk_score` | `float` from `0.0` through `100.0` | Overall educational risk score. |
| `risk_level` | `Low`, `Moderate`, `High`, or `Very High` | Current overall risk label. |
| `volatility_points` | `int` from `0` through `3` | Volatility component points. |
| `drawdown_points` | `int` from `0` through `3` | Drawdown component points. |
| `concentration_points` | `int` from `0` through `3` | Concentration component points. |
| `diversification_points` | `int` from `0` through `3`, or `null` | Diversification component points when available. |
| `metrics_used` | ordered `list[str]` | Component metric names used in scoring. |
| `reasons` | non-empty ordered `list[str]` | Deterministic current risk reasons. |

### `RiskDriverAnalysis` and `RiskDriverEntry`

`RiskDriverAnalysis` contains non-negative finite `portfolio_volatility`,
normalized `top_driver`, and a non-empty ordered `entries` list. The top driver
matches the first ranked entry.

Each `RiskDriverEntry` contains:

| Field | Type | Meaning |
| --- | --- | --- |
| `rank` | positive `int` | Existing analytics rank. |
| `symbol` | `AssetSymbol` | Normalized asset symbol. |
| `weight` | decimal `float` from `0.0` through `1.0` | Asset weight. |
| `annualized_asset_volatility` | non-negative finite `float` | Annualized asset volatility. |
| `marginal_volatility_contribution` | finite `float` | Signed marginal contribution. |
| `component_volatility_contribution` | finite `float` | Signed component contribution. |
| `percentage_volatility_contribution` | finite `float` | Signed fractional contribution. |

Negative contribution values are valid and are not clamped or converted to
absolute values.

### `AssetMetrics`

| Field | Type | Meaning |
| --- | --- | --- |
| `symbol` | `AssetSymbol` | Normalized asset symbol. |
| `weight` | decimal `float` from `0.0` through `1.0` | Asset weight. |
| `cumulative_return` | finite `float` | Compounded asset return as a decimal. |
| `annualized_return` | finite `float` | Annualized asset return as a decimal. |
| `annualized_volatility` | non-negative finite `float` | Annualized volatility as a decimal. |
| `max_drawdown` | `float` from `-1.0` through `0.0` | Signed asset maximum drawdown. |
| `sharpe_ratio` | finite `float \| null` | Annualized Sharpe ratio, or `null` when undefined. |

### Correlations

`CorrelationMatrix` contains ordered, unique `symbols` and a square `values`
array with exactly one row and column per symbol. `CorrelationPair` contains
ordered `asset_a`, `asset_b`, and `correlation`. Present correlations range from
`-1.0` through `1.0`; `null` represents an undefined value. Pair symbols must be
known matrix symbols, and duplicate unordered pairs are rejected.

### `PortfolioReturnPoint`

| Field | Type | Meaning |
| --- | --- | --- |
| `date` | `date` | Return observation date. |
| `portfolio_return` | finite `float` | Periodically rebalanced portfolio return as a decimal. |

Return dates are unique, strictly increasing, inside the inclusive response
period, and need not be consecutive.

## Cross-field and JSON behavior

Asset-metric, risk-driver, and correlation-matrix symbol sets must match.
Asset-metric weights sum to `1.0` with an absolute tolerance of `1e-9`.
Collections preserve supplied order and are not sorted or repaired.

Dates serialize as ISO strings. Intentionally unavailable values serialize as
JSON `null`. The public format contains no Pandas `DataFrame`, `Series`, or
`Timestamp`; no NumPy scalar; and no `NaN` or Infinity. Unknown fields are
rejected.

Canonical example:
[`backend/examples/analysis_response.json`](../../backend/examples/analysis_response.json).

This destination contract contains no AI explanation or recommendation field.
Routes, services, and production conversion from `PortfolioAnalyticsResult`
remain deferred.
