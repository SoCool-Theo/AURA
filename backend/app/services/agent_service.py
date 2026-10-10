"""Application-service boundary for one owned Aura explanation."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from ..agents.agent import AuraAgent
from ..agents.provider import LLMProvider
from ..agents.tools import AuraAgentTools
from ..agents.telemetry import AgentExecutionTrace
from ..schemas.agent import AgentExplainRequest, AgentExplainResponse


class AgentService:
    """Bind trusted caller identity to the read-only Aura agent workflow."""

    def __init__(self, session: Session, provider: LLMProvider, *, trace: AgentExecutionTrace | None = None) -> None:
        self._session = session
        self._provider = provider
        self._trace = trace

    def explain(
        self,
        *,
        user_id: UUID,
        request: AgentExplainRequest,
        valuation_date: date,
    ) -> AgentExplainResponse:
        """Explain one owned portfolio without managing the session lifecycle."""
        tools = AuraAgentTools(
            self._session,
            user_id=user_id,
            portfolio_id=request.portfolio_id,
            valuation_date=valuation_date,
        )
        options = {"trace": self._trace} if self._trace is not None else {}
        return AuraAgent(tools=tools, provider=self._provider, **options).explain(request)


__all__ = ["AgentService"]
