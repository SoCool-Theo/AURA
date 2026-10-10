"""Safe metadata recording and admin monitoring without provider probes."""

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from ..core.config import settings
from ..database.repositories.ai_monitoring_repository import AIMonitoringRepository
from ..schemas.ai_monitoring import (
    AIConfigurationResponse, AIMonitoringSummaryResponse, AIMonitoringTimeQuery,
    AIRequestEvent, AIRequestResponse, AIRequestsListResponse, AIRequestsQuery,
)


def _utc(value):
    if value is None:
        return None
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class AIMonitoringService:
    def __init__(self, session: Session) -> None:
        self._repository = AIMonitoringRepository(session)

    def record(self, event: AIRequestEvent):
        validated = AIRequestEvent.model_validate(event.model_dump())
        return self._repository.record(**validated.model_dump())

    def list(self, query: AIRequestsQuery) -> AIRequestsListResponse:
        validated = AIRequestsQuery.model_validate(query.model_dump())
        rows, total = self._repository.list(**validated.model_dump())
        items = []
        for row in rows:
            values = {name: getattr(row, name) for name in AIRequestResponse.model_fields}
            values["started_at"] = _utc(row.started_at)
            values["created_at"] = _utc(row.created_at)
            items.append(AIRequestResponse(**values))
        return AIRequestsListResponse(items=items, total=total, limit=validated.limit, offset=validated.offset)

    def summary(self, query: AIMonitoringTimeQuery) -> AIMonitoringSummaryResponse:
        validated = AIMonitoringTimeQuery.model_validate(query.model_dump())
        values = dict(self._repository.summary(**validated.model_dump()))
        for field in ["first_recorded_at", "last_recorded_at"]:
            values[field] = _utc(values[field])
        provider = settings.aura_llm_provider
        key = settings.openai_api_key if provider == "openai" else settings.groq_api_key if provider == "groq" else None
        credential = key is not None and bool(key.get_secret_value().strip())
        model = bool(settings.aura_llm_model and settings.aura_llm_model.strip())
        return AIMonitoringSummaryResponse(
            checked_at=datetime.now(UTC), **values,
            configuration=AIConfigurationResponse(
                configured_provider=provider, model_configured=model, credential_configured=credential,
                ready=provider is not None and model and credential,
            ),
        )
