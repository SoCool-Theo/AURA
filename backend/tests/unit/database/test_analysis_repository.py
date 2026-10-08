import copy
import importlib
from datetime import UTC, date, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.database.models import Analysis
from backend.app.database.repositories import AnalysisRepository
import backend.app.database.repositories.analysis_repository as repository_module


def _snapshot() -> dict[str, object]:
    return {
        "portfolio_name": "Core",
        "metrics": {
            "maximum_drawdown": -0.25,
            "sharpe_ratio": None,
        },
        "risk_drivers": [
            {"symbol": "AAPL", "contribution": -0.1},
        ],
    }


def test_save_snapshot_uses_injected_session_without_owning_transaction() -> None:
    session = MagicMock(spec=Session)
    portfolio_id = uuid4()
    start = date(2025, 1, 1)
    end = date(2025, 12, 31)

    analysis = AnalysisRepository(session).save_snapshot(
        portfolio_id=portfolio_id,
        start_date=start,
        end_date=end,
        schema_version="1.0",
        result_snapshot=_snapshot(),
    )

    session.add.assert_called_once_with(analysis)
    session.flush.assert_called_once_with()
    session.commit.assert_not_called()
    session.rollback.assert_not_called()
    session.close.assert_not_called()
    assert analysis.portfolio_id == portfolio_id
    assert analysis.start_date == start
    assert analysis.end_date == end
    assert analysis.schema_version == "1.0"


def test_repository_import_does_not_create_engine_or_connect() -> None:
    with (
        patch("sqlalchemy.create_engine") as create_database_engine,
        patch("psycopg.connect") as connect,
    ):
        importlib.reload(repository_module)

    create_database_engine.assert_not_called()
    connect.assert_not_called()
    assert not any(
        isinstance(value, Session)
        for value in vars(repository_module).values()
    )


def test_snapshot_is_copied_without_mutating_or_aliasing_caller_input() -> None:
    session = MagicMock(spec=Session)
    snapshot = _snapshot()
    original = copy.deepcopy(snapshot)

    analysis = AnalysisRepository(session).save_snapshot(
        portfolio_id=uuid4(),
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
        schema_version="1.0",
        result_snapshot=snapshot,
    )

    assert snapshot == original
    assert analysis.result_snapshot == snapshot
    assert analysis.result_snapshot is not snapshot
    assert analysis.result_snapshot["metrics"] is not snapshot["metrics"]
    assert analysis.result_snapshot["risk_drivers"] is not snapshot[
        "risk_drivers"
    ]

    snapshot["metrics"]["maximum_drawdown"] = 0.0  # type: ignore[index]
    snapshot["risk_drivers"][0]["symbol"] = "CHANGED"  # type: ignore[index]

    assert analysis.result_snapshot["metrics"]["maximum_drawdown"] == -0.25
    assert analysis.result_snapshot["risk_drivers"][0]["symbol"] == "AAPL"


def test_get_existing_and_missing_analysis() -> None:
    session = MagicMock(spec=Session)
    analysis_id = uuid4()
    existing = Analysis(
        id=analysis_id,
        portfolio_id=uuid4(),
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
        schema_version="1.0",
        result_snapshot=_snapshot(),
    )
    session.get.side_effect = [existing, None]
    repository = AnalysisRepository(session)

    assert repository.get_by_id(analysis_id) is existing
    assert repository.get_by_id(uuid4()) is None


def test_delete_existing_analysis_without_owning_transaction() -> None:
    session = MagicMock(spec=Session)
    analysis_id = uuid4()
    unrelated = Analysis(
        id=uuid4(),
        portfolio_id=uuid4(),
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
        schema_version="1.0",
        result_snapshot={"portfolio_name": "Unrelated"},
    )
    existing = Analysis(
        id=analysis_id,
        portfolio_id=uuid4(),
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
        schema_version="1.0",
        result_snapshot=_snapshot(),
    )
    original_snapshot = copy.deepcopy(existing.result_snapshot)
    session.get.return_value = existing

    result = AnalysisRepository(session).delete(analysis_id)

    assert result is True
    session.get.assert_called_once_with(Analysis, analysis_id)
    session.delete.assert_called_once_with(existing)
    assert session.delete.call_args.args[0] is not unrelated
    session.flush.assert_called_once_with()
    session.commit.assert_not_called()
    session.rollback.assert_not_called()
    session.close.assert_not_called()
    assert existing.result_snapshot == original_snapshot


