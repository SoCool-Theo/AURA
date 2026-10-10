from copy import deepcopy
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest
from sqlalchemy.orm import Session

from backend.app.database.models import Holding, Portfolio, PortfolioType
import backend.app.services.portfolio_service as service_module
from backend.app.services.portfolio_service import PortfolioService


def _real_replacement(
    symbol: str = "AAPL",
    *,
    invested_amount: Decimal = Decimal("1500.000000000000"),
    invested_currency: str = "USD",
    shares: Decimal = Decimal("10.000000000000"),
    purchase_date: date = date(2026, 1, 10),
) -> tuple[str, Decimal, str, Decimal, date]:
    return (
        symbol,
        invested_amount,
        invested_currency,
        shares,
        purchase_date,
    )


def _portfolio(
    user_id: UUID,
    *,
    name: str = "Core",
    portfolio_id: UUID | None = None,
    portfolio_type: str | None = None,
    plan_currency: str | None = None,
) -> Portfolio:
    portfolio = Portfolio(
        id=portfolio_id or uuid4(),
        user_id=user_id,
        name=name,
        plan_currency=plan_currency,
    )
    if portfolio_type is not None:
        portfolio.portfolio_type = portfolio_type
    return portfolio


def _service_with_repository() -> tuple[
    PortfolioService,
    MagicMock,
    MagicMock,
    MagicMock,
]:
    session = MagicMock(spec=Session)
    repository = MagicMock(spec=service_module.PortfolioRepository)

    with patch.object(
        service_module,
        "PortfolioRepository",
        return_value=repository,
    ) as repository_type:
        service = PortfolioService(session)

    return service, session, repository, repository_type


def _assert_session_lifecycle_untouched(session: MagicMock) -> None:
    session.commit.assert_not_called()
    session.rollback.assert_not_called()
    session.close.assert_not_called()


def test_phase3_constructor_uses_only_the_caller_owned_session() -> None:
    session = MagicMock(spec=Session)
    repository = MagicMock(spec=service_module.PortfolioRepository)

    with (
        patch.object(
            service_module,
            "PortfolioRepository",
            return_value=repository,
        ) as repository_type,
        patch("sqlalchemy.create_engine") as create_engine,
        patch("sqlalchemy.orm.sessionmaker") as sessionmaker,
    ):
        service = PortfolioService(session)

    assert service._session is session
    assert service._repository is repository
    repository_type.assert_called_once_with(session)
    create_engine.assert_not_called()
    sessionmaker.assert_not_called()
    _assert_session_lifecycle_untouched(session)


def test_phase3_create_delegates_owner_and_name_without_lifecycle_calls() -> None:
    service, session, repository, _ = _service_with_repository()
    user_id = uuid4()
    created = _portfolio(user_id, name="  Approved upstream  ")
    repository.create.return_value = created

    result = service.create(user_id=user_id, name="  Approved upstream  ")

    assert result is created
    repository.create.assert_called_once_with(
        user_id=user_id,
        name="  Approved upstream  ",
        portfolio_type="CURRENT",
        plan_currency=None,
    )
    _assert_session_lifecycle_untouched(session)


def test_phase3_get_returns_owned_portfolio_from_holdings_aware_lookup() -> None:
    service, _, repository, _ = _service_with_repository()
    user_id = uuid4()
    portfolio = _portfolio(user_id)
    repository.get_with_holdings.return_value = portfolio

    result = service.get(user_id=user_id, portfolio_id=portfolio.id)

    assert result is portfolio
    repository.get_with_holdings.assert_called_once_with(portfolio.id)
    repository.get_by_id.assert_not_called()


def test_phase3_get_returns_none_for_missing_portfolio() -> None:
    service, _, repository, _ = _service_with_repository()
    portfolio_id = uuid4()
    repository.get_with_holdings.return_value = None

    assert service.get(user_id=uuid4(), portfolio_id=portfolio_id) is None
    repository.get_with_holdings.assert_called_once_with(portfolio_id)


def test_phase3_get_returns_none_for_wrong_owner() -> None:
    service, _, repository, _ = _service_with_repository()
    portfolio = _portfolio(uuid4())
    repository.get_with_holdings.return_value = portfolio

    assert service.get(user_id=uuid4(), portfolio_id=portfolio.id) is None


