"""Request-local, content-free observations of the actual agent decisions."""

from dataclasses import dataclass
from typing import Literal

from .guardrails import GuardrailReason


@dataclass(slots=True)
class AgentExecutionTrace:
    provider_called: bool = False
    refusal_stage: Literal["INPUT", "OUTPUT"] | None = None
    guardrail_reason: GuardrailReason | None = None
