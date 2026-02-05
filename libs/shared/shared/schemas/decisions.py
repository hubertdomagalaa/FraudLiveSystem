from datetime import datetime
from enum import Enum
from typing import List

from pydantic import Field

from .base import BaseSchema
from .transactions import TransactionStored
from .agents import (
    ContextAgentOutput,
    ExecutionMetadata,
    LLMExplanationOutput,
    PolicyAgentOutput,
    RiskMLAgentOutput,
)

AgentOutput = ContextAgentOutput | RiskMLAgentOutput | PolicyAgentOutput | LLMExplanationOutput


class DecisionOutcome(str, Enum):
    APPROVE = "APPROVE"
    REVIEW = "REVIEW"
    DECLINE = "DECLINE"


class DecisionRequest(BaseSchema):
    transaction: TransactionStored


class AgentResult(BaseSchema):
    agent_name: str
    output: AgentOutput
    metadata: ExecutionMetadata


class DecisionAggregate(BaseSchema):
    decision_id: str
    transaction_id: str
    outcome: DecisionOutcome
    reason_codes: List[str] = Field(default_factory=list)
    agent_results: List[AgentResult] = Field(default_factory=list)
    created_at: datetime
