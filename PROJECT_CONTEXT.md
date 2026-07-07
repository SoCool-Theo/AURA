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
- An explainable AI system later

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
8. Build mobile app later

## Technical Direction

- Backend: FastAPI
- Language: Python 3.13
- Database: PostgreSQL
- Frontend: Website first
- Mobile app: Later
- Development: Local first, cloud deployment later

## Main System Flow

1. Market data is fetched and cleaned.
2. Clean market data is validated and stored.
3. The user creates a portfolio.
4. Analytics calculate portfolio risk.
5. The historical simulator tests the portfolio against past periods.
6. Services coordinate the application workflow.
7. The API sends results to the website.
8. The AI agent later explains computed results in simple language.

## AI Agent Rules (Adding Later)

1. The AI agent must explain results produced by Aura's analytics and simulation systems.
2. The AI agent must not invent portfolio calculations or replace the analytics engine.
3. Calculated values must come from deterministic backend calculations.

## Data Principle

1. Clean historical market data is used directly for portfolio calculations.
2. The system does not train a machine learning model on the market data at the current stage.
3. Market data sources and update methods must be explicitly defined before implementation.