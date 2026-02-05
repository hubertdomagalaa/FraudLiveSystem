import logging
from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from app.config import OrchestratorSettings
from app.orchestration.client import AgentClient
from shared.schemas.decisions import AgentResult, DecisionAggregate, DecisionOutcome
from shared.schemas.transactions import TransactionStored


class DecisionState(str, Enum):
    START = "start"
    CONTEXT = "context"
    RISK = "risk"
    POLICY = "policy"
    LLM = "llm"
    COMPLETE = "complete"


class DecisionStateMachine:
    def __init__(self, client: AgentClient, settings: OrchestratorSettings) -> None:
        self.client = client
        self.settings = settings
        self.state = DecisionState.START
        self.logger = logging.getLogger(settings.service_name)

    def transition(self, next_state: DecisionState) -> None:
        self.logger.info(
            "state_transition",
            extra={"from_state": self.state.value, "to_state": next_state.value},
        )
        self.state = next_state

    async def run(self, transaction: TransactionStored) -> DecisionAggregate:
        trace_id = str(uuid4())

        self.transition(DecisionState.CONTEXT)
        context_response = await self.client.call_context(transaction, trace_id)

        self.transition(DecisionState.RISK)
        risk_response = await self.client.call_risk(
            transaction,
            context_response.result,
            trace_id,
        )

        self.transition(DecisionState.POLICY)
        policy_response = await self.client.call_policy(
            transaction,
            context_response.result,
            risk_response.result.risk_score,
            trace_id,
        )

        self.transition(DecisionState.LLM)
        llm_response = await self.client.call_llm(
            transaction,
            risk_response.result.risk_score,
            policy_response.result.action.value,
            policy_response.result.violations,
            trace_id,
        )

        agent_results = [
            AgentResult(
                agent_name="context",
                output=context_response.result,
                metadata=context_response.metadata,
            ),
            AgentResult(
                agent_name="risk-ml",
                output=risk_response.result,
                metadata=risk_response.metadata,
            ),
            AgentResult(
                agent_name="policy",
                output=policy_response.result,
                metadata=policy_response.metadata,
            ),
            AgentResult(
                agent_name="llm-explainer",
                output=llm_response.result,
                metadata=llm_response.metadata,
            ),
        ]

        decision = DecisionAggregate(
            decision_id=str(uuid4()),
            transaction_id=transaction.transaction_id,
            outcome=DecisionOutcome(self.settings.default_decision),
            reason_codes=policy_response.result.violations,
            agent_results=agent_results,
            created_at=datetime.now(timezone.utc),
        )

        self.transition(DecisionState.COMPLETE)
        return decision
