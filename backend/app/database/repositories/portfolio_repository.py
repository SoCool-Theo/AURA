"""Caller-transaction-owned persistence operations for Aura portfolios."""

from collections.abc import Sequence
from decimal import Decimal
from typing import TypeAlias
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..models import Holding, Portfolio


HoldingReplacement: TypeAlias = tuple[str, Decimal]

_EXPECTED_TOTAL_WEIGHT = Decimal("1.0")
_TOTAL_WEIGHT_TOLERANCE = Decimal("1e-9")


class PortfolioRepository:
    """Persist portfolios within a caller-owned SQLAlchemy session."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, *, user_id: UUID, name: str) -> Portfolio:
        """Add and flush a portfolio without committing the transaction."""
        portfolio = Portfolio(user_id=user_id, name=name)
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

        new_holdings = [
            Holding(symbol=symbol, weight=weight, position=position)
            for position, (symbol, weight) in enumerate(replacements)
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
