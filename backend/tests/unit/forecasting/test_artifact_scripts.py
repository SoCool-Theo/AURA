from contextlib import contextmanager
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.exc import SQLAlchemyError

import backend.scripts.fingerprint_forecasting_market_data as fingerprint_script
import backend.scripts.validate_forecasting_artifact_preflight as preflight_script
import backend.scripts.train_forecasting_artifacts as training_script
from backend.app.forecasting.fingerprints import build_market_data_fingerprint


def test_fingerprint_database_path_is_read_only() -> None:
    engine = MagicMock()
    factory = MagicMock()
    session = MagicMock()
    service = MagicMock()
    service.get_range.return_value = [
        SimpleNamespace(
            symbol="AAPL",
            date=date(2026, 9, 17),
            adjusted_close=Decimal("100"),
            volume=100,
            source="synthetic",
        )
    ]

    @contextmanager
    def fake_scope(selected_factory):
        assert selected_factory is factory
        yield session

    with (
        patch.object(
            fingerprint_script,
            "USER_ASSET_SYMBOLS",
            ("AAPL",),
        ),
        patch.object(
            fingerprint_script,
            "create_database_engine",
            return_value=engine,
        ) as create_engine,
        patch.object(
            fingerprint_script,
            "create_session_factory",
            return_value=factory,
        ),
        patch.object(
            fingerprint_script,
            "session_scope",
            side_effect=fake_scope,
        ),
        patch.object(
            fingerprint_script,
            "MarketDataService",
            return_value=service,
        ),
    ):
        result = fingerprint_script.fingerprint_persisted_market_data(
            database_url="postgresql+psycopg://hidden",
            evaluation_cutoff=date(2026, 9, 17),
        )

    create_engine.assert_called_once_with("postgresql+psycopg://hidden")
    service.get_range.assert_called_once_with(
        ("AAPL",), date.min, date(2026, 9, 17)
    )
    session.commit.assert_not_called()
    session.add.assert_not_called()
    session.delete.assert_not_called()
    engine.dispose.assert_called_once_with()
    assert result.total_row_count == 1


def test_environment_file_loader_never_requires_printing_secret(tmp_path: Path) -> None:
    env_file = tmp_path / ".env.local"
    env_file.write_text(
        "DATABASE_URL=postgresql+psycopg://user:secret@localhost/aura\n",
        encoding="utf-8",
    )

    value = fingerprint_script.database_url_from_env_file(env_file)

    assert value.endswith("@localhost/aura")


@pytest.mark.parametrize("key", ["DATABASE_URL", "TEST_DATABASE_URL"])
def test_requested_database_key_is_selected_without_fallback(tmp_path, key, monkeypatch):
    env_file = tmp_path / ".env.synthetic"
    env_file.write_text(
        "DATABASE_URL=postgresql+psycopg://supabase:synthetic-secret@supabase/aura\n"
        "TEST_DATABASE_URL=postgresql+psycopg://docker:synthetic-secret@localhost/aura\n",
        encoding="utf-8",
    )
    monkeypatch.setenv(key, "postgresql+psycopg://unrequested/process")
    selected = fingerprint_script.database_url_from_env_file(
        env_file, database_url_key=key
    )
    assert ("supabase:" if key == "DATABASE_URL" else "docker:") in selected


@pytest.mark.parametrize("key", ["DATABASE_URL", "TEST_DATABASE_URL"])
def test_missing_requested_key_names_key_and_never_falls_back(tmp_path, key, monkeypatch):
    other_key = "TEST_DATABASE_URL" if key == "DATABASE_URL" else "DATABASE_URL"
    env_file = tmp_path / ".env.synthetic"
    env_file.write_text(f"{other_key}=postgresql+psycopg://user:secret@host/aura\n")
    monkeypatch.setenv(key, "postgresql+psycopg://process:secret@host/aura")
    with pytest.raises(fingerprint_script.DatabaseEnvironmentError) as caught:
        fingerprint_script.database_url_from_env_file(env_file, database_url_key=key)
    assert key in str(caught.value)
    assert "secret" not in str(caught.value)
    assert "postgresql" not in str(caught.value)


