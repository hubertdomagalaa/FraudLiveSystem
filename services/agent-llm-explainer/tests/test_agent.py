from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.services.agent import LLMExplanationAgent
from shared.schemas.agents import LLMExplanationRequest
from shared.schemas.transactions import TransactionStored


@pytest.mark.asyncio
async def test_explainer_returns_structured_rationale() -> None:
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

    response = await LLMExplanationAgent().execute(
        LLMExplanationRequest(
            transaction=transaction,
            risk_score=0.76,
            policy_action="REVIEW",
            reason_codes=["RISK_SCORE_HIGH"],
            trace_id="case-1",
        )
    )

    assert "Risk score" in response.result.summary
    assert response.result.confidence > 0
    assert response.result.model
