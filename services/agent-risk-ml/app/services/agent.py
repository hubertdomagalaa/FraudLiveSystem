import logging
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

        merchant_risk_score = request.transaction.merchant_risk_score
        if merchant_risk_score is None and metadata.get("merchant_risk_score") is not None:
            merchant_risk_score = float(metadata["merchant_risk_score"])
        merchant_risk_score = 0.0 if merchant_risk_score is None else max(0.0, min(1.0, float(merchant_risk_score)))

        prior_chargeback_flags = request.transaction.prior_chargeback_flags
        if prior_chargeback_flags is None:
            prior_chargeback_flags = bool(metadata.get("prior_chargeback_flags", False))

        country_tier = request.context.country_risk_tier if request.context else "LOW"
        is_new_device = request.context.is_new_device if request.context else bool(metadata.get("new_device", False))

        score_breakdown: dict[str, float] = {
            "amount_scaled": min(amount / 20000.0, 0.25),
            "merchant_risk": merchant_risk_score * 0.45,
            "prior_chargeback": 0.2 if prior_chargeback_flags else 0.0,
            "country_risk": 0.12 if country_tier == "HIGH" else 0.06 if country_tier == "MEDIUM" else 0.0,
            "new_device": 0.1 if is_new_device else 0.0,
            "high_velocity": 0.08 if "HIGH_VELOCITY" in context_signals else 0.0,
            "geo_mismatch": 0.08 if "GEO_MISMATCH" in context_signals else 0.0,
            "unverified_device": 0.05 if str(device_trust).lower() != "trusted" else 0.0,
            "young_account": 0.05 if account_age_days <= 7 else 0.02 if account_age_days <= 30 else 0.0,
        }

        signal_score = sum(score_breakdown.values())
        risk_score = max(settings.default_risk_score, signal_score)
        risk_score = max(0.01, min(0.99, risk_score))

        risk_signals: list[str] = []
        if merchant_risk_score >= 0.8:
            risk_signals.append("MERCHANT_RISK_CRITICAL")
        elif merchant_risk_score >= 0.6:
            risk_signals.append("MERCHANT_RISK_ELEVATED")
        if prior_chargeback_flags:
            risk_signals.append("PRIOR_CHARGEBACK_HISTORY")
        if country_tier == "HIGH":
            risk_signals.append("COUNTRY_HIGH_RISK")
        if is_new_device:
            risk_signals.append("NEW_DEVICE")
        if "HIGH_VELOCITY" in context_signals:
            risk_signals.append("HIGH_VELOCITY")

        output = RiskMLAgentOutput(
            risk_score=round(risk_score, 4),
            model_version=artifact.model_version,
            feature_version=artifact.feature_version,
            features_used=sorted(["default_floor", *score_breakdown.keys()]),
            score_breakdown={
                "default_floor": round(float(settings.default_risk_score), 4),
                **{key: round(value, 4) for key, value in score_breakdown.items()},
            },
            risk_signals=risk_signals,
            explanation=(
                f"Risk derived from amount, merchant risk, device and historical signals. "
                f"merchant_risk={merchant_risk_score:.2f}, country_tier={country_tier}, new_device={is_new_device}"
            ),
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
