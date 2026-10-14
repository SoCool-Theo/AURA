"""Admin global report reads with frozen snapshots and existing authentication."""

from copy import deepcopy
from datetime import UTC, date, datetime, timedelta
from unittest.mock import patch
from uuid import UUID

import pytest
from sqlalchemy import event, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database.models import Analysis, AuditLog, Holding, Portfolio
from app.database.repositories.admin_report_repository import AdminReportRepository
from app.services.analysis_service import AnalysisService
from app.services.market_data_service import MarketDataService
from app.services.portfolio_valuation_service import PortfolioValuationService
from backend.tests.integration.api.test_admin_portfolio_api import directory
from backend.tests.integration.api.test_admin_user_status_api import bearer, harness
from Admin.tests.report_fixture_data import snapshots

NOW = datetime(2026, 10, 14, 12, tzinfo=UTC)


@pytest.fixture
def reports(directory):
    client, factory = directory
    examples = snapshots()
    with factory() as session:
        for existing in session.scalars(select(Analysis)):
            existing.created_at = NOW - timedelta(days=1)
        for i in range(29):
            version, snapshot = examples[i] if i < 3 else examples[0]
            session.add(Analysis(id=UUID(int=300 + i), portfolio_id=UUID(int=101 if i == 2 else 100 if i < 2 else 103),
                start_date=date(2026,1,1), end_date=date(2026,1,31), schema_version=version, result_snapshot=deepcopy(snapshot), created_at=NOW))
        session.commit()
    return client, factory


def test_metadata_pagination_without_snapshot_loading_and_empty_total(reports):
    client, _ = reports
    data = client.get('/api/admin/reports', headers=bearer()).json()
    assert data['total'] == 31 and len(data['items']) == 25
    assert [item['id'] for item in data['items']][:3] == [str(UUID(int=i)) for i in (328, 327, 326)]
    tail = client.get('/api/admin/reports', headers=bearer(), params={'offset': 25}).json()
    assert len(tail['items']) == 6 and tail['total'] == 31
    empty = client.get('/api/admin/reports', headers=bearer(), params={'offset': 10000}).json()
    assert empty['items'] == [] and empty['total'] == 31
    for item in data['items'] + tail['items']:
        assert 'report' not in item and 'result_snapshot' not in item and 'risk_score' not in item
        assert item['owner']['id'] and item['schema_version'] and item['created_at'].endswith('Z')
    for private in ('password_hash', 'phone_number', 'auth_version', 'private_snapshot'):
        assert private not in str(data) + str(tail)


@pytest.mark.parametrize('query,total', [
    ({'report_version':'V1'},27), ({'report_version':'V2'},1), ({'report_version':'V3'},1), ({'report_version':'OTHER'},2),
    ({'owner_id':str(UUID(int=3))},1), ({'portfolio_id':str(UUID(int=100))},4), ({'q':' CUSTOMER@EXAMPLE.COM '},4),
    ({'q':'%'},4), ({'q':'_'},4), ({'q':'\\'},4), ({'q':'absent'},0),
    ({'portfolio_id':str(UUID(int=999))},0), ({'report_version':'V3','owner_id':str(UUID(int=2))},0),
    ({'created_from':'2026-10-14T12:00:00Z','created_to':'2026-10-14T19:00:00+07:00'},29),
    ({'created_to':'2026-10-14T11:59:59Z'},2),
])
def test_combined_literal_filters_and_utc_bounds(reports, query, total):
    response = reports[0].get('/api/admin/reports', headers=bearer(), params=query)
    assert response.status_code == 200 and response.json()['total'] == total


@pytest.mark.parametrize('i', [0,1,2])
def test_all_versions_use_frozen_reader_without_live_queries_or_writes(reports, i):
    client, factory = reports
    identifier = UUID(int=300+i)
    with factory() as session:
        before = deepcopy(session.get(Analysis, identifier).result_snapshot)
    with patch.object(AnalysisService,'analyze',side_effect=AssertionError('new analysis')), patch.object(PortfolioValuationService,'value',side_effect=AssertionError('live valuation'),create=True), patch.object(MarketDataService,'get_latest_usd_thb_fx_observation',side_effect=AssertionError('live FX')):
        response = client.get(f'/api/admin/reports/{identifier}', headers=bearer())
    assert response.status_code == 200
    data = response.json()
    assert data['report_version'] == f'V{i+1}'
    assert data['report']['id'] == str(identifier) and data['report']['portfolio_id'] == data['portfolio_id']
    assert data['report']['analysis']['portfolio_metrics']['annualized_volatility'] == .18
    if i == 2:
        assert data['report']['baseline']['portfolio_type'] == 'PLANNED'
        assert data['report']['monetary_metrics']['reference_amount'] == '10000'
        assert data['owner']['account_type'] == 'LEGACY' and data['owner']['status'] == 'SUSPENDED'
    with factory() as session:
        assert session.get(Analysis,identifier).result_snapshot == before


