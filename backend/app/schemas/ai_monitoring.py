"""Allowlisted operational metadata; never conversation text or resource identities."""

from datetime import UTC
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import AwareDatetime, Field, model_validator

from .common import AuraBaseModel


AIOutcome = Literal["COMPLETED", "REFUSED", "ERROR"]
AIProviderKind = Literal["openai", "groq", "custom"]
AIRefusalStage = Literal["INPUT", "OUTPUT"]
AIGuardrailReason = Literal["empty_message", "investment_advice", "invalid_output", "output_too_long", "system_leakage", "planned_ownership_claim"]
AIErrorCode = Literal[
    "CONTEXT_UNAVAILABLE", "REPORT_UNAVAILABLE", "SIMULATION_UNAVAILABLE",
    "MARKET_DATA_UNAVAILABLE", "HOLDING_STATE_INVALID", "PROVIDER_UNAVAILABLE",
    "PROVIDER_TIMEOUT", "INVALID_PROVIDER_RESPONSE", "UNSAFE_PROVIDER_OUTPUT", "INTERNAL_ERROR",
]


class AIRequestEvent(AuraBaseModel):
    started_at: AwareDatetime
    duration_ms: Annotated[float, Field(ge=0, allow_inf_nan=False)]
    outcome: AIOutcome
    http_status: Literal[200, 404, 409, 500, 502, 503]
    provider_kind: AIProviderKind | None
    provider_called: bool
    refusal_stage: AIRefusalStage | None = None
    guardrail_reason: AIGuardrailReason | None = None
    error_code: AIErrorCode | None = None
    has_portfolio_source: bool = False
    has_report_source: bool = False
    has_simulation_source: bool = False
    limitation_count: Annotated[int, Field(ge=0, le=10)] = 0

    @model_validator(mode="after")
    def validate_outcome(self) -> Self:
        if self.outcome == "ERROR":
            if self.http_status == 200 or self.error_code is None or self.refusal_stage is not None:
                raise ValueError("error outcome requires an HTTP error and safe error code")
        elif self.http_status != 200 or self.error_code is not None:
            raise ValueError("completed/refused outcomes require HTTP 200 without error code")
        if self.outcome == "REFUSED":
            if self.refusal_stage is None or self.guardrail_reason is None:
                raise ValueError("refused outcome requires an observed guardrail decision")
            if self.provider_called != (self.refusal_stage == "OUTPUT"):
                raise ValueError("refusal stage must agree with actual provider call")
        elif self.refusal_stage is not None:
            raise ValueError("refusal stage requires refused outcome")
        if self.outcome == "COMPLETED" and (not self.provider_called or self.guardrail_reason is not None):
            raise ValueError("completed explanation requires provider call and no rejection")
        if self.provider_called and self.provider_kind is None:
            raise ValueError("provider calls require provider kind")
        if self.outcome != "COMPLETED" and (self.has_portfolio_source or self.has_report_source or self.has_simulation_source or self.limitation_count):
            raise ValueError("only completed explanations expose returned source/limitation metadata")
        self.started_at = self.started_at.astimezone(UTC)
        return self


class AIRequestResponse(AIRequestEvent):
    id: UUID
    created_at: AwareDatetime


class AIMonitoringTimeQuery(AuraBaseModel):
    created_from: AwareDatetime | None = None
    created_to: AwareDatetime | None = None

    @model_validator(mode="after")
    def time_order(self) -> Self:
        if self.created_from is not None:
            self.created_from = self.created_from.astimezone(UTC)
        if self.created_to is not None:
            self.created_to = self.created_to.astimezone(UTC)
        if self.created_from is not None and self.created_to is not None and self.created_from > self.created_to:
            raise ValueError("created_from must be on or before created_to")
        return self


class AIRequestsQuery(AIMonitoringTimeQuery):
    limit: Annotated[int, Field(ge=1, le=100)] = 25
    offset: Annotated[int, Field(ge=0, le=10000)] = 0
    outcome: AIOutcome | None = None
    provider_kind: AIProviderKind | None = None
    refusal_stage: AIRefusalStage | None = None
    error_code: AIErrorCode | None = None


class AIRequestsListResponse(AuraBaseModel):
    items: list[AIRequestResponse]
    total: Annotated[int, Field(ge=0)]
    limit: int
    offset: int


class AIConfigurationResponse(AuraBaseModel):
    configured_provider: Literal["openai", "groq"] | None
    model_configured: bool
    credential_configured: bool
    ready: bool
    connectivity: Literal["not_checked"] = "not_checked"
    telemetry_mode: Literal["best_effort_metadata"] = "best_effort_metadata"
    advice_guard_enabled: Literal[True] = True


class AIMonitoringSummaryResponse(AuraBaseModel):
    checked_at: AwareDatetime
    configuration: AIConfigurationResponse
    total: Annotated[int, Field(ge=0)]
    completed: Annotated[int, Field(ge=0)]
    refused: Annotated[int, Field(ge=0)]
    errors: Annotated[int, Field(ge=0)]
    provider_calls: Annotated[int, Field(ge=0)]
    input_refusals: Annotated[int, Field(ge=0)]
    output_refusals: Annotated[int, Field(ge=0)]
    average_duration_ms: Annotated[float, Field(ge=0, allow_inf_nan=False)] | None
    first_recorded_at: AwareDatetime | None
    last_recorded_at: AwareDatetime | None
