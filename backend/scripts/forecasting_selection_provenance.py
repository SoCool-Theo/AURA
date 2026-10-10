"""Offline selection-only provenance gate using the canonical fingerprint."""

import argparse
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
import re

from app.core.instruments import USER_ASSET_SYMBOLS
from app.forecasting.fingerprints import build_market_data_fingerprint
from backend.scripts.fingerprint_forecasting_market_data import (
    DatabaseEnvironmentError, database_url_from_env_file,
)


class SelectionProvenanceError(ValueError):
    """Safe expected-dataset validation failure; never contains connection data."""


@dataclass(frozen=True, slots=True)
class SelectionDataProvenance:
    provenance_verified: bool
    evaluation_cutoff: date
    symbol_count: int
    row_count: int
    market_data_fingerprint_sha256: str


def validate_explicit_database_url(database_url: str) -> None:
    """Prevent a None URL from selecting application settings implicitly."""
    if not isinstance(database_url, str) or not database_url.strip():
        raise SelectionProvenanceError("an explicit database URL is required")


def validate_expectations(
    expected_fingerprint: str | None, expected_row_count: int | None,
) -> None:
    if (expected_fingerprint is None) != (expected_row_count is None):
        raise SelectionProvenanceError("expected fingerprint and row count must be supplied together")
    if expected_fingerprint is not None and (
        not isinstance(expected_fingerprint, str)
        or re.fullmatch(r"[0-9a-fA-F]{64}", expected_fingerprint) is None
    ):
        raise SelectionProvenanceError("expected market-data fingerprint must be a SHA-256 hex digest")
    if expected_row_count is not None and (
        type(expected_row_count) is not int or expected_row_count <= 0
    ):
        raise SelectionProvenanceError("expected row count must be a positive integer")


def verify_selection_records(
    records: Sequence[object], *, evaluation_cutoff: date,
    expected_fingerprint: str | None, expected_row_count: int | None,
) -> SelectionDataProvenance:
    validate_expectations(expected_fingerprint, expected_row_count)
    fingerprint = build_market_data_fingerprint(
        records, evaluation_cutoff=evaluation_cutoff, symbols=USER_ASSET_SYMBOLS,
    )
    verified = expected_fingerprint is not None
    if verified and (
        fingerprint.sha256 != expected_fingerprint.lower()
        or fingerprint.total_row_count != expected_row_count
    ):
        raise SelectionProvenanceError("market-data provenance mismatch: fingerprint or row count differs from expectation")
    return SelectionDataProvenance(
        verified, fingerprint.evaluation_cutoff, len(fingerprint.symbols),
        fingerprint.total_row_count, fingerprint.sha256,
    )


def provenance_payload(
    provenance: SelectionDataProvenance | None, *, evaluation_cutoff: date,
) -> dict[str, object]:
    if provenance is None:
        # Pure history-based developer/test calls lack canonical volume/source.
        return {
            "provenance_verified": False,
            "evaluation_cutoff": evaluation_cutoff.isoformat(),
            "symbol_count": None,
            "row_count": None,
            "market_data_fingerprint_sha256": None,
        }
    payload = asdict(provenance)
    payload["evaluation_cutoff"] = provenance.evaluation_cutoff.isoformat()
    return payload


def add_provenance_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--env-file", type=Path, required=True,
                        help="Environment file containing the explicitly selected database URL.")
    parser.add_argument("--database-url-key", default="DATABASE_URL",
                        help="Read only this key from --env-file; no fallback.")
    parser.add_argument("--expected-market-data-fingerprint",
                        help="Expected canonical SHA-256; supply together with --expected-row-count.")
    parser.add_argument("--expected-row-count", type=int,
                        help="Expected persisted row count; both expected values enable verification.")