def test_phase3_list_preserves_repository_order_without_sorting() -> None:
    service, _, repository, _ = _service_with_repository()
    user_id = uuid4()
    second_id = _portfolio(
        user_id,
        name="Second ID First",
        portfolio_id=UUID("00000000-0000-0000-0000-000000000002"),
    )
    first_id = _portfolio(
        user_id,
        name="First ID Second",
        portfolio_id=UUID("00000000-0000-0000-0000-000000000001"),
    )
    repository_order = [second_id, first_id]
    repository.list_for_user.return_value = repository_order

    result = service.list_for_user(user_id=user_id)

    assert result is repository_order
    assert result == [second_id, first_id]
    repository.list_for_user.assert_called_once_with(user_id)


def test_phase3_rename_owned_portfolio_delegates_after_lookup() -> None:
    service, session, repository, _ = _service_with_repository()
    user_id = uuid4()
    portfolio = _portfolio(user_id)
    renamed = _portfolio(user_id, name="New name", portfolio_id=portfolio.id)
    repository.get_by_id.return_value = portfolio
    repository.rename.return_value = renamed

    result = service.rename(
        user_id=user_id,
        portfolio_id=portfolio.id,
        name="New name",
    )

    assert result is renamed
    repository.get_by_id.assert_called_once_with(portfolio.id)
    repository.rename.assert_called_once_with(portfolio.id, "New name")
    _assert_session_lifecycle_untouched(session)


def test_phase3_rename_missing_returns_none_without_mutation() -> None:
    service, _, repository, _ = _service_with_repository()
    repository.get_by_id.return_value = None

    result = service.rename(
        user_id=uuid4(),
        portfolio_id=uuid4(),
        name="New name",
    )

    assert result is None
    repository.rename.assert_not_called()


def test_phase3_rename_wrong_owner_returns_none_without_mutation() -> None:
    service, _, repository, _ = _service_with_repository()
    portfolio = _portfolio(uuid4())
    repository.get_by_id.return_value = portfolio

    result = service.rename(
        user_id=uuid4(),
        portfolio_id=portfolio.id,
        name="New name",
    )

    assert result is None
    repository.rename.assert_not_called()


def test_phase6_replace_holdings_preserves_real_facts_and_order() -> None:
    service, session, repository, _ = _service_with_repository()
    user_id = uuid4()
    portfolio = _portfolio(user_id)
    repository.get_with_holdings.return_value = portfolio
    caller_holdings = [
        _real_replacement("AAPL"),
        _real_replacement(
            "MSFT",
            invested_amount=Decimal("3000.000000000000"),
            invested_currency="THB",
            shares=Decimal("4.500000000000"),
            purchase_date=date(2026, 2, 20),
        ),
    ]
    original = deepcopy(caller_holdings)

    def replace(
        portfolio_id: UUID,
        replacements: tuple[
            tuple[str, Decimal, str, Decimal, date], ...
        ],
    ) -> list[Holding]:
        assert portfolio_id == portfolio.id
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
        portfolio.holdings.clear()
        portfolio.holdings.extend(new_holdings)
        return new_holdings

    repository.replace_real_holdings.side_effect = replace

    result = service.replace_holdings(
        user_id=user_id,
        portfolio_id=portfolio.id,
        holdings=caller_holdings,
    )

    assert result is portfolio
    assert caller_holdings == original
    replacements = repository.replace_real_holdings.call_args.args[1]
    assert replacements == tuple(caller_holdings)
    assert [(holding.symbol, holding.position) for holding in result.holdings] == [
        ("AAPL", 0),
        ("MSFT", 1),
    ]
    assert all(holding.weight is None for holding in result.holdings)
    _assert_session_lifecycle_untouched(session)


def test_phase3_replace_holdings_returns_none_when_missing() -> None:
    service, _, repository, _ = _service_with_repository()
    repository.get_with_holdings.return_value = None

    result = service.replace_holdings(
        user_id=uuid4(),
        portfolio_id=uuid4(),
        holdings=[_real_replacement()],
    )

    assert result is None
    repository.replace_real_holdings.assert_not_called()


