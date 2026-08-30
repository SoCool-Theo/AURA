# Aura Mobile – All Frontend Features

This React Native + TypeScript build keeps Aura's agreed mobile `src/` architecture and contains the customer-facing frontend features from the Aura web application, adapted for phone use.

## Main navigation

```text
Home | Portfolio | Simulate | AI | More
```

`More` contains:

```text
Analytics
Reports
Watchlist
Learn
Settings
```

Nested Portfolio, Simulation, Report, Watchlist, Learn and Settings screens retain a Home shortcut in the header.

## Included frontend functionality

- Onboarding
- Local/mock Login and Register
- Home dashboard and quick shortcuts
- Portfolio create/open/rename/duplicate/delete
- Add assets and invested amounts
- Edit/remove holdings
- Automatic local weight recalculation
- Demo portfolio analysis
- Save/view/delete local report snapshots
- Historical Scenario simulation
- Allocation Change simulation
- Combined Simulation
- Simulation Result and History
- Redesigned AI Assistant UI with no fake AI answers
- Watchlist search/add/remove with local persistence
- Learn search/category filters, lesson detail and completion progress
- Settings, reset local demo data and sign out

## Web-to-mobile feature parity

The mobile frontend now includes the same main customer areas documented for the web app:

```text
Dashboard
Portfolios
Analytics
Simulations
AI Assistant
Reports
Watchlist
Learn
Settings
```

It also includes Login/Register and Report Detail.

The layouts are adapted for mobile rather than copied from the web.

## Backend boundary

The local calculations in `src/utils/localCalculations.ts` are demo-only so the complete frontend can be tested without FastAPI. They are not Aura's production analytics.

When FastAPI integration is enabled, the backend remains authoritative for authentication, ownership, official analytics, simulations, reports, history, market data, and future AI explanations.

## Run

```bash
cd "/Users/kelvin/Downloads/Aura test/AURA/mobile"
npm install
npx expo install --fix
npm run typecheck
npx expo start -c
```
