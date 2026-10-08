"""Strict public contracts for Aura's stateless AI explanations."""

from typing import Annotated, Literal
from uuid import UUID

from pydantic import BeforeValidator, Field, Strict, model_validator

from .common import AuraBaseModel


def _normalize_required_text(value: object) -> object:
    """Trim required public text without coercing non-string input."""
    if not isinstance(value, str):
        return value

    normalized = value.strip()
    if not normalized:
        raise ValueError("text cannot be empty after normalization")
    return normalized


AgentMessage = Annotated[
    str,
    Strict(),
    BeforeValidator(_normalize_required_text),
    Field(min_length=1, max_length=4000),
]
AgentAnswer = Annotated[
    str,
    Strict(),
    BeforeValidator(_normalize_required_text),
    Field(min_length=1, max_length=8000),
]
AgentLimitation = Annotated[
    str,
    Strict(),
    BeforeValidator(_normalize_required_text),
    Field(min_length=1, max_length=1000),
]
AgentSourceType = Literal["portfolio", "report", "simulation"]
AgentConversationRole = Literal["user", "assistant"]


class AgentConversationMessage(AuraBaseModel):
    """One bounded prior chat message supplied for follow-up context."""

    role: AgentConversationRole
    content: AgentAnswer


class AgentExplainRequest(AuraBaseModel):
    """Public input for a future stateless, grounded Aura explanation."""

    portfolio_id: UUID
    message: AgentMessage
    report_id: UUID | None = None
    simulation_id: UUID | None = None
    history: list[AgentConversationMessage] = Field(default_factory=list, max_length=8)

    @model_validator(mode="after")
    def validate_completed_history_turns(self):
        """History must contain completed user/assistant pairs in order."""
        if len(self.history) % 2 != 0:
            raise ValueError("history must contain completed user/assistant pairs")
        for index, item in enumerate(self.history):
            expected_role = "user" if index % 2 == 0 else "assistant"
            if item.role != expected_role:
                raise ValueError("history must alternate user and assistant messages")
        return self


class AgentSourceReference(AuraBaseModel):
    """One stored Aura resource used to ground an explanation."""

    type: AgentSourceType
    id: UUID


class AgentExplainResponse(AuraBaseModel):
    """Public, grounded result from a future Aura explanation workflow."""

    answer: AgentAnswer
    sources: Annotated[list[AgentSourceReference], Field(max_length=10)]
    limitations: Annotated[list[AgentLimitation], Field(max_length=10)]
