"""Provider-neutral contracts for future synchronous Aura explanations."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
import math
from typing import Any, Protocol, TypeAlias, runtime_checkable


JSONValue: TypeAlias = (
    None
    | bool
    | int
    | float
    | str
    | list["JSONValue"]
    | dict[str, "JSONValue"]
)
JSONContext: TypeAlias = dict[str, JSONValue]

_FORBIDDEN_CONTEXT_KEYS = frozenset(
    {
        "access_token",
        "api_key",
        "authorization",
        "database_url",
        "email",
        "headers",
        "jwt",
        "password",
        "password_hash",
        "repository",
        "session",
        "token",
    }
)


class LLMProviderError(RuntimeError):
    """Base failure for a provider without exposing remote details."""

    message = "LLM provider request failed"

    def __init__(self) -> None:
        super().__init__(self.message)


class LLMProviderTimeoutError(LLMProviderError):
    """Raised when a provider does not respond within its allowed time."""

    message = "LLM provider request timed out"


class LLMProviderUnavailableError(LLMProviderError):
    """Raised when a provider cannot be reached or used."""

    message = "LLM provider is unavailable"


class LLMProviderResponseError(LLMProviderError):
    """Raised when a provider cannot produce usable explanatory text."""

    message = "LLM provider returned an invalid response"


def _require_non_empty_text(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("provider text must be a non-empty string")
    return value


def _validate_json_value(value: object) -> None:
    if value is None or isinstance(value, (bool, str)):
        return
    if isinstance(value, int) and not isinstance(value, bool):
        return
    if isinstance(value, float):
        if math.isfinite(value):
            return
        raise TypeError("grounded_context must contain finite JSON numbers")
    if isinstance(value, list):
        for item in value:
            _validate_json_value(item)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("grounded_context keys must be strings")
            if key.casefold() in _FORBIDDEN_CONTEXT_KEYS:
                raise TypeError("grounded_context contains a prohibited field")
            _validate_json_value(item)
        return
    raise TypeError("grounded_context must contain only JSON-safe values")


def _validated_context(context: object) -> JSONContext:
    if not isinstance(context, dict):
        raise TypeError("grounded_context must be a JSON object")
    _validate_json_value(context)
    return deepcopy(context)


@dataclass(frozen=True, slots=True, init=False)
class ProviderRequest:
    """Immutable provider input built from Aura-owned grounded context.

    This contract is synchronous to match Aura's existing synchronous services
    and caller-owned SQLAlchemy session architecture. Grounded context must
    already be projected to JSON-safe values by ``AuraAgentTools``.
    """

    system_instructions: str
    user_message: str
    _grounded_context: JSONContext = field(repr=False)

    def __init__(
        self,
        *,
        system_instructions: str,
        user_message: str,
        grounded_context: JSONContext,
    ) -> None:
        object.__setattr__(
            self,
            "system_instructions",
            _require_non_empty_text(system_instructions),
        )
        object.__setattr__(self, "user_message", _require_non_empty_text(user_message))
        object.__setattr__(
            self,
            "_grounded_context",
            _validated_context(grounded_context),
        )

    @property
    def grounded_context(self) -> JSONContext:
        """Return an independent JSON-safe copy for a provider adapter."""
        return deepcopy(self._grounded_context)


@dataclass(frozen=True, slots=True)
class ProviderResponse:
    """Narrow provider result containing only explanatory text."""

    text: str

    def __post_init__(self) -> None:
        try:
            _require_non_empty_text(self.text)
        except ValueError as error:
            raise LLMProviderResponseError from error


@runtime_checkable
class LLMProvider(Protocol):
    """Synchronous vendor-neutral provider used by future Aura orchestration."""

    def generate(self, request: ProviderRequest) -> ProviderResponse:
        """Generate one grounded explanation without tool calling."""


__all__ = [
    "JSONContext",
    "JSONValue",
    "LLMProvider",
    "LLMProviderError",
    "LLMProviderResponseError",
    "LLMProviderTimeoutError",
    "LLMProviderUnavailableError",
    "ProviderRequest",
    "ProviderResponse",
]
