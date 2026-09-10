import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import httpx2
import pytest
from fastapi import HTTPException
from openai import (
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
    RateLimitError,
)
from pydantic import SecretStr, ValidationError

import app.api.routes.agent as route_module
from app.agents.openai_provider import OpenAIProvider
from app.agents.provider import (
    LLMProvider,
    LLMProviderResponseError,
    LLMProviderTimeoutError,
    LLMProviderUnavailableError,
    ProviderRequest,
)
import app.agents.openai_provider as provider_module
from app.core.config import Settings


_API_KEY = "test-openai-key-not-a-production-secret"
_MODEL = "gpt-5-mini"


def _request() -> ProviderRequest:
    return ProviderRequest(
        system_instructions="Explain only supplied Aura results.",
        user_message="Why is my portfolio risky?",
        grounded_context={
            "portfolio": {"name": "Core", "weight": 0.0},
            "report": {
                "max_drawdown": -0.25,
                "sharpe_ratio": None,
                "comparison_delta": -0.1,
            },
            "simulation": None,
        },
    )


def _provider(client: MagicMock) -> OpenAIProvider:
    return OpenAIProvider(
        api_key=_API_KEY,
        model=_MODEL,
        timeout_seconds=30,
        max_output_tokens=1200,
        client=client,
    )


def _request_error() -> httpx2.Request:
    return httpx2.Request("POST", "https://api.openai.invalid/v1/responses")


def _status_error(error_type: type[RateLimitError] | type[InternalServerError], status: int) -> Exception:
    return error_type(
        "provider-secret-detail",
        response=httpx2.Response(status, request=_request_error()),
        body={"secret": "provider-secret-detail"},
    )


def test_openai_provider_constructs_official_client_with_timeout_and_no_retries() -> None:
    with patch.object(provider_module, "OpenAI") as client_type:
        provider = OpenAIProvider(
            api_key=_API_KEY,
            model=_MODEL,
            timeout_seconds=30,
            max_output_tokens=1200,
        )

    assert isinstance(provider, LLMProvider)
    client_type.assert_called_once_with(
        api_key=_API_KEY,
        timeout=30,
        max_retries=0,
    )


@pytest.mark.parametrize("api_key,model", [("", _MODEL), (_API_KEY, "  ")])
def test_openai_provider_rejects_incomplete_construction(api_key: str, model: str) -> None:
    with pytest.raises(ValueError, match="configuration is incomplete"):
        OpenAIProvider(
            api_key=api_key,
            model=model,
            timeout_seconds=30,
            max_output_tokens=1200,
            client=MagicMock(),
        )


def test_responses_api_maps_only_grounded_data_and_preserves_financial_values() -> None:
    client = MagicMock()
    client.responses.create.return_value = SimpleNamespace(output_text="Grounded explanation.")
    request = _request()

    response = _provider(client).generate(request)

    assert response.text == "Grounded explanation."
    client.responses.create.assert_called_once()
    arguments = client.responses.create.call_args.kwargs
    assert arguments == {
        "model": _MODEL,
        "instructions": request.system_instructions,
        "input": arguments["input"],
        "max_output_tokens": 1200,
        "store": False,
    }
    input_data = json.loads(arguments["input"])
    assert input_data == {
        "aura_grounding_context": request.grounded_context,
        "user_question": request.user_message,
    }
    context = input_data["aura_grounding_context"]
    assert context["report"]["max_drawdown"] == -0.25
    assert context["report"]["comparison_delta"] == -0.1
    assert context["report"]["sharpe_ratio"] is None
    assert context["portfolio"]["weight"] == 0.0
    serialized = arguments["input"]
    for forbidden in (
        "jwt",
        "email",
        "database_url",
        "password",
        "session",
        "repository",
        _API_KEY,
    ):
        assert forbidden not in serialized.casefold()
    assert "tools" not in arguments
    assert "web_search" not in arguments
    assert "file_search" not in arguments


@pytest.mark.parametrize("output_text", [None, "", " \t\n "])
def test_blank_or_missing_output_text_is_rejected(output_text: object) -> None:
    client = MagicMock()
    client.responses.create.return_value = SimpleNamespace(output_text=output_text)

    with pytest.raises(LLMProviderResponseError):
        _provider(client).generate(_request())


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (APITimeoutError(request=_request_error()), LLMProviderTimeoutError),
        (
            APIConnectionError(
                message="provider-secret-detail",
                request=_request_error(),
            ),
            LLMProviderUnavailableError,
        ),
        (_status_error(RateLimitError, 429), LLMProviderUnavailableError),
        (_status_error(InternalServerError, 500), LLMProviderUnavailableError),
    ],
)
def test_vendor_failures_map_to_safe_provider_errors(
    error: Exception,
    expected: type[Exception],
) -> None:
    client = MagicMock()
    client.responses.create.side_effect = error

    with pytest.raises(expected) as raised:
        _provider(client).generate(_request())

    assert "provider-secret-detail" not in str(raised.value)
    assert client.responses.create.call_count == 1


def test_settings_keep_openai_secret_hidden_and_validate_bounds() -> None:
    configured = Settings(
        _env_file=None,
        openai_api_key=_API_KEY,
        aura_llm_model="  gpt-5-mini  ",
    )

    assert isinstance(configured.openai_api_key, SecretStr)
    assert configured.openai_api_key.get_secret_value() == _API_KEY
    assert _API_KEY not in repr(configured)
    assert configured.aura_llm_model == "gpt-5-mini"
    assert configured.aura_llm_timeout_seconds == 30
    assert configured.aura_llm_max_output_tokens == 1200
    with pytest.raises(ValidationError):
        Settings(_env_file=None, aura_llm_timeout_seconds=0)
    with pytest.raises(ValidationError):
        Settings(_env_file=None, aura_llm_max_output_tokens=1501)


def test_agent_provider_dependency_requires_key_and_model_and_constructs_configured_provider() -> None:
    with (
        patch.object(route_module.settings, "aura_llm_provider", "openai"),
        patch.object(route_module.settings, "openai_api_key", None),
        patch.object(route_module.settings, "aura_llm_model", None),
    ):
        with pytest.raises(HTTPException) as missing:
            route_module.get_agent_provider()
    assert missing.value.status_code == 503
    assert missing.value.detail == "AI explanation service is currently unavailable."

    with (
        patch.object(route_module.settings, "aura_llm_provider", "openai"),
        patch.object(route_module.settings, "openai_api_key", SecretStr(_API_KEY)),
        patch.object(route_module.settings, "aura_llm_model", _MODEL),
        patch.object(route_module.settings, "aura_llm_timeout_seconds", 25),
        patch.object(route_module.settings, "aura_llm_max_output_tokens", 1000),
        patch.object(route_module, "OpenAIProvider") as provider_type,
    ):
        provider = route_module.get_agent_provider()

    assert provider is provider_type.return_value
    provider_type.assert_called_once_with(
        api_key=_API_KEY,
        model=_MODEL,
        timeout_seconds=25,
        max_output_tokens=1000,
    )
