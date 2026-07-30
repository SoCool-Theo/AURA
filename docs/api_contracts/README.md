# Aura API contracts

This directory documents Aura's current Pydantic data contracts. The branch
defines data structures and validation rules, not HTTP endpoints.

## Supported contract areas

- [Portfolio analysis input](portfolio_analysis.md)
- [Prepared historical market data](market_data.md)
- [Portfolio analytics response](analytics_response.md)

Canonical JSON examples:

- [`backend/examples/portfolio_request.json`](../../backend/examples/portfolio_request.json)
- [`backend/examples/market_data_request.json`](../../backend/examples/market_data_request.json)
- [`backend/examples/market_data_response.json`](../../backend/examples/market_data_response.json)
- [`backend/examples/analysis_response.json`](../../backend/examples/analysis_response.json)

All models reject unknown fields. The contracts are provider-independent and
database-independent; they do not imply that fetching, persistence, routes, or
services exist.

## Deferred work

- API routes and services
- Production analytics adapters
- Database contracts
- Portfolio CRUD
- Investment-amount and share-quantity conversion
- Simulation contracts
- AI-agent contracts

