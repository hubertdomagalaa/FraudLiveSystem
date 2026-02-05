import logging
import time
from datetime import datetime, timezone
from uuid import uuid4

from app.config import RiskMLSettings
from shared.schemas.agents import ExecutionMetadata, RiskMLAgentOutput, RiskMLAgentRequest, RiskMLAgentResponse

logger = logging.getLogger("agent-risk-ml")
settings = RiskMLSettings()


class RiskMLAgent:
    async def execute(self, request: RiskMLAgentRequest) -> RiskMLAgentResponse:
        started_at = datetime.now(timezone.utc)
        start = time.perf_counter()

        output = RiskMLAgentOutput(
            risk_score=settings.default_risk_score,
            model_version=settings.model_version,
            feature_version="placeholder",
            features_used=[],
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
        return RiskMLAgentResponse(metadata=metadata, result=output)