def test_changed_current_portfolio_cannot_rewrite_saved_name_or_results(reports):
    client, factory = reports
    identifier = UUID(int=301)
    before = client.get(f'/api/admin/reports/{identifier}', headers=bearer()).json()
    with factory() as session:
        session.get(Portfolio, UUID(int=100)).name = 'Renamed portfolio'
        session.get(Holding, UUID(int=200)).shares = 999
        session.commit()
    after = client.get(f'/api/admin/reports/{identifier}', headers=bearer()).json()
    assert after['portfolio_name'] == 'Renamed portfolio'
    assert after['report'] == before['report']


@pytest.mark.parametrize('path',['/api/admin/reports',f'/api/admin/reports/{UUID(int=301)}',f'/api/admin/reports/{UUID(int=999)}'])
def test_permissions_before_read_or_existence(reports,path):
    client,_ = reports
    assert client.get(path).status_code == 401
    assert client.get(path,headers=bearer(2)).status_code == 403
    assert client.get(path,headers=bearer(version=1)).status_code == 401
    assert client.get(path,headers={'X-User-ID':str(UUID(int=1))}).status_code == 401


@pytest.mark.parametrize('query',[{'limit':0},{'limit':101},{'offset':-1},{'offset':10001},{'report_version':'V4'}, {'q':'x'*101},{'owner_id':'bad'},{'portfolio_id':'bad'},{'created_from':'2026-10-14T00:00:00'}, {'created_from':'2026-10-15T00:00:00Z','created_to':'2026-10-14T00:00:00Z'}])
def test_invalid_filters(reports,query):
    assert reports[0].get('/api/admin/reports',headers=bearer(),params=query).status_code == 422


def test_missing_unknown_corrupt_and_customer_ownership(reports):
    client,factory = reports
    assert client.get(f'/api/admin/reports/{UUID(int=999)}',headers=bearer()).status_code == 404
    assert client.get('/api/admin/reports/bad',headers=bearer()).status_code == 422
    assert client.get(f'/api/portfolios/{UUID(int=100)}/reports/{UUID(int=300)}',headers=bearer()).status_code == 404
    with factory() as session:
        unknown = session.scalars(select(Analysis).where(Analysis.schema_version=='synthetic')).first().id
    assert client.get(f'/api/admin/reports/{unknown}',headers=bearer()).status_code == 503
    with factory() as session:
        row = session.get(Analysis,UUID(int=300))
        row.result_snapshot = {'private_failure': 'credentials'}
        session.commit()
    response = client.get(f'/api/admin/reports/{UUID(int=300)}',headers=bearer())
    assert response.status_code == 503 and response.json() == {'detail':'Admin report details unavailable'}
    assert client.get('/api/admin/reports',headers=bearer()).status_code == 200


@pytest.mark.parametrize('method,path',[('list','/api/admin/reports'),('detail',f'/api/admin/reports/{UUID(int=301)}')])
def test_storage_failure_has_safe_feedback(reports,method,path):
    with patch.object(AdminReportRepository,method,side_effect=SQLAlchemyError('private DB secret')):
        response = reports[0].get(path,headers=bearer())
    assert response.status_code == 503 and 'private' not in response.text


def test_metadata_and_detail_use_one_snapshot_and_never_commit_or_audit(reports):
    client,factory = reports
    statements=[]
    def capture(connection,cursor,statement,parameters,context,executemany):
        statements.append(statement)
    engine=factory.kw['bind']
    event.listen(engine,'before_cursor_execute',capture)
    try:
        with patch.object(Session,'commit',side_effect=AssertionError('read committed')),patch.object(Session,'flush',side_effect=AssertionError('read wrote')):
            for path in ('/api/admin/reports',f'/api/admin/reports/{UUID(int=301)}'):
                statements.clear()
                assert client.get(path,headers=bearer()).status_code == 200
                assert len(statements) == 2
                assert all(private not in statements[-1] for private in ('password_hash','phone_number','auth_version'))
                if path.endswith('/reports'):
                    assert 'result_snapshot' not in statements[-1]
    finally:
        event.remove(engine,'before_cursor_execute',capture)
    with factory() as session:
        assert list(session.scalars(select(AuditLog))) == []
