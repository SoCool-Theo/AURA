# Aura API contracts

This directory documents Aura's current Pydantic and HTTP contracts.

## Supported contract areas

- [Portfolio analysis input](portfolio_analysis.md)
- [Prepared historical market data](market_data.md)
- [Portfolio analytics response](analytics_response.md)
- [Final public HTTP API, holding modes, valuation, versioning, and errors](public_api.md)
- [Approved planned-portfolio target contract](planned_portfolios.md)
- [Administrator access, audit history, Dashboard statistics, Users directory, and Market Data administration](admin.md)

Canonical JSON examples:

- [`backend/examples/portfolio_request.json`](../../backend/examples/portfolio_request.json)
- [`backend/examples/market_data_request.json`](../../backend/examples/market_data_request.json)
- [`backend/examples/market_data_response.json`](../../backend/examples/market_data_response.json)
- [`backend/examples/analysis_response.json`](../../backend/examples/analysis_response.json)

All request models reject unknown fields. Deterministic analytics contracts
remain provider-independent; the public API now coordinates authenticated
PostgreSQL persistence, current valuation, immutable reports and simulations,
and grounded AI explanations.

## Current client boundary

- Customer web/mobile real-holding input and valuation rendering
- Customer web/mobile V1/V2/V3 report and simulation-history rendering
- Production deployment to a fresh Supabase project
- Optional capabilities listed in the
  [frontend/mobile integration backlog](../frontend_mobile_integration_backlog.md)
