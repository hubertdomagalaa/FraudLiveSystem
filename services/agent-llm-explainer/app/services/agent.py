import logging
import time
from datetime import datetime, timezone
from uuid import uuid4

from app.config import LLMExplainerSettings
from shared.schemas.agents import ExecutionMetadata, LLMExplanationOutput, LLMExplanationRequest, LLMExplanationResponse

logger = logging.getLogger("agent-llm-explainer")
settings = LLMExplainerSettings()


class LLMExplanationAgent:
    async def execute(self, request: LLMExplanationRequest) -> LLMExplanationResponse:
        started_at = datetime.now(timezone.utc)
        start = time.perf_counter()

        output = LLMExplanationOutput(
            summary="Placeholder explanation.",
            rationale="Provider-agnostic structured explanation placeholder.",
            confidence=0.0,
            provider=settings.provider,
            model=settings.model,
            prompt_version=settings.prompt_version,
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
        return LLMExplanationResponse(metadata=metadata, result=output)
