from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.services.agent import PolicyAgent
from shared.schemas.agents import ContextAgentOutput, PolicyAction, PolicyAgentRequest
from shared.schemas.transactions import TransactionStored


@pytest.mark.asyncio
async def test_policy_agent_routes_geo_device_and_chargeback_signals() -> None:
    agent = PolicyAgent()

    transaction = TransactionStored(
        transaction_id="tx-1",
        received_at=datetime.now(timezone.utc),
        amount=Decimal("2500.00"),
        currency="USD",
        merchant_id="merchant-1",
        card_id="card-1",
        timestamp=datetime.now(timezone.utc),
        country="NG",
        device_id="dev-risk",
        prior_chargeback_flags=True,
        merchant_risk_score=0.8,
        metadata={},
    )
    context = ContextAgentOutput(
        customer_segment="standard",
        device_trust="unverified",
        account_age_days=10,
        signals=["NEW_DEVICE", "COUNTRY_HIGH_RISK", "PRIOR_CHARGEBACK_HISTORY"],
        country_code="NG",
        country_risk_tier="HIGH",
        is_new_device=True,
        has_prior_chargeback=True,
        merchant_risk_score=0.8,
    )

    review = await agent.execute(PolicyAgentRequest(transaction=transaction, context=context, risk_score=0.72, trace_id="c1"))
    block = await agent.execute(PolicyAgentRequest(transaction=transaction, context=context, risk_score=0.9, trace_id="c2"))

    assert review.result.action == PolicyAction.REVIEW
    assert any(code in review.result.violations for code in ["HIGH_RISK_COUNTRY_NEW_DEVICE", "RISK_SCORE_HIGH"])
    assert block.result.action == PolicyAction.BLOCK
    assert "HIGH_RISK_COUNTRY_NEW_DEVICE_CRITICAL" in block.result.violations
