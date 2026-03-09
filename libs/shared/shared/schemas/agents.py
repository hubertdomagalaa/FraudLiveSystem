from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import Field

from .base import BaseSchema
from .transactions import TransactionStored


class ExecutionMetadata(BaseSchema):
    execution_id: str
    service_name: str
    started_at: datetime
    completed_at: datetime
    latency_ms: int
    trace_id: Optional[str] = None


class ContextAgentOutput(BaseSchema):
    customer_segment: str
    device_trust: str
    account_age_days: int
    signals: List[str] = Field(default_factory=list)
    signal_details: List[dict[str, str]] = Field(default_factory=list)
    country_code: Optional[str] = None
    country_risk_tier: Optional[str] = None
    is_new_device: bool = False
    has_prior_chargeback: bool = False
    merchant_risk_score: Optional[float] = None


class RiskMLAgentOutput(BaseSchema):
    risk_score: float
    model_version: str
    feature_version: str
    features_used: List[str] = Field(default_factory=list)
    score_breakdown: dict[str, float] = Field(default_factory=dict)
    risk_signals: List[str] = Field(default_factory=list)
    explanation: Optional[str] = None


class PolicyAction(str, Enum):
    ALLOW = "ALLOW"
    REVIEW = "REVIEW"
    BLOCK = "BLOCK"


class PolicyAgentOutput(BaseSchema):
    ruleset_version: str
    violations: List[str] = Field(default_factory=list)
    action: PolicyAction
    triggered_rules: List[str] = Field(default_factory=list)
    explanation: Optional[str] = None


class LLMExplanationOutput(BaseSchema):
    summary: str
    rationale: str
    confidence: float
    provider: str
    model: str
    prompt_version: str


class AggregateAgentOutput(BaseSchema):
    recommendation: str
    requires_human_review: bool
    reason_codes: List[str] = Field(default_factory=list)
    confidence: float
    summary: str
    risk_score: Optional[float] = None
    signals: List[str] = Field(default_factory=list)
    policy_violations: List[str] = Field(default_factory=list)
    policy_action: Optional[str] = None
    explanation: Optional[str] = None


class ContextAgentRequest(BaseSchema):
    transaction: TransactionStored
    trace_id: Optional[str] = None


class RiskMLAgentRequest(BaseSchema):
    transaction: TransactionStored
    context: Optional[ContextAgentOutput] = None
    trace_id: Optional[str] = None


class PolicyAgentRequest(BaseSchema):
    transaction: TransactionStored
    context: Optional[ContextAgentOutput] = None
    risk_score: Optional[float] = None
    trace_id: Optional[str] = None


class LLMExplanationRequest(BaseSchema):
    transaction: TransactionStored
    risk_score: Optional[float] = None
    policy_action: Optional[str] = None
    reason_codes: List[str] = Field(default_factory=list)
    trace_id: Optional[str] = None


class AggregateAgentRequest(BaseSchema):
    transaction: TransactionStored
    context: Optional[ContextAgentOutput] = None
    risk: Optional[RiskMLAgentOutput] = None
    policy: Optional[PolicyAgentOutput] = None
    explain: Optional[LLMExplanationOutput] = None
    trace_id: Optional[str] = None


class ContextAgentResponse(BaseSchema):
    metadata: ExecutionMetadata
    result: ContextAgentOutput


class RiskMLAgentResponse(BaseSchema):
    metadata: ExecutionMetadata
    result: RiskMLAgentOutput


class PolicyAgentResponse(BaseSchema):
    metadata: ExecutionMetadata
    result: PolicyAgentOutput


class LLMExplanationResponse(BaseSchema):
    metadata: ExecutionMetadata
    result: LLMExplanationOutput


class AggregateAgentResponse(BaseSchema):
    metadata: ExecutionMetadata
    result: AggregateAgentOutput
