import logging
import time
from datetime import datetime, timezone
from uuid import uuid4

from app.config import PolicySettings
from app.services.rules import load_ruleset
from shared.observability import observe_agent_latency
from shared.schemas.agents import (
    ExecutionMetadata,
    PolicyAction,
    PolicyAgentOutput,
    PolicyAgentRequest,
    PolicyAgentResponse,
)

logger = logging.getLogger("agent-policy")
settings = PolicySettings()
ruleset = load_ruleset(settings.ruleset_path, settings.ruleset_version)


class PolicyAgent:
    async def execute(self, request: PolicyAgentRequest) -> PolicyAgentResponse:
        started_at = datetime.now(timezone.utc)
        start = time.perf_counter()

        risk_score = float(request.risk_score or 0.0)
        amount = float(request.transaction.amount)
        violations: list[str] = []

        action = PolicyAction.ALLOW
        if risk_score >= ruleset.block_risk_score_gte:
            action = PolicyAction.BLOCK
            violations.append(ruleset.reason_block_risk)
        elif risk_score >= ruleset.review_risk_score_gte:
            action = PolicyAction.REVIEW
            violations.append(ruleset.reason_review_risk)

        if amount >= ruleset.review_amount_gte and action == PolicyAction.ALLOW:
            action = PolicyAction.REVIEW
            violations.append(ruleset.reason_review_amount)

        output = PolicyAgentOutput(
            ruleset_version=ruleset.ruleset_version,
            violations=violations,
            action=action,
        )

        latency_ms = int((time.perf_counter() - start) * 1000)
        completed_at = datetime.now(timezone.utc)

        metadata = ExecutionMetadata(
            execution_id=str(uuid4()),
            service_name=settings.service_name,
            started_at=started_at,
            completed_at=completed_at,
            latency_ms=latency_ms,
            trace_id=request.trace_id,
        )

        observe_agent_latency(settings.service_name, "policy", latency_ms / 1000.0)
        logger.info(
            "agent_executed",
            extra={"execution_id": metadata.execution_id, "latency_ms": latency_ms},
        )
        return PolicyAgentResponse(metadata=metadata, result=output)
