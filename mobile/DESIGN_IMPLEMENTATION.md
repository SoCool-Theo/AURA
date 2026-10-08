# Aura Mobile Premium UI v3

This version applies the generated Aura mobile design direction to the working all-features frontend.

## Visual direction

- deep navy background
- elevated slate cards
- cyan / teal primary accent
- purple, blue, green and amber feature accents
- compact investor-style metric cards
- rounded list rows
- cleaner five-tab bottom navigation
- dense but readable mobile information hierarchy

## Redesigned screens

- Home / Dashboard
- Portfolios
- Portfolio Detail
- Analytics
- Simulations
- Aura Assistant
- Reports
- Report Detail
- Watchlist
- Learn
- More
- Settings

Existing working Create Portfolio, Add Asset, Edit Holdings, simulation detail/result/history, onboarding and auth flows are retained and inherit the new shared theme.

## Functional scope retained

All local frontend functionality from the previous all-features build is retained:

- local/mock authentication
- portfolio CRUD
- holdings editing
- local demo analysis
- report snapshots
- three simulator flows
- simulation history
- watchlist persistence
- learning progress
- AI interface without fabricated answers
- settings / reset demo data

The real FastAPI backend is still intentionally separate.
