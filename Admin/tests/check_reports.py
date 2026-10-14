"""Immutable report browsing checks in the guarded disposable PostgreSQL schema."""

from copy import deepcopy
from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import select

from app.database.models import Analysis, Portfolio
from report_fixture_data import snapshots


def check_reports(client, factory, password):
    login = client.post('/api/auth/login', json={'email':'admin@example.com','password':password})
    admin = {'Authorization':f"Bearer {login.json()['access_token']}"}
    login = client.post('/api/auth/login', json={'email':'customer00@example.com','password':password})
    customer = {'Authorization':f"Bearer {login.json()['access_token']}"}
    now = datetime.now(UTC)
    examples = snapshots()
    with factory() as session:
        for i in range(29):
            version, snapshot = examples[i] if i < 3 else examples[0]
            session.add(Analysis(id=UUID(int=600+i),portfolio_id=UUID(int=101 if i==2 else 100),
                start_date=date(2026,1,1),end_date=date(2026,1,31),schema_version=version,result_snapshot=deepcopy(snapshot),created_at=now))
        session.commit()
    directory = client.get('/api/admin/reports',headers=admin).json()
    tail = client.get('/api/admin/reports',headers=admin,params={'offset':25}).json()
    assert directory['total']==37 and len(directory['items'])==25 and len(tail['items'])==12
    assert len({item['id'] for item in directory['items']+tail['items']})==37
    assert all('result_snapshot' not in item and 'report' not in item for item in directory['items'])
    assert client.get('/api/admin/reports',headers=admin,params={'report_version':'OTHER'}).json()['total']==8
    assert client.get('/api/admin/reports',headers=admin,params={'report_version':'V3','owner_id':str(UUID(int=99))}).json()['total']==1
    assert client.get('/api/admin/reports',headers=admin,params={'created_from':now.isoformat(),'created_to':now.isoformat()}).json()['total']==29
    assert client.get('/api/admin/reports',headers=admin,params={'q':'%'}).json()['total']==0
    for i in range(3):
        path=f'/api/admin/reports/{UUID(int=600+i)}'
        assert client.get(path).status_code==401 and client.get(path,headers=customer).status_code==403
        response=client.get(path,headers=admin)
        assert response.status_code==200 and response.json()['report_version']==f'V{i+1}'
        assert response.json()['report']['analysis']['portfolio_metrics']['annualized_volatility']==.18
    planned=client.get(f'/api/admin/reports/{UUID(int=602)}',headers=admin).json()
    assert planned['report']['baseline']['holdings'][0]['proposed_amount']=='5000'
    assert planned['report']['monetary_metrics']['reference_amount']=='10000'
    assert client.get(f'/api/portfolios/{UUID(int=100)}/reports/{UUID(int=600)}',headers=admin).status_code==404
    path=f'/api/admin/reports/{UUID(int=601)}'
    before=client.get(path,headers=admin).json()['report']
    with factory() as session:
        saved=deepcopy(session.get(Analysis,UUID(int=601)).result_snapshot)
        parent=session.get(Portfolio,UUID(int=100))
        previous_name=parent.name
        parent.name='Synthetic renamed portfolio'
        session.commit()
    after=client.get(path,headers=admin).json()
    assert after['portfolio_name']=='Synthetic renamed portfolio' and after['report']==before
    with factory() as session:
        assert session.get(Analysis,UUID(int=601)).result_snapshot==saved
        session.get(Portfolio,UUID(int=100)).name=previous_name
        unknown=session.scalars(select(Analysis).where(Analysis.schema_version=='synthetic')).first().id
        session.commit()
    assert client.get(f'/api/admin/reports/{unknown}',headers=admin).status_code==503
    assert client.get(f'/api/admin/reports/{UUID(int=999)}',headers=admin).status_code==404
    print('PASS PostgreSQL reports: all frozen versions, metadata pagination, owner/time filters, immutable snapshot after portfolio edit and safe unsupported format',flush=True)
