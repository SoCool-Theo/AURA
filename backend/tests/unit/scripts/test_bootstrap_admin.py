from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

import backend.scripts.bootstrap_admin as module


@pytest.mark.parametrize("arguments,code", [
    (["--user-id", str(uuid4())], 2),
    (["--user-id", "invalid", "--apply"], 2),
    (["--help"], 0),
])
def test_non_applying_cli_paths_never_open_database(arguments, code):
    with patch.object(module, "create_database_engine") as create:
        with pytest.raises(SystemExit) as error:
            module.main(arguments)
    assert error.value.code == code
    create.assert_not_called()


def test_bootstrap_commits_once_and_disposes_engine():
    user_id = uuid4()
    engine, session, service = MagicMock(), MagicMock(), MagicMock()
    with (
        patch.object(module, "create_database_engine", return_value=engine),
        patch.object(module, "create_session_factory", return_value=lambda: session),
        patch.object(module, "AdminAccessService", return_value=service),
    ):
        module.main(["--user-id", str(user_id), "--apply"])
    service.bootstrap_first_admin.assert_called_once_with(user_id)
    session.commit.assert_called_once()
    session.rollback.assert_not_called()
    session.close.assert_called_once()
    engine.dispose.assert_called_once()


@pytest.mark.parametrize("failure", [module.AdminBootstrapError("bootstrap is closed"), RuntimeError("private database details")])
def test_bootstrap_failure_rolls_back_and_cleans_up(failure):
    engine, session, service = MagicMock(), MagicMock(), MagicMock()
    service.bootstrap_first_admin.side_effect = failure
    with (
        patch.object(module, "create_database_engine", return_value=engine),
        patch.object(module, "create_session_factory", return_value=lambda: session),
        patch.object(module, "AdminAccessService", return_value=service),
    ):
        with pytest.raises(SystemExit) as error:
            module.main(["--user-id", str(uuid4()), "--apply"])
    assert "private database details" not in str(error.value)
    session.commit.assert_not_called()
    session.rollback.assert_called_once()
    session.close.assert_called_once()
    engine.dispose.assert_called_once()
