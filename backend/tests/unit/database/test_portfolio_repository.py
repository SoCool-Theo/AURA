import importlib
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.database.models import Holding, Portfolio, User
from backend.app.database.repositories import PortfolioRepository
import backend.app.database.repositories.portfolio_repository as repository_module


@pytest.fixture
def database_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    User.__table__.create(engine)
    Portfolio.__table__.create(engine)
    Holding.__table__.create(engine)
    session = Session(engine, autoflush=False, expire_on_commit=False)
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _persist_user(session: Session, user_id: UUID | None = None) -> User:
    user = User(id=user_id or uuid4())
    session.add(user)
    session.flush()
    return user


def _persist_portfolio(
    session: Session,
    user: User,
    *,
    name: str = "Core",
    portfolio_id: UUID | None = None,
    created_at: datetime | None = None,
) -> Portfolio:
    portfolio = Portfolio(
        id=portfolio_id or uuid4(),
        user_id=user.id,
        name=name,
        **({"created_at": created_at} if created_at is not None else {}),
    )
    session.add(portfolio)
    session.flush()
    return portfolio


def test_repository_uses_injected_session_without_owning_its_lifecycle() -> None:
    session = MagicMock(spec=Session)
    user_id = uuid4()

    portfolio = PortfolioRepository(session).create(
        user_id=user_id,
        name="  Already approved name  ",
    )

    session.add.assert_called_once_with(portfolio)
    session.flush.assert_called_once_with()
    session.commit.assert_not_called()
    session.rollback.assert_not_called()
    session.close.assert_not_called()
    assert portfolio.user_id == user_id
    assert portfolio.name == "  Already approved name  "


def test_repository_import_does_not_create_engine_or_connect() -> None:
    with (
        patch("sqlalchemy.create_engine") as create_database_engine,
        patch("psycopg.connect") as connect,
    ):
        importlib.reload(repository_module)

    create_database_engine.assert_not_called()
    connect.assert_not_called()
    assert not any(
        isinstance(value, Session)
        for value in vars(repository_module).values()
    )


def test_create_and_get_existing_portfolio(
    database_session: Session,
) -> None:
    user = _persist_user(database_session)
    repository = PortfolioRepository(database_session)

    created = repository.create(user_id=user.id, name="Core")

    assert created.id is not None
    assert repository.get_by_id(created.id) is created
    assert created.user_id == user.id
    assert created.name == "Core"


def test_get_missing_portfolio_returns_none(database_session: Session) -> None:
    assert PortfolioRepository(database_session).get_by_id(uuid4()) is None


def test_get_with_holdings_eager_loads_in_position_order(
    database_session: Session,
) -> None:
    user = _persist_user(database_session)
    portfolio = _persist_portfolio(database_session, user)
    portfolio.holdings.extend(
        [
            Holding(symbol="LAST", weight=Decimal("0.4"), position=2),
            Holding(symbol="FIRST", weight=Decimal("0.3"), position=0),
            Holding(symbol="MIDDLE", weight=Decimal("0.3"), position=1),
        ]
    )
    database_session.flush()
    database_session.expire_all()

    loaded = PortfolioRepository(database_session).get_with_holdings(
        portfolio.id
    )

    assert loaded is not None
    assert [holding.symbol for holding in loaded.holdings] == [
        "FIRST",
        "MIDDLE",
        "LAST",
    ]
    assert "holdings" not in loaded.__dict__["_sa_instance_state"].unloaded


def test_list_for_user_filters_and_orders_deterministically(
    database_session: Session,
) -> None:
    target_user = _persist_user(database_session)
    other_user = _persist_user(database_session)
    created_at = datetime(2026, 1, 1, tzinfo=UTC)
    later_id = UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")
    earlier_id = UUID("00000000-0000-0000-0000-000000000001")
    earlier = _persist_portfolio(
        database_session,
        target_user,
        name="Earlier ID",
        portfolio_id=earlier_id,
        created_at=created_at,
    )
    later = _persist_portfolio(
        database_session,
        target_user,
        name="Later ID",
        portfolio_id=later_id,
        created_at=created_at,
    )
    _persist_portfolio(
        database_session,
        other_user,
        name="Other user",
        created_at=created_at,
    )

    result = PortfolioRepository(database_session).list_for_user(
        target_user.id
    )

    assert result == [earlier, later]


def test_rename_updates_existing_without_normalization(
    database_session: Session,
) -> None:
    user = _persist_user(database_session)
    portfolio = _persist_portfolio(database_session, user)

    renamed = PortfolioRepository(database_session).rename(
        portfolio.id,
        "  Approved upstream  ",
    )

    assert renamed is portfolio
    assert portfolio.name == "  Approved upstream  "


def test_rename_missing_returns_none_without_flushing() -> None:
    session = MagicMock(spec=Session)
    session.get.return_value = None

    result = PortfolioRepository(session).rename(uuid4(), "New name")

    assert result is None
    session.flush.assert_not_called()
    session.commit.assert_not_called()


