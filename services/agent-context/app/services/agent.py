import logging
import time
from datetime import datetime, timezone
from uuid import uuid4

from app.config import ContextSettings
from shared.schemas.agents import (
    ContextAgentOutput,
    ContextAgentRequest,
    ContextAgentResponse,
    ExecutionMetadata,
)

logger = logging.getLogger("agent-context")
settings = ContextSettings()


class ContextAgent:
    async def execute(self, request: ContextAgentRequest) -> ContextAgentResponse:
        started_at = datetime.now(timezone.utc)
        start = time.perf_counter()

        output = ContextAgentOutput(
            customer_segment="unknown",
            device_trust="unverified",
            account_age_days=0,
            signals=[],
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
        return ContextAgentResponse(metadata=metadata, result=output)
