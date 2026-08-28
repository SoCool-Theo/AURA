"""Pure coverage auditing for historical market-data backfills."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime

import pandas as pd

from .providers.market_provider import _coerce_date, _normalize_symbols
from .validator import REQUIRED_COLUMNS, raise_if_invalid


@dataclass(frozen=True, slots=True)
class HistoricalSymbolCoverage:
    """Observed coverage for one normalized requested symbol."""

    symbol: str
    row_count: int
    earliest_date: date | None
    latest_date: date | None


@dataclass(frozen=True, slots=True)
class HistoricalCoverageAudit:
    """Complete observed coverage for one inclusive backfill request."""

    requested_start_date: date
    requested_end_date: date
    coverage: tuple[HistoricalSymbolCoverage, ...]


class HistoricalCoverageError(ValueError):
    """Raised when returned rows do not safely account for the request."""


def _normalize_optional_symbols(symbols: Iterable[str]) -> tuple[str, ...]:
    selected_symbols = tuple(symbols)
    if not selected_symbols:
        return ()
    return tuple(_normalize_symbols(selected_symbols))


def _raise_coverage_errors(errors: list[str]) -> None:
    if errors:
        details = "\n".join(f"- {error}" for error in errors)
        raise HistoricalCoverageError(
            f"Historical market-data coverage audit failed:\n{details}"
        )


def audit_historical_coverage(
    requested_symbols: Iterable[str],
    start_date: date | datetime | str,
    end_date: date | datetime | str,
    data: pd.DataFrame,
    *,
    failed_symbols: Iterable[str] = (),
) -> HistoricalCoverageAudit:
    """Audit canonical rows against one inclusive historical request.

    The function reports observed coverage only. It does not infer why a
    symbol begins late or ends early, and it never repairs or clips data.
    """
    normalized_symbols = tuple(_normalize_symbols(requested_symbols))
    normalized_failed_symbols = _normalize_optional_symbols(failed_symbols)
    requested_start = _coerce_date(start_date, "start_date")
    requested_end = _coerce_date(end_date, "end_date")
    if requested_start > requested_end:
        raise ValueError("start_date must be on or before end_date")

    if not isinstance(data, pd.DataFrame):
        raise_if_invalid(data)

    missing_columns = [
        column for column in REQUIRED_COLUMNS if column not in data.columns
    ]
    if missing_columns:
        raise ValueError(
            "Market data validation failed:\n"
            f"- Missing required columns: {missing_columns}"
        )
    if not data.empty:
        raise_if_invalid(data)

    accounting_data = data.loc[:, ["date", "symbol"]].copy(deep=True)
    accounting_data["date"] = pd.to_datetime(
        accounting_data["date"],
        errors="coerce",
    ).dt.date

    requested_set = set(normalized_symbols)
    returned_symbols = tuple(
        accounting_data["symbol"].astype(str).drop_duplicates().tolist()
    )
    unexpected_returned = sorted(set(returned_symbols) - requested_set)
    unexpected_failed = sorted(
        set(normalized_failed_symbols) - requested_set
    )

    coverage: list[HistoricalSymbolCoverage] = []
    for symbol in normalized_symbols:
        symbol_dates = accounting_data.loc[
            accounting_data["symbol"] == symbol,
            "date",
        ]
        coverage.append(
            HistoricalSymbolCoverage(
                symbol=symbol,
                row_count=int(len(symbol_dates)),
                earliest_date=(
                    min(symbol_dates) if not symbol_dates.empty else None
                ),
                latest_date=(
                    max(symbol_dates) if not symbol_dates.empty else None
                ),
            )
        )

    errors: list[str] = []
    if unexpected_returned:
        errors.append(
            "Returned data contains unexpected symbols: "
            f"{', '.join(unexpected_returned)}."
        )
    if unexpected_failed:
        errors.append(
            "Provider failure metadata contains unrequested symbols: "
            f"{', '.join(unexpected_failed)}."
        )

    failed_set = set(normalized_failed_symbols)
    requested_failures = [
        symbol for symbol in normalized_symbols if symbol in failed_set
    ]
    if requested_failures:
        errors.append(
            "Provider reported failures for requested symbols: "
            f"{', '.join(requested_failures)}."
        )

    unresolved_symbols = [
        item.symbol for item in coverage if item.row_count == 0
    ]
    if unresolved_symbols:
        errors.append(
            "Requested symbols with zero returned rows: "
            f"{', '.join(unresolved_symbols)}."
        )

    for item in coverage:
        if (
            item.earliest_date is not None
            and item.earliest_date < requested_start
        ):
            errors.append(
                f"Returned observations for {item.symbol} begin before "
                f"requested start date {requested_start.isoformat()}: "
                f"{item.earliest_date.isoformat()}."
            )
        if item.latest_date is not None and item.latest_date > requested_end:
            errors.append(
                f"Returned observations for {item.symbol} end after "
                f"requested end date {requested_end.isoformat()}: "
                f"{item.latest_date.isoformat()}."
            )

    _raise_coverage_errors(errors)
    return HistoricalCoverageAudit(
        requested_start_date=requested_start,
        requested_end_date=requested_end,
        coverage=tuple(coverage),
    )
