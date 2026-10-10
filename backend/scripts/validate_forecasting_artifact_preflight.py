"""Read-only official forecasting artifact preflight validation."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
import json
from pathlib import Path
import sys

from sqlalchemy.exc import SQLAlchemyError


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPOSITORY_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.forecasting.artifacts import (
    OFFICIAL_ARTIFACT_VERSION,
    ArtifactPreflight,
    build_artifact_preflight,
    preflight_json,
    read_git_revision_state,
)
from app.forecasting.fingerprints import verification_from_dict
from app.forecasting.selection_manifest import (
    OFFICIAL_EVALUATION_CUTOFF,
    selection_manifest_from_dict,
)
from backend.scripts.fingerprint_forecasting_market_data import (
    DatabaseEnvironmentError,
    database_url_from_env_file,
    fingerprint_persisted_market_data,
)


OFFICIAL_ARTIFACT_ROOT = (
    REPOSITORY_ROOT
    / "backend"
    / "artifacts"
    / "forecasting"
    / OFFICIAL_ARTIFACT_VERSION
)


def validate_preflight(
    *,
    env_file: Path,
    database_url_key: str = "DATABASE_URL",
    verification_path: Path,
    selection_manifest_path: Path,
    artifact_root: Path = OFFICIAL_ARTIFACT_ROOT,
) -> ArtifactPreflight:
    selection = selection_manifest_from_dict(
        json.loads(selection_manifest_path.read_text(encoding="utf-8"))
    )
    verification = verification_from_dict(
        json.loads(verification_path.read_text(encoding="utf-8"))
    )
    fingerprint = fingerprint_persisted_market_data(
        database_url=database_url_from_env_file(
            env_file, database_url_key=database_url_key
        ),
        evaluation_cutoff=OFFICIAL_EVALUATION_CUTOFF,
    )
    return build_artifact_preflight(
        artifact_root=artifact_root,
        artifact_version=OFFICIAL_ARTIFACT_VERSION,
        selection_manifest=selection,
        verification=verification,
        fingerprint=fingerprint,
        git_state=read_git_revision_state(REPOSITORY_ROOT),
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate official forecasting artifact inputs without fitting."
    )
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--database-url-key", default="DATABASE_URL")
    parser.add_argument("--verification", type=Path, required=True)
    parser.add_argument("--selection-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = _build_parser().parse_args(argv)
    try:
        preflight = validate_preflight(
            env_file=args.env_file,
            database_url_key=args.database_url_key,
            verification_path=args.verification,
            selection_manifest_path=args.selection_manifest,
        )
        args.output.write_text(preflight_json(preflight), encoding="utf-8")
    except DatabaseEnvironmentError as error:
        raise SystemExit(
            f"Forecasting artifact preflight failed: {error}"
        ) from None
    except (
        OSError,
        SQLAlchemyError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
    ):
        raise SystemExit(
            "Forecasting artifact preflight failed: input or database validation failed."
        ) from None
    print("Aura forecasting artifact preflight passed.")
    print(f"Artifact version: {preflight.artifact_version}")
    print(f"Git commit: {preflight.git_commit}")
    print(f"Output: {args.output}")


if __name__ == "__main__":
    main()
