import logging
import time
from datetime import datetime, timezone
from uuid import uuid4

from app.config import LLMExplainerSettings
from app.services.providers import DeterministicProvider, resolve_provider
from shared.observability import observe_agent_latency
from shared.schemas.agents import ExecutionMetadata, LLMExplanationRequest, LLMExplanationResponse

logger = logging.getLogger("agent-llm-explainer")
settings = LLMExplainerSettings()


class LLMExplanationAgent:
    async def execute(self, request: LLMExplanationRequest) -> LLMExplanationResponse:
        started_at = datetime.now(timezone.utc)
        start = time.perf_counter()

        provider = resolve_provider(settings.provider)
        try:
            output = provider.generate(
                request,
                model=settings.model,
                prompt_version=settings.prompt_version,
            ).output
        except Exception:
            logger.exception("explainer_provider_failed", extra={"provider": settings.provider})
            output = DeterministicProvider().generate(
                request,
                model=settings.model,
                prompt_version=settings.prompt_version,
            ).output

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

        observe_agent_latency(settings.service_name, "explain", latency_ms / 1000.0)
        logger.info(
            "agent_executed",
            extra={"execution_id": metadata.execution_id, "latency_ms": latency_ms},
        )
        return LLMExplanationResponse(metadata=metadata, result=output)
