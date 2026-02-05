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
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TransactionStored(TransactionIn):
    transaction_id: str
    received_at: datetime


class TransactionEvent(BaseSchema):
    event_id: str
    transaction_id: str
    occurred_at: datetime
    payload: TransactionStored
