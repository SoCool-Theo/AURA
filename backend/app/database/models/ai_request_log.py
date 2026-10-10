"""Content-free AI request outcomes, independent of account/portfolio history."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, Index, Integer, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base


class AIRequestLog(Base):
    __tablename__ = "ai_request_logs"
    __table_args__ = (
        CheckConstraint("outcome IN ('COMPLETED', 'REFUSED', 'ERROR')", name="ck_ai_requests_outcome"),
        CheckConstraint("duration_ms >= 0 AND limitation_count BETWEEN 0 AND 10", name="ck_ai_requests_counts"),
        CheckConstraint("provider_kind IS NULL OR provider_kind IN ('openai', 'groq', 'custom')", name="ck_ai_requests_provider"),
        CheckConstraint("NOT provider_called OR provider_kind IS NOT NULL", name="ck_ai_requests_provider_call"),
        CheckConstraint("refusal_stage IS NULL OR refusal_stage IN ('INPUT', 'OUTPUT')", name="ck_ai_requests_stage"),
        CheckConstraint("guardrail_reason IS NULL OR guardrail_reason IN ('empty_message', 'investment_advice', 'invalid_output', 'output_too_long', 'system_leakage', 'planned_ownership_claim')", name="ck_ai_requests_guardrail"),
        CheckConstraint("error_code IS NULL OR error_code IN ('CONTEXT_UNAVAILABLE', 'REPORT_UNAVAILABLE', 'SIMULATION_UNAVAILABLE', 'MARKET_DATA_UNAVAILABLE', 'HOLDING_STATE_INVALID', 'PROVIDER_UNAVAILABLE', 'PROVIDER_TIMEOUT', 'INVALID_PROVIDER_RESPONSE', 'UNSAFE_PROVIDER_OUTPUT', 'INTERNAL_ERROR')", name="ck_ai_requests_error_code"),
        CheckConstraint("(outcome IN ('COMPLETED', 'REFUSED') AND http_status = 200 AND error_code IS NULL) OR (outcome = 'ERROR' AND http_status IN (404, 409, 500, 502, 503) AND error_code IS NOT NULL)", name="ck_ai_requests_http_outcome"),
        CheckConstraint("(outcome = 'REFUSED' AND refusal_stage IS NOT NULL AND guardrail_reason IS NOT NULL AND ((refusal_stage = 'INPUT' AND NOT provider_called) OR (refusal_stage = 'OUTPUT' AND provider_called))) OR (outcome != 'REFUSED' AND refusal_stage IS NULL)", name="ck_ai_requests_refusal"),
        CheckConstraint("outcome != 'COMPLETED' OR (provider_called AND guardrail_reason IS NULL)", name="ck_ai_requests_completed"),
        CheckConstraint("outcome = 'COMPLETED' OR (NOT has_portfolio_source AND NOT has_report_source AND NOT has_simulation_source AND limitation_count = 0)", name="ck_ai_requests_sources"),
        Index("ix_ai_requests_created_at", "created_at", "id"),
        Index("ix_ai_requests_outcome_created_at", "outcome", "created_at", "id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_ms: Mapped[float] = mapped_column(Float, nullable=False)
    outcome: Mapped[str] = mapped_column(Text, nullable=False)
    http_status: Mapped[int] = mapped_column(Integer, nullable=False)
    provider_kind: Mapped[str | None] = mapped_column(Text)
    provider_called: Mapped[bool] = mapped_column(Boolean, nullable=False)
    refusal_stage: Mapped[str | None] = mapped_column(Text)
    guardrail_reason: Mapped[str | None] = mapped_column(Text)
    error_code: Mapped[str | None] = mapped_column(Text)
    has_portfolio_source: Mapped[bool] = mapped_column(Boolean, nullable=False)
    has_report_source: Mapped[bool] = mapped_column(Boolean, nullable=False)
    has_simulation_source: Mapped[bool] = mapped_column(Boolean, nullable=False)
    limitation_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
