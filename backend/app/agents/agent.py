"""Deterministic orchestration for one grounded Aura explanation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from ..schemas.agent import (
    AgentExplainRequest,
    AgentExplainResponse,
    AgentSourceReference,
)
from .guardrails import (
    GuardrailReason,
    HISTORICAL_LIMITATION,
    UNAVAILABLE_DATA_RESPONSE,
    evaluate_user_message,
    validate_provider_output,
)
from .prompts import build_system_instructions
from .provider import LLMProvider, ProviderRequest
from .tools import AuraAgentTools


class AuraAgentContextUnavailableError(RuntimeError):
    """Raised when owned Aura context cannot safely ground an explanation."""

    def __init__(self) -> None:
        super().__init__("Aura explanation context is unavailable")


class AuraAgentOutputError(RuntimeError):
    """Raised when provider output fails Aura's deterministic safety checks."""

    def __init__(self) -> None:
        super().__init__("Aura explanation output is unsafe")


@dataclass(slots=True)
class AuraAgent:
    """Coordinate one bounded, ownership-scoped Aura explanation."""

    tools: AuraAgentTools
    provider: LLMProvider

    def explain(self, request: AgentExplainRequest) -> AgentExplainResponse:
        """Return one guardrailed explanation from deterministic Aura context."""
        decision = evaluate_user_message(request.message)
        if not decision.allowed:
            return AgentExplainResponse(
                answer=decision.response or "I can explain Aura's historical risk results.",
                sources=[],
                limitations=[],
            )

        portfolio = self.tools.get_portfolio_context()
        if portfolio is None:
            raise AuraAgentContextUnavailableError()

        report, report_source, report_unavailable = self._select_report(request)
        simulation, simulation_source = self._select_simulation(request)
        grounded_context = {
            "portfolio": portfolio,
            "report": report,
            "simulation": simulation,
        }
        provider_request = ProviderRequest(
            system_instructions=build_system_instructions(),
            user_message=request.message,
            grounded_context=grounded_context,
        )
        provider_response = self.provider.generate(provider_request)
        output_decision = validate_provider_output(provider_response.text)
        if output_decision.reason is GuardrailReason.INVESTMENT_ADVICE:
            return AgentExplainResponse(
                answer=output_decision.response
                or "I can explain Aura's historical risk results.",
                sources=[],
                limitations=[],
            )
        if not output_decision.allowed:
            raise AuraAgentOutputError()

        sources = [
            AgentSourceReference(type="portfolio", id=request.portfolio_id),
            *([report_source] if report_source is not None else []),
            *([simulation_source] if simulation_source is not None else []),
        ]
        limitations = self._limitations(
            has_historical_context=report_source is not None or simulation_source is not None,
            report_unavailable=report_unavailable,
        )
        return AgentExplainResponse(
            answer=provider_response.text,
            sources=sources,
            limitations=limitations,
        )

    def _select_report(
        self,
        request: AgentExplainRequest,
    ) -> tuple[dict[str, Any], AgentSourceReference | None, bool]:
        if request.report_id is not None:
            report = self.tools.get_report(request.report_id)
            if report is None:
                raise AuraAgentContextUnavailableError()
            return report, self._source_reference("report", report), False

        latest_report = self.tools.get_latest_report()
        if latest_report is None:
            raise AuraAgentContextUnavailableError()
        if latest_report.get("available") is False:
            return {"available": False}, None, True

        report = latest_report["report"]
        return report, self._source_reference("report", report), False

    def _select_simulation(
        self,
        request: AgentExplainRequest,
    ) -> tuple[dict[str, Any] | None, AgentSourceReference | None]:
        if request.simulation_id is None:
            return None, None

        simulation = self.tools.get_simulation(request.simulation_id)
        if simulation is None:
            raise AuraAgentContextUnavailableError()
        return simulation, self._source_reference("simulation", simulation)

    @staticmethod
    def _source_reference(
        source_type: str,
        context: dict[str, Any],
    ) -> AgentSourceReference:
        return AgentSourceReference(type=source_type, id=UUID(str(context["id"])))

    @staticmethod
    def _limitations(
        *,
        has_historical_context: bool,
        report_unavailable: bool,
    ) -> list[str]:
        limitations: list[str] = []
        if has_historical_context:
            limitations.append(HISTORICAL_LIMITATION)
        if report_unavailable:
            limitations.append(UNAVAILABLE_DATA_RESPONSE)
        return limitations


__all__ = [
    "AuraAgent",
    "AuraAgentContextUnavailableError",
    "AuraAgentOutputError",
]
