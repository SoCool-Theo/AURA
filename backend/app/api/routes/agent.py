"""Authenticated, read-only Aura explanation endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.agents.agent import AuraAgentContextUnavailableError, AuraAgentOutputError
from app.agents.openai_provider import OpenAIProvider
from app.agents.provider import (
    LLMProvider,
    LLMProviderResponseError,
    LLMProviderTimeoutError,
    LLMProviderUnavailableError,
)
from app.api.dependencies import CurrentUser, DatabaseSession
from app.core.config import settings
from app.schemas.agent import AgentExplainRequest, AgentExplainResponse
from app.services.agent_service import AgentService
from app.services.analysis_reporting_service import ReportNotFoundError
from app.services.simulation_history_service import SimulationNotFoundError


router = APIRouter(prefix="/agent", tags=["Agent"])


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


def get_agent_provider() -> LLMProvider:
    """Create the configured provider only for AI explanation requests."""
    api_key = settings.openai_api_key
    if api_key is None or not api_key.get_secret_value().strip():
        raise _provider_unavailable()
    if settings.aura_llm_model is None:
        raise _provider_unavailable()
    try:
        return OpenAIProvider(
            api_key=api_key.get_secret_value(),
            model=settings.aura_llm_model,
            timeout_seconds=settings.aura_llm_timeout_seconds,
            max_output_tokens=settings.aura_llm_max_output_tokens,
        )
    except ValueError as error:
        raise _provider_unavailable() from error


AgentProvider = Annotated[LLMProvider, Depends(get_agent_provider)]


@router.post(
    "/explain",
    response_model=AgentExplainResponse,
    status_code=status.HTTP_200_OK,
)
def explain(
    request: AgentExplainRequest,
    session: DatabaseSession,
    current_user: CurrentUser,
    provider: AgentProvider,
) -> AgentExplainResponse:
    """Explain only data owned by the authenticated Aura user."""
    try:
        return AgentService(session, provider).explain(
            user_id=current_user.id,
            request=request,
        )
    except AuraAgentContextUnavailableError as error:
        raise _portfolio_not_found() from error
    except ReportNotFoundError as error:
        raise _report_not_found() from error
    except SimulationNotFoundError as error:
        raise _simulation_not_found() from error
    except (LLMProviderTimeoutError, LLMProviderUnavailableError) as error:
        raise _provider_unavailable() from error
    except (LLMProviderResponseError, AuraAgentOutputError) as error:
        raise _invalid_provider_response() from error
    except Exception as error:
        raise _internal_error() from error
