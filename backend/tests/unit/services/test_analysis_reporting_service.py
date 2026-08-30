from copy import deepcopy
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, call, patch
from uuid import UUID, uuid4

import pytest
from sqlalchemy.orm import Session

from backend.app.database.models import Analysis, Holding, Portfolio
from backend.app.database.repositories import AnalysisRepository
from backend.app.schemas.analytics import PortfolioAnalysisResponse
from backend.app.schemas.common import AnalysisPeriod
from backend.app.schemas.reporting import (
    PortfolioReportListResponse,
    PortfolioReportResponse,
    PortfolioReportSummary,
)
from backend.app.services.analysis_reporting_mapper import (
    PORTFOLIO_ANALYSIS_RESPONSE_SCHEMA_VERSION,
    analysis_record_to_report_summary,
    analysis_response_to_snapshot,
)
from backend.app.services.analysis_reporting_service import (
    AnalysisReportingService,
    ReportNotFoundError,
)
from backend.app.services.analysis_service import AnalysisService
from backend.app.services.portfolio_service import PortfolioService
import backend.app.services.analysis_reporting_service as service_module
from backend.tests.unit.services.test_analysis_reporting_mapper import (
    _analysis_record,
    _valid_response,
)


_USER_ID = UUID("30000000-0000-0000-0000-000000000001")
_PORTFOLIO_ID = UUID("20000000-0000-0000-0000-000000000001")
_REPORT_ID = UUID("10000000-0000-0000-0000-000000000001")
_FIRST_WEIGHT = Decimal("0.123456789012345678")
_SECOND_WEIGHT = Decimal("0.876543210987654322")


def _portfolio() -> Portfolio:
    portfolio = Portfolio(
        id=_PORTFOLIO_ID,
        user_id=_USER_ID,
        name="Synthetic Balanced Portfolio",
    )
    portfolio.holdings.extend(
        [
            Holding(
                id=uuid4(),
                portfolio_id=portfolio.id,
                symbol="BND",
                weight=_FIRST_WEIGHT,
                position=0,
            ),
            Holding(
                id=uuid4(),
                portfolio_id=portfolio.id,
                symbol="AAPL",
                weight=_SECOND_WEIGHT,
                position=1,
            ),
        ]
    )
    return portfolio


def _period() -> AnalysisPeriod:
    return AnalysisPeriod(start_date=date(2026, 1, 1), end_date=date(2026, 1, 31))


def _service_with_dependencies() -> tuple[
    AnalysisReportingService,
    MagicMock,
    MagicMock,
    MagicMock,
    MagicMock,
]:
    session = MagicMock(spec=Session)
    portfolio_service = MagicMock(spec=PortfolioService)
    analysis_service = MagicMock(spec=AnalysisService)
    repository = MagicMock(spec=AnalysisRepository)

    with (
        patch.object(
            service_module,
            "PortfolioService",
            return_value=portfolio_service,
        ) as portfolio_service_type,
        patch.object(
            service_module,
            "AnalysisService",
            return_value=analysis_service,
        ) as analysis_service_type,
        patch.object(
            service_module,
            "AnalysisRepository",
            return_value=repository,
        ) as repository_type,
    ):
        service = AnalysisReportingService(session)

    portfolio_service_type.assert_called_once_with(session)
    analysis_service_type.assert_called_once_with(session)
    repository_type.assert_called_once_with(session)
    return service, session, portfolio_service, analysis_service, repository


def _assert_session_lifecycle_untouched(session: MagicMock) -> None:
    session.commit.assert_not_called()
    session.rollback.assert_not_called()
    session.close.assert_not_called()


def test_constructor_uses_only_the_caller_owned_session() -> None:
    service, session, _, _, _ = _service_with_dependencies()

    assert service._session is session
    _assert_session_lifecycle_untouched(session)


