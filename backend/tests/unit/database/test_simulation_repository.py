import copy
import importlib
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.database.models import Simulation
from backend.app.database.repositories import SimulationRepository
import backend.app.database.repositories.simulation_repository as repository_module


def _snapshot() -> dict[str, object]:
    return {"metrics": {"drawdown": -0.2}, "returns": [0.1, None]}


def _create(repository: SimulationRepository) -> Simulation:
    return repository.create(
        portfolio_id=uuid4(),
        simulation_type="historical-scenario",
        scenario_id="covid-crash",
        requested_start_date=date(2020, 2, 1),
        requested_end_date=date(2020, 4, 30),
        schema_version="1.0",
        result_snapshot=_snapshot(),
    )


def test_create_adds_flushes_returns_and_does_not_own_transaction() -> None:
    session = MagicMock(spec=Session)

    simulation = _create(SimulationRepository(session))

    session.add.assert_called_once_with(simulation)
    session.flush.assert_called_once_with()
    session.commit.assert_not_called()
    session.rollback.assert_not_called()
    session.close.assert_not_called()
    assert simulation.simulation_type == "historical-scenario"
    assert simulation.scenario_id == "covid-crash"
    assert simulation.schema_version == "1.0"


def test_create_defensively_copies_snapshot_without_mutating_input() -> None:
    session = MagicMock(spec=Session)
    snapshot = _snapshot()
    original = copy.deepcopy(snapshot)

    simulation = SimulationRepository(session).create(
        portfolio_id=uuid4(),
        simulation_type="allocation",
        scenario_id=None,
        requested_start_date=date(2026, 1, 1),
        requested_end_date=date(2026, 1, 31),
        schema_version="1.0",
        result_snapshot=snapshot,
    )

    assert snapshot == original
    assert simulation.result_snapshot == snapshot
    assert simulation.result_snapshot is not snapshot
    assert simulation.result_snapshot["metrics"] is not snapshot["metrics"]
    snapshot["metrics"]["drawdown"] = 0.0  # type: ignore[index]
    assert simulation.result_snapshot["metrics"]["drawdown"] == -0.2


def test_repository_import_does_not_connect_or_create_engine() -> None:
    with (
        patch("sqlalchemy.create_engine") as create_engine,
        patch("psycopg.connect") as connect,
    ):
        importlib.reload(repository_module)

    create_engine.assert_not_called()
    connect.assert_not_called()


def test_list_for_portfolio_is_scoped_and_deterministically_ordered() -> None:
    session = MagicMock(spec=Session)
    expected = [MagicMock(spec=Simulation), MagicMock(spec=Simulation)]
    session.scalars.return_value.all.return_value = expected
    portfolio_id = uuid4()

    result = SimulationRepository(session).list_for_portfolio(portfolio_id)

    assert result == expected
    statement = session.scalars.call_args.args[0]
    compiled = statement.compile(dialect=postgresql.dialect())
    sql = str(compiled)
    assert "WHERE simulations.portfolio_id = %(portfolio_id_1)s::UUID" in sql
    assert "ORDER BY simulations.created_at DESC, simulations.id" in sql
    assert compiled.params == {"portfolio_id_1": portfolio_id}


def test_get_for_portfolio_scopes_both_identifiers_and_returns_none() -> None:
    session = MagicMock(spec=Session)
    session.scalar.return_value = None
    portfolio_id = uuid4()
    simulation_id = uuid4()

    result = SimulationRepository(session).get_for_portfolio(
        portfolio_id=portfolio_id,
        simulation_id=simulation_id,
    )

    assert result is None
    statement = session.scalar.call_args.args[0]
    compiled = statement.compile(dialect=postgresql.dialect())
    sql = str(compiled)
    assert "simulations.portfolio_id = %(portfolio_id_1)s::UUID" in sql
    assert "simulations.id = %(id_1)s::UUID" in sql
    assert compiled.params == {
        "portfolio_id_1": portfolio_id,
        "id_1": simulation_id,
    }


def test_repository_exposes_no_update_or_transaction_methods() -> None:
    method_names = set(dir(SimulationRepository))
    assert {"update", "replace", "commit", "delete"}.isdisjoint(method_names)


def test_sqlalchemy_failure_propagates_without_transaction_cleanup() -> None:
    session = MagicMock(spec=Session)
    failure = SQLAlchemyError("write failed")
    session.flush.side_effect = failure

    with pytest.raises(SQLAlchemyError) as raised:
        _create(SimulationRepository(session))

    assert raised.value is failure
    session.commit.assert_not_called()
    session.rollback.assert_not_called()
    session.close.assert_not_called()


def test_repository_has_no_schema_or_service_dependency() -> None:
    source = Path(repository_module.__file__).read_text(encoding="utf-8")
    assert "pydantic" not in source
    assert "schemas" not in source
    assert "services" not in source
