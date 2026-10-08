"""Authenticated, read-only Aura explanation endpoint."""

from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.agents.agent import AuraAgentContextUnavailableError, AuraAgentOutputError
from app.agents.groq_provider import GroqProvider
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
from app.services.market_data_service import MarketDataUnavailableError
from app.services.portfolio_valuation_service import (
    InvalidHoldingModeError,
    InvalidPortfolioValueError,
    UnsupportedHoldingInstrumentError,
)
from app.services.simulation_history_service import SimulationNotFoundError


router = APIRouter(prefix="/agent", tags=["Agent"])


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
            valuation_date=_current_utc_date(),
        )
    except AuraAgentContextUnavailableError as error:
        raise _portfolio_not_found() from error
    except ReportNotFoundError as error:
        raise _report_not_found() from error
    except SimulationNotFoundError as error:
        raise _simulation_not_found() from error
    except MarketDataUnavailableError as error:
        raise _current_market_data_unavailable() from error
    except (
        InvalidHoldingModeError,
        InvalidPortfolioValueError,
        UnsupportedHoldingInstrumentError,
    ) as error:
        raise _portfolio_holding_conflict() from error
    except (LLMProviderTimeoutError, LLMProviderUnavailableError) as error:
        raise _provider_unavailable() from error
    except (LLMProviderResponseError, AuraAgentOutputError) as error:
        raise _invalid_provider_response() from error
    except Exception as error:
        raise _internal_error() from error
