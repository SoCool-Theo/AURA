"""OpenAI Responses API adapter for Aura's provider-neutral contract."""

from __future__ import annotations

import json

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    InternalServerError,
    OpenAI,
    RateLimitError,
)

from .provider import (
    LLMProviderResponseError,
    LLMProviderTimeoutError,
    LLMProviderUnavailableError,
    ProviderRequest,
    ProviderResponse,
)


class OpenAIProvider:
    """Generate one grounded Aura explanation through OpenAI Responses."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout_seconds: float,
        max_output_tokens: int,
        client: OpenAI | None = None,
    ) -> None:
        if not api_key.strip() or not model.strip():
            raise ValueError("OpenAI provider configuration is incomplete")
        self._model = model
        self._max_output_tokens = max_output_tokens
        self._client = client or OpenAI(
            api_key=api_key,
            timeout=timeout_seconds,
            max_retries=0,
        )

    def generate(self, request: ProviderRequest) -> ProviderResponse:
        """Map Aura's approved request into one non-stored Responses call."""
        input_data = json.dumps(
            {
                "aura_grounding_context": request.grounded_context,
                "user_question": request.user_message,
            },
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        try:
            response = self._client.responses.create(
                model=self._model,
                instructions=request.system_instructions,
                input=input_data,
                max_output_tokens=self._max_output_tokens,
                store=False,
            )
        except APITimeoutError as error:
            raise LLMProviderTimeoutError() from error
        except (
            APIConnectionError,
            RateLimitError,
            InternalServerError,
            AuthenticationError,
            APIStatusError,
        ) as error:
            raise LLMProviderUnavailableError() from error

        output_text = getattr(response, "output_text", None)
        if not isinstance(output_text, str) or not output_text.strip():
            raise LLMProviderResponseError()
        try:
            return ProviderResponse(text=output_text)
        except LLMProviderResponseError as error:
            raise LLMProviderResponseError() from error


__all__ = ["OpenAIProvider"]
