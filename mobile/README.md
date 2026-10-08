# Aura Mobile — Web Parity Complete Frontend

React Native + TypeScript mobile application adapted from Aura's customer React web product structure and visual system.

## Included

- Login / Register
- Home / Dashboard
- Portfolio list
- Portfolio detail with Overview / Holdings / Performance / Activity tabs
- Create Portfolio
- Add Asset
- Edit Holdings
- Analytics
- Historical Scenario simulation
- Allocation Change simulation
- Combined Simulation
- Simulation Results
- Simulation History
- AI Assistant UI
- Reports
- Report Detail
- Watchlist
- Learn
- Settings
- Dark mode / Light mode
- Local display name
- Hide portfolio values
- Local persistence for frontend testing

## Mobile navigation

```text
Home | Portfolio | Simulate | AI | More
```

More contains Analytics, Reports, Watchlist, Learn, and Settings.

## Run

```bash
cd mobile
npm install
npx expo install --fix
npm run typecheck
npx expo start -c
```

## Important

This package is frontend-complete for mobile testing. The production Aura backend remains the source of truth for authentication, portfolio ownership, financial analytics, reports, simulations, market data, and future AI explanations.

See `WEB_MOBILE_PARITY.md` for the web-to-mobile mapping.
