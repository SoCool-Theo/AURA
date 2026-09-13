"""Caller-transaction-owned persistence operations for Aura portfolios."""

from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from typing import TypeAlias
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..models import Holding, Portfolio, PortfolioType


HoldingReplacement: TypeAlias = tuple[str, Decimal]
RealHoldingReplacement: TypeAlias = tuple[
    str,
    Decimal,
    str,
    Decimal,
    date,
]
PlannedHoldingReplacement: TypeAlias = tuple[str, Decimal]

_EXPECTED_TOTAL_WEIGHT = Decimal("1.0")
_TOTAL_WEIGHT_TOLERANCE = Decimal("1e-9")


class PortfolioTypeConflictError(ValueError):
    """Raised when an operation conflicts with persisted portfolio intent."""


class PortfolioRepository:
    """Persist portfolios within a caller-owned SQLAlchemy session."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        user_id: UUID,
        name: str,
        portfolio_type: str = PortfolioType.CURRENT.value,
        plan_currency: str | None = None,
        source_plan_id: UUID | None = None,
    ) -> Portfolio:
        """Add and flush a portfolio without committing the transaction."""
        self._validate_portfolio_context(
            portfolio_type=portfolio_type,
            plan_currency=plan_currency,
            source_plan_id=source_plan_id,
        )
        portfolio = Portfolio(
            user_id=user_id,
            name=name,
            portfolio_type=portfolio_type,
            plan_currency=plan_currency,
            source_plan_id=source_plan_id,
        )
        self._session.add(portfolio)
        self._session.flush()
        return portfolio

    def get_by_id(self, portfolio_id: UUID) -> Portfolio | None:
        """Return a portfolio by primary key, or ``None`` when absent."""
        return self._session.get(Portfolio, portfolio_id)

    def get_with_holdings(self, portfolio_id: UUID) -> Portfolio | None:
        """Return one portfolio with its position-ordered holdings loaded."""
        statement = (
            select(Portfolio)
            .options(selectinload(Portfolio.holdings))
            .where(Portfolio.id == portfolio_id)
        )
        return self._session.scalars(statement).one_or_none()

    def list_for_user(self, user_id: UUID) -> list[Portfolio]:
        """Return a user's portfolios in deterministic creation order."""
        statement = (
            select(Portfolio)
            .where(Portfolio.user_id == user_id)
            .order_by(Portfolio.created_at, Portfolio.id)
        )
        return list(self._session.scalars(statement).all())

    def rename(
        self,
        portfolio_id: UUID,
        name: str,
    ) -> Portfolio | None:
        """Rename an existing portfolio without normalizing or committing."""
        portfolio = self.get_by_id(portfolio_id)
        if portfolio is None:
            return None

        portfolio.name = name
        self._session.flush()
        return portfolio

    def replace_holdings(
        self,
        portfolio_id: UUID,
        holdings: Sequence[HoldingReplacement],
    ) -> list[Holding] | None:
        """Replace holdings in input order within the caller's transaction."""
        replacements = tuple(
            (symbol, weight) for symbol, weight in holdings
        )
        self._validate_total_weight(replacements)

        portfolio = self.get_with_holdings(portfolio_id)
        if portfolio is None:
            return None
        if portfolio.portfolio_type != PortfolioType.LEGACY.value:
            raise PortfolioTypeConflictError(
                "saved weights can replace only legacy portfolio holdings"
            )

        new_holdings = [
            Holding(symbol=symbol, weight=weight, position=position)
            for position, (symbol, weight) in enumerate(replacements)
        ]

        portfolio.holdings.clear()
        self._session.flush()
        portfolio.holdings.extend(new_holdings)
        self._session.flush()
        return new_holdings

    def replace_real_holdings(
        self,
        portfolio_id: UUID,
        holdings: Sequence[RealHoldingReplacement],
    ) -> list[Holding] | None:
        """Replace holdings with complete real rows in caller input order."""
        replacements = tuple(
            (
                symbol,
                invested_amount,
                invested_currency,
                shares,
                purchase_date,
            )
            for (
                symbol,
                invested_amount,
                invested_currency,
                shares,
                purchase_date,
            ) in holdings
        )
        self._validate_unique_symbols(
            [replacement[0] for replacement in replacements]
        )

        portfolio = self.get_with_holdings(portfolio_id)
        if portfolio is None:
            return None
        if portfolio.portfolio_type == PortfolioType.PLANNED.value:
            raise PortfolioTypeConflictError(
                "current holdings cannot replace planned portfolio holdings"
            )
        if portfolio.portfolio_type not in {
            PortfolioType.CURRENT.value,
            PortfolioType.LEGACY.value,
        }:
            raise PortfolioTypeConflictError("unsupported portfolio type")
        new_holdings = [
            Holding(
                symbol=symbol,
                weight=None,
                invested_amount=invested_amount,
                invested_currency=invested_currency,
                shares=shares,
                purchase_date=purchase_date,
                position=position,
            )
            for position, (
                symbol,
                invested_amount,
                invested_currency,
                shares,
                purchase_date,
            ) in enumerate(replacements)
        ]

        portfolio.portfolio_type = PortfolioType.CURRENT.value
        portfolio.plan_currency = None
        portfolio.holdings.clear()
        self._session.flush()
        portfolio.holdings.extend(new_holdings)
        self._session.flush()
        return new_holdings

    def replace_planned_holdings(
        self,
        portfolio_id: UUID,
        holdings: Sequence[PlannedHoldingReplacement],
    ) -> list[Holding] | None:
        """Replace planned amounts in caller order without deriving shares."""
        replacements = tuple(
            (symbol, proposed_amount)
            for symbol, proposed_amount in holdings
        )
        self._validate_unique_symbols(
            [replacement[0] for replacement in replacements]
        )

        portfolio = self.get_with_holdings(portfolio_id)
        if portfolio is None:
            return None
        if portfolio.portfolio_type != PortfolioType.PLANNED.value:
            raise PortfolioTypeConflictError(
                "proposed amounts can replace only planned portfolio holdings"
            )

        new_holdings = [
            Holding(
                symbol=symbol,
                proposed_amount=proposed_amount,
                position=position,
            )
            for position, (symbol, proposed_amount) in enumerate(replacements)
        ]

        portfolio.holdings.clear()
        self._session.flush()
        portfolio.holdings.extend(new_holdings)
        self._session.flush()
        return new_holdings

    def delete(self, portfolio_id: UUID) -> bool:
        """Delete a portfolio when present without committing."""
        portfolio = self.get_by_id(portfolio_id)
        if portfolio is None:
            return False

        self._session.delete(portfolio)
        self._session.flush()
        return True

    @staticmethod
    def _validate_total_weight(
        holdings: Sequence[HoldingReplacement],
    ) -> None:
        total_weight = sum(
            (weight for _, weight in holdings),
            start=Decimal("0"),
        )
        if (
            abs(total_weight - _EXPECTED_TOTAL_WEIGHT)
            > _TOTAL_WEIGHT_TOLERANCE
        ):
            raise ValueError(
                "holding weights must sum to 1.0 within an absolute "
                "tolerance of 1e-9"
            )

    @staticmethod
    def _validate_unique_symbols(symbols: Sequence[str]) -> None:
        if len(symbols) != len(set(symbols)):
            raise ValueError("holding symbols must be unique")

    @staticmethod
    def _validate_portfolio_context(
        *,
        portfolio_type: str,
        plan_currency: str | None,
        source_plan_id: UUID | None,
    ) -> None:
        if portfolio_type not in {
            PortfolioType.CURRENT.value,
            PortfolioType.PLANNED.value,
            PortfolioType.LEGACY.value,
        }:
            raise PortfolioTypeConflictError("unsupported portfolio type")
        if portfolio_type == PortfolioType.PLANNED.value:
            if plan_currency not in {"USD", "THB"}:
                raise PortfolioTypeConflictError(
                    "planned portfolios require USD or THB plan currency"
                )
            if source_plan_id is not None:
                raise PortfolioTypeConflictError(
                    "planned portfolios cannot reference a source plan"
                )
            return
        if plan_currency is not None:
            raise PortfolioTypeConflictError(
                "only planned portfolios can define plan currency"
            )
        if (
            portfolio_type != PortfolioType.CURRENT.value
            and source_plan_id is not None
        ):
            raise PortfolioTypeConflictError(
                "only current portfolios can reference a source plan"
            )
