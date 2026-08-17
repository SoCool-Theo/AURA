from copy import deepcopy
from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest
from sqlalchemy.orm import Session

from backend.app.database.models import Holding, Portfolio
import backend.app.services.portfolio_service as service_module
from backend.app.services.portfolio_service import PortfolioService


def _portfolio(
    user_id: UUID,
    *,
    name: str = "Core",
    portfolio_id: UUID | None = None,
) -> Portfolio:
    return Portfolio(
        id=portfolio_id or uuid4(),
        user_id=user_id,
        name=name,
    )


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


def test_phase3_replace_holdings_converts_weights_and_preserves_order() -> None:
    service, session, repository, _ = _service_with_repository()
    user_id = uuid4()
    portfolio = _portfolio(user_id)
    repository.get_with_holdings.return_value = portfolio
    caller_holdings = [
        ("BETA", 0.2),
        ("ALPHA", 0.5),
        ("CASH", 0.3),
    ]
    original = deepcopy(caller_holdings)

    def replace(
        portfolio_id: UUID,
        replacements: tuple[tuple[str, Decimal], ...],
    ) -> list[Holding]:
        assert portfolio_id == portfolio.id
        new_holdings = [
            Holding(symbol=symbol, weight=weight, position=position)
            for position, (symbol, weight) in enumerate(replacements)
        ]
        portfolio.holdings.clear()
        portfolio.holdings.extend(new_holdings)
        return new_holdings

    repository.replace_holdings.side_effect = replace

    result = service.replace_holdings(
        user_id=user_id,
        portfolio_id=portfolio.id,
        holdings=caller_holdings,
    )

    assert result is portfolio
    assert caller_holdings == original
    replacements = repository.replace_holdings.call_args.args[1]
    assert replacements == (
        ("BETA", Decimal("0.2")),
        ("ALPHA", Decimal("0.5")),
        ("CASH", Decimal("0.3")),
    )
    assert [(holding.symbol, holding.position) for holding in result.holdings] == [
        ("BETA", 0),
        ("ALPHA", 1),
        ("CASH", 2),
    ]
    _assert_session_lifecycle_untouched(session)


def test_phase3_replace_holdings_returns_none_when_missing() -> None:
    service, _, repository, _ = _service_with_repository()
    repository.get_with_holdings.return_value = None

    result = service.replace_holdings(
        user_id=uuid4(),
        portfolio_id=uuid4(),
        holdings=[("AAPL", 1.0)],
    )

    assert result is None
    repository.replace_holdings.assert_not_called()


def test_phase3_replace_holdings_wrong_owner_never_mutates() -> None:
    service, _, repository, _ = _service_with_repository()
    portfolio = _portfolio(uuid4())
    repository.get_with_holdings.return_value = portfolio

    result = service.replace_holdings(
        user_id=uuid4(),
        portfolio_id=portfolio.id,
        holdings=[("AAPL", 1.0)],
    )

    assert result is None
    repository.replace_holdings.assert_not_called()


def test_phase3_replace_holdings_propagates_repository_value_error() -> None:
    service, session, repository, _ = _service_with_repository()
    user_id = uuid4()
    portfolio = _portfolio(user_id)
    repository.get_with_holdings.return_value = portfolio
    failure = ValueError("holding weights must sum to 1.0")
    repository.replace_holdings.side_effect = failure

    with pytest.raises(ValueError) as raised:
        service.replace_holdings(
            user_id=user_id,
            portfolio_id=portfolio.id,
            holdings=[("AAPL", 0.9)],
        )

    assert raised.value is failure
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
    repository.create.assert_called_once_with(user_id=user_id, name="Copy")
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
    repository.create.assert_called_once_with(user_id=user_id, name="Copy")
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
