"""Portfolio business operations within a caller-owned transaction."""

from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from ..database.models import Portfolio, PortfolioType
from ..database.repositories import (
    PortfolioRepository,
    PortfolioTypeConflictError,
)


RealHoldingReplacement = tuple[str, Decimal | None, str | None, Decimal, date | None]
PlannedHoldingReplacement = tuple[str, Decimal]


class PortfolioService:
    """Coordinate owned portfolio operations without managing transactions."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._repository = PortfolioRepository(session)

    def create(
        self,
        *,
        user_id: UUID,
        name: str,
        portfolio_type: str = PortfolioType.CURRENT.value,
        plan_currency: str | None = None,
    ) -> Portfolio:
        """Create an empty portfolio for one owner."""
        return self._repository.create(
            user_id=user_id,
            name=name,
            portfolio_type=portfolio_type,
            plan_currency=plan_currency,
        )

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
        holdings: Sequence[RealHoldingReplacement],
    ) -> Portfolio | None:
        """Replace an owned portfolio's ordered real holdings."""
        portfolio = self._repository.get_with_holdings(portfolio_id)
        if not self._is_owned_by(portfolio, user_id):
            return None
        if self._effective_type(portfolio) == PortfolioType.PLANNED.value:
            raise PortfolioTypeConflictError(
                "current holdings cannot replace planned portfolio holdings"
            )

        replacements = tuple(holdings)
        self._repository.replace_real_holdings(portfolio_id, replacements)
        return portfolio

    def replace_planned_holdings(
        self,
        *,
        user_id: UUID,
        portfolio_id: UUID,
        holdings: Sequence[PlannedHoldingReplacement],
    ) -> Portfolio | None:
        """Replace proposed amounts only for an owned planned portfolio."""
        portfolio = self._repository.get_with_holdings(portfolio_id)
        if not self._is_owned_by(portfolio, user_id):
            return None
        if self._effective_type(portfolio) != PortfolioType.PLANNED.value:
            raise PortfolioTypeConflictError(
                "proposed amounts can replace only planned portfolio holdings"
            )

        replacements = tuple(holdings)
        self._repository.replace_planned_holdings(portfolio_id, replacements)
        return portfolio

    def duplicate(
        self,
        *,
        user_id: UUID,
        portfolio_id: UUID,
        name: str,
    ) -> Portfolio | None:
        """Copy an owned portfolio without converting its holding mode."""
        source = self._repository.get_with_holdings(portfolio_id)
        if not self._is_owned_by(source, user_id):
            return None

        portfolio_type = self._effective_type(source)
        legacy_replacements = None
        real_replacements = None
        planned_replacements = None
        if source.holdings:
            if portfolio_type == PortfolioType.LEGACY.value and all(
                holding.weight is not None
                and holding.proposed_amount is None
                and holding.invested_amount is None
                and holding.invested_currency is None
                and holding.shares is None
                and holding.purchase_date is None
                for holding in source.holdings
            ):
                legacy_replacements = tuple(
                    (holding.symbol, holding.weight)
                    for holding in source.holdings
                )
            elif portfolio_type == PortfolioType.CURRENT.value and all(
                holding.weight is None
                and holding.proposed_amount is None
                and holding.shares is not None
                and (
                    (
                        holding.invested_amount is None
                        and holding.invested_currency is None
                        and holding.purchase_date is None
                    )
                    or (
                        holding.invested_amount is not None
                        and holding.invested_currency is not None
                        and holding.purchase_date is not None
                    )
                )
                for holding in source.holdings
            ):
                real_replacements = tuple(
                    (
                        holding.symbol,
                        holding.invested_amount,
                        holding.invested_currency,
                        holding.shares,
                        holding.purchase_date,
                    )
                    for holding in source.holdings
                )
            elif portfolio_type == PortfolioType.PLANNED.value and all(
                holding.weight is None
                and holding.proposed_amount is not None
                and holding.invested_amount is None
                and holding.invested_currency is None
                and holding.shares is None
                and holding.purchase_date is None
                for holding in source.holdings
            ):
                planned_replacements = tuple(
                    (holding.symbol, holding.proposed_amount)
                    for holding in source.holdings
                )
            else:
                raise ValueError(
                    "cannot duplicate mixed or incomplete holding state"
                )

        duplicate = self._repository.create(
            user_id=user_id,
            name=name,
            portfolio_type=portfolio_type,
            plan_currency=(
                source.plan_currency
                if portfolio_type == PortfolioType.PLANNED.value
                else None
            ),
        )
        if legacy_replacements is not None:
            self._repository.replace_holdings(
                duplicate.id,
                legacy_replacements,
            )
        elif real_replacements is not None:
            self._repository.replace_real_holdings(
                duplicate.id,
                real_replacements,
            )
        elif planned_replacements is not None:
            self._repository.replace_planned_holdings(
                duplicate.id,
                planned_replacements,
            )
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

    @staticmethod
    def _effective_type(portfolio: Portfolio) -> str:
        if portfolio.portfolio_type in {
            PortfolioType.CURRENT.value,
            PortfolioType.PLANNED.value,
            PortfolioType.LEGACY.value,
        }:
            return portfolio.portfolio_type

        holdings = tuple(portfolio.holdings)
        if holdings and all(holding.weight is not None for holding in holdings):
            return PortfolioType.LEGACY.value
        if holdings and all(
            holding.proposed_amount is not None for holding in holdings
        ):
            return PortfolioType.PLANNED.value
        return PortfolioType.CURRENT.value
