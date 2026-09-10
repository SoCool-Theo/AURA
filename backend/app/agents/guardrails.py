"""Deterministic safety rules for Aura's future explanation orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re


MAX_PROVIDER_OUTPUT_CHARACTERS = 8_000
HISTORICAL_LIMITATION = (
    "Historical analysis and simulations describe past results and do not predict "
    "future performance."
)
UNAVAILABLE_DATA_RESPONSE = (
    "I can explain Aura's available historical results, but the information needed "
    "for that explanation is unavailable."
)
INVESTMENT_ADVICE_REFUSAL = (
    "I can explain the historical risk characteristics of your portfolio, but I "
    "can't recommend whether you should buy, sell, or hold a specific investment, "
    "add or remove assets, or change your allocation. "
    "I can explain how a holding contributes to your portfolio's calculated risk."
)
INVALID_MESSAGE_RESPONSE = "Please ask a portfolio-risk or historical-simulation question."


class GuardrailReason(str, Enum):
    """Stable internal reasons for deterministic guardrail decisions."""

    ALLOWED = "allowed"
    EMPTY_MESSAGE = "empty_message"
    INVESTMENT_ADVICE = "investment_advice"
    INVALID_OUTPUT = "invalid_output"
    OUTPUT_TOO_LONG = "output_too_long"
    SYSTEM_LEAKAGE = "system_leakage"


@dataclass(frozen=True, slots=True)
class GuardrailDecision:
    """Result of a deterministic input or output safety check."""

    allowed: bool
    reason: GuardrailReason
    response: str | None = None


_INVESTMENT_ADVICE_PATTERNS = (
    re.compile(r"\bshould\s+i\s+(?:buy|sell|hold)\b"),
    re.compile(r"\btell\s+me\s+what\s+(?:stock|investment|asset)\s+to\s+buy\b"),
    re.compile(r"\b(?:what|which)\s+(?:stock|investment|asset)s?\s+(?:should\s+i\s+)?buy\b"),
    re.compile(r"\bwhat\s+should\s+i\s+invest\s+in\b"),
    re.compile(r"\b(?:give|provide)\s+me\s+(?:a\s+)?target\s+price\b"),
    re.compile(r"\bwhen\s+should\s+i\s+(?:buy|sell)\b"),
    re.compile(r"\b(?:guarantee|guaranteed|ensure)\b.*\b(?:return|profit|gain|money)\b"),
    re.compile(r"\b(?:build|create)\s+me\s+(?:the\s+)?(?:best|optimal)\s+portfolio\b"),
    re.compile(r"\b(?:tell\s+me\s+)?exactly\s+how\s+to\s+allocate\s+my\s+money\b"),
    re.compile(r"\b(?:which|what)\s+(?:stock|asset)\b.*\b(?:will\s+)?(?:go\s+up|rise|fall|drop)\b"),
    re.compile(r"\bpretend\s+(?:you\s+are|to\s+be)\s+(?:my\s+)?financial\s+advi[sc]er\b"),
    re.compile(r"\b(?:recommend|recommendation)\b.*\b(?:buy|sell|hold)(?:ing)?\b"),
)
_SYSTEM_LEAKAGE_PATTERN = re.compile(
    r"\b(?:system\s+message|system\s+instructions|developer\s+message)\b",
)
_PROHIBITED_OUTPUT_ADVICE_PATTERNS = (
    re.compile(
        r"\b(?:you\s+)?(?:should|need\s+to|ought\s+to)\s+"
        r"(?:add|include|buy|purchase|sell|remove|reduce|increase|decrease|"
        r"change|adjust|move|shift|rebalance)\b"
    ),
    re.compile(
        r"\byou\s+(?:could|can)\s+(?:add|include|buy|purchase|sell|remove|"
        r"reduce|increase|decrease|change|adjust|move|shift|rebalance)\b"
    ),
    re.compile(
        r"\bconsider\s+(?:adding|including|buying|purchasing|selling|removing|"
        r"reducing|increasing|decreasing|changing|adjusting|moving|shifting|"
        r"rebalancing)\b"
    ),
    re.compile(
        r"\b(?:add|include|buy|purchase)\s+(?:more\s+)?"
        r"(?:stocks?|bonds?|crypto(?:currency|currencies)?|coins?|stablecoins?|"
        r"asset\s+classes?)\b"
    ),
    re.compile(
        r"(?:^|[:;]\s*|\n\s*(?:[-*]\s*)?)(?:add|include)\b[^.!?]{0,80}"
        r"\b(?:stocks?|bonds?|crypto(?:currency|currencies)?|coins?|stablecoins?|"
        r"asset\s+classes?)\b"
    ),
    re.compile(
        r"\b(?:reduce|increase|decrease|change|adjust|move|shift|rebalance)\s+"
        r"(?:your\s+)?(?:[a-z0-9._-]+\s+)?(?:portfolio\s+)?(?:allocation|allocations|exposure|"
        r"weight|weights|position|positions|holding|holdings)\b"
    ),
    re.compile(
        r"\b(?:move|shift)\s+(?:part|some|a\s+portion)\s+of\s+(?:your\s+)?"
        r"portfolio\s+(?:into|to)\b"
    ),
    re.compile(
        r"\bdiversif(?:y|ication)\b.*\b(?:by\s+)?(?:adding|including|buying|"
        r"purchasing)\b"
    ),
    re.compile(r"(?:^|[.!?]\s*|\n\s*(?:[-*]\s*)?)(?:buy|purchase|sell)\b"),
)


def _normalized_message(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = " ".join(value.split()).casefold()
    return normalized or None


def evaluate_user_message(message: object) -> GuardrailDecision:
    """Refuse only clearly recognizable requests for investment advice."""
    normalized = _normalized_message(message)
    if normalized is None:
        return GuardrailDecision(
            allowed=False,
            reason=GuardrailReason.EMPTY_MESSAGE,
            response=INVALID_MESSAGE_RESPONSE,
        )

    if any(pattern.search(normalized) for pattern in _INVESTMENT_ADVICE_PATTERNS):
        return GuardrailDecision(
            allowed=False,
            reason=GuardrailReason.INVESTMENT_ADVICE,
            response=INVESTMENT_ADVICE_REFUSAL,
        )

    return GuardrailDecision(allowed=True, reason=GuardrailReason.ALLOWED)


def validate_provider_output(text: object) -> GuardrailDecision:
    """Validate Aura-specific provider output safety without changing its text."""
    if not isinstance(text, str) or not text.strip():
        return GuardrailDecision(False, GuardrailReason.INVALID_OUTPUT)
    if len(text) > MAX_PROVIDER_OUTPUT_CHARACTERS:
        return GuardrailDecision(False, GuardrailReason.OUTPUT_TOO_LONG)
    if _SYSTEM_LEAKAGE_PATTERN.search(text.casefold()):
        return GuardrailDecision(False, GuardrailReason.SYSTEM_LEAKAGE)
    if any(pattern.search(text.casefold()) for pattern in _PROHIBITED_OUTPUT_ADVICE_PATTERNS):
        return GuardrailDecision(
            False,
            GuardrailReason.INVESTMENT_ADVICE,
            INVESTMENT_ADVICE_REFUSAL,
        )
    return GuardrailDecision(True, GuardrailReason.ALLOWED)


__all__ = [
    "GuardrailDecision",
    "GuardrailReason",
    "HISTORICAL_LIMITATION",
    "INVALID_MESSAGE_RESPONSE",
    "INVESTMENT_ADVICE_REFUSAL",
    "MAX_PROVIDER_OUTPUT_CHARACTERS",
    "UNAVAILABLE_DATA_RESPONSE",
    "evaluate_user_message",
    "validate_provider_output",
]
