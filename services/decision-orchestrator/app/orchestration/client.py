import httpx

from app.config import OrchestratorSettings
from shared.schemas.agents import (
    ContextAgentRequest,
    ContextAgentResponse,
    LLMExplanationRequest,
    LLMExplanationResponse,
    PolicyAgentRequest,
    PolicyAgentResponse,
    RiskMLAgentRequest,
    RiskMLAgentResponse,
)
from shared.schemas.transactions import TransactionStored


class AgentClient:
    def __init__(self, settings: OrchestratorSettings) -> None:
        self.settings = settings

    async def _post(self, url: str, payload: dict) -> dict:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json()

    async def call_context(self, transaction: TransactionStored, trace_id: str) -> ContextAgentResponse:
        request = ContextAgentRequest(transaction=transaction, trace_id=trace_id)
        data = await self._post(
            f"{self.settings.context_agent_url}/v1/invoke",
            request.model_dump(mode="json"),
        )
        return ContextAgentResponse.model_validate(data)

    async def call_risk(
        self,
        transaction: TransactionStored,
        context,
        trace_id: str,
    ) -> RiskMLAgentResponse:
        request = RiskMLAgentRequest(transaction=transaction, context=context, trace_id=trace_id)
        data = await self._post(
            f"{self.settings.risk_agent_url}/v1/invoke",
            request.model_dump(mode="json"),
        )
        return RiskMLAgentResponse.model_validate(data)

    async def call_policy(
        self,
        transaction: TransactionStored,
        context,
        risk_score: float,
        trace_id: str,
    ) -> PolicyAgentResponse:
        request = PolicyAgentRequest(
            transaction=transaction,
            context=context,
            risk_score=risk_score,
            trace_id=trace_id,
        )
        data = await self._post(
            f"{self.settings.policy_agent_url}/v1/invoke",
            request.model_dump(mode="json"),
        )
        return PolicyAgentResponse.model_validate(data)

    async def call_llm(
        self,
        transaction: TransactionStored,
        risk_score: float,
        policy_action: str,
        reason_codes: list[str],
        trace_id: str,
    ) -> LLMExplanationResponse:
        request = LLMExplanationRequest(
            transaction=transaction,
            risk_score=risk_score,
            policy_action=policy_action,
            reason_codes=reason_codes,
            trace_id=trace_id,
        )
        data = await self._post(
            f"{self.settings.llm_agent_url}/v1/invoke",
            request.model_dump(mode="json"),
        )
        return LLMExplanationResponse.model_validate(data)
