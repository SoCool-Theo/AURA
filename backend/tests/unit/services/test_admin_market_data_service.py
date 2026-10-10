from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

from pydantic import ValidationError
import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session

from backend.app.database.repositories.admin_market_data_repository import AdminMarketDataRepository
from backend.app.schemas.admin_market_data import AdminMarketDataQuery
import backend.app.services.admin_market_data_service as module


@pytest.mark.parametrize("query", [
    {"limit": 0}, {"limit": 101}, {"offset": -1}, {"offset": 10001},
    {"symbol": " "}, {"symbol": "x" * 65},
    {"date_from": date(2026, 10, 10), "date_to": date(2026, 10, 9)},
])
def test_constructed_internal_queries_validated_before_database(query):
    with patch.object(module, "AdminMarketDataRepository") as repository:
        with pytest.raises(ValidationError):
            module.AdminMarketDataService(MagicMock(spec=Session)).observations(AdminMarketDataQuery.model_construct(**query))
    repository.return_value.observations.assert_not_called()


def test_postgresql_history_binds_filters_and_projects_only_price_columns():
    session = MagicMock(spec=Session)
    session.execute.return_value.mappings.return_value.all.return_value = [{"symbol": None, "total": 0}]
    rows, total = AdminMarketDataRepository(session).observations(
        limit=25, offset=100, symbol="' OR 1=1 --", date_from=date(2026, 10, 1), date_to=date(2026, 10, 9),
    )
    assert rows == [] and total == 0
    compiled = session.execute.call_args.args[0].compile(dialect=postgresql.dialect())
    sql = str(compiled)
    assert "OR 1=1" not in sql and "' OR 1=1 --" in compiled.params.values()
    assert "market_data.date >=" in sql and "market_data.date <=" in sql
    assert "LEFT OUTER JOIN admin_prices_page ON true" in sql
    assert "admin_prices_page.date DESC, admin_prices_page.symbol ASC" in sql
    assert "users" not in sql and "password" not in sql
    session.execute.assert_called_once()


def test_postgresql_inventory_joins_latest_composite_key_without_row_multiplication():
    session = MagicMock(spec=Session)
    AdminMarketDataRepository(session).inventory()
    sql = str(session.execute.call_args.args[0].compile(dialect=postgresql.dialect()))
    assert "min(market_data.date)" in sql and "max(market_data.date)" in sql
    assert "GROUP BY market_data.symbol" in sql
    assert "market_data.symbol = admin_market_inventory.symbol AND market_data.date = admin_market_inventory.latest_price_date" in sql
    assert "JOIN users" not in sql
    session.execute.assert_called_once()
    session.commit.assert_not_called()
    session.flush.assert_not_called()


def test_price_serialization_preserves_database_decimal_precision_without_float_conversion():
    price = Decimal("1234567890123456.123456789012")
    with patch.object(module, "AdminMarketDataRepository") as repository:
        repository.return_value.observations.return_value = ([
            {"symbol": "AAPL", "date": date(2026, 10, 9), "adjusted_close": price, "volume": None, "source": "Synthetic"},
        ], 1)
        result = module.AdminMarketDataService(MagicMock(spec=Session)).observations(AdminMarketDataQuery(symbol=" aapl "))
    assert result.model_dump(mode="json")["items"][0]["adjusted_close"] == str(price)
    repository.return_value.observations.assert_called_once_with(limit=25, offset=0, symbol="AAPL", date_from=None, date_to=None)