def test_create_report_preserves_owned_portfolio_allocation_and_period() -> None:
    service, session, portfolio_service, analysis_service, repository = (
        _service_with_dependencies()
    )
    portfolio = _portfolio()
    period = _period()
    portfolio_snapshot = [
        (holding.id, holding.symbol, holding.weight, holding.position)
        for holding in portfolio.holdings
    ]
    period_snapshot = period.model_dump()
    response = _valid_response()
    snapshot = analysis_response_to_snapshot(response)
    saved = _analysis_record(result_snapshot=snapshot)
    mapped = MagicMock(spec=PortfolioReportResponse)
    portfolio_service.get.return_value = portfolio
    analysis_service.analyze.return_value = response
    repository.save_snapshot.return_value = saved

    with (
        patch.object(
            service_module,
            "analysis_response_to_snapshot",
            return_value=snapshot,
        ) as snapshot_mapper,
        patch.object(
            service_module,
            "analysis_record_to_report_response",
            return_value=mapped,
        ) as report_mapper,
    ):
        result = service.create_report(
            user_id=_USER_ID,
            portfolio_id=_PORTFOLIO_ID,
            period=period,
        )

    assert result is mapped
    portfolio_service.get.assert_called_once_with(
        user_id=_USER_ID,
        portfolio_id=_PORTFOLIO_ID,
    )
    analysis_service.analyze.assert_called_once()
    request = analysis_service.analyze.call_args.args[0]
    assert request.portfolio_name == portfolio.name
    assert [holding.symbol for holding in request.holdings] == ["BND", "AAPL"]
    assert [holding.weight for holding in request.holdings] == [
        float(_FIRST_WEIGHT),
        float(_SECOND_WEIGHT),
    ]
    assert request.start_date == period.start_date
    assert request.end_date == period.end_date
    snapshot_mapper.assert_called_once_with(response)
    repository.save_snapshot.assert_called_once_with(
        portfolio_id=portfolio.id,
        start_date=response.start_date,
        end_date=response.end_date,
        schema_version=PORTFOLIO_ANALYSIS_RESPONSE_SCHEMA_VERSION,
        result_snapshot=snapshot,
    )
    report_mapper.assert_called_once_with(saved)
    assert [
        (holding.id, holding.symbol, holding.weight, holding.position)
        for holding in portfolio.holdings
    ] == portfolio_snapshot
    assert period.model_dump() == period_snapshot
    _assert_session_lifecycle_untouched(session)


def test_create_report_analyzes_before_snapshot_and_persistence() -> None:
    service, session, portfolio_service, analysis_service, repository = (
        _service_with_dependencies()
    )
    response = _valid_response()
    snapshot = analysis_response_to_snapshot(response)
    saved = _analysis_record(result_snapshot=snapshot)
    events: list[str] = []
    portfolio_service.get.return_value = _portfolio()
    analysis_service.analyze.side_effect = lambda request: (
        events.append("analyze") or response
    )
    repository.save_snapshot.side_effect = lambda **kwargs: (
        events.append("save") or saved
    )

    with (
        patch.object(
            service_module,
            "analysis_response_to_snapshot",
            side_effect=lambda result: events.append("snapshot") or snapshot,
        ),
        patch.object(
            service_module,
            "analysis_record_to_report_response",
            side_effect=lambda record: events.append("map") or MagicMock(
                spec=PortfolioReportResponse
            ),
        ),
    ):
        service.create_report(
            user_id=_USER_ID,
            portfolio_id=_PORTFOLIO_ID,
            period=_period(),
        )

    assert events == ["analyze", "snapshot", "save", "map"]
    _assert_session_lifecycle_untouched(session)


def test_create_report_analysis_failure_never_persists_and_propagates() -> None:
    service, session, portfolio_service, analysis_service, repository = (
        _service_with_dependencies()
    )
    failure = ValueError("market data is unavailable")
    portfolio_service.get.return_value = _portfolio()
    analysis_service.analyze.side_effect = failure

    with (
        patch.object(
            service_module,
            "analysis_response_to_snapshot",
        ) as snapshot_mapper,
        patch.object(
            service_module,
            "analysis_record_to_report_response",
        ) as report_mapper,
        pytest.raises(ValueError) as raised,
    ):
        service.create_report(
            user_id=_USER_ID,
            portfolio_id=_PORTFOLIO_ID,
            period=_period(),
        )

    assert raised.value is failure
    analysis_service.analyze.assert_called_once()
    snapshot_mapper.assert_not_called()
    repository.save_snapshot.assert_not_called()
    report_mapper.assert_not_called()
    _assert_session_lifecycle_untouched(session)


