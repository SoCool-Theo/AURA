"""Role acceptance inside the guarded fixture; never edits public accounts."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import UUID

from sqlalchemy import select

from app.database.models import User


def check_user_roles(client, factory, password):
    def login(email):
        response = client.post("/api/auth/login", json={"email": email, "password": password})
        assert response.status_code == 200
        return {"Authorization": f"Bearer {response.json()['access_token']}"}
    def change(target, role="ADMIN", expected="CUSTOMER", headers=None):
        return client.patch(f"/api/admin/users/{UUID(int=target)}/role", headers=headers or admin,
                            json={"role": role, "expected_role": expected})
    admin = login("admin@example.com")
    customer = login("customer00@example.com")
    assert change(2, headers=customer).status_code == 403
    assert change(1, role="CUSTOMER", expected="ADMIN").status_code == 409
    assert change(99).status_code == 409  # Credentialless legacy owner.
    assert change(2).status_code == 200
    assert client.get("/api/admin/me", headers=customer).status_code == 401
    promoted = login("customer00@example.com")
    assert client.get("/api/admin/me", headers=promoted).status_code == 200
    assert change(2).status_code == 200  # No duplicate transition/audit.
    assert change(2, role="CUSTOMER", expected="ADMIN").status_code == 200
    assert client.get("/api/admin/me", headers=promoted).status_code == 401
    assert client.get("/api/admin/me", headers=login("customer00@example.com")).status_code == 403
    audit = client.get("/api/admin/audit-logs", headers=admin, params={"action": "USER_ROLE_CHANGED", "target_id": str(UUID(int=2))}).json()
    assert audit["total"] == 2
    assert {tuple(item["details"].values()) for item in audit["items"]} == {("CUSTOMER", "ADMIN"), ("ADMIN", "CUSTOMER")}
    assert change(3).status_code == 200
    other_admin = login("customer01@example.com")
    barrier = Barrier(2)
    def compete(item):
        target, headers = item
        barrier.wait(timeout=10)
        return change(target, role="CUSTOMER", expected="ADMIN", headers=headers)
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(compete, [(3, admin), (1, other_admin)]))
    assert sorted(response.status_code for response in outcomes) == [200, 401]
    with factory() as session:
        remaining = session.scalars(select(User.id).where(User.role == "ADMIN", User.is_suspended.is_(False))).all()
        assert len(remaining) == 1
    winner = login("admin@example.com" if remaining[0] == UUID(int=1) else "customer01@example.com")
    loser = 3 if remaining[0] == UUID(int=1) else 1
    assert change(loser, headers=winner).status_code == 200
    # Restore the browser fixture's intended sole administrator using the API.
    restored_admin = login("admin@example.com")
    assert change(3, role="CUSTOMER", expected="ADMIN", headers=restored_admin).status_code == 200
    with factory() as session:
        assert session.get(User, UUID(int=1)).role == "ADMIN"
        assert session.get(User, UUID(int=2)).role == "CUSTOMER"
        assert session.get(User, UUID(int=3)).role == "CUSTOMER"
    print("PASS PostgreSQL roles: real promotion/demotion, fresh login, idempotent audit and competing demotions leave one active administrator", flush=True)
