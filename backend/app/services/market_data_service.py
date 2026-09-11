"""Storage coordination and pure conversion for prepared market data."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

import pandas as pd
from sqlalchemy.orm import Session

from ..core.instruments import (
    InstrumentType,
    USD_THB_FX_SYMBOL,
    get_instrument_metadata,
)
from ..database.models import MarketData
from ..database.repositories import MarketDataRepository


_CANONICAL_COLUMNS: tuple[str, ...] = (
    "date",
    "symbol",
    "adjusted_close",
    "volume",
    "source",
)
_ADJUSTED_CLOSE_QUANTUM = Decimal("0.000000000001")
_DEFAULT_BATCH_SIZE = 1_000
MAX_LATEST_OBSERVATION_AGE_DAYS = 4


class MarketDataUnavailableError(ValueError):
    """Raised when a current market observation is unusable or unavailable."""


def validate_latest_market_observation(
    observation: MarketData | None,
    *,
    symbol: str,
    requested_date: date,
) -> MarketData:
    """Return one positive, finite observation no more than four days old."""
    if observation is None:
        raise MarketDataUnavailableError(
            f"latest market data is unavailable for {symbol}"
        )
    if observation.symbol != symbol:
        raise MarketDataUnavailableError(
            f"latest market data symbol mismatch for {symbol}"
        )
    if observation.date > requested_date:
        raise MarketDataUnavailableError(
            f"latest market data is after the requested date for {symbol}"
        )

    age_days = (requested_date - observation.date).days
    if age_days > MAX_LATEST_OBSERVATION_AGE_DAYS:
        raise MarketDataUnavailableError(
            f"latest market data is stale for {symbol}"
        )

    adjusted_close = observation.adjusted_close
    if (
        not isinstance(adjusted_close, Decimal)
        or not adjusted_close.is_finite()
        or adjusted_close <= 0
    ):
        raise MarketDataUnavailableError(
            f"latest market data price is invalid for {symbol}"
        )
    return observation


def _to_market_data_records(data: pd.DataFrame) -> list[dict[str, object]]:
    """Return repository-ready records from validated canonical rows."""
    records: list[dict[str, object]] = []
    canonical_rows = data.loc[:, _CANONICAL_COLUMNS].itertuples(
        index=False,
        name=None,
    )

    for observation_date, symbol, adjusted_close, volume, source in canonical_rows:
        records.append(
            {
                "symbol": symbol,
                "date": observation_date.date(),
                "adjusted_close": Decimal(str(adjusted_close)).quantize(
                    _ADJUSTED_CLOSE_QUANTUM,
                    rounding=ROUND_HALF_UP,
                ),
                "volume": None if pd.isna(volume) else int(volume),
                "source": source,
            }
        )

    return records


class MarketDataService:
    """Coordinate market-data persistence within a caller-owned session."""

    def __init__(self, session: Session) -> None:
        self._repository = MarketDataRepository(session)

    def store(self, data: pd.DataFrame) -> int:
        """Submit validated canonical rows in bounded repository batches."""
        records = _to_market_data_records(data)
        stored_count = 0

        for start in range(0, len(records), _DEFAULT_BATCH_SIZE):
            batch = records[start : start + _DEFAULT_BATCH_SIZE]
            stored_count += self._repository.upsert_many(batch)

        return stored_count

    def get_range(
        self,
        symbols: Sequence[str],
        start_date: date,
        end_date: date,
    ) -> list[MarketData]:
        """Return the repository's inclusive ordered historical range."""
        return self._repository.get_range(symbols, start_date, end_date)

    def get_latest_valid_observations(
        self,
        symbols: Sequence[str],
        requested_date: date,
    ) -> list[MarketData]:
        """Return fresh observations in de-duplicated requested order."""
        selected_symbols = tuple(dict.fromkeys(symbols))
        rows = self._repository.get_latest_on_or_before(
            selected_symbols,
            requested_date,
        )
        rows_by_symbol = {row.symbol: row for row in rows}
        return [
            validate_latest_market_observation(
                rows_by_symbol.get(symbol),
                symbol=symbol,
                requested_date=requested_date,
            )
            for symbol in selected_symbols
        ]

    def get_latest_usd_asset_observations(
        self,
        symbols: Sequence[str],
        requested_date: date,
    ) -> list[MarketData]:
        """Return fresh rows for approved USD-quoted user assets only."""
        provider_symbols: list[str] = []
        for symbol in tuple(dict.fromkeys(symbols)):
            metadata = get_instrument_metadata(symbol)
            if (
                metadata.instrument_type is not InstrumentType.ASSET
                or metadata.quote_currency != "USD"
            ):
                raise ValueError(
                    f"market instrument is not a USD user asset: {symbol}"
                )
            provider_symbols.append(metadata.provider_symbol)
        return self.get_latest_valid_observations(
            provider_symbols,
            requested_date,
        )

    def get_latest_usd_thb_fx_observation(
        self,
        requested_date: date,
    ) -> MarketData:
        """Return fresh THB-per-USD data without performing conversion."""
        metadata = get_instrument_metadata(USD_THB_FX_SYMBOL)
        if (
            metadata.instrument_type is not InstrumentType.FX
            or metadata.base_currency != "USD"
            or metadata.quote_currency != "THB"
        ):
            raise RuntimeError("USD/THB instrument metadata is invalid")
        return self.get_latest_valid_observations(
            [metadata.provider_symbol],
            requested_date,
        )[0]
