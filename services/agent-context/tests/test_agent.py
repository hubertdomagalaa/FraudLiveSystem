from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.services.agent import ContextAgent
from shared.schemas.agents import ContextAgentRequest
from shared.schemas.transactions import TransactionStored


@pytest.mark.asyncio
async def test_context_agent_extracts_signals() -> None:
    transaction = TransactionStored(
        transaction_id="tx-1",
        received_at=datetime.now(timezone.utc),
        amount=Decimal("1200.50"),
        currency="USD",
        merchant_id="merchant-1",
        card_id="card-1",
        timestamp=datetime.now(timezone.utc),
        metadata={
            "customer_segment": "vip",
            "device_trust": "trusted",
            "account_age_days": 42,
            "new_device": True,
            "high_velocity": True,
        },
    )

    response = await ContextAgent().execute(ContextAgentRequest(transaction=transaction, trace_id="case-1"))

    assert response.result.customer_segment == "vip"
    assert response.result.device_trust == "trusted"
    assert response.result.account_age_days == 42
    assert "NEW_DEVICE" in response.result.signals
    assert "HIGH_VELOCITY" in response.result.signals
