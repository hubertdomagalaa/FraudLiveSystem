import logging
import time
from datetime import datetime, timezone
from uuid import uuid4

from app.config import AggregateSettings
from shared.observability import observe_agent_latency
from shared.schemas.agents import (
    AggregateAgentOutput,
    AggregateAgentRequest,
    AggregateAgentResponse,
    ExecutionMetadata,
)

logger = logging.getLogger("agent-aggregate")
settings = AggregateSettings()


class AggregateAgent:
    async def execute(self, request: AggregateAgentRequest) -> AggregateAgentResponse:
        started_at = datetime.now(timezone.utc)
        start = time.perf_counter()

        risk_score = float(request.risk.risk_score if request.risk else 0.0)
        policy_action = str(request.policy.action.value if request.policy else "REVIEW")
        reason_codes = list(request.policy.violations if request.policy else [])

        recommendation = "ALLOW"
        if policy_action == "BLOCK":
            recommendation = "BLOCK"
        elif policy_action == "REVIEW" or risk_score >= 0.6:
            recommendation = "REVIEW"

        requires_human_review = recommendation == "REVIEW"
        if requires_human_review and "HUMAN_REVIEW_REQUIRED" not in reason_codes:
            reason_codes.append("HUMAN_REVIEW_REQUIRED")

        output = AggregateAgentOutput(
            recommendation=recommendation,
            requires_human_review=requires_human_review,
            reason_codes=reason_codes,
            confidence=round(min(0.99, max(0.05, risk_score)), 4),
            summary=f"Aggregated recommendation={recommendation}, risk_score={risk_score:.2f}",
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

        observe_agent_latency(settings.service_name, "aggregate", latency_ms / 1000.0)
        logger.info(
            "agent_executed",
            extra={"execution_id": metadata.execution_id, "latency_ms": latency_ms},
        )
        return AggregateAgentResponse(metadata=metadata, result=output)
