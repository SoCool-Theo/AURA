"""Authenticated Aura explanations with best-effort, content-free monitoring."""

from datetime import UTC, date, datetime
import logging
from time import perf_counter

from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.agents.agent import AuraAgentContextUnavailableError, AuraAgentOutputError
from app.agents.groq_provider import GroqProvider
from app.agents.openai_provider import OpenAIProvider
from app.agents.provider import (
    LLMProvider,
    LLMProviderResponseError,
    LLMProviderTimeoutError,
    LLMProviderUnavailableError,
)
from app.agents.telemetry import AgentExecutionTrace
from app.api.dependencies import CurrentUser, DatabaseSession
from app.core.config import settings
from app.schemas.agent import AgentExplainRequest, AgentExplainResponse
from app.schemas.ai_monitoring import AIRequestEvent
from app.services.ai_monitoring_service import AIMonitoringService
from app.services.agent_service import AgentService
from app.services.analysis_reporting_service import ReportNotFoundError
from app.services.market_data_service import MarketDataUnavailableError
from app.services.portfolio_valuation_service import (
    InvalidHoldingModeError,
    InvalidPortfolioValueError,
    UnsupportedHoldingInstrumentError,
)
from app.services.simulation_history_service import SimulationNotFoundError


router = APIRouter(prefix="/agent", tags=["Agent"])
logger = logging.getLogger(__name__)


def _current_utc_date() -> date:
    """Capture one current UTC calendar date per explanation request."""
    return datetime.now(UTC).date()


def _provider_unavailable() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="AI explanation service is currently unavailable.",
    )


def _invalid_provider_response() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="AI explanation service returned an invalid response.",
    )


def _portfolio_not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Portfolio not found",
    )


def _report_not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Report not found",
    )


def _simulation_not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Simulation not found",
    )


def _internal_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Unable to explain portfolio risk",
    )


def _portfolio_holding_conflict() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Portfolio cannot be explained in its current holding state",
    )


def _current_market_data_unavailable() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Required current market data is unavailable",
    )


def get_agent_provider() -> LLMProvider:
    """Create the configured provider only for AI explanation requests."""
    provider_name = settings.aura_llm_provider
    if provider_name is None or settings.aura_llm_model is None:
        raise _provider_unavailable()

    if provider_name == "openai":
        api_key = settings.openai_api_key
        provider_type = OpenAIProvider
    else:
        api_key = settings.groq_api_key
        provider_type = GroqProvider

    if api_key is None or not api_key.get_secret_value().strip():
        raise _provider_unavailable()
    try:
        return provider_type(
            api_key=api_key.get_secret_value(),
            model=settings.aura_llm_model,
            timeout_seconds=settings.aura_llm_timeout_seconds,
            max_output_tokens=settings.aura_llm_max_output_tokens,
        )
    except ValueError as error:
        raise _provider_unavailable() from error


def _store_monitoring(session: Session, **values) -> None:
    """API-owned commit; telemetry failure must preserve the primary response."""
    try:
        AIMonitoringService(session).record(AIRequestEvent(**values))
        session.commit()
    except Exception:
        try:
            session.rollback()
        except Exception:
            pass
        # Never log payloads, exception strings, SQL, or connection details.
        logger.warning("AI monitoring metadata could not be stored")


@router.post(
    "/explain",
    response_model=AgentExplainResponse,
    status_code=status.HTTP_200_OK,
)
def explain(
    request: AgentExplainRequest,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> AgentExplainResponse:
    """Explain only data owned by the authenticated Aura user."""
    started_at = datetime.now(UTC)
    started = perf_counter()
    trace = AgentExecutionTrace()
    provider_kind = settings.aura_llm_provider
    response = None
    problem = None
    failure = None
    code = None
    try:
        # Resolve after auth/body validation so unavailable configuration is
        # observed alongside other handler outcomes, without logging bad bodies.
        provider = get_agent_provider()
        provider_kind = "groq" if isinstance(provider, GroqProvider) else "openai" if isinstance(provider, OpenAIProvider) else "custom"
        response = AgentService(session, provider, trace=trace).explain(
            user_id=current_user.id,
            request=request,
            valuation_date=_current_utc_date(),
        )
    except Exception as error:
        failure = error
        if isinstance(error, AuraAgentContextUnavailableError):
            problem, code = _portfolio_not_found(), "CONTEXT_UNAVAILABLE"
        elif isinstance(error, ReportNotFoundError):
            problem, code = _report_not_found(), "REPORT_UNAVAILABLE"
        elif isinstance(error, SimulationNotFoundError):
            problem, code = _simulation_not_found(), "SIMULATION_UNAVAILABLE"
        elif isinstance(error, MarketDataUnavailableError):
            problem, code = _current_market_data_unavailable(), "MARKET_DATA_UNAVAILABLE"
        elif isinstance(error, (InvalidHoldingModeError, InvalidPortfolioValueError, UnsupportedHoldingInstrumentError)):
            problem, code = _portfolio_holding_conflict(), "HOLDING_STATE_INVALID"
        elif isinstance(error, LLMProviderTimeoutError):
            problem, code = _provider_unavailable(), "PROVIDER_TIMEOUT"
        elif isinstance(error, LLMProviderUnavailableError) or (isinstance(error, HTTPException) and error.status_code == 503):
            problem, code = _provider_unavailable(), "PROVIDER_UNAVAILABLE"
        elif isinstance(error, LLMProviderResponseError):
            problem, code = _invalid_provider_response(), "INVALID_PROVIDER_RESPONSE"
        elif isinstance(error, AuraAgentOutputError):
            problem, code = _invalid_provider_response(), "UNSAFE_PROVIDER_OUTPUT"
        else:
            problem, code = _internal_error(), "INTERNAL_ERROR"
        if isinstance(error, SQLAlchemyError):
            try:
                session.rollback()
            except Exception:
                pass
    source_types = {source.type for source in response.sources} if response is not None else set()
    _store_monitoring(
        session, started_at=started_at, duration_ms=round((perf_counter() - started) * 1000, 3),
        outcome="ERROR" if problem is not None else "REFUSED" if trace.refusal_stage else "COMPLETED",
        http_status=problem.status_code if problem is not None else 200,
        provider_kind=provider_kind, provider_called=trace.provider_called,
        refusal_stage=trace.refusal_stage if problem is None else None,
        guardrail_reason=trace.guardrail_reason.value if trace.guardrail_reason else None,
        error_code=code, has_portfolio_source="portfolio" in source_types,
        has_report_source="report" in source_types, has_simulation_source="simulation" in source_types,
        limitation_count=len(response.limitations) if response is not None else 0,
    )
    if problem is not None:
        raise problem from failure
    return response
