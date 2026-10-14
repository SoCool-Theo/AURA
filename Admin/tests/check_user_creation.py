"""Account creation acceptance, only inside the guarded disposable schema."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.core.security import verify_password
from app.database.models import AuditLog, User
from app.services.audit_log_service import AuditLogService


def check_user_creation(client, factory, password):
    def login(email):
        response = client.post("/api/auth/login", json={"email": email, "password": password})
        assert response.status_code == 200
        return {"Authorization": f"Bearer {response.json()['access_token']}"}
    admin, customer = login("admin@example.com"), login("customer00@example.com")
    def create(email="created@example.com", headers=admin, **extra):
        return client.post("/api/admin/users", headers=headers, json={"email": email, "password": password, **extra})
    assert create(headers={}).status_code == 401
    assert create(headers=customer).status_code == 403
    invalid = create(password="short", role="ADMIN")
    assert invalid.status_code == 422 and invalid.json() == {"detail": "Invalid account details"}
    response = create(email=" Created@Example.COM ", display_name=" Synthetic Created User ")
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "created@example.com" and data["display_name"] == "Synthetic Created User"
    assert (data["role"], data["account_type"], data["status"], data["portfolio_count"]) == ("CUSTOMER", "REGISTERED", "ACTIVE", 0)
    assert password not in response.text and "password_hash" not in response.text
    assert create().status_code == 409
    created = login("created@example.com")
    assert client.get("/api/auth/me", headers=created).status_code == 200
    assert client.get("/api/admin/me", headers=created).status_code == 403
    with factory() as session:
        stored = session.get(User, UUID(data["id"]))
        assert verify_password(password, stored.password_hash) and stored.password_hash != password
        assert stored.role == "CUSTOMER" and stored.auth_version == 0 and not stored.is_suspended
    barrier = Barrier(2)
    def compete(_):
        barrier.wait(timeout=10)
        return create(email="race-created@example.com")
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(compete, range(2)))
    assert sorted(response.status_code for response in outcomes) == [201, 409]
    with factory() as session:
        assert len(session.scalars(select(User).where(User.email == "race-created@example.com")).all()) == 1
    with patch.object(AuditLogService, "record", side_effect=SQLAlchemyError("synthetic private failure")):
        failed = create(email="rollback-created@example.com")
    assert failed.status_code == 503 and failed.json() == {"detail": "Account creation unavailable"}
    with factory() as session:
        assert session.scalars(select(User).where(User.email == "rollback-created@example.com")).first() is None
        events = session.scalars(select(AuditLog).where(AuditLog.action == "USER_CREATED")).all()
        assert len(events) == 2
        assert all(event.actor_user_id == UUID(int=1) and event.details == {"role": "CUSTOMER", "account_type": "REGISTERED"} for event in events)
    audit = client.get("/api/admin/audit-logs", headers=admin, params={"action": "USER_CREATED"})
    assert audit.status_code == 200 and password not in audit.text and data["email"] not in audit.text
    print("PASS PostgreSQL account creation: safe customer defaults, shared login, canonical duplicate race, private audit and atomic rollback", flush=True)
