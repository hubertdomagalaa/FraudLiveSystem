from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.services.agent import RiskMLAgent
from shared.schemas.agents import ContextAgentOutput, RiskMLAgentRequest
from shared.schemas.transactions import TransactionStored


@pytest.mark.asyncio
async def test_risk_agent_increases_score_for_high_velocity() -> None:
    transaction = TransactionStored(
        transaction_id="tx-1",
        received_at=datetime.now(timezone.utc),
        amount=Decimal("7000.00"),
        currency="USD",
        merchant_id="merchant-1",
        card_id="card-1",
        timestamp=datetime.now(timezone.utc),
        metadata={},
    )
    context = ContextAgentOutput(
        customer_segment="standard",
        device_trust="unverified",
        account_age_days=1,
        signals=["HIGH_VELOCITY"],
    )

    response = await RiskMLAgent().execute(RiskMLAgentRequest(transaction=transaction, context=context, trace_id="c1"))

    assert response.result.risk_score >= 0.6
    assert response.result.model_version
