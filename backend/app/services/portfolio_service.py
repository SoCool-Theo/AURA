"""Portfolio business operations within a caller-owned transaction."""

from collections.abc import Sequence
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from ..database.models import Portfolio
from ..database.repositories import PortfolioRepository


class PortfolioService:
    """Coordinate owned portfolio operations without managing transactions."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._repository = PortfolioRepository(session)

    def create(self, *, user_id: UUID, name: str) -> Portfolio:
        """Create an empty portfolio for one owner."""
        return self._repository.create(user_id=user_id, name=name)

    def get(
        self,
        *,
        user_id: UUID,
        portfolio_id: UUID,
    ) -> Portfolio | None:
        """Return an owned portfolio with ordered holdings, if present."""
        portfolio = self._repository.get_with_holdings(portfolio_id)
        if not self._is_owned_by(portfolio, user_id):
            return None
        return portfolio

    def list_for_user(self, *, user_id: UUID) -> list[Portfolio]:
        """Return the repository's deterministically ordered owner list."""
        return self._repository.list_for_user(user_id)

    def rename(
        self,
        *,
        user_id: UUID,
        portfolio_id: UUID,
        name: str,
    ) -> Portfolio | None:
        """Rename a portfolio only after ownership is confirmed."""
        portfolio = self._repository.get_by_id(portfolio_id)
        if not self._is_owned_by(portfolio, user_id):
            return None
        return self._repository.rename(portfolio_id, name)

    def replace_holdings(
        self,
        *,
        user_id: UUID,
        portfolio_id: UUID,
        holdings: Sequence[tuple[str, float]],
    ) -> Portfolio | None:
        """Replace an owned portfolio's ordered holdings."""
        portfolio = self._repository.get_with_holdings(portfolio_id)
        if not self._is_owned_by(portfolio, user_id):
            return None

        replacements = tuple(
            (symbol, Decimal(str(weight)))
            for symbol, weight in holdings
        )
        self._repository.replace_holdings(portfolio_id, replacements)
        return portfolio

    def duplicate(
        self,
        *,
        user_id: UUID,
        portfolio_id: UUID,
        name: str,
    ) -> Portfolio | None:
        """Copy an owned portfolio and its exact ordered allocation."""
        source = self._repository.get_with_holdings(portfolio_id)
        if not self._is_owned_by(source, user_id):
            return None

        duplicate = self._repository.create(user_id=user_id, name=name)
        if source.holdings:
            replacements = tuple(
                (holding.symbol, holding.weight)
                for holding in source.holdings
            )
            self._repository.replace_holdings(duplicate.id, replacements)
        return duplicate

    def delete(
        self,
        *,
        user_id: UUID,
        portfolio_id: UUID,
    ) -> bool:
        """Delete a portfolio only after ownership is confirmed."""
        portfolio = self._repository.get_by_id(portfolio_id)
        if not self._is_owned_by(portfolio, user_id):
            return False
        return self._repository.delete(portfolio_id)

    @staticmethod
    def _is_owned_by(
        portfolio: Portfolio | None,
        user_id: UUID,
    ) -> bool:
        return portfolio is not None and portfolio.user_id == user_id