def test_create_report_missing_or_wrong_owner_returns_none_without_analysis() -> None:
    service, session, portfolio_service, analysis_service, repository = (
        _service_with_dependencies()
    )
    portfolio_service.get.return_value = None

    result = service.create_report(
        user_id=_USER_ID,
        portfolio_id=_PORTFOLIO_ID,
        period=_period(),
    )

    assert result is None
    analysis_service.analyze.assert_not_called()
    repository.save_snapshot.assert_not_called()
    _assert_session_lifecycle_untouched(session)


def test_list_reports_verifies_ownership_and_preserves_repository_order() -> None:
    service, session, portfolio_service, _, repository = (
        _service_with_dependencies()
    )
    portfolio = _portfolio()
    first = _analysis_record()
    second = _analysis_record()
    second.id = UUID("10000000-0000-0000-0000-000000000002")
    first_summary = analysis_record_to_report_summary(first)
    second_summary = analysis_record_to_report_summary(second)
    events: list[str] = []
    portfolio_service.get.side_effect = lambda **kwargs: (
        events.append("ownership") or portfolio
    )
    repository.list_for_portfolio.side_effect = lambda portfolio_id: (
        events.append("list") or [second, first]
    )

    with patch.object(
        service_module,
        "analysis_record_to_report_summary",
        side_effect=[second_summary, first_summary],
    ) as summary_mapper:
        result = service.list_reports(
            user_id=_USER_ID,
            portfolio_id=_PORTFOLIO_ID,
        )

    assert isinstance(result, PortfolioReportListResponse)
    assert result.reports == [second_summary, first_summary]
    assert events == ["ownership", "list"]
    repository.list_for_portfolio.assert_called_once_with(portfolio.id)
    assert summary_mapper.call_args_list == [call(second), call(first)]
    _assert_session_lifecycle_untouched(session)


def test_list_reports_empty_history_returns_valid_empty_response() -> None:
    service, session, portfolio_service, _, repository = (
        _service_with_dependencies()
    )
    portfolio_service.get.return_value = _portfolio()
    repository.list_for_portfolio.return_value = []

    result = service.list_reports(
        user_id=_USER_ID,
        portfolio_id=_PORTFOLIO_ID,
    )

    assert isinstance(result, PortfolioReportListResponse)
    assert result.reports == []
    _assert_session_lifecycle_untouched(session)


def test_list_reports_unowned_portfolio_returns_none_before_repository() -> None:
    service, session, portfolio_service, _, repository = (
        _service_with_dependencies()
    )
    portfolio_service.get.return_value = None

    result = service.list_reports(
        user_id=_USER_ID,
        portfolio_id=_PORTFOLIO_ID,
    )

    assert result is None
    repository.list_for_portfolio.assert_not_called()
    _assert_session_lifecycle_untouched(session)


def test_get_report_verifies_parent_and_returns_associated_report() -> None:
    service, session, portfolio_service, _, repository = (
        _service_with_dependencies()
    )
    portfolio = _portfolio()
    analysis = _analysis_record()
    mapped = MagicMock(spec=PortfolioReportResponse)
    events: list[str] = []
    portfolio_service.get.side_effect = lambda **kwargs: (
        events.append("ownership") or portfolio
    )
    repository.get_by_id.side_effect = lambda report_id: (
        events.append("get") or analysis
    )

    with patch.object(
        service_module,
        "analysis_record_to_report_response",
        return_value=mapped,
    ) as report_mapper:
        result = service.get_report(
            user_id=_USER_ID,
            portfolio_id=_PORTFOLIO_ID,
            report_id=_REPORT_ID,
        )

    assert result is mapped
    assert events == ["ownership", "get"]
    portfolio_service.get.assert_called_once_with(
        user_id=_USER_ID,
        portfolio_id=_PORTFOLIO_ID,
    )
    repository.get_by_id.assert_called_once_with(_REPORT_ID)
    report_mapper.assert_called_once_with(analysis)
    _assert_session_lifecycle_untouched(session)


