"""Application-service boundary for one owned Aura explanation."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from ..agents.agent import AuraAgent
from ..agents.provider import LLMProvider
from ..agents.tools import AuraAgentTools
from ..schemas.agent import AgentExplainRequest, AgentExplainResponse


class AgentService:
    """Bind trusted caller identity to the read-only Aura agent workflow."""

    def __init__(self, session: Session, provider: LLMProvider) -> None:
        self._session = session
        self._provider = provider

    def explain(
        self,
        *,
        user_id: UUID,
        request: AgentExplainRequest,
    ) -> AgentExplainResponse:
        """Explain one owned portfolio without managing the session lifecycle."""
        tools = AuraAgentTools(
            self._session,
            user_id=user_id,
            portfolio_id=request.portfolio_id,
        )
        return AuraAgent(tools=tools, provider=self._provider).explain(request)


__all__ = ["AgentService"]
