"""Strict public contracts for Aura's stateless AI explanations."""

from typing import Annotated, Literal
from uuid import UUID

from pydantic import BeforeValidator, Field, Strict

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


class AgentExplainRequest(AuraBaseModel):
    """Public input for a future stateless, grounded Aura explanation."""

    portfolio_id: UUID
    message: AgentMessage
    report_id: UUID | None = None
    simulation_id: UUID | None = None


class AgentSourceReference(AuraBaseModel):
    """One stored Aura resource used to ground an explanation."""

    type: AgentSourceType
    id: UUID


class AgentExplainResponse(AuraBaseModel):
    """Public, grounded result from a future Aura explanation workflow."""

    answer: AgentAnswer
    sources: Annotated[list[AgentSourceReference], Field(max_length=10)]
    limitations: Annotated[list[AgentLimitation], Field(max_length=10)]
