import importlib
from copy import deepcopy
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.database.models import Holding, Portfolio, PortfolioType, User
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
    portfolio_type: str = PortfolioType.LEGACY.value,
    plan_currency: str | None = None,
) -> Portfolio:
    portfolio = Portfolio(
        id=portfolio_id or uuid4(),
        user_id=user.id,
        name=name,
        portfolio_type=portfolio_type,
        plan_currency=plan_currency,
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
    assert portfolio.portfolio_type == PortfolioType.CURRENT.value


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
    assert created.portfolio_type == PortfolioType.CURRENT.value
    assert created.plan_currency is None


def test_create_planned_portfolio_persists_explicit_context(
    database_session: Session,
) -> None:
    user = _persist_user(database_session)

    created = PortfolioRepository(database_session).create(
        user_id=user.id,
        name="Plan",
        portfolio_type=PortfolioType.PLANNED.value,
        plan_currency="THB",
    )

    assert created.portfolio_type == PortfolioType.PLANNED.value
    assert created.plan_currency == "THB"
    assert created.source_plan_id is None


@pytest.mark.parametrize(
    ("portfolio_type", "plan_currency"),
    [("PLANNED", None), ("CURRENT", "USD"), ("UNKNOWN", None)],
)
def test_create_rejects_invalid_type_context_before_session_mutation(
    portfolio_type: str,
    plan_currency: str | None,
) -> None:
    session = MagicMock(spec=Session)

    with pytest.raises(repository_module.PortfolioTypeConflictError):
        PortfolioRepository(session).create(
            user_id=uuid4(),
            name="Invalid",
            portfolio_type=portfolio_type,
            plan_currency=plan_currency,
        )

    session.add.assert_not_called()
    session.flush.assert_not_called()


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
    portfolio = Portfolio(
        id=uuid4(),
        user_id=uuid4(),
        name="Core",
        portfolio_type=PortfolioType.LEGACY.value,
    )
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


def test_replace_real_holdings_preserves_facts_order_and_decimal_values(
    database_session: Session,
) -> None:
    user = _persist_user(database_session)
    portfolio = _persist_portfolio(database_session, user)
    portfolio.holdings.append(
        Holding(symbol="BND", weight=Decimal("1"), position=0)
    )
    database_session.flush()
    replacements = [
        (
            "AAPL",
            Decimal("1500.000000000000"),
            "USD",
            Decimal("10.250000000000"),
            date(2026, 1, 10),
        ),
        (
            "MSFT",
            Decimal("90000.000000000000"),
            "THB",
            Decimal("4.500000000000"),
            date(2026, 2, 20),
        ),
    ]
    original = deepcopy(replacements)

    result = PortfolioRepository(database_session).replace_real_holdings(
        portfolio.id,
        replacements,
    )
    portfolio_id = portfolio.id
    database_session.commit()
    with Session(database_session.get_bind()) as fresh_session:
        loaded = PortfolioRepository(fresh_session).get_with_holdings(
            portfolio_id
        )

    assert result is not None
    assert loaded is not None
    assert loaded.id == portfolio_id
    assert replacements == original
    assert [
        (
            holding.symbol,
            holding.weight,
            holding.invested_amount,
            holding.invested_currency,
            holding.shares,
            holding.purchase_date,
            holding.position,
        )
        for holding in loaded.holdings
    ] == [
        (
            "AAPL",
            None,
            Decimal("1500.000000000000"),
            "USD",
            Decimal("10.250000000000"),
            date(2026, 1, 10),
            0,
        ),
        (
            "MSFT",
            None,
            Decimal("90000.000000000000"),
            "THB",
            Decimal("4.500000000000"),
            date(2026, 2, 20),
            1,
        ),
    ]
    assert all(holding.symbol != "BND" for holding in loaded.holdings)
    assert not hasattr(loaded.holdings[0], "current_value")
    assert not hasattr(loaded.holdings[0], "current_allocation")


def test_replace_real_holdings_flushes_delete_before_insert_without_commit() -> None:
    session = MagicMock(spec=Session)
    portfolio = Portfolio(
        id=uuid4(),
        user_id=uuid4(),
        name="Core",
        portfolio_type=PortfolioType.LEGACY.value,
    )
    portfolio.holdings.append(
        Holding(symbol="BND", weight=Decimal("1"), position=0)
    )
    session.scalars.return_value.one_or_none.return_value = portfolio
    snapshots: list[list[tuple[str, int]]] = []
    session.flush.side_effect = lambda: snapshots.append(
        [(holding.symbol, holding.position) for holding in portfolio.holdings]
    )

    result = PortfolioRepository(session).replace_real_holdings(
        portfolio.id,
        [
            (
                "AAPL",
                Decimal("1500"),
                "USD",
                Decimal("10"),
                date(2026, 1, 10),
            )
        ],
    )

    assert result == portfolio.holdings
    assert snapshots == [[], [("AAPL", 0)]]
    assert result[0].weight is None
    session.commit.assert_not_called()
    session.rollback.assert_not_called()
    session.close.assert_not_called()


def test_replace_real_holdings_rejects_duplicates_before_mutation() -> None:
    session = MagicMock(spec=Session)

    with pytest.raises(ValueError, match="symbols must be unique"):
        PortfolioRepository(session).replace_real_holdings(
            uuid4(),
            [
                ("AAPL", Decimal("1"), "USD", Decimal("1"), date(2026, 1, 1)),
                ("AAPL", Decimal("2"), "USD", Decimal("2"), date(2026, 1, 2)),
            ],
        )

    session.scalars.assert_not_called()
    session.flush.assert_not_called()


def test_failed_real_replacement_can_rollback_without_losing_legacy_rows(
    database_session: Session,
) -> None:
    user = _persist_user(database_session)
    portfolio = _persist_portfolio(database_session, user)
    portfolio.holdings.append(
        Holding(symbol="BND", weight=Decimal("1"), position=0)
    )
    portfolio_id = portfolio.id
    database_session.commit()

    with pytest.raises(IntegrityError):
        PortfolioRepository(database_session).replace_real_holdings(
            portfolio_id,
            [
                (
                    "AAPL",
                    Decimal("1500"),
                    "EUR",
                    Decimal("10"),
                    date(2026, 1, 10),
                )
            ],
        )
    database_session.rollback()
    database_session.expire_all()

    loaded = PortfolioRepository(database_session).get_with_holdings(
        portfolio_id
    )
    assert loaded is not None
    assert [(holding.symbol, holding.weight) for holding in loaded.holdings] == [
        ("BND", Decimal("1.000000000000000000"))
    ]


def test_replace_planned_holdings_preserves_amounts_and_order(
    database_session: Session,
) -> None:
    user = _persist_user(database_session)
    portfolio = _persist_portfolio(
        database_session,
        user,
        portfolio_type=PortfolioType.PLANNED.value,
        plan_currency="USD",
    )

    result = PortfolioRepository(database_session).replace_planned_holdings(
        portfolio.id,
        [
            ("MSFT", Decimal("6000.000000000000")),
            ("AAPL", Decimal("4000.000000000000")),
        ],
    )

    assert result is not None
    assert [holding.symbol for holding in result] == ["MSFT", "AAPL"]
    assert [holding.proposed_amount for holding in result] == [
        Decimal("6000.000000000000"),
        Decimal("4000.000000000000"),
    ]
    assert [holding.position for holding in result] == [0, 1]
    assert all(holding.weight is None for holding in result)
    assert all(holding.shares is None for holding in result)


def test_current_and_planned_replacements_reject_wrong_portfolio_type() -> None:
    session = MagicMock(spec=Session)
    current = Portfolio(
        id=uuid4(),
        user_id=uuid4(),
        name="Current",
        portfolio_type=PortfolioType.CURRENT.value,
    )
    session.scalars.return_value.one_or_none.return_value = current

    with pytest.raises(repository_module.PortfolioTypeConflictError):
        PortfolioRepository(session).replace_planned_holdings(
            current.id,
            [("AAPL", Decimal("1000"))],
        )

    planned = Portfolio(
        id=uuid4(),
        user_id=uuid4(),
        name="Plan",
        portfolio_type=PortfolioType.PLANNED.value,
        plan_currency="USD",
    )
    session.scalars.return_value.one_or_none.return_value = planned
    with pytest.raises(repository_module.PortfolioTypeConflictError):
        PortfolioRepository(session).replace_real_holdings(
            planned.id,
            [
                (
                    "AAPL",
                    Decimal("1000"),
                    "USD",
                    Decimal("5"),
                    date(2026, 1, 1),
                )
            ],
        )


def test_replace_real_missing_portfolio_returns_none_without_flush() -> None:
    session = MagicMock(spec=Session)
    session.scalars.return_value.one_or_none.return_value = None

    result = PortfolioRepository(session).replace_real_holdings(
        uuid4(),
        [
            (
                "AAPL",
                Decimal("1500"),
                "USD",
                Decimal("10"),
                date(2026, 1, 10),
            )
        ],
    )

    assert result is None
    session.flush.assert_not_called()
    session.commit.assert_not_called()


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
