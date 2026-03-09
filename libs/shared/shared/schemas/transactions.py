from datetime import datetime
from decimal import Decimal
from typing import Any, Dict

from pydantic import Field

from .base import BaseSchema


class TransactionIn(BaseSchema):
    amount: Decimal = Field(..., ge=0)
    currency: str = Field(..., min_length=3, max_length=3)
    merchant_id: str
    card_id: str
    timestamp: datetime
    country: str | None = Field(default=None, min_length=2, max_length=2)
    ip: str | None = None
    device_id: str | None = None
    prior_chargeback_flags: bool | None = None
    merchant_risk_score: float | None = Field(default=None, ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TransactionStored(TransactionIn):
    transaction_id: str
    received_at: datetime


class TransactionEvent(BaseSchema):
    event_id: str
    transaction_id: str
    occurred_at: datetime
    payload: TransactionStored
