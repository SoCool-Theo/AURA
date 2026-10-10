"""Local UI acceptance only: real Aura routers with disposable in-memory data.

Never connects to PostgreSQL or calls an AI/market provider. Generates fresh
synthetic login credentials under ignored Admin/.wrangler on each launch.
"""

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from secrets import token_urlsafe
from threading import Lock
import sys
from uuid import UUID

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from fastapi import FastAPI  # noqa: E402
from pydantic import SecretStr  # noqa: E402
from sqlalchemy import JSON, MetaData, create_engine  # noqa: E402
from sqlalchemy.dialects.postgresql import JSONB  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402
import uvicorn  # noqa: E402

from app.api.dependencies import get_database_session  # noqa: E402
from app.api.routes import admin, auth  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.database.models import (  # noqa: E402
    AIRequestLog, Analysis, AuditLog, MarketData, MarketDataRefreshState,
    Portfolio, Simulation, User,
)

settings.database_url = None
settings.market_data_worker_database_url = None
settings.jwt_secret_key = SecretStr(token_urlsafe(48))
settings.access_token_expire_minutes = 30
settings.aura_llm_provider = None
settings.aura_llm_model = None
settings.openai_api_key = settings.groq_api_key = None
engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
metadata = MetaData()
for model in [User, Portfolio, Analysis, Simulation, MarketData, MarketDataRefreshState, AuditLog, AIRequestLog]:
    copied = model.__table__.to_metadata(metadata)
    for column in copied.columns:
        if isinstance(column.type, JSONB):
            column.type = JSON()
metadata.create_all(engine)
factory = sessionmaker(bind=engine, expire_on_commit=False)
password = token_urlsafe(24)
encoded = hash_password(password)
now = datetime.now(UTC)
with factory() as session:
    session.add(User(id=UUID(int=1), email="admin@example.com", display_name="Synthetic Admin", password_hash=encoded, role="ADMIN"))
    session.add_all([User(id=UUID(int=index + 2), email=f"customer{index:02d}@example.com", display_name=f"Synthetic Customer {index:02d}", password_hash=encoded, role="CUSTOMER") for index in range(30)])
    session.add(User(id=UUID(int=99), display_name="Synthetic Legacy", role="CUSTOMER"))
    portfolio = Portfolio(id=UUID(int=100), user_id=UUID(int=2), name="Synthetic Portfolio", portfolio_type="CURRENT")
    session.add(portfolio)
    session.flush()
    session.add_all([Analysis(portfolio_id=portfolio.id, start_date=now.date() - timedelta(days=60), end_date=now.date(), schema_version="synthetic", result_snapshot={}, created_at=now - timedelta(days=index)) for index in range(8)])
    session.add(MarketData(symbol="AAPL", date=now.date(), adjusted_close=Decimal("123.45678901"), volume=1000, source="Synthetic"))
    session.add(AuditLog(actor_kind="OPERATOR", actor_user_id=None, action="ADMIN_BOOTSTRAPPED", target_type="USER", target_id=UUID(int=1), details={"previous_role": "CUSTOMER", "new_role": "ADMIN"}))
    session.add(AIRequestLog(started_at=now, duration_ms=1.25, outcome="REFUSED", http_status=200, provider_kind=None, provider_called=False, refusal_stage="INPUT", guardrail_reason="investment_advice", error_code=None, has_portfolio_source=False, has_report_source=False, has_simulation_source=False, limitation_count=0))
    session.commit()

app = FastAPI(debug=False)
app.include_router(auth.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
session_lock = Lock()

def synthetic_session():
    # StaticPool shares one in-memory SQLite connection. Browser requests run
    # concurrently, unlike sequential TestClient fixtures, so serialize reads.
    # A plain Lock can be released by FastAPI's dependency-cleanup worker.
    with session_lock, factory() as session:
        yield session

app.dependency_overrides[get_database_session] = synthetic_session
output = ROOT / "Admin" / ".wrangler"
output.mkdir(exist_ok=True)
(output / "admin-fixture-credentials.json").write_text(json.dumps({"admin": "admin@example.com", "customer": "customer00@example.com", "password": password}), encoding="utf-8")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8019, log_level="warning")
