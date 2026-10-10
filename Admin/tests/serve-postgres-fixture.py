"""Opt-in admin acceptance in a disposable schema of the approved Docker DB.

Reads TEST_DATABASE_URL from .env.test-database without printing credentials.
Exercises real Alembic migrations, bootstrap and application HTTP routes. The
public schema is fingerprinted before/after; only this run's schema is removed.
No market/AI provider, worker, remote database or existing account is used.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from decimal import Decimal
import json
from pathlib import Path
from secrets import token_urlsafe
from threading import Barrier
import sys
from uuid import UUID, uuid4

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "backend")]

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from pydantic import SecretStr  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
import uvicorn  # noqa: E402

from backend.tests.integration.database.postgres_test_guard import (  # noqa: E402
    read_only_preflight, read_test_database_url, validate_test_database_url,
)
from backend.app.core.config import settings as migration_settings  # noqa: E402
from app.api.dependencies import get_database_session  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.database.models import AIRequestLog, Analysis, MarketData, Portfolio, User  # noqa: E402
from app.services.admin_access_service import AdminAccessService, AdminBootstrapError  # noqa: E402


def public_fingerprint(engine):
    """Compare existing data without exposing any row content or credentials."""
    with engine.connect() as connection, connection.begin():
        connection.execute(text("SET TRANSACTION READ ONLY"))
        tables = connection.execute(text(
            "SELECT tablename FROM pg_catalog.pg_tables "
            "WHERE schemaname = 'public' ORDER BY tablename"
        )).scalars().all()
        quote = connection.dialect.identifier_preparer.quote_identifier
        return {
            name: tuple(connection.execute(text(
                'SELECT count(*), md5(string_agg(md5(to_jsonb(t)::text), '
                "',' ORDER BY md5(to_jsonb(t)::text))) "
                f"FROM public.{quote(name)} AS t"
            )).one())
            for name in tables
        }


def seed(factory, password):
    now = datetime.now(UTC)
    encoded = hash_password(password)
    with factory() as session:
        session.get(User, UUID(int=99)).display_name = "Synthetic Legacy"
        session.add(User(id=UUID(int=1), email="admin@example.com", display_name="Synthetic Admin", password_hash=encoded))
        session.add_all([
            User(id=UUID(int=index + 2), email=f"customer{index:02d}@example.com",
                 display_name=f"Synthetic Customer {index:02d}", password_hash=encoded)
            for index in range(30)
        ])
        session.commit()
    with factory() as session:
        service = AdminAccessService(session)
        service.bootstrap_first_admin(UUID(int=1))
        session.commit()
        service.bootstrap_first_admin(UUID(int=1))
        session.commit()
        try:
            service.bootstrap_first_admin(UUID(int=2))
        except AdminBootstrapError:
            session.rollback()
        else:
            raise AssertionError("Bootstrap allowed a second administrator")
    with factory() as session:
        portfolio = Portfolio(id=UUID(int=100), user_id=UUID(int=2), name="Synthetic Portfolio", portfolio_type="CURRENT")
        session.add(portfolio)
        session.flush()
        session.add_all([
            Analysis(portfolio_id=portfolio.id, start_date=now.date() - timedelta(days=60),
                     end_date=now.date(), schema_version="synthetic", result_snapshot={},
                     created_at=now - timedelta(days=index))
            for index in range(8)
        ])
        session.add(MarketData(symbol="AAPL", date=now.date(), adjusted_close=Decimal("123.45678901"), volume=1000, source="Synthetic"))
        session.add(AIRequestLog(
            started_at=now, duration_ms=1.25, outcome="REFUSED", http_status=200,
            provider_kind=None, provider_called=False, refusal_stage="INPUT",
            guardrail_reason="investment_advice", error_code=None,
            has_portfolio_source=False, has_report_source=False,
            has_simulation_source=False, limitation_count=0,
        ))
        session.commit()


def check_http(app, password, factory):
    paths = ["me", "dashboard", "users", "market-data", "market-data/status",
             "market-data/observations", "system-health", "ai-monitoring",
             "ai-monitoring/requests", "audit-logs"]
    with TestClient(app) as client:
        def login(email):
            response = client.post("/api/auth/login", json={"email": email, "password": password})
            assert response.status_code == 200
            return {"Authorization": f"Bearer {response.json()['access_token']}"}

        customer = login("customer00@example.com")
        admin = login("admin@example.com")
        for path in paths:
            url = f"/api/admin/{path}"
            assert client.get(url).status_code == 401
            assert client.get(url, headers=customer).status_code == 403
            assert client.get(url, headers=admin).status_code == 200
        print("PASS PostgreSQL: all 10 routes, anonymous 401 and customer 403", flush=True)
        dashboard = client.get("/api/admin/dashboard", headers=admin).json()
        assert dashboard["users"]["total"] == 32 and dashboard["users"]["admins"] == 1
        assert dashboard["portfolios"]["total"] == 1
        assert dashboard["saved_reports"]["total"] == 8
        assert len(dashboard["daily"]) == 30
        assert sum(day["saved_reports"] for day in dashboard["daily"]) == 8
        users = client.get("/api/admin/users", headers=admin).json()
        assert users["total"] == 32 and len(users["items"]) == 25
        assert all("password_hash" not in user and "phone_number" not in user for user in users["items"])
        audit = client.get("/api/admin/audit-logs", headers=admin).json()
        assert audit["total"] == 1 and audit["items"][0]["action"] == "ADMIN_BOOTSTRAPPED"
        observations = client.get("/api/admin/market-data/observations", headers=admin).json()
        assert Decimal(observations["items"][0]["adjusted_close"]) == Decimal("123.45678901")
        health = client.get("/api/admin/system-health", headers=admin).json()
        assert next(check for check in health["checks"] if check["component"] == "database")["status"] == "healthy"
        print("PASS PostgreSQL: exact aggregates, safe directory, bootstrap audit and decimal price", flush=True)
        with ThreadPoolExecutor(max_workers=5) as executor:
            statuses = list(executor.map(lambda path: client.get(f"/api/admin/{path}", headers=admin).status_code, paths * 3))
        assert statuses == [200] * 30
        print("PASS PostgreSQL: 30 concurrent reads with independent sessions", flush=True)
        check_account_status(client, password, factory, admin, customer)


def check_account_status(client, password, factory, admin, customer):
    def change(target, headers=admin, status="SUSPENDED", expected="ACTIVE"):
        return client.patch(f"/api/admin/users/{UUID(int=target)}/status", headers=headers,
                            json={"status": status, "expected_status": expected})

    assert change(1).status_code == 409
    assert change(2, headers=customer).status_code == 403
    assert change(2).status_code == 200
    assert change(2).status_code == 200
    assert client.get("/api/auth/me", headers=customer).status_code == 401
    assert client.post("/api/auth/login", json={"email": "customer00@example.com", "password": password}).status_code == 401
    assert client.get("/api/admin/users", headers=admin, params={"status": "SUSPENDED"}).json()["total"] == 1
    assert change(2, status="ACTIVE", expected="SUSPENDED").status_code == 200
    assert client.get("/api/auth/me", headers=customer).status_code == 401
    login = client.post("/api/auth/login", json={"email": "customer00@example.com", "password": password})
    assert login.status_code == 200
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {login.json()['access_token']}"}).status_code == 200
    events = client.get("/api/admin/audit-logs", headers=admin, params={"target_id": str(UUID(int=2))}).json()
    assert events["total"] == 2
    assert {event["action"] for event in events["items"]} == {"USER_SUSPENDED", "USER_REACTIVATED"}
    assert all(event["actor_user_id"] == str(UUID(int=1)) for event in events["items"])
    print("PASS PostgreSQL: suspension, fresh-login reactivation, idempotency, status filters and atomic audit", flush=True)

    # Fixture-only second admin setup; no production role-management API exists.
    with factory() as session:
        session.get(User, UUID(int=3)).role = "ADMIN"
        session.commit()
    login = client.post("/api/auth/login", json={"email": "customer01@example.com", "password": password})
    second = {"Authorization": f"Bearer {login.json()['access_token']}"}
    barrier = Barrier(2)

    def competing(request):
        barrier.wait(timeout=10)
        target, headers = request
        return change(target, headers=headers).status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(competing, [(3, admin), (1, second)]))
    assert sorted(outcomes) == [200, 401], outcomes
    with factory() as session:
        active = session.query(User).filter(User.role == "ADMIN", User.is_suspended.is_(False)).all()
        assert len(active) == 1
        winner_id = active[0].id
    winner = admin if winner_id == UUID(int=1) else second
    loser = 3 if winner_id == UUID(int=1) else 1
    assert change(loser, headers=winner, status="ACTIVE", expected="SUSPENDED").status_code == 200
    # Return to the fixture's single-admin browser baseline without touching public.
    with factory() as session:
        session.get(User, UUID(int=3)).role = "CUSTOMER"
        session.commit()
    print("PASS PostgreSQL: competing administrators cannot suspend each other; one remains active", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-only", action="store_true", help="Run checks and clean up without starting a server")
    args = parser.parse_args()
    preflight = read_only_preflight()
    print(f"Verified PostgreSQL {preflight.postgresql_version}; public revision={preflight.alembic_revision}", flush=True)
    url = validate_test_database_url(read_test_database_url())
    control = create_engine(url)
    baseline = public_fingerprint(control)
    schema = f"aura_admin_acceptance_{uuid4().hex}"
    # Search path deliberately omits public: missing fixture tables must fail,
    # rather than falling back to existing data in the approved test database.
    scoped_url = url.set(query={"options": f"-csearch_path={schema}"})
    engine = None
    created = False
    credentials_written = False
    output = ROOT / "Admin" / ".wrangler" / "admin-fixture-credentials.json"
    try:
        with control.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        created = True
        migration_settings.database_url = scoped_url.render_as_string(hide_password=False)
        config = Config(str(ROOT / "backend" / "alembic.ini"))
        command.upgrade(config, "a8d3f1c6b2e7")
        engine = create_engine(scoped_url)
        with engine.begin() as connection:
            connection.execute(text("INSERT INTO users (id) VALUES (:id)"), {"id": UUID(int=99)})
        command.upgrade(config, "head")
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT role FROM users WHERE id = :id"), {"id": UUID(int=99)}) == "CUSTOMER"
            assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "b0c2d4e6f8a1"
            assert connection.scalar(text("SELECT is_suspended FROM users WHERE id = :id"), {"id": UUID(int=99)}) is False
            assert connection.scalar(text("SELECT auth_version FROM users WHERE id = :id"), {"id": UUID(int=99)}) == 0
        print("PASS PostgreSQL: migration chain to head preserves existing customer role", flush=True)
        settings.database_url = scoped_url.render_as_string(hide_password=False)
        settings.market_data_worker_database_url = None
        settings.jwt_secret_key = SecretStr(token_urlsafe(48))
        settings.access_token_expire_minutes = 30
        settings.aura_llm_provider = settings.aura_llm_model = None
        settings.openai_api_key = settings.groq_api_key = None
        settings.debug = False
        from app.main import app

        factory = sessionmaker(bind=engine, expire_on_commit=False)
        password = token_urlsafe(24)
        seed(factory, password)

        def isolated_session():
            with factory() as session:
                yield session

        app.dependency_overrides[get_database_session] = isolated_session
        check_http(app, password, factory)
        if not args.check_only:
            output.parent.mkdir(exist_ok=True)
            output.write_text(json.dumps({"admin": "admin@example.com", "customer": "customer00@example.com", "password": password}), encoding="utf-8")
            credentials_written = True
            print("PostgreSQL acceptance ready on http://127.0.0.1:8019 (isolated schema)", flush=True)
            uvicorn.run(app, host="127.0.0.1", port=8019, log_level="warning")
    finally:
        if engine is not None:
            engine.dispose()
        if created:
            with control.begin() as connection:
                # Generated schema name only; never a public or user input name.
                connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
            if credentials_written:
                output.unlink(missing_ok=True)
            with control.connect() as connection:
                assert connection.scalar(text("SELECT count(*) FROM pg_namespace WHERE nspname = :schema"), {"schema": schema}) == 0
            print("PASS cleanup: disposable PostgreSQL schema removed; run credentials cleared", flush=True)
        assert public_fingerprint(control) == baseline, "Existing public database data changed during verification"
        print("PASS preservation: public table inventory and row fingerprints unchanged", flush=True)
        control.dispose()


if __name__ == "__main__":
    main()