def test_fingerprint_cli_key_does_not_change_content_or_expose_url(tmp_path, capsys):
    fingerprint = build_market_data_fingerprint(
        [SimpleNamespace(symbol="AAPL", date=date(2026, 9, 17),
                         adjusted_close=Decimal("100"), volume=100, source="synthetic")],
        evaluation_cutoff=date(2026, 9, 17), symbols=("AAPL",),
    )
    outputs = []
    for key in ("DATABASE_URL", "TEST_DATABASE_URL"):
        env_file = tmp_path / f".env.{key}"
        url = f"postgresql+psycopg://user:synthetic-secret@{key.lower()}/aura"
        env_file.write_text(f"{key}={url}\n", encoding="utf-8")
        output = tmp_path / f"{key}.json"
        args = ["--env-file", str(env_file), "--evaluation-cutoff", "2026-09-17",
                "--output", str(output)]
        if key == "TEST_DATABASE_URL":
            args += ["--database-url-key", key]
        with patch.object(fingerprint_script, "fingerprint_persisted_market_data",
                          return_value=fingerprint) as mocked:
            fingerprint_script.main(args)
        mocked.assert_called_once_with(database_url=url, evaluation_cutoff=date(2026, 9, 17))
        outputs.append(output.read_text(encoding="utf-8"))
    assert outputs[0] == outputs[1]
    combined = capsys.readouterr().out + "".join(outputs)
    assert "synthetic-secret" not in combined
    assert "postgresql" not in combined
    assert "DATABASE_URL" not in outputs[0]


def test_fingerprint_cli_missing_key_is_safe_and_never_connects(tmp_path):
    env_file = tmp_path / ".env.synthetic"
    env_file.write_text("DATABASE_URL=postgresql+psycopg://user:secret@host/aura\n")
    with patch.object(fingerprint_script, "fingerprint_persisted_market_data") as mocked:
        with pytest.raises(SystemExit, match="TEST_DATABASE_URL") as caught:
            fingerprint_script.main([
                "--env-file", str(env_file), "--database-url-key", "TEST_DATABASE_URL",
                "--evaluation-cutoff", "2026-09-17", "--output", str(tmp_path / "out.json"),
            ])
    mocked.assert_not_called()
    assert "secret" not in str(caught.value)
    assert caught.value.__suppress_context__


@pytest.mark.parametrize("script, operation, args", [
    (fingerprint_script, "fingerprint_persisted_market_data",
     ["--evaluation-cutoff", "2026-09-17", "--output", "unused.json"]),
    (preflight_script, "validate_preflight",
     ["--verification", "unused.json", "--selection-manifest", "unused.json", "--output", "unused.json"]),
    (training_script, "run_official_artifact_generation",
     ["--verification", "unused.json", "--selection-manifest", "unused.json", "--preflight", "unused.json"]),
])
@pytest.mark.parametrize("error_type", [SQLAlchemyError, ValueError])
def test_workflow_cli_errors_do_not_expose_connection_details(tmp_path, capsys, script, operation, args, error_type):
    env_file = tmp_path / ".env.synthetic"
    url = "postgresql+psycopg://user:synthetic-secret@host/aura"
    env_file.write_text(f"TEST_DATABASE_URL={url}\n")
    with patch.object(script, operation, side_effect=error_type(url)) as mocked:
        with pytest.raises(SystemExit) as caught:
            script.main(["--env-file", str(env_file), "--database-url-key", "TEST_DATABASE_URL", *args])
    if script is not fingerprint_script:
        assert mocked.call_args.kwargs["database_url_key"] == "TEST_DATABASE_URL"
    captured = capsys.readouterr()
    rendered = str(caught.value) + captured.out + captured.err
    assert "synthetic-secret" not in rendered
    assert "postgresql" not in rendered
    assert caught.value.__suppress_context__


def test_manual_artifact_scripts_have_no_provider_or_write_workflow() -> None:
    scripts = (
        "backend/scripts/fingerprint_forecasting_market_data.py",
        "backend/scripts/compare_forecasting_market_data_fingerprints.py",
        "backend/scripts/freeze_forecasting_selection.py",
        "backend/scripts/validate_forecasting_artifact_preflight.py",
        "backend/scripts/train_forecasting_artifacts.py",
    )
    source = "\n".join(
        Path(script).read_text(encoding="utf-8").casefold()
        for script in scripts
    )

    assert "yfinance" not in source
    assert "update_market_data" not in source
    assert "backfill" not in source
    assert "--force" not in source
    assert "marketdatarepository" not in source
    assert ".commit(" not in source
    assert ".add(" not in source
    assert ".delete(" not in source


def test_joblib_is_already_a_direct_pinned_requirement() -> None:
    requirements = Path("backend/requirements.txt").read_text(encoding="utf-16")
    assert "joblib==1.6.0" in requirements.splitlines()
