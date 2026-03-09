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

HIGH_RISK_COUNTRIES = {"NG", "RU", "KP", "IR"}
MEDIUM_RISK_COUNTRIES = {"UA", "PK", "ID"}


class ContextAgent:
    async def execute(self, request: ContextAgentRequest) -> ContextAgentResponse:
        started_at = datetime.now(timezone.utc)
        start = time.perf_counter()

        transaction = request.transaction
        metadata = transaction.metadata or {}

        customer_segment = str(metadata.get("customer_segment", "standard"))
        device_trust = str(metadata.get("device_trust", "unverified"))
        account_age_days = int(metadata.get("account_age_days", 0))

        country_code = (transaction.country or str(metadata.get("country", ""))).strip().upper() or None
        merchant_risk_score = transaction.merchant_risk_score
        if merchant_risk_score is None and metadata.get("merchant_risk_score") is not None:
            merchant_risk_score = float(metadata["merchant_risk_score"])

        has_prior_chargeback = bool(
            transaction.prior_chargeback_flags
            if transaction.prior_chargeback_flags is not None
            else metadata.get("prior_chargeback_flags", False)
        )

        known_devices = metadata.get("known_device_ids")
        if isinstance(known_devices, list) and transaction.device_id:
            is_new_device = transaction.device_id not in {str(item) for item in known_devices}
        else:
            is_new_device = bool(metadata.get("new_device", False))

        country_risk_tier = "LOW"
        if country_code in HIGH_RISK_COUNTRIES:
            country_risk_tier = "HIGH"
        elif country_code in MEDIUM_RISK_COUNTRIES:
            country_risk_tier = "MEDIUM"

        signals: list[str] = []
        signal_details: list[dict[str, str]] = []

        if is_new_device:
            signals.append("NEW_DEVICE")
            signal_details.append({"signal": "NEW_DEVICE", "severity": "MEDIUM", "reason": "first_seen_device"})
        if bool(metadata.get("geo_mismatch", False)):
            signals.append("GEO_MISMATCH")
            signal_details.append({"signal": "GEO_MISMATCH", "severity": "HIGH", "reason": "device_ip_country_mismatch"})
        if bool(metadata.get("high_velocity", False)):
            signals.append("HIGH_VELOCITY")
            signal_details.append({"signal": "HIGH_VELOCITY", "severity": "HIGH", "reason": "short_window_tx_spike"})
        if has_prior_chargeback:
            signals.append("PRIOR_CHARGEBACK_HISTORY")
            signal_details.append({"signal": "PRIOR_CHARGEBACK_HISTORY", "severity": "HIGH", "reason": "known_chargeback_history"})
        if country_risk_tier == "HIGH":
            signals.append("COUNTRY_HIGH_RISK")
            signal_details.append({"signal": "COUNTRY_HIGH_RISK", "severity": "HIGH", "reason": "country_in_high_risk_list"})
        if merchant_risk_score is not None and merchant_risk_score >= 0.8:
            signals.append("MERCHANT_RISK_HIGH")
            signal_details.append({"signal": "MERCHANT_RISK_HIGH", "severity": "HIGH", "reason": "merchant_risk_score_gte_0_8"})

        output = ContextAgentOutput(
            customer_segment=customer_segment,
            device_trust=device_trust,
            account_age_days=account_age_days,
            signals=signals,
            signal_details=signal_details,
            country_code=country_code,
            country_risk_tier=country_risk_tier,
            is_new_device=is_new_device,
            has_prior_chargeback=has_prior_chargeback,
            merchant_risk_score=merchant_risk_score,
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