def test_delete_missing_analysis_returns_false_without_mutation() -> None:
    session = MagicMock(spec=Session)
    analysis_id = uuid4()
    session.get.return_value = None

    result = AnalysisRepository(session).delete(analysis_id)

    assert result is False
    session.get.assert_called_once_with(Analysis, analysis_id)
    session.delete.assert_not_called()
    session.flush.assert_not_called()
    session.commit.assert_not_called()
    session.rollback.assert_not_called()
    session.close.assert_not_called()


def test_delete_failure_propagates_without_owning_transaction() -> None:
    session = MagicMock(spec=Session)
    analysis_id = uuid4()
    analysis = MagicMock(spec=Analysis)
    failure = SQLAlchemyError("analysis delete failed")
    session.get.return_value = analysis
    session.flush.side_effect = failure

    with pytest.raises(SQLAlchemyError) as raised:
        AnalysisRepository(session).delete(analysis_id)

    assert raised.value is failure
    session.delete.assert_called_once_with(analysis)
    session.commit.assert_not_called()
    session.rollback.assert_not_called()
    session.close.assert_not_called()


def test_list_for_portfolio_filters_and_orders_newest_first() -> None:
    session = MagicMock(spec=Session)
    expected = [MagicMock(spec=Analysis), MagicMock(spec=Analysis)]
    session.scalars.return_value.all.return_value = expected
    portfolio_id = uuid4()

    result = AnalysisRepository(session).list_for_portfolio(portfolio_id)

    assert result == expected
    statement = session.scalars.call_args.args[0]
    compiled = statement.compile(dialect=postgresql.dialect())
    sql = str(compiled)
    assert "WHERE analyses.portfolio_id = %(portfolio_id_1)s::UUID" in sql
    assert "ORDER BY analyses.created_at DESC, analyses.id" in sql
    assert compiled.params == {"portfolio_id_1": portfolio_id}


def test_list_returns_session_result_without_reordering() -> None:
    session = MagicMock(spec=Session)
    newest = Analysis(
        id=uuid4(),
        portfolio_id=uuid4(),
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
        schema_version="1.0",
        result_snapshot={},
        created_at=datetime(2026, 2, 1, tzinfo=UTC),
    )
    older = Analysis(
        id=uuid4(),
        portfolio_id=newest.portfolio_id,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
        schema_version="1.0",
        result_snapshot={},
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    session.scalars.return_value.all.return_value = [newest, older]

    result = AnalysisRepository(session).list_for_portfolio(
        newest.portfolio_id
    )

    assert result == [newest, older]


def test_repository_exposes_no_snapshot_update_operation() -> None:
    method_names = set(dir(AnalysisRepository))

    assert "update_snapshot" not in method_names
    assert "replace_snapshot" not in method_names
    assert "update" not in method_names


def test_sqlalchemy_failure_propagates_without_rollback_or_commit() -> None:
    session = MagicMock(spec=Session)
    failure = SQLAlchemyError("snapshot write failed")
    session.flush.side_effect = failure

    with pytest.raises(SQLAlchemyError) as raised:
        AnalysisRepository(session).save_snapshot(
            portfolio_id=uuid4(),
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            schema_version="1.0",
            result_snapshot=_snapshot(),
        )

    assert raised.value is failure
    session.commit.assert_not_called()
    session.rollback.assert_not_called()
    session.close.assert_not_called()


def test_repository_has_no_analytics_or_pydantic_schema_dependency() -> None:
    source = Path(repository_module.__file__).read_text(encoding="utf-8")

    assert "analytics" not in source
    assert "pydantic" not in source
    assert "schemas" not in source
