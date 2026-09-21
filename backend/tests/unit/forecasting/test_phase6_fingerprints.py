from datetime import date
from decimal import Decimal
import json
from types import SimpleNamespace

import pytest

from backend.app.forecasting.fingerprints import (
    ForecastFingerprintError,
    build_market_data_fingerprint,
    compare_market_data_fingerprints,
    fingerprint_from_dict,
    fingerprint_json,
    verification_from_dict,
    verification_json,
)


SYMBOLS = ("AAPL", "MSFT")
CUTOFF = date(2026, 9, 17)


def _row(
    symbol: str,
    observation_date: date,
    price: str,
    *,
    volume=100,
    source="yahoo",
):
    return SimpleNamespace(
        symbol=symbol,
        date=observation_date,
        adjusted_close=Decimal(price),
        volume=volume,
        source=source,
    )


def _rows():
    return (
        _row("MSFT", date(2026, 9, 16), "200.5", volume=None),
        _row("AAPL", date(2026, 9, 15), "100.000000000001"),
        _row("AAPL", date(2026, 9, 16), "101.25", volume=200),
    )


def _fingerprint(rows=None):
    return build_market_data_fingerprint(
        _rows() if rows is None else rows,
        evaluation_cutoff=CUTOFF,
        symbols=SYMBOLS,
    )


def test_fingerprint_is_order_independent_and_round_trips() -> None:
    first = _fingerprint()
    second = _fingerprint(tuple(reversed(_rows())))

    assert first == second
    assert first.total_row_count == 3
    assert first.symbols == ("AAPL", "MSFT")
    assert first.evaluation_cutoff == CUTOFF
    assert first.canonical_fields == (
        "symbol",
        "date",
        "adjusted_close",
        "volume",
        "source",
    )
    assert fingerprint_from_dict(json.loads(fingerprint_json(first))) == first


@pytest.mark.parametrize(
    "changed",
    (
        (_row("AAPL", date(2026, 9, 14), "200.5"), *_rows()[1:]),
        (_rows()[0], _row("AAPL", date(2026, 9, 14), "100"), _rows()[2]),
        (_rows()[0], _row("AAPL", date(2026, 9, 15), "99"), _rows()[2]),
        (_rows()[0], _row("AAPL", date(2026, 9, 15), "100", volume=999), _rows()[2]),
        (_rows()[0], _row("AAPL", date(2026, 9, 15), "100", source="other"), _rows()[2]),
    ),
)
def test_relevant_persisted_value_changes_hash(changed) -> None:
    assert _fingerprint(changed).sha256 != _fingerprint().sha256


def test_fingerprint_json_contains_no_credentials() -> None:
    payload = fingerprint_json(_fingerprint()).casefold()

    assert "password" not in payload
    assert "database_url" not in payload
    assert "api_key" not in payload
    assert "postgresql+psycopg" not in payload


def test_matching_fingerprints_pass_and_verification_round_trips() -> None:
    fingerprint = _fingerprint()
    verification = compare_market_data_fingerprints(fingerprint, fingerprint)

    assert verification.matches
    assert verification.mismatch_fields == ()
    assert verification_from_dict(
        json.loads(verification_json(verification))
    ) == verification


def test_mismatched_fingerprints_fail_comparison() -> None:
    authoritative = _fingerprint()
    local = _fingerprint(
        (*_rows()[:2], _row("AAPL", date(2026, 9, 16), "102", volume=200))
    )
    verification = compare_market_data_fingerprints(authoritative, local)

    assert not verification.matches
    assert "sha256" in verification.mismatch_fields


def test_tampered_verification_is_rejected() -> None:
    verification = compare_market_data_fingerprints(_fingerprint(), _fingerprint())
    payload = json.loads(verification_json(verification))
    payload["local_total_row_count"] += 1

    with pytest.raises(ForecastFingerprintError, match="hash mismatch"):
        verification_from_dict(payload)
