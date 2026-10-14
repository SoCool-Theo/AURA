"""Global portfolio acceptance in this run's disposable PostgreSQL schema."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from app.database.models import Holding, Portfolio, Simulation


def check_portfolios(client, factory, password):
    login = client.post('/api/auth/login', json={'email': 'admin@example.com', 'password': password})
    admin = {'Authorization': f"Bearer {login.json()['access_token']}"}
    login = client.post('/api/auth/login', json={'email': 'customer00@example.com', 'password': password})
    customer = {'Authorization': f"Bearer {login.json()['access_token']}"}
    with factory() as session:
        session.add_all([
            Portfolio(id=UUID(int=101), user_id=UUID(int=99), name='Synthetic Planned Portfolio', portfolio_type='PLANNED', plan_currency='THB'),
            Portfolio(id=UUID(int=102), user_id=UUID(int=2), name='Synthetic Legacy Portfolio', portfolio_type='LEGACY'),
            Portfolio(id=UUID(int=103), user_id=UUID(int=1), name='Synthetic Empty Portfolio'),
            *[Portfolio(id=UUID(int=i), user_id=UUID(int=2), name=f'Synthetic Portfolio {i}') for i in range(104, 131)],
        ])
        session.flush()
        session.add_all([
            Holding(portfolio_id=UUID(int=100), symbol='MSFT', shares=Decimal('0.123456789012'), position=1),
            Holding(portfolio_id=UUID(int=100), symbol='AAPL', shares=Decimal('2.123456789012'), invested_amount=Decimal('123.456789012345'), invested_currency='USD', purchase_date=date(2026, 1, 2), position=0),
            Holding(portfolio_id=UUID(int=101), symbol='AAPL', proposed_amount=Decimal('1234567890.123456789012'), position=0),
            Holding(portfolio_id=UUID(int=102), symbol='AAPL', weight=Decimal('1'), position=0),
            *[Simulation(portfolio_id=UUID(int=100), simulation_type='allocation', scenario_id=None, requested_start_date=date(2026, 1, 1), requested_end_date=date(2026, 1, 2), schema_version='synthetic', result_snapshot={'private_snapshot': True}) for _ in range(3)],
        ])
        session.commit()
    paths = ['/api/admin/portfolios', *[f'/api/admin/portfolios/{UUID(int=i)}' for i in range(100, 104)]]
    for path in paths:
        assert client.get(path).status_code == 401
        assert client.get(path, headers=customer).status_code == 403
        assert client.get(path, headers=admin).status_code == 200
    directory = client.get(paths[0], headers=admin).json()
    tail = client.get(paths[0], headers=admin, params={'offset': 25}).json()
    assert directory['total'] == 31 and len(directory['items']) == 25 and len(tail['items']) == 6
    assert len({item['id'] for item in directory['items'] + tail['items']}) == 31
    planned = client.get(paths[0], headers=admin, params={'portfolio_type': 'PLANNED', 'owner_id': str(UUID(int=99))}).json()
    assert planned['total'] == 1 and planned['items'][0]['owner']['email'] is None
    assert client.get(paths[0], headers=admin, params={'q': 'customer00@example.com'}).json()['total'] == 29
    assert client.get(paths[0], headers=admin, params={'q': '%'}).json()['total'] == 0
    current = client.get(paths[1], headers=admin).json()
    assert [holding['symbol'] for holding in current['holdings']] == ['AAPL', 'MSFT']
    assert current['holding_count'] == 2 and current['saved_report_count'] == 8 and current['saved_simulation_count'] == 3
    assert current['holdings'][0]['shares'] == '2.123456789012'
    assert current['holdings'][0]['invested_amount'] == '123.456789012345'
    planned = client.get(paths[2], headers=admin).json()
    assert planned['holdings'][0]['proposed_amount'] == '1234567890.123456789012'
    assert client.get(paths[3], headers=admin).json()['holdings'][0]['weight'] == 1
    assert client.get(paths[4], headers=admin).json()['holdings'] == []
    assert client.get(f'/api/portfolios/{UUID(int=100)}', headers=admin).status_code == 404
    assert client.get(f'/api/admin/portfolios/{UUID(int=999)}', headers=admin).status_code == 404
    assert 'private_snapshot' not in str(current) + str(directory)
    print('PASS PostgreSQL portfolios: all modes, exact decimals, owner filters, global counts, pagination, read permissions and customer ownership', flush=True)
