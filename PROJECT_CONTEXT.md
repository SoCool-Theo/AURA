# Aura Project Context

## Project Name

Aura: AI-Agent Portfolio Risk Intelligence System

## Main Problem

Beginner and retail investors can easily buy assets through trading apps,
but many do not understand the risks inside their portfolios.

## Main Goal

Aura analyzes a user's portfolio and translates complex financial risk
calculations into understandable explanations.

## Aura is

- A portfolio risk analysis system
- An educational system
- A historical what-if simulator
- An explainable AI system grounded in deterministic backend results

## Aura is not

- A trading bot
- A stock price prediction system
- A buy/sell recommendation system
- A financial advisor
- An automatic trading system

## Core Analytics

- Returns
- Volatility
- Maximum drawdown
- Sharpe ratio
- Correlation
- Concentration
- Diversification
- Risk drivers
- Risk classification

## Development Order

1. Build and verify analytics
2. Build market data pipeline
3. Build database
4. Connect services and API
5. Build historical simulator
6. Build website
7. Add AI agent
8. Build the mobile app and keep it aligned with the shared backend contract

## Technical Direction

- Backend: FastAPI
- Language: Python 3.13
- Database: PostgreSQL
- Frontend: React website
- Mobile app: React Native client sharing the FastAPI backend
- Development: Local first, cloud deployment later

## Main System Flow

1. Market data is fetched and cleaned.
2. Clean market data is validated and stored.
3. The user creates a portfolio and records ordered real holding facts.
4. The backend values shares from fresh persisted USD market observations and
   derives the current allocation.
5. Analytics apply that current allocation to a user-selected historical
   period; they do not reconstruct historical ownership from share counts.
6. The historical simulator tests the resolved allocation against past
   periods.
7. Reports and simulation history persist immutable, versioned snapshots.
8. The API sends backend-owned results to customer clients.
9. The AI agent explains live or frozen backend context in simple language.

## AI Agent Rules

1. The AI agent must explain results produced by Aura's analytics and simulation systems.
2. The AI agent must not invent portfolio calculations or replace the analytics engine.
3. Calculated values must come from deterministic backend calculations.

## Current Backend Capability Boundary

The backend on `feat/backend-real-holdings-dynamic-allocation` supports real
holding facts (`symbol`, `invested_amount`, `invested_currency`, `shares`, and
`purchase_date`), backend-owned holding order, dynamic USD valuation, optional THB
display, V2 immutable reports, V2 immutable simulation history, and compatible
AI grounding. The last fully integrated runtime migration is `d4a6f8c2e1b7`.
The additive planned-portfolio database foundation is implemented at migration
`e5b7c9d2a4f1`. Type-aware `CURRENT`/`PLANNED` CRUD, backend-derived
price-independent target allocation, optional estimated-share previews, and
shared `CURRENT`/`PLANNED`/`LEGACY` analysis baseline resolution are
implemented. Planned analysis and all three simulation modes now persist new
immutable V3 snapshots containing the authoritative proposed-amount baseline;
opening V3 history never queries current prices or recalculates results.
Mode-aware AI grounding now supports live planned allocations and frozen V3
report/simulation context with explicit hypothetical language and ownership-
claim rejection. Conversion and client behavior remain sequenced follow-on work.

Weight-only legacy portfolios remain temporarily readable and operable. A
normal holdings replacement converts a legacy portfolio to the real model.
Customer web and mobile clients still require a later integration branch for
real holding entry, valuation display, and V2 history rendering. A fresh
Supabase deployment is also pending; Phase 13 does not deploy or access
Supabase.

## Data Principle

1. Clean historical market data is used directly for portfolio calculations.
2. The system does not train a machine learning model on the market data at the current stage.
3. Market data sources and update methods must be explicitly defined before implementation.
