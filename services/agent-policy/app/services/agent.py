import logging
import time
from datetime import datetime, timezone
from uuid import uuid4

from app.config import PolicySettings
from shared.schemas.agents import (
    ExecutionMetadata,
    PolicyAction,
    PolicyAgentOutput,
    PolicyAgentRequest,
    PolicyAgentResponse,
)

logger = logging.getLogger("agent-policy")
settings = PolicySettings()


class PolicyAgent:
    async def execute(self, request: PolicyAgentRequest) -> PolicyAgentResponse:
        started_at = datetime.now(timezone.utc)
        start = time.perf_counter()

        output = PolicyAgentOutput(
            ruleset_version=settings.ruleset_version,
            violations=[],
            action=PolicyAction.REVIEW,
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

        logger.info(
            "agent_executed",
            extra={"execution_id": metadata.execution_id, "latency_ms": latency_ms},
        )
        return PolicyAgentResponse(metadata=metadata, result=output)
