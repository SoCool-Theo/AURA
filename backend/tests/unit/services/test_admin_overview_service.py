from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

from pydantic import ValidationError
import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session

from backend.app.database.repositories.admin_overview_repository import AdminOverviewRepository
from backend.app.schemas.admin import AdminUsersQuery
import backend.app.services.admin_overview_service as module


@pytest.mark.parametrize("query", [
    {"limit": 0}, {"limit": 101}, {"offset": -1}, {"offset": 10001},
    {"role": "OWNER"}, {"account_type": "ACTIVE"}, {"q": "x" * 101},
])
def test_internal_user_queries_are_validated_before_database(query: dict) -> None:
    constructed = AdminUsersQuery.model_construct(**query)
    with patch.object(module, "AdminOverviewRepository") as repository:
        with pytest.raises(ValidationError):
            module.AdminOverviewService(MagicMock(spec=Session)).list_users(constructed)
    repository.return_value.list_users.assert_not_called()


def test_postgresql_dashboard_uses_explicit_utc_buckets_without_result_payloads() -> None:
    session = MagicMock(spec=Session)
    session.get_bind.return_value.dialect.name = "postgresql"
    today = datetime(2026, 10, 10, tzinfo=UTC)
    AdminOverviewRepository(session).dashboard(
        today=today, tomorrow=today + timedelta(days=1),
        yesterday=today - timedelta(days=1), week_start=today - timedelta(days=6),
        window_start=today - timedelta(days=29),
    )
    statement = session.execute.call_args.args[0]
    sql = str(statement.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
    # A session-local timezone must not change any of the four day buckets.
    for table in ["users", "portfolios", "analyses", "simulations"]:
        assert f"CAST(timezone('UTC', {table}.created_at) AS DATE)" in sql
    assert "password_hash" not in sql and "result_snapshot" not in sql
    session.execute.assert_called_once()
    session.commit.assert_not_called()
    session.flush.assert_not_called()


def test_postgresql_directory_projects_safe_columns_and_binds_literal_search() -> None:
    session = MagicMock(spec=Session)
    session.execute.return_value.mappings.return_value.all.return_value = [{"id": None, "total": 0}]
    rows, total = AdminOverviewRepository(session).list_users(limit=25, offset=0, q="%_/' OR 1=1 --")
    assert rows == [] and total == 0
    compiled = session.execute.call_args.args[0].compile(dialect=postgresql.dialect())
    sql = str(compiled)
    assert "password_hash" not in sql and "phone_number" not in sql
    assert "OR 1=1" not in sql
    assert any("/%/_//" in str(value) for value in compiled.params.values())
    session.execute.assert_called_once()
