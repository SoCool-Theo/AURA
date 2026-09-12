# Fresh Supabase PostgreSQL Readiness

The previous development Supabase application schema is not a deployment
target. Do not attempt to recover or reuse it. Production deployment remains a
future task and must begin from a new Supabase PostgreSQL project.

## Phase 12 verified local baseline

The final guarded end-to-end run used this credential-free environment:

- PostgreSQL `18.4`
- host `127.0.0.1`
- port `5433`
- database `aura_test`
- role `aura`
- starting Alembic revision `7c1e2f4a6b90`
- ending Alembic revision `d4a6f8c2e1b7`

The migration preserved baseline legacy rows. Verification passed real CRUD,
USD and THB valuation, Report V2 JSONB round-trip, all three Simulation V2
JSONB round-trips, immutability after market-data changes, stale-data behavior,
THB-failure independence, ownership privacy, transaction rollback, and AI
integration with a mock provider. Cleanup restored all business and market-data
row counts to their baseline. The local test database intentionally remains at
`d4a6f8c2e1b7`.

No database password, test URL, or connection string belongs in this document.

## Future fresh-project checklist

1. Create a fresh Supabase PostgreSQL project.
2. Obtain the runtime `DATABASE_URL` through the approved secrets channel.
3. Configure a migration-capable direct PostgreSQL connection when required by
   Supabase/Alembic networking; do not assume a pooled runtime URL is suitable
   for migrations.
4. Keep every credential in ignored local environment files or the deployment
   platform's secret store. Never commit them.
5. From `backend/`, run `alembic upgrade head` against the explicitly selected
   new project.
6. Verify the database reports Alembic head `d4a6f8c2e1b7`.
7. Verify the expected `users`, `portfolios`, `holdings`, `market_data`,
   `analyses`, and `simulations` tables, ownership foreign keys/cascades,
   unique holding symbol/position constraints, complete holding-mode checks,
   positive amount/share checks, supported invested currencies, and report and
   simulation metadata/snapshot constraints.
8. Backfill historical coverage for the 17 user asset symbols.
9. Ensure the internal `THB=X` USD/THB series has current and scheduled update
   coverage; do not add it to the user asset list.
10. Run the market-data coverage audit, checking duplicates, per-symbol date
    ranges, fresh current observations, and required historical periods.
11. Configure the backend and the one intended scheduler process through
    deployment environment variables and secret storage.
12. Run backend health and authenticated register/login/me smoke tests.
13. Create one small real portfolio using only disposable deployment-smoke
    records.
14. Verify current USD valuation.
15. Verify current THB valuation and FX metadata.
16. Create and reopen one Report V2.
17. Run and reopen one guarded simulation, then clean up disposable records by
    an approved recoverable process.
18. Audit the final tracked changes and deployment configuration for secrets.

This is a readiness checklist, not evidence that Supabase deployment has been
performed.
