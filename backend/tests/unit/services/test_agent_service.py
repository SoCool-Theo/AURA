from unittest.mock import MagicMock, patch
from datetime import date
from uuid import UUID, uuid4

import pytest
from sqlalchemy.orm import Session

import backend.app.services.agent_service as service_module
from backend.app.agents.agent import AuraAgentContextUnavailableError, AuraAgentOutputError
from backend.app.agents.provider import (
    LLMProviderResponseError,
    LLMProviderTimeoutError,
    LLMProviderUnavailableError,
    ProviderRequest,
    ProviderResponse,
)
from backend.app.schemas.agent import AgentExplainRequest, AgentExplainResponse
from backend.app.services.agent_service import AgentService
from backend.app.services.analysis_reporting_service import ReportNotFoundError
from backend.app.services.simulation_history_service import SimulationNotFoundError


_USER_ID = UUID("40000000-0000-0000-0000-000000000001")
_PORTFOLIO_ID = UUID("20000000-0000-0000-0000-000000000001")
_VALUATION_DATE = date(2026, 9, 12)


def _request(portfolio_id: UUID = _PORTFOLIO_ID) -> AgentExplainRequest:
    return AgentExplainRequest(
        portfolio_id=portfolio_id,
        message="Explain my portfolio risk.",
    )


def _response() -> AgentExplainResponse:
    return AgentExplainResponse(
        answer="Aura explains a stored risk result.",
        sources=[],
        limitations=[],
    )


def _assert_session_lifecycle_untouched(session: MagicMock) -> None:
    session.commit.assert_not_called()
    session.rollback.assert_not_called()
    session.close.assert_not_called()
    session.flush.assert_not_called()


def test_service_binds_trusted_identity_and_delegates_once() -> None:
    session = MagicMock(spec=Session)
    provider = MagicMock(spec=service_module.LLMProvider)
    tools = MagicMock(spec=service_module.AuraAgentTools)
    agent = MagicMock(spec=service_module.AuraAgent)
    response = _response()
    agent.explain.return_value = response
    tools_type = MagicMock(return_value=tools)
    agent_type = MagicMock(return_value=agent)

    with (
        patch.object(service_module, "AuraAgentTools", tools_type),
        patch.object(service_module, "AuraAgent", agent_type),
    ):
        result = AgentService(session, provider).explain(
            user_id=_USER_ID,
            request=_request(),
            valuation_date=_VALUATION_DATE,
        )

    tools_type.assert_called_once_with(
        session,
        user_id=_USER_ID,
        portfolio_id=_PORTFOLIO_ID,
        valuation_date=_VALUATION_DATE,
    )
    agent_type.assert_called_once_with(tools=tools, provider=provider)
    agent.explain.assert_called_once()
    assert agent.explain.call_args.args[0].portfolio_id == _PORTFOLIO_ID
    assert result is response
    _assert_session_lifecycle_untouched(session)


def test_service_invocations_do_not_share_user_or_portfolio_binding() -> None:
    session = MagicMock(spec=Session)
    provider = MagicMock(spec=service_module.LLMProvider)
    tools_type = MagicMock()
    agent = MagicMock(spec=service_module.AuraAgent)
    agent.explain.return_value = _response()
    agent_type = MagicMock(return_value=agent)
    other_user_id = uuid4()
    other_portfolio_id = uuid4()

    with (
        patch.object(service_module, "AuraAgentTools", tools_type),
        patch.object(service_module, "AuraAgent", agent_type),
    ):
        service = AgentService(session, provider)
        service.explain(
            user_id=_USER_ID,
            request=_request(),
            valuation_date=_VALUATION_DATE,
        )
        service.explain(
            user_id=other_user_id,
            request=_request(other_portfolio_id),
            valuation_date=_VALUATION_DATE,
        )

    assert tools_type.call_args_list[0].kwargs == {
        "user_id": _USER_ID,
        "portfolio_id": _PORTFOLIO_ID,
        "valuation_date": _VALUATION_DATE,
    }
    assert tools_type.call_args_list[1].kwargs == {
        "user_id": other_user_id,
        "portfolio_id": other_portfolio_id,
        "valuation_date": _VALUATION_DATE,
    }
    assert all(call.args == (session,) for call in tools_type.call_args_list)
    _assert_session_lifecycle_untouched(session)


@pytest.mark.parametrize(
    "failure",
    [
        AuraAgentContextUnavailableError(),
        ReportNotFoundError(),
        SimulationNotFoundError("Simulation not found"),
        LLMProviderTimeoutError(),
        LLMProviderUnavailableError(),
        LLMProviderResponseError(),
        AuraAgentOutputError(),
    ],
)
def test_service_propagates_agent_and_provider_errors_unchanged(
    failure: Exception,
) -> None:
    session = MagicMock(spec=Session)
    provider = MagicMock(spec=service_module.LLMProvider)
    agent = MagicMock(spec=service_module.AuraAgent)
    agent.explain.side_effect = failure

    with (
        patch.object(service_module, "AuraAgentTools"),
        patch.object(service_module, "AuraAgent", return_value=agent),
    ):
        with pytest.raises(type(failure)) as raised:
            AgentService(session, provider).explain(
                user_id=_USER_ID,
                request=_request(),
                valuation_date=_VALUATION_DATE,
            )

    assert raised.value is failure
    _assert_session_lifecycle_untouched(session)


def test_service_rejects_untrusted_identity_keywords() -> None:
    session = MagicMock(spec=Session)
    provider = MagicMock(spec=service_module.LLMProvider)
    service = AgentService(session, provider)

    with pytest.raises(TypeError):
        service.explain(email="user@example.com", request=_request())  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        service.explain(x_user_id=_USER_ID, request=_request())  # type: ignore[call-arg]

    _assert_session_lifecycle_untouched(session)


class _FakeTools:
    def __init__(
        self,
        session: Session,
        *,
        user_id: UUID,
        portfolio_id: UUID,
        valuation_date: date,
    ) -> None:
        self.session = session
        self.user_id = user_id
        self.portfolio_id = portfolio_id
        self.valuation_date = valuation_date

    def get_portfolio_context(
        self,
        *,
        resolve_current_baseline: bool = True,
    ) -> dict[str, object]:
        return {"id": str(self.portfolio_id), "name": "Core", "holdings": []}

    def get_latest_report(self) -> dict[str, object]:
        return {"available": False}

    def get_report(self, report_id: UUID) -> dict[str, object]:
        raise AssertionError("specific report was not requested")

    def get_simulation(self, simulation_id: UUID) -> dict[str, object]:
        raise AssertionError("simulation was not requested")


class _FakeProvider:
    def __init__(self) -> None:
        self.requests: list[ProviderRequest] = []

    def generate(self, request: ProviderRequest) -> ProviderResponse:
        self.requests.append(request)
        return ProviderResponse("Aura explains the available portfolio context.")


def test_service_integrates_real_agent_with_bound_fake_tools_and_provider() -> None:
    session = MagicMock(spec=Session)
    provider = _FakeProvider()

    with patch.object(service_module, "AuraAgentTools", _FakeTools):
        response = AgentService(session, provider).explain(
            user_id=_USER_ID,
            request=_request(),
            valuation_date=_VALUATION_DATE,
        )

    assert response.answer == "Aura explains the available portfolio context."
    assert len(provider.requests) == 1
    assert provider.requests[0].grounded_context == {
        "portfolio": {"id": str(_PORTFOLIO_ID), "name": "Core", "holdings": []},
        "report": {"available": False},
        "simulation": None,
    }
    _assert_session_lifecycle_untouched(session)