def test_phase3_replace_holdings_wrong_owner_never_mutates() -> None:
    service, _, repository, _ = _service_with_repository()
    portfolio = _portfolio(uuid4())
    repository.get_with_holdings.return_value = portfolio

    result = service.replace_holdings(
        user_id=uuid4(),
        portfolio_id=portfolio.id,
        holdings=[_real_replacement()],
    )

    assert result is None
    repository.replace_real_holdings.assert_not_called()


def test_phase6_replace_holdings_propagates_repository_value_error() -> None:
    service, session, repository, _ = _service_with_repository()
    user_id = uuid4()
    portfolio = _portfolio(user_id)
    repository.get_with_holdings.return_value = portfolio
    failure = ValueError("holding symbols must be unique")
    repository.replace_real_holdings.side_effect = failure

    with pytest.raises(ValueError) as raised:
        service.replace_holdings(
            user_id=user_id,
            portfolio_id=portfolio.id,
            holdings=[_real_replacement()],
        )

    assert raised.value is failure
    _assert_session_lifecycle_untouched(session)


def test_planned_holding_replacement_preserves_amounts_and_order() -> None:
    service, session, repository, _ = _service_with_repository()
    user_id = uuid4()
    portfolio = _portfolio(
        user_id,
        portfolio_type=PortfolioType.PLANNED.value,
        plan_currency="USD",
    )
    repository.get_with_holdings.return_value = portfolio
    replacements = [
        ("AAPL", Decimal("4000.000000000000")),
        ("MSFT", Decimal("6000.000000000000")),
    ]

    result = service.replace_planned_holdings(
        user_id=user_id,
        portfolio_id=portfolio.id,
        holdings=replacements,
    )

    assert result is portfolio
    repository.replace_planned_holdings.assert_called_once_with(
        portfolio.id,
        tuple(replacements),
    )
    repository.replace_real_holdings.assert_not_called()
    _assert_session_lifecycle_untouched(session)


def test_current_and_planned_replacements_reject_mode_mismatch() -> None:
    service, session, repository, _ = _service_with_repository()
    user_id = uuid4()
    planned = _portfolio(
        user_id,
        portfolio_type=PortfolioType.PLANNED.value,
        plan_currency="USD",
    )
    repository.get_with_holdings.return_value = planned

    with pytest.raises(service_module.PortfolioTypeConflictError):
        service.replace_holdings(
            user_id=user_id,
            portfolio_id=planned.id,
            holdings=[_real_replacement()],
        )

    current = _portfolio(
        user_id,
        portfolio_type=PortfolioType.CURRENT.value,
    )
    repository.get_with_holdings.return_value = current
    with pytest.raises(service_module.PortfolioTypeConflictError):
        service.replace_planned_holdings(
            user_id=user_id,
            portfolio_id=current.id,
            holdings=[("AAPL", Decimal("1000"))],
        )

    repository.replace_real_holdings.assert_not_called()
    repository.replace_planned_holdings.assert_not_called()
    _assert_session_lifecycle_untouched(session)