def test_delete_existing_and_missing_portfolio(
    database_session: Session,
) -> None:
    user = _persist_user(database_session)
    portfolio = _persist_portfolio(database_session, user)
    repository = PortfolioRepository(database_session)

    assert repository.delete(portfolio.id) is True
    assert repository.get_by_id(portfolio.id) is None
    assert repository.delete(uuid4()) is False


@pytest.mark.parametrize(
    "holdings",
    [
        [("AAPL", Decimal("0.6")), ("MSFT", Decimal("0.4"))],
        [
            ("AAPL", Decimal("0.5000000000")),
            ("MSFT", Decimal("0.5000000005")),
        ],
    ],
)
def test_replace_holdings_accepts_exact_and_tolerated_totals(
    database_session: Session,
    holdings: list[tuple[str, Decimal]],
) -> None:
    user = _persist_user(database_session)
    portfolio = _persist_portfolio(database_session, user)

    result = PortfolioRepository(database_session).replace_holdings(
        portfolio.id,
        holdings,
    )

    assert result is not None
    assert [holding.symbol for holding in result] == ["AAPL", "MSFT"]
    assert [holding.position for holding in result] == [0, 1]
    assert [holding.weight for holding in result] == [
        holdings[0][1],
        holdings[1][1],
    ]


def test_invalid_total_raises_before_session_or_holdings_mutation() -> None:
    session = MagicMock(spec=Session)
    portfolio = Portfolio(id=uuid4(), user_id=uuid4(), name="Core")
    original = Holding(symbol="AAPL", weight=Decimal("1"), position=0)
    portfolio.holdings.append(original)
    session.scalars.return_value.one_or_none.return_value = portfolio

    with pytest.raises(
        ValueError,
        match="holding weights must sum to 1.0",
    ):
        PortfolioRepository(session).replace_holdings(
            portfolio.id,
            [("MSFT", Decimal("0.999999998"))],
        )

    assert portfolio.holdings == [original]
    session.scalars.assert_not_called()
    session.flush.assert_not_called()
    session.commit.assert_not_called()


def test_replace_holdings_copies_input_and_flushes_deletes_before_inserts() -> None:
    session = MagicMock(spec=Session)
    portfolio = Portfolio(id=uuid4(), user_id=uuid4(), name="Core")
    portfolio.holdings.extend(
        [
            Holding(symbol="AAPL", weight=Decimal("0.5"), position=0),
            Holding(symbol="MSFT", weight=Decimal("0.5"), position=1),
        ]
    )
    session.scalars.return_value.one_or_none.return_value = portfolio
    snapshots: list[list[tuple[str, int]]] = []
    session.flush.side_effect = lambda: snapshots.append(
        [(holding.symbol, holding.position) for holding in portfolio.holdings]
    )
    caller_input = [
        ("MSFT", Decimal("0.4")),
        ("AAPL", Decimal("0.6")),
    ]
    input_snapshot = list(caller_input)

    result = PortfolioRepository(session).replace_holdings(
        portfolio.id,
        caller_input,
    )

    assert caller_input == input_snapshot
    assert snapshots == [[], [("MSFT", 0), ("AAPL", 1)]]
    assert result == portfolio.holdings
    session.commit.assert_not_called()


def test_replace_holdings_reuses_symbols_and_positions_without_conflict(
    database_session: Session,
) -> None:
    user = _persist_user(database_session)
    portfolio = _persist_portfolio(database_session, user)
    portfolio.holdings.extend(
        [
            Holding(symbol="AAPL", weight=Decimal("0.6"), position=0),
            Holding(symbol="MSFT", weight=Decimal("0.4"), position=1),
        ]
    )
    database_session.flush()

    PortfolioRepository(database_session).replace_holdings(
        portfolio.id,
        [("MSFT", Decimal("0.3")), ("AAPL", Decimal("0.7"))],
    )

    assert [(item.symbol, item.position) for item in portfolio.holdings] == [
        ("MSFT", 0),
        ("AAPL", 1),
    ]


def test_replace_missing_portfolio_returns_none_after_validation() -> None:
    session = MagicMock(spec=Session)
    session.scalars.return_value.one_or_none.return_value = None

    result = PortfolioRepository(session).replace_holdings(
        uuid4(),
        [("AAPL", Decimal("1"))],
    )

    assert result is None
    session.flush.assert_not_called()
    session.commit.assert_not_called()


def test_sqlalchemy_failure_is_propagated_without_rollback_or_commit() -> None:
    session = MagicMock(spec=Session)
    failure = SQLAlchemyError("write failed")
    session.flush.side_effect = failure

    with pytest.raises(SQLAlchemyError) as raised:
        PortfolioRepository(session).create(user_id=uuid4(), name="Core")

    assert raised.value is failure
    session.commit.assert_not_called()
    session.rollback.assert_not_called()
    session.close.assert_not_called()


def test_repository_has_no_pydantic_or_schema_dependency() -> None:
    source = Path(repository_module.__file__).read_text(encoding="utf-8")

    assert "pydantic" not in source
    assert "schemas" not in source
