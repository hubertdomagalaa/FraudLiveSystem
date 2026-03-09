import logging
import time
from datetime import datetime, timezone
from uuid import uuid4

from app.config import PolicySettings
from app.services.rules import load_ruleset
from shared.observability import observe_agent_latency
from shared.schemas.agents import (
    ExecutionMetadata,
    PolicyAction,
    PolicyAgentOutput,
    PolicyAgentRequest,
    PolicyAgentResponse,
)

logger = logging.getLogger("agent-policy")
settings = PolicySettings()
ruleset = load_ruleset(settings.ruleset_path, settings.ruleset_version)


class PolicyAgent:
    async def execute(self, request: PolicyAgentRequest) -> PolicyAgentResponse:
        started_at = datetime.now(timezone.utc)
        start = time.perf_counter()

        risk_score = float(request.risk_score or 0.0)
        amount = float(request.transaction.amount)
        merchant_risk_score = float(request.transaction.merchant_risk_score or 0.0)
        prior_chargeback_flags = bool(request.transaction.prior_chargeback_flags)

        violations: list[str] = []
        triggered_rules: list[str] = []

        action = PolicyAction.ALLOW
        if risk_score >= ruleset.block_risk_score_gte:
            action = PolicyAction.BLOCK
            violations.append(ruleset.reason_block_risk)
            triggered_rules.append("risk_score_block")
        elif risk_score >= ruleset.review_risk_score_gte:
            action = PolicyAction.REVIEW
            violations.append(ruleset.reason_review_risk)
            triggered_rules.append("risk_score_review")

        if amount >= ruleset.review_amount_gte and action == PolicyAction.ALLOW:
            action = PolicyAction.REVIEW
            violations.append(ruleset.reason_review_amount)
            triggered_rules.append("high_amount_review")

        if merchant_risk_score >= ruleset.merchant_risk_review_gte and action == PolicyAction.ALLOW:
            action = PolicyAction.REVIEW
            violations.append(ruleset.reason_review_merchant_risk)
            triggered_rules.append("merchant_risk_review")

        if prior_chargeback_flags and amount >= ruleset.chargeback_review_amount_gte and action == PolicyAction.ALLOW:
            action = PolicyAction.REVIEW
            violations.append(ruleset.reason_review_chargeback_amount)
            triggered_rules.append("chargeback_amount_review")

        country_tier = request.context.country_risk_tier if request.context else "LOW"
        is_new_device = bool(request.context.is_new_device) if request.context else False
        if country_tier == "HIGH" and is_new_device:
            if risk_score >= ruleset.block_high_risk_country_new_device_risk_gte:
                action = PolicyAction.BLOCK
                violations.append(ruleset.reason_block_geo_device)
                triggered_rules.append("high_risk_country_new_device_block")
            elif action != PolicyAction.BLOCK:
                action = PolicyAction.REVIEW
                violations.append(ruleset.reason_review_geo_device)
                triggered_rules.append("high_risk_country_new_device_review")

        output = PolicyAgentOutput(
            ruleset_version=ruleset.ruleset_version,
            violations=violations,
            action=action,
            triggered_rules=triggered_rules,
            explanation=(
                f"Policy action={action.value} based on risk_score={risk_score:.2f}, amount={amount:.2f}, "
                f"merchant_risk_score={merchant_risk_score:.2f}, country_tier={country_tier}, new_device={is_new_device}"
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

        observe_agent_latency(settings.service_name, "policy", latency_ms / 1000.0)
        logger.info(
            "agent_executed",
            extra={"execution_id": metadata.execution_id, "latency_ms": latency_ms},
        )
        return PolicyAgentResponse(metadata=metadata, result=output)