def test_phase3_duplicate_populated_portfolio_preserves_exact_holdings() -> None:
    service, session, repository, _ = _service_with_repository()
    user_id = uuid4()
    source = _portfolio(user_id, name="Source")
    first_weight = Decimal("0.123456789012345678")
    second_weight = Decimal("0.876543210987654322")
    source_holdings = [
        Holding(
            id=uuid4(),
            symbol="FIRST",
            weight=first_weight,
            position=0,
        ),
        Holding(
            id=uuid4(),
            symbol="SECOND",
            weight=second_weight,
            position=1,
        ),
    ]
    source.holdings.extend(source_holdings)
    source_snapshot = [
        (holding.id, holding.symbol, holding.weight, holding.position)
        for holding in source.holdings
    ]
    duplicate = _portfolio(user_id, name="Copy")
    repository.get_with_holdings.return_value = source
    repository.create.return_value = duplicate

    def copy_holdings(
        portfolio_id: UUID,
        replacements: tuple[tuple[str, Decimal], ...],
    ) -> list[Holding]:
        assert portfolio_id == duplicate.id
        copied = [
            Holding(
                id=uuid4(),
                symbol=symbol,
                weight=weight,
                position=position,
            )
            for position, (symbol, weight) in enumerate(replacements)
        ]
        duplicate.holdings.extend(copied)
        return copied

    repository.replace_holdings.side_effect = copy_holdings

    result = service.duplicate(
        user_id=user_id,
        portfolio_id=source.id,
        name="Copy",
    )

    assert result is duplicate
    assert result is not source
    assert result.id != source.id
    assert result.user_id == source.user_id
    assert result.name == "Copy"
    replacements = repository.replace_holdings.call_args.args[1]
    assert replacements == (
        ("FIRST", first_weight),
        ("SECOND", second_weight),
    )
    assert replacements[0][1] is first_weight
    assert replacements[1][1] is second_weight
    assert [holding.id for holding in result.holdings] != [
        holding.id for holding in source.holdings
    ]
    assert [(holding.symbol, holding.weight) for holding in result.holdings] == [
        ("FIRST", first_weight),
        ("SECOND", second_weight),
    ]
    assert [
        (holding.id, holding.symbol, holding.weight, holding.position)
        for holding in source.holdings
    ] == source_snapshot
    repository.create.assert_called_once_with(
        user_id=user_id,
        name="Copy",
        portfolio_type="LEGACY",
        plan_currency=None,
    )
    repository.replace_real_holdings.assert_not_called()
    _assert_session_lifecycle_untouched(session)


def test_duplicate_quantity_only_portfolio_preserves_mode_and_order() -> None:
    service, session, repository, _ = _service_with_repository()
    user_id = uuid4()
    source = _portfolio(
        user_id,
        name="Quantity Source",
        portfolio_type=PortfolioType.CURRENT.value,
    )
    source.holdings.extend(
        [
            Holding(
                id=uuid4(),
                symbol="AAPL",
                weight=None,
                invested_amount=None,
                invested_currency=None,
                shares=Decimal("5.000000000000"),
                purchase_date=None,
                position=0,
            ),
            Holding(
                id=uuid4(),
                symbol="BTC-USD",
                weight=None,
                invested_amount=None,
                invested_currency=None,
                shares=Decimal("0.250000000000"),
                purchase_date=None,
                position=1,
            ),
        ]
    )
    duplicate = _portfolio(
        user_id,
        name="Quantity Copy",
        portfolio_type=PortfolioType.CURRENT.value,
    )
    repository.get_with_holdings.return_value = source
    repository.create.return_value = duplicate

    result = service.duplicate(
        user_id=user_id,
        portfolio_id=source.id,
        name="Quantity Copy",
    )

    assert result is duplicate
    repository.replace_real_holdings.assert_called_once_with(
        duplicate.id,
        (
            ("AAPL", None, None, Decimal("5.000000000000"), None),
            ("BTC-USD", None, None, Decimal("0.250000000000"), None),
        ),
    )
    _assert_session_lifecycle_untouched(session)


