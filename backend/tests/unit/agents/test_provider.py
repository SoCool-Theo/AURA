from datetime import date
from decimal import Decimal
from typing import Type
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

import backend.app.agents.provider as provider_module
from backend.app.agents.provider import (
    LLMProvider,
    LLMProviderError,
    LLMProviderResponseError,
    LLMProviderTimeoutError,
    LLMProviderUnavailableError,
    ProviderRequest,
    ProviderResponse,
)


class FakeProvider:
    """Deterministic test-only provider with an optional generic failure."""

    def __init__(
        self,
        *,
        response_text: str = "Grounded educational explanation.",
        error_type: Type[LLMProviderError] | None = None,
    ) -> None:
        self.response_text = response_text
        self.error_type = error_type
        self.requests: list[ProviderRequest] = []

    def generate(self, request: ProviderRequest) -> ProviderResponse:
        self.requests.append(request)
        if self.error_type is not None:
            raise self.error_type()
        return ProviderResponse(text=self.response_text)


def _request(context: dict[str, object] | None = None) -> ProviderRequest:
    return ProviderRequest(
        system_instructions="Explain only verified Aura data.",
        user_message="Why is my portfolio high risk?",
        grounded_context=(
            {"portfolio": {"id": "portfolio-1", "weight": 0.25}}
            if context is None
            else context  # type: ignore[arg-type]
        ),
    )


def test_provider_request_accepts_json_safe_grounded_context() -> None:
    context = {
        "portfolio": {
            "id": "portfolio-1",
            "holdings": [{"symbol": "AAPL", "weight": 0.0}],
        },
        "report": {"max_drawdown": -0.25, "sharpe_ratio": None},
    }

    request = _request(context)

    assert request.system_instructions == "Explain only verified Aura data."
    assert request.user_message == "Why is my portfolio high risk?"
    assert request.grounded_context == context


def test_provider_request_preserves_bounded_conversation_history_separately() -> None:
    history = [
        {"role": "user", "content": "What is my portfolio?"},
        {"role": "assistant", "content": "It is concentrated in TLT."},
    ]
    request = ProviderRequest(
        system_instructions="Explain only verified Aura data.",
        user_message="Why does that matter?",
        grounded_context={"portfolio": {"id": "portfolio-1"}},
        conversation_history=history,
    )

    history[0]["content"] = "mutated"
    received = request.conversation_history
    received[1]["content"] = "mutated again"

    assert request.conversation_history == [
        {"role": "user", "content": "What is my portfolio?"},
        {"role": "assistant", "content": "It is concentrated in TLT."},
    ]


@pytest.mark.parametrize(
    "history",
    [
        [{"role": "user", "content": "unfinished"}],
        [
            {"role": "assistant", "content": "wrong first role"},
            {"role": "user", "content": "wrong second role"},
        ],
        [
            {"role": "user", "content": "q"},
            {"role": "assistant", "content": "a"},
        ] * 5,
    ],
)
def test_provider_request_rejects_invalid_conversation_history(
    history: list[dict[str, str]],
) -> None:
    with pytest.raises(TypeError, match="conversation_history"):
        ProviderRequest(
            system_instructions="Explain only verified Aura data.",
            user_message="Follow up",
            grounded_context={"portfolio": {"id": "portfolio-1"}},
            conversation_history=history,
        )


def test_provider_request_copies_context_without_mutating_caller_data() -> None:
    context = {"portfolio": {"holdings": [{"weight": 0.0}]}}
    request = _request(context)

    context["portfolio"]["holdings"][0]["weight"] = 1.0
    received_context = request.grounded_context
    received_context["portfolio"]["holdings"][0]["weight"] = 0.5

    assert request.grounded_context == {
        "portfolio": {"holdings": [{"weight": 0.0}]}
    }


@pytest.mark.parametrize(
    "invalid_value",
    [uuid4(), date(2026, 8, 29), Decimal("0.25"), object()],
)
def test_provider_request_rejects_non_json_safe_context_values(
    invalid_value: object,
) -> None:
    with pytest.raises(TypeError, match="JSON-safe"):
        _request({"invalid": invalid_value})


@pytest.mark.parametrize("invalid_value", [float("nan"), float("inf")])
def test_provider_request_rejects_non_finite_json_numbers(
    invalid_value: float,
) -> None:
    with pytest.raises(TypeError, match="finite JSON numbers"):
        _request({"invalid": invalid_value})


@pytest.mark.parametrize("field_name", ["session", "repository", "email", "token"])
def test_provider_request_rejects_prohibited_context_fields(field_name: str) -> None:
    with pytest.raises(TypeError, match="prohibited field"):
        _request({field_name: "sensitive-value"})


def test_provider_request_rejects_sqlalchemy_session_like_context() -> None:
    with pytest.raises(TypeError, match="JSON-safe"):
        _request({"invalid": Session()})


def test_provider_request_preserves_financial_values_without_transformation() -> None:
    context = {
        "metrics": {
            "max_drawdown": -0.125,
            "signed_contribution": -0.02,
            "sharpe_ratio": None,
            "zero_weight": 0.0,
            "comparison_delta": 0.15,
        }
    }

    assert _request(context).grounded_context == context


@pytest.mark.parametrize("text", ["Grounded explanation.", "  Grounded explanation.  "])
def test_provider_response_accepts_non_empty_explanatory_text(text: str) -> None:
    assert ProviderResponse(text=text).text == text


@pytest.mark.parametrize("text", ["", " \t\n "])
def test_provider_response_rejects_empty_or_whitespace_text(text: str) -> None:
    with pytest.raises(LLMProviderResponseError):
        ProviderResponse(text=text)


def test_fake_provider_returns_deterministic_success_and_matches_protocol() -> None:
    provider = FakeProvider(response_text="Verified explanation.")
    request = _request()

    response = provider.generate(request)

    assert isinstance(provider, LLMProvider)
    assert response == ProviderResponse(text="Verified explanation.")
    assert provider.requests == [request]


@pytest.mark.parametrize(
    "error_type",
    [LLMProviderError, LLMProviderUnavailableError, LLMProviderTimeoutError],
)
def test_fake_provider_simulates_generic_failure_and_timeout_without_secret_leakage(
    error_type: Type[LLMProviderError],
) -> None:
    provider = FakeProvider(error_type=error_type)

    with pytest.raises(error_type) as error:
        provider.generate(_request())

    assert "test-api-key-secret" not in str(error.value)
    assert "sensitive-value" not in str(error.value)


def test_provider_module_has_no_vendor_or_network_dependency() -> None:
    module_names = set(provider_module.__dict__)

    assert not {
        "openai",
        "anthropic",
        "google",
        "langchain",
        "llama_index",
        "requests",
        "httpx",
    }.intersection(module_names)
