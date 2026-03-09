from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.services.agent import RiskMLAgent
from shared.schemas.agents import ContextAgentOutput, RiskMLAgentRequest
from shared.schemas.transactions import TransactionStored


@pytest.mark.asyncio
async def test_risk_agent_increases_score_for_high_risk_signals() -> None:
    agent = RiskMLAgent()

    baseline_tx = TransactionStored(
        transaction_id="tx-baseline",
        received_at=datetime.now(timezone.utc),
        amount=Decimal("200.00"),
        currency="USD",
        merchant_id="merchant-1",
        card_id="card-1",
        timestamp=datetime.now(timezone.utc),
        country="US",
        device_id="dev-safe",
        prior_chargeback_flags=False,
        merchant_risk_score=0.1,
        metadata={},
    )
    baseline_context = ContextAgentOutput(
        customer_segment="standard",
        device_trust="trusted",
        account_age_days=500,
        signals=[],
        country_code="US",
        country_risk_tier="LOW",
        is_new_device=False,
        has_prior_chargeback=False,
        merchant_risk_score=0.1,
    )

    elevated_tx = TransactionStored(
        transaction_id="tx-elevated",
        received_at=datetime.now(timezone.utc),
        amount=Decimal("7000.00"),
        currency="USD",
        merchant_id="merchant-1",
        card_id="card-1",
        timestamp=datetime.now(timezone.utc),
        country="NG",
        device_id="dev-risk",
        prior_chargeback_flags=True,
        merchant_risk_score=0.9,
        metadata={},
    )
    elevated_context = ContextAgentOutput(
        customer_segment="standard",
        device_trust="unverified",
        account_age_days=1,
        signals=["HIGH_VELOCITY", "NEW_DEVICE", "COUNTRY_HIGH_RISK"],
        country_code="NG",
        country_risk_tier="HIGH",
        is_new_device=True,
        has_prior_chargeback=True,
        merchant_risk_score=0.9,
    )

    baseline = await agent.execute(RiskMLAgentRequest(transaction=baseline_tx, context=baseline_context, trace_id="c1"))
    elevated = await agent.execute(RiskMLAgentRequest(transaction=elevated_tx, context=elevated_context, trace_id="c2"))

    assert elevated.result.risk_score > baseline.result.risk_score
    assert "MERCHANT_RISK_CRITICAL" in elevated.result.risk_signals
    assert "PRIOR_CHARGEBACK_HISTORY" in elevated.result.risk_signals