def test_phase6_duplicate_real_portfolio_preserves_mode_facts_and_order() -> None:
    service, session, repository, _ = _service_with_repository()
    user_id = uuid4()
    source = _portfolio(user_id, name="Real Source")
    source.holdings.extend(
        [
            Holding(
                id=uuid4(),
                symbol="AAPL",
                weight=None,
                invested_amount=Decimal("1500.000000000000"),
                invested_currency="USD",
                shares=Decimal("10.000000000000"),
                purchase_date=date(2026, 1, 10),
                position=0,
            ),
            Holding(
                id=uuid4(),
                symbol="MSFT",
                weight=None,
                invested_amount=Decimal("90000.000000000000"),
                invested_currency="THB",
                shares=Decimal("4.500000000000"),
                purchase_date=date(2026, 2, 20),
                position=1,
            ),
        ]
    )
    source_snapshot = [
        (
            holding.id,
            holding.symbol,
            holding.invested_amount,
            holding.invested_currency,
            holding.shares,
            holding.purchase_date,
            holding.weight,
            holding.position,
        )
        for holding in source.holdings
    ]
    duplicate = _portfolio(user_id, name="Real Copy")
    repository.get_with_holdings.return_value = source
    repository.create.return_value = duplicate

    def copy_real_holdings(
        portfolio_id: UUID,
        replacements: tuple[
            tuple[str, Decimal, str, Decimal, date], ...
        ],
    ) -> list[Holding]:
        assert portfolio_id == duplicate.id
        copied = [
            Holding(
                id=uuid4(),
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
        duplicate.holdings.extend(copied)
        return copied

    repository.replace_real_holdings.side_effect = copy_real_holdings

    result = service.duplicate(
        user_id=user_id,
        portfolio_id=source.id,
        name="Real Copy",
    )

    assert result is duplicate
    assert result.id != source.id
    assert [holding.id for holding in result.holdings] != [
        holding.id for holding in source.holdings
    ]
    assert [
        (
            holding.symbol,
            holding.invested_amount,
            holding.invested_currency,
            holding.shares,
            holding.purchase_date,
            holding.weight,
            holding.position,
        )
        for holding in result.holdings
    ] == [
        (
            "AAPL",
            Decimal("1500.000000000000"),
            "USD",
            Decimal("10.000000000000"),
            date(2026, 1, 10),
            None,
            0,
        ),
        (
            "MSFT",
            Decimal("90000.000000000000"),
            "THB",
            Decimal("4.500000000000"),
            date(2026, 2, 20),
            None,
            1,
        ),
    ]
    assert [
        (
            holding.id,
            holding.symbol,
            holding.invested_amount,
            holding.invested_currency,
            holding.shares,
            holding.purchase_date,
            holding.weight,
            holding.position,
        )
        for holding in source.holdings
    ] == source_snapshot
    repository.replace_holdings.assert_not_called()
    _assert_session_lifecycle_untouched(session)


def test_step3_duplicate_planned_portfolio_preserves_amounts_and_currency(
) -> None:
    service, session, repository, _ = _service_with_repository()
    user_id = uuid4()
    source = _portfolio(
        user_id,
        name="Plan Source",
        portfolio_type=PortfolioType.PLANNED.value,
        plan_currency="THB",
    )
    source.holdings.extend(
        [
            Holding(
                id=uuid4(),
                symbol="AAPL",
                proposed_amount=Decimal("4000.000000000000"),
                position=0,
            ),
            Holding(
                id=uuid4(),
                symbol="BND",
                proposed_amount=Decimal("1000.000000000000"),
                position=1,
            ),
        ]
    )
    duplicate = _portfolio(
        user_id,
        name="Plan Copy",
        portfolio_type=PortfolioType.PLANNED.value,
        plan_currency="THB",
    )
    repository.get_with_holdings.return_value = source
    repository.create.return_value = duplicate

    result = service.duplicate(
        user_id=user_id,
        portfolio_id=source.id,
        name="Plan Copy",
    )

    assert result is duplicate
    repository.create.assert_called_once_with(
        user_id=user_id,
        name="Plan Copy",
        portfolio_type="PLANNED",
        plan_currency="THB",
    )
    repository.replace_planned_holdings.assert_called_once_with(
        duplicate.id,
        (
            ("AAPL", Decimal("4000.000000000000")),
            ("BND", Decimal("1000.000000000000")),
        ),
    )
    repository.replace_real_holdings.assert_not_called()
    repository.replace_holdings.assert_not_called()
    _assert_session_lifecycle_untouched(session)


def test_phase3_duplicate_empty_source_skips_holding_replacement() -> None:
    service, _, repository, _ = _service_with_repository()
    user_id = uuid4()
    source = _portfolio(user_id, name="Empty")
    duplicate = _portfolio(user_id, name="Empty Copy")
    repository.get_with_holdings.return_value = source
    repository.create.return_value = duplicate

    result = service.duplicate(
        user_id=user_id,
        portfolio_id=source.id,
        name="Empty Copy",
    )

    assert result is duplicate
    assert result.holdings == []
    repository.replace_holdings.assert_not_called()
    repository.replace_real_holdings.assert_not_called()


@pytest.mark.parametrize("state", ["mixed", "incomplete-real"])
def test_phase6_duplicate_rejects_invalid_modes_before_creating(
    state: str,
) -> None:
    service, session, repository, _ = _service_with_repository()
    user_id = uuid4()
    source = _portfolio(user_id)
    source.holdings.append(
        Holding(symbol="AAPL", weight=Decimal("1"), position=0)
    )
    if state == "mixed":
        source.holdings.append(
            Holding(
                symbol="MSFT",
                weight=None,
                invested_amount=Decimal("100"),
                invested_currency="USD",
                shares=Decimal("1"),
                purchase_date=date(2026, 1, 10),
                position=1,
            )
        )
    else:
        source.holdings.clear()
        source.holdings.append(
            Holding(
                symbol="AAPL",
                weight=None,
                invested_amount=Decimal("100"),
                invested_currency="USD",
                shares=None,
                purchase_date=date(2026, 1, 10),
                position=0,
            )
        )
    repository.get_with_holdings.return_value = source

    with pytest.raises(
        ValueError,
        match="cannot duplicate mixed or incomplete holding state",
    ):
        service.duplicate(
            user_id=user_id,
            portfolio_id=source.id,
            name="Copy",
        )

    repository.create.assert_not_called()
    repository.replace_holdings.assert_not_called()
    repository.replace_real_holdings.assert_not_called()
    _assert_session_lifecycle_untouched(session)


def test_phase3_duplicate_missing_source_returns_none() -> None:
    service, _, repository, _ = _service_with_repository()
    repository.get_with_holdings.return_value = None

    result = service.duplicate(
        user_id=uuid4(),
        portfolio_id=uuid4(),
        name="Copy",
    )

    assert result is None
    repository.create.assert_not_called()
    repository.replace_holdings.assert_not_called()
    repository.replace_real_holdings.assert_not_called()


def test_phase3_duplicate_wrong_owner_returns_none_without_writes() -> None:
    service, _, repository, _ = _service_with_repository()
    source = _portfolio(uuid4())
    repository.get_with_holdings.return_value = source

    result = service.duplicate(
        user_id=uuid4(),
        portfolio_id=source.id,
        name="Copy",
    )

    assert result is None
    repository.create.assert_not_called()
    repository.replace_holdings.assert_not_called()
    repository.replace_real_holdings.assert_not_called()


def test_phase3_duplicate_copy_failure_propagates_without_transaction_calls() -> None:
    service, session, repository, _ = _service_with_repository()
    user_id = uuid4()
    source = _portfolio(user_id)
    source.holdings.append(
        Holding(symbol="AAPL", weight=Decimal("1"), position=0)
    )
    duplicate = _portfolio(user_id, name="Copy")
    repository.get_with_holdings.return_value = source
    repository.create.return_value = duplicate
    failure = RuntimeError("holding copy failed")
    repository.replace_holdings.side_effect = failure

    with pytest.raises(RuntimeError) as raised:
        service.duplicate(
            user_id=user_id,
            portfolio_id=source.id,
            name="Copy",
        )

    assert raised.value is failure
    repository.create.assert_called_once_with(
        user_id=user_id,
        name="Copy",
        portfolio_type="LEGACY",
        plan_currency=None,
    )
    _assert_session_lifecycle_untouched(session)


def test_phase3_delete_owned_portfolio_returns_repository_result() -> None:
    service, session, repository, _ = _service_with_repository()
    user_id = uuid4()
    portfolio = _portfolio(user_id)
    repository.get_by_id.return_value = portfolio
    repository.delete.return_value = True

    result = service.delete(user_id=user_id, portfolio_id=portfolio.id)

    assert result is True
    repository.delete.assert_called_once_with(portfolio.id)
    _assert_session_lifecycle_untouched(session)


def test_phase3_delete_missing_returns_false_without_mutation() -> None:
    service, _, repository, _ = _service_with_repository()
    repository.get_by_id.return_value = None

    result = service.delete(user_id=uuid4(), portfolio_id=uuid4())

    assert result is False
    repository.delete.assert_not_called()


def test_phase3_delete_wrong_owner_returns_false_without_mutation() -> None:
    service, _, repository, _ = _service_with_repository()
    portfolio = _portfolio(uuid4())
    repository.get_by_id.return_value = portfolio

    result = service.delete(user_id=uuid4(), portfolio_id=portfolio.id)

    assert result is False
    repository.delete.assert_not_called()
