import logging
import time
from datetime import datetime, timezone
from uuid import uuid4

from app.config import ContextSettings
from shared.observability import observe_agent_latency
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

        metadata = request.transaction.metadata or {}
        customer_segment = str(metadata.get("customer_segment", "standard"))
        device_trust = str(metadata.get("device_trust", "unverified"))
        account_age_days = int(metadata.get("account_age_days", 0))

        signals: list[str] = []
        if bool(metadata.get("new_device", False)):
            signals.append("NEW_DEVICE")
        if bool(metadata.get("geo_mismatch", False)):
            signals.append("GEO_MISMATCH")
        if bool(metadata.get("high_velocity", False)):
            signals.append("HIGH_VELOCITY")

        output = ContextAgentOutput(
            customer_segment=customer_segment,
            device_trust=device_trust,
            account_age_days=account_age_days,
            signals=signals,
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

        observe_agent_latency(settings.service_name, "context", latency_ms / 1000.0)
        logger.info(
            "agent_executed",
            extra={"execution_id": metadata.execution_id, "latency_ms": latency_ms},
        )
        return ContextAgentResponse(metadata=metadata, result=output)
