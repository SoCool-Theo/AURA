"""Deterministic fingerprints for frozen forecasting market-data slices."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
import hashlib
import json
from numbers import Integral


FINGERPRINT_SCHEMA_VERSION = "forecast-market-data-fingerprint-v1"
FINGERPRINT_VERIFICATION_SCHEMA_VERSION = (
    "forecast-market-data-verification-v1"
)
CANONICAL_MARKET_DATA_FIELDS: tuple[str, ...] = (
    "symbol",
    "date",
    "adjusted_close",
    "volume",
    "source",
)
_PRICE_QUANTUM = Decimal("0.000000000001")


class ForecastFingerprintError(ValueError):
    """Raised when fingerprint input or comparison metadata is invalid."""


@dataclass(frozen=True, slots=True)
class SymbolFingerprintSummary:
    symbol: str
    row_count: int
    minimum_date: date | None
    maximum_date: date | None


@dataclass(frozen=True, slots=True)
class ForecastMarketDataFingerprint:
    schema_version: str
    evaluation_cutoff: date
    symbols: tuple[str, ...]
    canonical_fields: tuple[str, ...]
    total_row_count: int
    symbol_summaries: tuple[SymbolFingerprintSummary, ...]
    sha256: str


@dataclass(frozen=True, slots=True)
class ForecastFingerprintVerification:
    schema_version: str
    evaluation_cutoff: date
    symbols: tuple[str, ...]
    authoritative_sha256: str
    local_sha256: str
    authoritative_total_row_count: int
    local_total_row_count: int
    matches: bool
    mismatch_fields: tuple[str, ...]
    verification_sha256: str


def canonical_json_bytes(value: object) -> bytes:
    """Serialize JSON deterministically without accepting NaN or Infinity."""
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_price(value: object) -> str:
    if isinstance(value, bool):
        raise ForecastFingerprintError("adjusted_close must be numeric")
    try:
        normalized = Decimal(str(value)).quantize(_PRICE_QUANTUM)
    except (InvalidOperation, ValueError, TypeError) as error:
        raise ForecastFingerprintError(
            "adjusted_close must be a finite decimal"
        ) from error
    if not normalized.is_finite() or normalized <= 0:
        raise ForecastFingerprintError(
            "adjusted_close must be positive and finite"
        )
    return format(normalized, ".12f")


def _canonical_volume(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise ForecastFingerprintError("volume must be an integer or null")
    normalized = int(value)
    if normalized < 0:
        raise ForecastFingerprintError("volume must be non-negative")
    return normalized


def _canonical_row(record: object) -> dict[str, object]:
    try:
        symbol = record.symbol
        observation_date = record.date
        adjusted_close = record.adjusted_close
        volume = record.volume
        source = record.source
    except AttributeError as error:
        raise ForecastFingerprintError(
            "market-data rows must expose every canonical fingerprint field"
        ) from error
    if not isinstance(symbol, str) or not symbol:
        raise ForecastFingerprintError("market-data symbol must be non-empty")
    if type(observation_date) is not date:
        raise ForecastFingerprintError("market-data date must be a date")
    if not isinstance(source, str) or not source:
        raise ForecastFingerprintError("market-data source must be non-empty")
    return {
        "symbol": symbol,
        "date": observation_date.isoformat(),
        "adjusted_close": _canonical_price(adjusted_close),
        "volume": _canonical_volume(volume),
        "source": source,
    }


def build_market_data_fingerprint(
    records: Iterable[object],
    *,
    evaluation_cutoff: date,
    symbols: Sequence[str],
) -> ForecastMarketDataFingerprint:
    """Hash an ordered canonical view independent of retrieval order."""
    if type(evaluation_cutoff) is not date:
        raise ForecastFingerprintError("evaluation_cutoff must be a date")
    normalized_symbols = tuple(sorted(symbols))
    if not normalized_symbols or len(set(normalized_symbols)) != len(
        normalized_symbols
    ):
        raise ForecastFingerprintError("fingerprint symbols must be unique")
    allowed = frozenset(normalized_symbols)
    canonical_rows = tuple(_canonical_row(record) for record in records)
    if any(row["symbol"] not in allowed for row in canonical_rows):
        raise ForecastFingerprintError(
            "fingerprint rows contain a symbol outside the approved set"
        )
    if any(
        date.fromisoformat(str(row["date"])) > evaluation_cutoff
        for row in canonical_rows
    ):
        raise ForecastFingerprintError(
            "fingerprint rows cannot exceed the evaluation cutoff"
        )
    ordered_rows = tuple(
        sorted(canonical_rows, key=lambda row: (row["symbol"], row["date"]))
    )
    keys = tuple((row["symbol"], row["date"]) for row in ordered_rows)
    if len(set(keys)) != len(keys):
        raise ForecastFingerprintError(
            "fingerprint rows contain duplicate symbol/date observations"
        )

    summaries: list[SymbolFingerprintSummary] = []
    for symbol in normalized_symbols:
        dates = tuple(
            date.fromisoformat(str(row["date"]))
            for row in ordered_rows
            if row["symbol"] == symbol
        )
        summaries.append(
            SymbolFingerprintSummary(
                symbol=symbol,
                row_count=len(dates),
                minimum_date=None if not dates else dates[0],
                maximum_date=None if not dates else dates[-1],
            )
        )

    hash_payload = {
        "schema_version": FINGERPRINT_SCHEMA_VERSION,
        "evaluation_cutoff": evaluation_cutoff.isoformat(),
        "symbols": list(normalized_symbols),
        "canonical_fields": list(CANONICAL_MARKET_DATA_FIELDS),
        "rows": list(ordered_rows),
    }
    return ForecastMarketDataFingerprint(
        schema_version=FINGERPRINT_SCHEMA_VERSION,
        evaluation_cutoff=evaluation_cutoff,
        symbols=normalized_symbols,
        canonical_fields=CANONICAL_MARKET_DATA_FIELDS,
        total_row_count=len(ordered_rows),
        symbol_summaries=tuple(summaries),
        sha256=sha256_bytes(canonical_json_bytes(hash_payload)),
    )


def _fingerprint_payload(
    fingerprint: ForecastMarketDataFingerprint,
) -> dict[str, object]:
    payload = asdict(fingerprint)
    payload["evaluation_cutoff"] = fingerprint.evaluation_cutoff.isoformat()
    payload["symbols"] = list(fingerprint.symbols)
    payload["canonical_fields"] = list(fingerprint.canonical_fields)
    payload["symbol_summaries"] = [
        {
            "symbol": summary.symbol,
            "row_count": summary.row_count,
            "minimum_date": (
                None
                if summary.minimum_date is None
                else summary.minimum_date.isoformat()
            ),
            "maximum_date": (
                None
                if summary.maximum_date is None
                else summary.maximum_date.isoformat()
            ),
        }
        for summary in fingerprint.symbol_summaries
    ]
    return payload


def fingerprint_json(fingerprint: ForecastMarketDataFingerprint) -> str:
    return json.dumps(
        _fingerprint_payload(fingerprint),
        allow_nan=False,
        indent=2,
        sort_keys=True,
    ) + "\n"


def fingerprint_from_dict(payload: object) -> ForecastMarketDataFingerprint:
    if not isinstance(payload, dict):
        raise ForecastFingerprintError("fingerprint payload must be an object")
    try:
        summaries = tuple(
            SymbolFingerprintSummary(
                symbol=item["symbol"],
                row_count=item["row_count"],
                minimum_date=(
                    None
                    if item["minimum_date"] is None
                    else date.fromisoformat(item["minimum_date"])
                ),
                maximum_date=(
                    None
                    if item["maximum_date"] is None
                    else date.fromisoformat(item["maximum_date"])
                ),
            )
            for item in payload["symbol_summaries"]
        )
        fingerprint = ForecastMarketDataFingerprint(
            schema_version=payload["schema_version"],
            evaluation_cutoff=date.fromisoformat(payload["evaluation_cutoff"]),
            symbols=tuple(payload["symbols"]),
            canonical_fields=tuple(payload["canonical_fields"]),
            total_row_count=payload["total_row_count"],
            symbol_summaries=summaries,
            sha256=payload["sha256"],
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ForecastFingerprintError("fingerprint payload is malformed") from error
    if fingerprint.schema_version != FINGERPRINT_SCHEMA_VERSION:
        raise ForecastFingerprintError("unsupported fingerprint schema version")
    if fingerprint.canonical_fields != CANONICAL_MARKET_DATA_FIELDS:
        raise ForecastFingerprintError("unexpected fingerprint canonical fields")
    if (
        not fingerprint.symbols
        or fingerprint.symbols != tuple(sorted(fingerprint.symbols))
        or len(set(fingerprint.symbols)) != len(fingerprint.symbols)
        or tuple(item.symbol for item in summaries) != fingerprint.symbols
    ):
        raise ForecastFingerprintError("fingerprint symbol metadata is invalid")
    if (
        type(fingerprint.total_row_count) is not int
        or fingerprint.total_row_count < 0
        or any(
            type(item.row_count) is not int
            or item.row_count < 0
            or (item.minimum_date is None) != (item.maximum_date is None)
            or (
                item.minimum_date is not None
                and (
                    item.minimum_date > item.maximum_date
                    or item.maximum_date > fingerprint.evaluation_cutoff
                )
            )
            for item in summaries
        )
        or sum(item.row_count for item in summaries)
        != fingerprint.total_row_count
    ):
        raise ForecastFingerprintError("fingerprint row counts are invalid")
    if len(fingerprint.sha256) != 64:
        raise ForecastFingerprintError("fingerprint SHA-256 is invalid")
    return fingerprint


def compare_market_data_fingerprints(
    authoritative: ForecastMarketDataFingerprint,
    local: ForecastMarketDataFingerprint,
) -> ForecastFingerprintVerification:
    """Compare all identity metadata and hashes without database mutation."""
    comparisons = {
        "schema_version": (
            authoritative.schema_version == local.schema_version
        ),
        "evaluation_cutoff": (
            authoritative.evaluation_cutoff == local.evaluation_cutoff
        ),
        "symbols": authoritative.symbols == local.symbols,
        "canonical_fields": (
            authoritative.canonical_fields == local.canonical_fields
        ),
        "total_row_count": (
            authoritative.total_row_count == local.total_row_count
        ),
        "symbol_summaries": (
            authoritative.symbol_summaries == local.symbol_summaries
        ),
        "sha256": authoritative.sha256 == local.sha256,
    }
    mismatch_fields = tuple(
        name for name, matches in comparisons.items() if not matches
    )
    base = {
        "schema_version": FINGERPRINT_VERIFICATION_SCHEMA_VERSION,
        "evaluation_cutoff": authoritative.evaluation_cutoff.isoformat(),
        "symbols": list(authoritative.symbols),
        "authoritative_sha256": authoritative.sha256,
        "local_sha256": local.sha256,
        "authoritative_total_row_count": authoritative.total_row_count,
        "local_total_row_count": local.total_row_count,
        "matches": not mismatch_fields,
        "mismatch_fields": list(mismatch_fields),
    }
    return ForecastFingerprintVerification(
        schema_version=FINGERPRINT_VERIFICATION_SCHEMA_VERSION,
        evaluation_cutoff=authoritative.evaluation_cutoff,
        symbols=authoritative.symbols,
        authoritative_sha256=authoritative.sha256,
        local_sha256=local.sha256,
        authoritative_total_row_count=authoritative.total_row_count,
        local_total_row_count=local.total_row_count,
        matches=not mismatch_fields,
        mismatch_fields=mismatch_fields,
        verification_sha256=sha256_bytes(canonical_json_bytes(base)),
    )


def verification_json(verification: ForecastFingerprintVerification) -> str:
    payload = asdict(verification)
    payload["evaluation_cutoff"] = verification.evaluation_cutoff.isoformat()
    payload["symbols"] = list(verification.symbols)
    payload["mismatch_fields"] = list(verification.mismatch_fields)
    return json.dumps(payload, allow_nan=False, indent=2, sort_keys=True) + "\n"


def verification_from_dict(payload: object) -> ForecastFingerprintVerification:
    if not isinstance(payload, dict):
        raise ForecastFingerprintError("verification payload must be an object")
    try:
        verification = ForecastFingerprintVerification(
            schema_version=payload["schema_version"],
            evaluation_cutoff=date.fromisoformat(payload["evaluation_cutoff"]),
            symbols=tuple(payload["symbols"]),
            authoritative_sha256=payload["authoritative_sha256"],
            local_sha256=payload["local_sha256"],
            authoritative_total_row_count=payload[
                "authoritative_total_row_count"
            ],
            local_total_row_count=payload["local_total_row_count"],
            matches=payload["matches"],
            mismatch_fields=tuple(payload["mismatch_fields"]),
            verification_sha256=payload["verification_sha256"],
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ForecastFingerprintError(
            "verification payload is malformed"
        ) from error
    if (
        verification.schema_version
        != FINGERPRINT_VERIFICATION_SCHEMA_VERSION
        or type(verification.matches) is not bool
        or len(verification.authoritative_sha256) != 64
        or len(verification.local_sha256) != 64
        or len(verification.verification_sha256) != 64
    ):
        raise ForecastFingerprintError("verification contract is invalid")
    base = {
        "schema_version": verification.schema_version,
        "evaluation_cutoff": verification.evaluation_cutoff.isoformat(),
        "symbols": list(verification.symbols),
        "authoritative_sha256": verification.authoritative_sha256,
        "local_sha256": verification.local_sha256,
        "authoritative_total_row_count": (
            verification.authoritative_total_row_count
        ),
        "local_total_row_count": verification.local_total_row_count,
        "matches": verification.matches,
        "mismatch_fields": list(verification.mismatch_fields),
    }
    if (
        sha256_bytes(canonical_json_bytes(base))
        != verification.verification_sha256
    ):
        raise ForecastFingerprintError("verification hash mismatch")
    if verification.matches and (
        verification.mismatch_fields
        or verification.authoritative_sha256 != verification.local_sha256
        or verification.authoritative_total_row_count
        != verification.local_total_row_count
    ):
        raise ForecastFingerprintError("verification match claim is invalid")
    return verification
