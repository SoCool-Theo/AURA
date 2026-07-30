# Prepared historical market data

These provider-independent contracts describe requests for, and exchange of,
prepared daily historical market data. They do not fetch, clean, or store data.

## `HistoricalMarketDataRequest`

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `symbols` | `list[AssetSymbol]` | Yes | One or more ordered, normalized, unique symbols. |
| `start_date` | `date` | Yes | Inclusive requested start date. |
| `end_date` | `date` | Yes | Inclusive requested end date. |

## `HistoricalPricePoint`

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `date` | `date` | Yes | Observation date. |
| `adjusted_close` | `float` | Yes | Positive finite adjusted-close value. |
| `volume` | `int \| null` | No | Non-negative integer volume; defaults to `null`. |

## `AssetPriceSeries`

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `symbol` | `AssetSymbol` | Yes | Normalized asset symbol. |
| `source` | `str` | Yes | Non-empty trimmed source description; not a closed provider enum. |
| `points` | `list[HistoricalPricePoint]` | Yes | One or more observations in strictly increasing date order. |

Point dates must be unique. Schemas preserve supplied order and reject, rather
than sort or repair, malformed series. Consecutive calendar or business dates
are not required.

## `HistoricalMarketDataResponse`

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `series` | `list[AssetPriceSeries]` | Yes | One or more ordered series with unique normalized symbols. |
| `start_date` | `date` | Yes | Inclusive response-period start. |
| `end_date` | `date` | Yes | Inclusive response-period end. |

Every point must fall inside the declared period. Assets may have different
trading dates and different point counts. Unknown fields are rejected.

Canonical examples:

- [`backend/examples/market_data_request.json`](../../backend/examples/market_data_request.json)
- [`backend/examples/market_data_response.json`](../../backend/examples/market_data_response.json)

Live provider integration, provider-specific symbol validation, fetching,
cleaning, and persistence are not implemented by this schema branch.