@pytest.mark.parametrize("report_state", ["missing", "different-portfolio"])
def test_get_report_missing_and_different_portfolio_are_identical_not_found(
    report_state: str,
) -> None:
    service, session, portfolio_service, _, repository = (
        _service_with_dependencies()
    )
    portfolio_service.get.return_value = _portfolio()
    if report_state == "missing":
        repository.get_by_id.return_value = None
    else:
        analysis = _analysis_record()
        analysis.portfolio_id = uuid4()
        repository.get_by_id.return_value = analysis

    with (
        patch.object(
            service_module,
            "analysis_record_to_report_response",
        ) as report_mapper,
        pytest.raises(ReportNotFoundError),
    ):
        service.get_report(
            user_id=_USER_ID,
            portfolio_id=_PORTFOLIO_ID,
            report_id=_REPORT_ID,
        )

    report_mapper.assert_not_called()
    _assert_session_lifecycle_untouched(session)


@pytest.mark.parametrize("portfolio_state", ["missing", "wrong-owner"])
def test_get_report_unowned_parent_returns_none_before_report_lookup(
    portfolio_state: str,
) -> None:
    service, session, portfolio_service, _, repository = (
        _service_with_dependencies()
    )
    portfolio_service.get.return_value = None

    result = service.get_report(
        user_id=_USER_ID,
        portfolio_id=_PORTFOLIO_ID,
        report_id=_REPORT_ID,
    )

    assert result is None
    repository.get_by_id.assert_not_called()
    _assert_session_lifecycle_untouched(session)


def test_delete_report_validates_association_then_delegates_delete() -> None:
    service, session, portfolio_service, _, repository = (
        _service_with_dependencies()
    )
    portfolio = _portfolio()
    analysis = _analysis_record()
    events: list[str] = []
    portfolio_service.get.side_effect = lambda **kwargs: (
        events.append("ownership") or portfolio
    )
    repository.get_by_id.side_effect = lambda report_id: (
        events.append("get") or analysis
    )
    repository.delete.side_effect = lambda report_id: (
        events.append("delete") or True
    )

    result = service.delete_report(
        user_id=_USER_ID,
        portfolio_id=_PORTFOLIO_ID,
        report_id=_REPORT_ID,
    )

    assert result is True
    assert events == ["ownership", "get", "delete"]
    portfolio_service.get.assert_called_once_with(
        user_id=_USER_ID,
        portfolio_id=_PORTFOLIO_ID,
    )
    repository.get_by_id.assert_called_once_with(_REPORT_ID)
    repository.delete.assert_called_once_with(_REPORT_ID)
    _assert_session_lifecycle_untouched(session)


@pytest.mark.parametrize("report_state", ["missing", "different-portfolio"])
def test_delete_report_missing_and_wrong_association_are_identical_not_found(
    report_state: str,
) -> None:
    service, session, portfolio_service, _, repository = (
        _service_with_dependencies()
    )
    portfolio_service.get.return_value = _portfolio()
    if report_state == "missing":
        repository.get_by_id.return_value = None
    else:
        analysis = _analysis_record()
        analysis.portfolio_id = uuid4()
        repository.get_by_id.return_value = analysis

    with pytest.raises(ReportNotFoundError):
        service.delete_report(
            user_id=_USER_ID,
            portfolio_id=_PORTFOLIO_ID,
            report_id=_REPORT_ID,
        )

    repository.delete.assert_not_called()
    _assert_session_lifecycle_untouched(session)


@pytest.mark.parametrize("portfolio_state", ["missing", "wrong-owner"])
def test_delete_report_unowned_parent_returns_none_before_report_lookup(
    portfolio_state: str,
) -> None:
    service, session, portfolio_service, _, repository = (
        _service_with_dependencies()
    )
    portfolio_service.get.return_value = None

    result = service.delete_report(
        user_id=_USER_ID,
        portfolio_id=_PORTFOLIO_ID,
        report_id=_REPORT_ID,
    )

    assert result is None
    repository.get_by_id.assert_not_called()
    repository.delete.assert_not_called()
    _assert_session_lifecycle_untouched(session)


def test_delete_report_missing_during_repository_delete_is_not_found() -> None:
    service, session, portfolio_service, _, repository = (
        _service_with_dependencies()
    )
    portfolio_service.get.return_value = _portfolio()
    repository.get_by_id.return_value = _analysis_record()
    repository.delete.return_value = False

    with pytest.raises(ReportNotFoundError):
        service.delete_report(
            user_id=_USER_ID,
            portfolio_id=_PORTFOLIO_ID,
            report_id=_REPORT_ID,
        )

    repository.delete.assert_called_once_with(_REPORT_ID)
    _assert_session_lifecycle_untouched(session)
