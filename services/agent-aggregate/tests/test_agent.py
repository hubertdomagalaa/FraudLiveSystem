from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.services.agent import AggregateAgent
from shared.schemas.agents import (
    AggregateAgentRequest,
    ContextAgentOutput,
    LLMExplanationOutput,
    PolicyAction,
    PolicyAgentOutput,
    RiskMLAgentOutput,
)
from shared.schemas.transactions import TransactionStored


@pytest.mark.asyncio
async def test_aggregate_marks_review_as_human_required() -> None:
    transaction = TransactionStored(
        transaction_id="tx-1",
        received_at=datetime.now(timezone.utc),
        amount=Decimal("1200.50"),
        currency="USD",
        merchant_id="merchant-1",
        card_id="card-1",
        timestamp=datetime.now(timezone.utc),
        metadata={},
    )
    response = await AggregateAgent().execute(
        AggregateAgentRequest(
            transaction=transaction,
            context=ContextAgentOutput(
                customer_segment="standard",
                device_trust="unverified",
                account_age_days=1,
                signals=["NEW_DEVICE"],
                country_code="NG",
                country_risk_tier="HIGH",
                is_new_device=True,
                has_prior_chargeback=True,
                merchant_risk_score=0.8,
            ),
            risk=RiskMLAgentOutput(
                risk_score=0.7,
                model_version="v1",
                feature_version="rules-v1",
                features_used=["amount"],
                risk_signals=["MERCHANT_RISK_ELEVATED"],
                score_breakdown={"merchant_risk": 0.3},
                explanation="risk explanation",
            ),
            policy=PolicyAgentOutput(
                ruleset_version="v2",
                violations=["RISK_SCORE_HIGH", "HIGH_RISK_COUNTRY_NEW_DEVICE"],
                action=PolicyAction.REVIEW,
                triggered_rules=["risk_score_review", "high_risk_country_new_device_review"],
                explanation="policy explanation",
            ),
            explain=LLMExplanationOutput(
                summary="summary",
                rationale="rationale",
                confidence=0.8,
                provider="stub",
                model="stub",
                prompt_version="v1",
            ),
            trace_id="case-1",
        )
    )

    assert response.result.recommendation == "REVIEW"
    assert response.result.requires_human_review is True
    assert "HUMAN_REVIEW_REQUIRED" in response.result.reason_codes
    assert response.result.risk_score == 0.7
    assert "NEW_DEVICE" in response.result.signals
    assert "RISK_SCORE_HIGH" in response.result.policy_violations
