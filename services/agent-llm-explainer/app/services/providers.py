from __future__ import annotations

from dataclasses import dataclass

from shared.schemas.agents import LLMExplanationOutput, LLMExplanationRequest


@dataclass(slots=True)
class ProviderResult:
    provider_name: str
    output: LLMExplanationOutput


class ExplainerProvider:
    name: str

    def generate(self, request: LLMExplanationRequest, *, model: str, prompt_version: str) -> ProviderResult:
        raise NotImplementedError


class DeterministicProvider(ExplainerProvider):
    name = "deterministic"

    def generate(self, request: LLMExplanationRequest, *, model: str, prompt_version: str) -> ProviderResult:
        risk = float(request.risk_score or 0.0)
        policy_action = request.policy_action or "REVIEW"
        reason_codes = request.reason_codes or []
        output = LLMExplanationOutput(
            summary=f"Risk score {risk:.2f} with policy action {policy_action}.",
            rationale=(
                "Deterministic explainer fallback. "
                f"Reason codes: {', '.join(reason_codes) if reason_codes else 'none'}."
            ),
            confidence=min(0.99, max(0.05, risk)),
            provider=self.name,
            model=model,
            prompt_version=prompt_version,
        )
        return ProviderResult(provider_name=self.name, output=output)


class TemplateProvider(ExplainerProvider):
    name = "template"

    def generate(self, request: LLMExplanationRequest, *, model: str, prompt_version: str) -> ProviderResult:
        risk = float(request.risk_score or 0.0)
        policy_action = request.policy_action or "REVIEW"
        reason_codes = request.reason_codes or []
        level = "low"
        if risk >= 0.9:
            level = "critical"
        elif risk >= 0.6:
            level = "elevated"
        output = LLMExplanationOutput(
            summary=f"Template explainer: {level} risk, proposed action {policy_action}.",
            rationale=(
                f"Rule-driven explanation built from risk={risk:.2f}, policy={policy_action}, "
                f"signals={', '.join(reason_codes) if reason_codes else 'none'}."
            ),
            confidence=min(0.99, max(0.05, risk)),
            provider=self.name,
            model=model,
            prompt_version=prompt_version,
        )
        return ProviderResult(provider_name=self.name, output=output)


def resolve_provider(provider_name: str) -> ExplainerProvider:
    normalized = (provider_name or "").strip().lower()
    if normalized in {"template", "rules"}:
        return TemplateProvider()
    return DeterministicProvider()
