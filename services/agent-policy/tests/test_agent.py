from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.services.agent import PolicyAgent
from shared.schemas.agents import PolicyAction, PolicyAgentRequest
from shared.schemas.transactions import TransactionStored


@pytest.mark.asyncio
async def test_policy_agent_routes_high_risk_to_review_or_block() -> None:
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

    review = await PolicyAgent().execute(PolicyAgentRequest(transaction=transaction, risk_score=0.65, trace_id="c1"))
    block = await PolicyAgent().execute(PolicyAgentRequest(transaction=transaction, risk_score=0.95, trace_id="c1"))

    assert review.result.action == PolicyAction.REVIEW
    assert block.result.action == PolicyAction.BLOCK
