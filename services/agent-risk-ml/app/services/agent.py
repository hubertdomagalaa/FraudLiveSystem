import logging
import math
import time
from datetime import datetime, timezone
from uuid import uuid4

from app.config import RiskMLSettings
from app.services.model_registry import load_model_artifact
from shared.observability import observe_agent_latency
from shared.schemas.agents import ExecutionMetadata, RiskMLAgentOutput, RiskMLAgentRequest, RiskMLAgentResponse

logger = logging.getLogger("agent-risk-ml")
settings = RiskMLSettings()
artifact = load_model_artifact(settings.model_artifact_path, settings.model_version)


class RiskMLAgent:
    async def execute(self, request: RiskMLAgentRequest) -> RiskMLAgentResponse:
        started_at = datetime.now(timezone.utc)
        start = time.perf_counter()

        amount = float(request.transaction.amount or 0.0)
        metadata = request.transaction.metadata or {}
        context_signals = request.context.signals if request.context else []
        device_trust = request.context.device_trust if request.context else str(metadata.get("device_trust", "unverified"))
        account_age_days = request.context.account_age_days if request.context else int(metadata.get("account_age_days", 0))

        features = {
            "amount_scaled": min(amount / 10000.0, 2.0),
            "new_device": 1.0 if bool(metadata.get("new_device", False)) else 0.0,
            "geo_mismatch": 1.0 if bool(metadata.get("geo_mismatch", False)) else 0.0,
            "high_velocity": 1.0 if "HIGH_VELOCITY" in context_signals else 0.0,
            "device_trusted": 1.0 if str(device_trust).lower() == "trusted" else 0.0,
            "account_age_years": min(max(account_age_days / 365.0, 0.0), 10.0),
        }

        logit = artifact.intercept
        for name, value in features.items():
            logit += artifact.weights.get(name, 0.0) * value

        score = 1.0 / (1.0 + math.exp(-logit))
        base_score = max(0.01, min(0.99, score))
        base_score = (base_score + settings.default_risk_score) / 2.0

        output = RiskMLAgentOutput(
            risk_score=round(base_score, 4),
            model_version=artifact.model_version,
            feature_version=artifact.feature_version,
            features_used=sorted(features.keys()),
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

        observe_agent_latency(settings.service_name, "risk", latency_ms / 1000.0)
        logger.info(
            "agent_executed",
            extra={"execution_id": metadata.execution_id, "latency_ms": latency_ms},
        )
        return RiskMLAgentResponse(metadata=metadata, result=output)
