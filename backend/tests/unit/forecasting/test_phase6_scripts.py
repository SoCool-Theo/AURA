from contextlib import contextmanager
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

import backend.scripts.fingerprint_forecasting_market_data as fingerprint_script


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


def test_phase6_manual_scripts_have_no_provider_or_write_workflow() -> None:
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
