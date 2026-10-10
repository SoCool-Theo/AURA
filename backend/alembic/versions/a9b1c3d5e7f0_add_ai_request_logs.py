"""Add content-free AI monitoring outcomes."""

from alembic import op
import sqlalchemy as sa

revision = "a9b1c3d5e7f0"
down_revision = "f8a0b2c4d6e9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_request_logs",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_ms", sa.Float(), nullable=False),
        sa.Column("outcome", sa.Text(), nullable=False),
        sa.Column("http_status", sa.Integer(), nullable=False),
        sa.Column("provider_kind", sa.Text(), nullable=True),
        sa.Column("provider_called", sa.Boolean(), nullable=False),
        sa.Column("refusal_stage", sa.Text(), nullable=True),
        sa.Column("guardrail_reason", sa.Text(), nullable=True),
        sa.Column("error_code", sa.Text(), nullable=True),
        sa.Column("has_portfolio_source", sa.Boolean(), nullable=False),
        sa.Column("has_report_source", sa.Boolean(), nullable=False),
        sa.Column("has_simulation_source", sa.Boolean(), nullable=False),
        sa.Column("limitation_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("outcome IN ('COMPLETED', 'REFUSED', 'ERROR')", name="ck_ai_requests_outcome"),
        sa.CheckConstraint("duration_ms >= 0 AND limitation_count BETWEEN 0 AND 10", name="ck_ai_requests_counts"),
        sa.CheckConstraint("provider_kind IS NULL OR provider_kind IN ('openai', 'groq', 'custom')", name="ck_ai_requests_provider"),
        sa.CheckConstraint("NOT provider_called OR provider_kind IS NOT NULL", name="ck_ai_requests_provider_call"),
        sa.CheckConstraint("refusal_stage IS NULL OR refusal_stage IN ('INPUT', 'OUTPUT')", name="ck_ai_requests_stage"),
        sa.CheckConstraint("guardrail_reason IS NULL OR guardrail_reason IN ('empty_message', 'investment_advice', 'invalid_output', 'output_too_long', 'system_leakage', 'planned_ownership_claim')", name="ck_ai_requests_guardrail"),
        sa.CheckConstraint("error_code IS NULL OR error_code IN ('CONTEXT_UNAVAILABLE', 'REPORT_UNAVAILABLE', 'SIMULATION_UNAVAILABLE', 'MARKET_DATA_UNAVAILABLE', 'HOLDING_STATE_INVALID', 'PROVIDER_UNAVAILABLE', 'PROVIDER_TIMEOUT', 'INVALID_PROVIDER_RESPONSE', 'UNSAFE_PROVIDER_OUTPUT', 'INTERNAL_ERROR')", name="ck_ai_requests_error_code"),
        sa.CheckConstraint("(outcome IN ('COMPLETED', 'REFUSED') AND http_status = 200 AND error_code IS NULL) OR (outcome = 'ERROR' AND http_status IN (404, 409, 500, 502, 503) AND error_code IS NOT NULL)", name="ck_ai_requests_http_outcome"),
        sa.CheckConstraint("(outcome = 'REFUSED' AND refusal_stage IS NOT NULL AND guardrail_reason IS NOT NULL AND ((refusal_stage = 'INPUT' AND NOT provider_called) OR (refusal_stage = 'OUTPUT' AND provider_called))) OR (outcome != 'REFUSED' AND refusal_stage IS NULL)", name="ck_ai_requests_refusal"),
        sa.CheckConstraint("outcome != 'COMPLETED' OR (provider_called AND guardrail_reason IS NULL)", name="ck_ai_requests_completed"),
        sa.CheckConstraint("outcome = 'COMPLETED' OR (NOT has_portfolio_source AND NOT has_report_source AND NOT has_simulation_source AND limitation_count = 0)", name="ck_ai_requests_sources"),
    )
    op.create_index("ix_ai_requests_created_at", "ai_request_logs", ["created_at", "id"])
    op.create_index("ix_ai_requests_outcome_created_at", "ai_request_logs", ["outcome", "created_at", "id"])


def downgrade() -> None:
    op.drop_index("ix_ai_requests_outcome_created_at", table_name="ai_request_logs")
    op.drop_index("ix_ai_requests_created_at", table_name="ai_request_logs")
    op.drop_table("ai_request_logs")
